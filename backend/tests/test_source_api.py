from fastapi.testclient import TestClient

import main


client = TestClient(main.app)


def setup_function():
    main._request_times.clear()


def test_source_list_returns_database_items_and_caps_pagination(monkeypatch):
    observed = {}

    def search_source_records(**kwargs):
        observed.update(kwargs)
        return (
            [
                {
                    "id": "source-1",
                    "title": "BNS record",
                    "content": "Real database text",
                    "source": "BNS2023.pdf",
                    "verification_status": "needs_review",
                }
            ],
            1,
        )

    monkeypatch.setattr(
        main.retrieval,
        "search_source_records",
        search_source_records,
    )
    response = client.get(
        "/api/legal/sources",
        params={
            "query": "section 103",
            "jurisdiction": "Maharashtra",
            "limit": 500,
            "offset": -4,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "source-1"
    assert data["items"][0]["content"] == "Real database text"
    assert data["limit"] == 50
    assert data["offset"] == 0
    assert observed["query"] == "section 103"
    assert observed["jurisdiction"] == "Maharashtra"


def test_source_list_reports_database_errors(monkeypatch):
    monkeypatch.setattr(
        main.retrieval,
        "search_source_records",
        lambda **kwargs: (_ for _ in ()).throw(
            main.retrieval.RetrievalUnavailable()
        ),
    )
    response = client.get("/api/legal/sources")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "RETRIEVAL_UNAVAILABLE"


def test_source_detail_returns_actual_record_or_not_found(monkeypatch):
    monkeypatch.setattr(
        main.retrieval,
        "get_source_record",
        lambda source_id: {"id": source_id, "title": "Stored source"},
    )
    found = client.get("/api/legal/sources/record-42")
    assert found.status_code == 200
    assert found.json()["id"] == "record-42"

    monkeypatch.setattr(main.retrieval, "get_source_record", lambda _: None)
    missing = client.get("/api/legal/sources/no-such-record")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "SOURCE_NOT_FOUND"


def test_source_endpoints_use_persistent_sqlite_records():
    main.database.upsert_legal_sources(
        [
            {
                "id": "local-bns-103",
                "title": "Bharatiya Nyaya Sanhita",
                "content": "Section 103 explains this legal provision.",
                "source": "BNS2023.pdf",
                "page": 12,
                "section": "103",
                "verification_status": "needs_review",
            }
        ]
    )

    listed = client.get("/api/legal/sources", params={"query": "section 103"})
    detail = client.get("/api/legal/sources/local-bns-103")

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == "local-bns-103"
    assert listed.json()["items"][0]["page"] == 12
    assert detail.status_code == 200
    assert detail.json()["content"] == "Section 103 explains this legal provision."
