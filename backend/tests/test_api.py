import sqlite3

from fastapi.testclient import TestClient

import main


client = TestClient(main.app)


def setup_function():
    main._request_times.clear()


def sample_source(**overrides):
    source = {
        "id": "chunk-123",
        "title": "Bharatiya Nyaya Sanhita",
        "content": "A legal passage.",
        "source": "BNS2023.pdf",
        "page": 12,
        "section": "103",
        "act_name": "Bharatiya Nyaya Sanhita, 2023",
        "source_type": "statute",
        "jurisdiction": "India",
        "publication_date": None,
        "effective_date": None,
        "verification_status": "needs_review",
        "source_url": "https://example.gov.in/act",
    }
    source.update(overrides)
    return source


def test_query_returns_grounded_answer_and_actual_source_metadata(monkeypatch):
    monkeypatch.setattr(
        main.retrieval,
        "search_legal_sources",
        lambda query, limit: [sample_source()],
    )
    received = {}

    def explain(**kwargs):
        received.update(kwargs)
        return "The retrieved passage says this."

    monkeypatch.setattr(main.ai_services, "simplify_legal_language", explain)
    response = client.post(
        "/api/legal/query",
        json={
            "question": "Explain section 103",
            "language": "Hindi",
            "legal_timeframe": "2024",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "The retrieved passage says this."
    assert data["retrieval_status"] == "sources_found"
    assert data["language"] == "Hindi"
    assert data["citations"][0]["source_id"] == "chunk-123"
    assert data["citations"][0]["section"] == "103"
    assert data["citations"][0]["act_name"] == "Bharatiya Nyaya Sanhita, 2023"
    assert data["citations"][0]["source_type"] == "statute"
    assert data["citations"][0]["jurisdiction"] == "India"
    assert data["citations"][0]["page"] == 12
    assert data["citations"][0]["verification_status"] == "needs_review"
    assert any("timeframe" in item.lower() for item in data["limitations"])
    assert received["legal_context"] == "Requested legal timeframe: 2024"


def test_query_redacts_identifiers_before_retrieval_and_ai(monkeypatch):
    observed = {}
    question = (
        "Contact alice@example.com or 9876543210; "
        "PAN ABCDE1234F and ID 1234 5678 9012"
    )

    def search(query, limit):
        observed["query"] = query
        return [sample_source()]

    def explain(**kwargs):
        observed["ai_question"] = kwargs["question"]
        return "Grounded answer"

    monkeypatch.setattr(main.retrieval, "search_legal_sources", search)
    monkeypatch.setattr(main.ai_services, "simplify_legal_language", explain)
    response = client.post(
        "/api/legal/query",
        json={"question": question, "language": "English"},
    )

    assert response.status_code == 200
    assert "alice@example.com" not in observed["query"]
    assert "9876543210" not in observed["query"]
    assert "ABCDE1234F" not in observed["query"]
    assert "1234 5678 9012" not in observed["query"]
    assert observed["ai_question"] == observed["query"]


def test_no_sources_returns_explicit_localized_answer_without_calling_ai(
    monkeypatch,
):
    monkeypatch.setattr(main.retrieval, "search_legal_sources", lambda query, limit: [])

    def unexpected_ai_call(**kwargs):
        raise AssertionError("AI must not answer without retrieved evidence.")

    monkeypatch.setattr(
        main.ai_services,
        "simplify_legal_language",
        unexpected_ai_call,
    )
    response = client.post(
        "/api/legal/query",
        json={
            "question": "उपलब्ध कायदेशीर तरतूद जामिनाबद्दल काय सांगते?",
            "language": "Marathi",
        },
    )

    assert response.status_code == 200
    assert response.json()["retrieval_status"] == "no_sources"
    assert response.json()["citations"] == []
    assert "उपलब्ध संग्रहात" in response.json()["answer"]


def test_missing_corpus_text_is_disclosed_without_ai_fallback(monkeypatch):
    monkeypatch.setattr(
        main.retrieval,
        "search_legal_sources",
        lambda query, limit: [],
    )
    response = client.post(
        "/api/legal/query",
        json={
            "question": (
                "What is the difference between murder and culpable homicide?"
            ),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["retrieval_status"] == "no_sources"
    assert data["citations"] == []
    assert "corpus does not contain" in data["answer"]


def test_retrieval_failure_is_not_reported_as_empty_results(monkeypatch):
    def fail_search(query, limit):
        raise main.retrieval.RetrievalUnavailable()

    monkeypatch.setattr(main.retrieval, "search_legal_sources", fail_search)
    response = client.post(
        "/api/legal/query",
        json={"question": "What does this law say?"},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "RETRIEVAL_UNAVAILABLE"


def test_missing_local_database_returns_service_unavailable(monkeypatch):
    def fail_database(query, limit):
        raise main.retrieval.RetrievalUnavailable(
            "database unavailable"
        )

    monkeypatch.setattr(main.retrieval, "search_legal_sources", fail_database)
    response = client.post(
        "/api/legal/query",
        json={"question": "What does this law say?"},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "RETRIEVAL_UNAVAILABLE"


def test_missing_ai_configuration_returns_service_error(monkeypatch):
    monkeypatch.setattr(
        main.retrieval,
        "search_legal_sources",
        lambda query, limit: [sample_source()],
    )

    def fail_ai(**kwargs):
        raise main.ai_services.AIServiceConfigurationError()

    monkeypatch.setattr(main.ai_services, "simplify_legal_language", fail_ai)
    response = client.post(
        "/api/legal/query",
        json={"question": "What does this law say?"},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "AI_NOT_CONFIGURED"


def test_ai_timeout_returns_gateway_timeout(monkeypatch):
    monkeypatch.setattr(
        main.retrieval,
        "search_legal_sources",
        lambda query, limit: [sample_source()],
    )
    monkeypatch.setattr(
        main.ai_services,
        "simplify_legal_language",
        lambda **kwargs: (_ for _ in ()).throw(
            main.ai_services.AIServiceTimeoutError()
        ),
    )
    response = client.post(
        "/api/legal/query",
        json={"question": "What does this law say?"},
    )
    assert response.status_code == 504
    assert response.json()["detail"]["code"] == "AI_TIMEOUT"


def test_unsupported_language_and_blank_question_are_rejected():
    unsupported = client.post(
        "/api/legal/query",
        json={"question": "A valid question", "language": "Gujarati"},
    )
    blank = client.post("/api/legal/query", json={"question": "   "})
    assert unsupported.status_code == 422
    assert blank.status_code == 422


def test_oversized_request_body_is_rejected():
    response = client.post(
        "/api/legal/query",
        content='{"question":"' + ("x" * main.MAX_REQUEST_BYTES) + '"}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "REQUEST_TOO_LARGE"


def test_unsafe_source_url_is_not_returned_as_a_clickable_citation(monkeypatch):
    monkeypatch.setattr(
        main.retrieval,
        "search_legal_sources",
        lambda query, limit: [
            sample_source(source_url="javascript:alert(1)")
        ],
    )
    monkeypatch.setattr(
        main.ai_services,
        "simplify_legal_language",
        lambda **kwargs: "Grounded answer",
    )
    response = client.post(
        "/api/legal/query",
        json={"question": "What does this law say?"},
    )
    assert response.status_code == 200
    assert response.json()["citations"][0]["source_url"] is None


def test_health_reports_sqlite_and_ai_state(monkeypatch):
    monkeypatch.setattr(main.database, "check_database", lambda: None)
    monkeypatch.setattr(main.ai_services, "client", object())
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["services"] == {
        "sqlite": "available",
        "ai": "configured",
    }
    assert response.json()["status"] == "ok"


def test_health_is_degraded_but_available_when_ai_is_unconfigured(monkeypatch):
    monkeypatch.setattr(main.database, "check_database", lambda: None)
    monkeypatch.setattr(main.ai_services, "client", None)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["services"] == {
        "sqlite": "available",
        "ai": "unconfigured",
    }


def test_health_reports_sqlite_failure_without_exposing_exception(monkeypatch, caplog):
    secret_marker = "private database path marker"

    def fail_database():
        raise sqlite3.OperationalError(secret_marker)

    monkeypatch.setattr(main.database, "check_database", fail_database)
    monkeypatch.setattr(main.ai_services, "client", object())
    response = client.get("/api/health")
    assert response.status_code == 503
    assert (
        response.json()["detail"]["database_diagnostic"]["code"]
        == "SQLITE_UNAVAILABLE"
    )
    assert secret_marker not in response.text
    assert secret_marker not in caplog.text
