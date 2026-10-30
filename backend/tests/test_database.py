import sqlite3

import pytest

import database
import retrieval


def test_initialization_creates_persistent_tables_and_indexes(tmp_path, monkeypatch):
    path = tmp_path / "store" / "justifi.db"
    monkeypatch.setattr(database, "DB_PATH", path)

    initialized_path = database.initialize_database()

    assert initialized_path == path
    assert path.is_file()
    with database.connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        indexes = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            )
        }
    assert {"legal_sources", "users", "chats", "feedback"} <= tables
    assert "idx_legal_sources_title" in indexes
    assert "idx_legal_sources_verification" in indexes


def test_legal_source_create_read_update_delete_and_persistence(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "justifi.db"
    monkeypatch.setattr(database, "DB_PATH", path)
    record = {
        "_id": "chunk-1",
        "title": "BNS reference",
        "content": "Section 10 legal content",
        "source": "BNS2023.pdf",
        "source_file": "BNS2023.pdf",
        "page": 3,
        "section": "10",
        "verification_status": "needs_review",
        "source_url": "https://example.gov.in/law",
        "extra_note": "Preserved metadata",
    }

    assert database.upsert_legal_sources([record]) == 1
    stored = database.get_legal_source("chunk-1")
    assert stored["id"] == "chunk-1"
    assert stored["page"] == 3
    assert stored["extra_note"] == "Preserved metadata"

    assert database.update_legal_source(
        "chunk-1",
        {"verification_status": "verified", "page": 4},
    )
    updated = database.get_legal_source("chunk-1")
    assert updated["verification_status"] == "verified"
    assert updated["page"] == 4
    assert updated["extra_note"] == "Preserved metadata"

    database._initialized_paths.clear()
    assert database.get_legal_source("chunk-1")["content"] == record["content"]

    assert database.delete_legal_source("chunk-1")
    assert database.get_legal_source("chunk-1") is None
    assert not database.delete_legal_source("chunk-1")


def test_upsert_updates_existing_record_without_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "justifi.db")
    database.upsert_legal_sources(
        [{"id": "same-id", "title": "First", "content": "Old passage"}]
    )
    database.upsert_legal_sources(
        [{"id": "same-id", "title": "Updated", "content": "New passage"}]
    )

    assert database.get_legal_source("same-id")["content"] == "New passage"
    with database.connection() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM legal_sources WHERE id = ?",
            ("same-id",),
        ).fetchone()[0] == 1


def test_database_rejects_nonpersistent_memory_path(monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", ":memory:")
    with pytest.raises(ValueError, match="persistent SQLite"):
        database.initialize_database()


def test_connection_rolls_back_failed_transaction(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "justifi.db")
    database.initialize_database()
    with pytest.raises(sqlite3.IntegrityError):
        with database.connection() as conn:
            conn.execute(
                "INSERT INTO users (id, data_json) VALUES (?, ?)",
                ("user-1", "{}"),
            )
            conn.execute(
                "INSERT INTO users (id, data_json) VALUES (?, ?)",
                ("user-1", "{}"),
            )
    with database.connection() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM users WHERE id = ?",
            ("user-1",),
        ).fetchone()[0] == 0


def test_source_search_filters_and_detail_preserve_metadata(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "justifi.db")
    database.upsert_legal_sources(
        [
            {
                "id": "bns-1",
                "title": "Bharatiya Nyaya Sanhita",
                "content": "Section 103 describes a legal provision.",
                "source": "BNS2023.pdf",
                "page": 12,
                "section": "103",
                "jurisdiction": "India",
                "verification_status": "needs_review",
                "source_url": "https://example.gov.in/bns",
            },
            {
                "id": "bnss-1",
                "title": "Bharatiya Nagarik Suraksha Sanhita",
                "content": "Procedure related text.",
                "source": "BNSS.pdf",
                "page": 4,
                "jurisdiction": "India",
                "verification_status": "unverified",
            },
        ]
    )

    matches = retrieval.search_legal_sources("section 103", limit=5)
    assert [item["id"] for item in matches] == ["bns-1"]
    assert matches[0]["page"] == 12
    assert matches[0]["source"] == "BNS2023.pdf"

    items, total = retrieval.search_source_records(
        query="Bharatiya",
        verification_status="needs_review",
        jurisdiction="india",
        limit=10,
    )
    assert total == 1
    assert items[0]["id"] == "bns-1"
    assert items[0]["source_url"] == "https://example.gov.in/bns"
    assert retrieval.get_source_record("bnss-1")["page"] == 4


def test_homicide_retrieval_uses_bns_definitions_not_bnss_procedure(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "justifi.db")
    database.upsert_legal_sources(
        [
            {
                "id": "bns-100",
                "title": "Bharatiya Nyaya Sanhita, 2023",
                "act_name": "Bharatiya Nyaya Sanhita, 2023",
                "source_type": "statute",
                "jurisdiction": "India",
                "section": "100. Culpable homicide",
                "content": (
                    "100. Whoever causes death with the required intention "
                    "or knowledge commits culpable homicide."
                ),
                "source": "BNS2023.pdf",
                "page": 121,
                "verification_status": "needs_review",
            },
            {
                "id": "bns-101",
                "title": "Bharatiya Nyaya Sanhita, 2023",
                "act_name": "Bharatiya Nyaya Sanhita, 2023",
                "source_type": "statute",
                "jurisdiction": "India",
                "section": "101. Murder",
                "content": (
                    "101. Except in the stated exceptions, culpable "
                    "homicide is murder when the specified conditions apply."
                ),
                "source": "BNS2023.pdf",
                "page": 122,
                "verification_status": "needs_review",
            },
            {
                "id": "bnss-103",
                "title": "Bharatiya Nagarik Suraksha Sanhita, 2023",
                "act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
                "source_type": "statute",
                "jurisdiction": "India",
                "section": "103. Search warrant provision",
                "content": "103. Procedural search-warrant provision.",
                "source": "BNSS.pdf",
                "page": 76,
                "verification_status": "needs_review",
            },
        ]
    )

    matches = retrieval.search_legal_sources(
        "What is the difference between murder and culpable homicide?"
    )

    assert {source["id"] for source in matches} == {"bns-100", "bns-101"}
    assert all(
        source["act_name"] == "Bharatiya Nyaya Sanhita, 2023"
        for source in matches
    )
    assert all(source["verification_status"] == "needs_review" for source in matches)


def test_punishment_query_retrieves_bns_punishment_sections(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "justifi.db")
    database.upsert_legal_sources(
        [
            {
                "id": f"bns-{section}",
                "title": "Bharatiya Nyaya Sanhita, 2023",
                "act_name": "Bharatiya Nyaya Sanhita, 2023",
                "source_type": "statute",
                "section": f"{section}. {heading}",
                "content": f"{section}. {heading}. Statutory text.",
                "source": "BNS2023.pdf",
                "page": section,
                "verification_status": "needs_review",
            }
            for section, heading in (
                ("100", "Culpable homicide"),
                ("101", "Murder"),
                ("103", "Punishment for murder"),
                ("105", "Punishment for culpable homicide not amounting to murder"),
            )
        ]
    )

    matches = retrieval.search_legal_sources(
        "What is the punishment for murder and culpable homicide?",
        limit=10,
    )

    assert {source["section"].split(".", 1)[0] for source in matches} == {
        "100",
        "101",
        "103",
        "105",
    }


def test_explicit_missing_bns_section_does_not_fall_back_to_procedure(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "justifi.db")
    database.upsert_legal_sources(
        [
            {
                "id": "bnss-103",
                "title": "Bharatiya Nagarik Suraksha Sanhita, 2023",
                "act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
                "source_type": "statute",
                "section": "103. Search procedure",
                "content": "103. Procedural search text.",
            }
        ]
    )

    assert retrieval.search_legal_sources("BNS Section 103") == []


def test_bnss_explicit_section_is_searched_only_in_bnss_records(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "justifi.db")
    database.upsert_legal_sources(
        [
            {
                "id": "bnss-103",
                "title": "Bharatiya Nagarik Suraksha Sanhita, 2023",
                "act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
                "source_type": "statute",
                "section": "103. Persons in charge of closed place to allow search",
                "content": (
                    "103. Whenever any place liable to search is closed, "
                    "the person in charge shall allow ingress."
                ),
                "verification_status": "needs_review",
            },
            {
                "id": "bns-103",
                "title": "Bharatiya Nyaya Sanhita, 2023",
                "act_name": "Bharatiya Nyaya Sanhita, 2023",
                "source_type": "statute",
                "section": "103. Punishment for murder",
                "content": "103. Whoever commits murder shall be punished.",
                "verification_status": "needs_review",
            },
        ]
    )

    matches = retrieval.search_legal_sources("BNSS Section 103", limit=10)

    assert [source["id"] for source in matches] == ["bnss-103"]
    assert matches[0]["act_name"] == "Bharatiya Nagarik Suraksha Sanhita, 2023"


def test_bns_target_retrieval_excludes_comparative_index_chunks(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "justifi.db")
    database.upsert_legal_sources(
        [
            {
                "id": "bns-statute-100",
                "title": "Bharatiya Nyaya Sanhita, 2023",
                "act_name": "Bharatiya Nyaya Sanhita, 2023",
                "source_type": "statute",
                "section": "100. Culpable homicide",
                "content": (
                    "100. Whoever causes death with the required intention "
                    "commits culpable homicide."
                ),
            },
            {
                "id": "bns-crosswalk-100",
                "title": "Bharatiya Nyaya Sanhita, 2023",
                "act_name": (
                    "Bharatiya Nyaya Sanhita, 2023; Indian Penal Code, 1860"
                ),
                "source_type": "comparative_section_table",
                "section": None,
                "content": "100. Culpable homicide. 299. Culpable homicide.",
            },
        ]
    )

    matches = retrieval.search_legal_sources("BNS Section 100")

    assert [source["id"] for source in matches] == ["bns-statute-100"]


def test_source_queries_treat_user_input_as_data(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "justifi.db")
    database.upsert_legal_sources(
        [
            {
                "id": "safe-record",
                "title": "Legal source",
                "content": "Ordinary legal text.",
            }
        ]
    )

    injection = "' UNION SELECT * FROM users --"
    items, total = retrieval.search_source_records(query=injection)
    assert items == []
    assert total == 0
    assert database.get_legal_source(injection) is None
