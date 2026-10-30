from fastapi.testclient import TestClient

import main


client = TestClient(main.app)


def setup_function():
    main._pending_documents.clear()
    main._request_times.clear()


def make_notice():
    return (
        "Notice dated 2026-01-15. Please reply within the stated period. "
        "Contact alice@example.com or 9876543210 for details."
    ).encode()


def test_document_preview_redacts_pii_and_extracts_explicit_dates():
    response = client.post(
        "/api/documents/preview",
        files={
            "file": (
                "notice.txt",
                make_notice(),
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["redaction_count"] == 2
    assert "alice@example.com" in data["original_preview"]
    assert "alice@example.com" not in data["redacted_preview"]
    assert data["dates"][0]["date"] == "2026-01-15"
    assert data["dates"][0]["requires_confirmation"] is True
    assert "alice@example.com" not in data["dates"][0]["context"]
    assert data["document_id"] in main._pending_documents


def test_document_preview_rejects_mime_mismatch_and_clears_explicitly():
    response = client.post(
        "/api/documents/preview",
        files={"file": ("notice.txt", make_notice(), "application/pdf")},
    )
    assert response.status_code == 415

    valid = client.post(
        "/api/documents/preview",
        files={"file": ("notice.txt", make_notice(), "text/plain")},
    )
    document_id = valid.json()["document_id"]
    cleared = client.delete(f"/api/documents/{document_id}")
    assert cleared.status_code == 200
    assert cleared.json()["deleted"] is True
    assert document_id not in main._pending_documents


def test_document_analysis_requires_external_ai_consent():
    preview = client.post(
        "/api/documents/preview",
        files={"file": ("notice.txt", make_notice(), "text/plain")},
    )
    response = client.post(
        "/api/documents/analyze",
        json={
            "document_id": preview.json()["document_id"],
            "language": "English",
            "confirm_external_ai": False,
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "AI_PROCESSING_NOT_CONFIRMED"


def test_document_analysis_returns_real_analysis_dates_and_source_metadata(
    monkeypatch,
):
    preview = client.post(
        "/api/documents/preview",
        files={"file": ("notice.txt", make_notice(), "text/plain")},
    )
    captured = {}
    source = {
        "id": "source-123",
        "title": "Legal reference",
        "content": "Relevant legal passage.",
        "source": "legal-reference.pdf",
        "page": 2,
        "section": "8",
        "verification_status": "needs_review",
    }

    def search(query, limit):
        assert "alice@example.com" not in query
        assert "9876543210" not in query
        return [source]

    def analyze(text, sources, language, date_reviews):
        captured["text"] = text
        captured["sources"] = sources
        captured["language"] = language
        captured["date_reviews"] = date_reviews
        return {
            "overview": "A notice with a stated date.",
            "important_clauses": [],
            "legal_terms": [],
            "obligations": ["Reply within the stated period."],
            "rights_or_remedies": [],
            "questions_to_clarify": [],
            "limitations": ["The deadline requires review."],
        }

    monkeypatch.setattr(main.retrieval, "search_legal_sources", search)
    monkeypatch.setattr(main.ai_services, "analyze_document", analyze)
    response = client.post(
        "/api/documents/analyze",
        json={
            "document_id": preview.json()["document_id"],
            "language": "Hindi",
            "confirm_external_ai": True,
            "date_reviews": [
                {
                    "source_text": "2026-01-15",
                    "date": "2026-01-20",
                    "confirmed": True,
                }
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["analysis"]["overview"] == "A notice with a stated date."
    assert result["dates"][0]["date"] == "2026-01-20"
    assert result["dates"][0]["confirmed_by_user"] is True
    assert result["citations"][0]["source_id"] == "source-123"
    assert "alice@example.com" not in captured["text"]
    assert "alice@example.com" not in captured["sources"][0]["content"]
    assert captured["language"] == "Hindi"
    assert captured["date_reviews"][0]["date"] == "2026-01-20"
    assert captured["date_reviews"][0]["confirmed_by_user"] is True
    assert "alice@example.com" not in captured["date_reviews"][0]["context"]
    assert preview.json()["document_id"] not in main._pending_documents


def test_document_analysis_requires_review_of_detected_dates(monkeypatch):
    preview = client.post(
        "/api/documents/preview",
        files={"file": ("notice.txt", make_notice(), "text/plain")},
    )
    monkeypatch.setattr(
        main.retrieval,
        "search_legal_sources",
        lambda query, limit: (_ for _ in ()).throw(
            AssertionError("Retrieval must not happen before date review.")
        ),
    )
    response = client.post(
        "/api/documents/analyze",
        json={
            "document_id": preview.json()["document_id"],
            "language": "English",
            "confirm_external_ai": True,
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "DATE_REVIEW_REQUIRED"


def test_document_analysis_surfaces_database_failure_without_ai_call(
    monkeypatch,
):
    preview = client.post(
        "/api/documents/preview",
        files={"file": ("notice.txt", make_notice(), "text/plain")},
    )
    monkeypatch.setattr(
        main.retrieval,
        "search_legal_sources",
        lambda query, limit: (_ for _ in ()).throw(
            main.retrieval.RetrievalUnavailable()
        ),
    )
    response = client.post(
        "/api/documents/analyze",
        json={
            "document_id": preview.json()["document_id"],
            "language": "English",
            "confirm_external_ai": True,
            "date_reviews": [
                {
                    "source_text": "2026-01-15",
                    "date": "2026-01-15",
                    "confirmed": True,
                }
            ],
        },
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "RETRIEVAL_UNAVAILABLE"
