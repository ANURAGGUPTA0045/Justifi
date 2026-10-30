"""SQLite persistence for JustiFi."""

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

_configured_path = Path(os.getenv("JUSTIFI_DB_PATH", "data/justifi.db"))
DB_PATH = (
    _configured_path
    if _configured_path.is_absolute()
    else BASE_DIR / _configured_path
)
DB_PATH = DB_PATH.resolve()

_initialized_paths: set[Path] = set()
_initialization_lock = threading.Lock()

LEGAL_SOURCE_COLUMNS = {
    "title",
    "content",
    "text",
    "source",
    "source_file",
    "file_hash",
    "page",
    "chunk_index",
    "verification_status",
    "source_url",
    "source_type",
    "jurisdiction",
    "act_name",
    "section",
    "publication_date",
    "effective_date",
    "amendment_information",
    "updated_at",
}


def _database_path() -> Path:
    path = Path(DB_PATH)
    if str(path) == ":memory:":
        raise ValueError("JustiFi requires a persistent SQLite database file.")
    return path.resolve()


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def initialize_database() -> Path:
    """Create the local database, tables, and indexes idempotently."""
    path = _database_path()
    with _initialization_lock:
        if path in _initialized_paths and path.is_file():
            return path
        with _connect(path) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS legal_sources (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT 'Legal document',
                    content TEXT NOT NULL DEFAULT '',
                    text TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'Unknown source',
                    source_file TEXT,
                    file_hash TEXT,
                    page INTEGER,
                    chunk_index INTEGER,
                    verification_status TEXT NOT NULL DEFAULT 'needs_review',
                    source_url TEXT,
                    source_type TEXT,
                    jurisdiction TEXT,
                    act_name TEXT,
                    section TEXT,
                    publication_date TEXT,
                    effective_date TEXT,
                    amendment_information TEXT,
                    updated_at TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_legal_sources_title
                    ON legal_sources(title);
                CREATE INDEX IF NOT EXISTS idx_legal_sources_source
                    ON legal_sources(source);
                CREATE INDEX IF NOT EXISTS idx_legal_sources_verification
                    ON legal_sources(verification_status);
                CREATE INDEX IF NOT EXISTS idx_legal_sources_jurisdiction
                    ON legal_sources(jurisdiction);
                CREATE INDEX IF NOT EXISTS idx_legal_sources_source_file
                    ON legal_sources(source_file);

                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        _initialized_paths.add(path)
    return path


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    """Open a short-lived connection with commit/rollback and cleanup."""
    path = initialize_database()
    conn = _connect(path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def check_database() -> None:
    """Initialize the persistent database and verify it can answer a query."""
    with connection() as conn:
        conn.execute("SELECT 1").fetchone()


def _json_value(value: object) -> str | int | float | None:
    if value is None or isinstance(value, (str, int, float)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return json.dumps(value, ensure_ascii=False, default=str)


def _row_to_source(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    record = dict(row)
    metadata = json.loads(record.pop("metadata_json") or "{}")
    return {**metadata, **record, "id": record["id"]}


def upsert_legal_sources(records: list[dict]) -> int:
    """Insert or update source chunks in one transaction."""
    if not records:
        return 0

    fields = (
        "id",
        "title",
        "content",
        "text",
        "source",
        "source_file",
        "file_hash",
        "page",
        "chunk_index",
        "verification_status",
        "source_url",
        "source_type",
        "jurisdiction",
        "act_name",
        "section",
        "publication_date",
        "effective_date",
        "amendment_information",
        "updated_at",
        "metadata_json",
    )
    sql = (
        f"INSERT INTO legal_sources ({', '.join(fields)}) "
        f"VALUES ({', '.join('?' for _ in fields)}) "
        "ON CONFLICT(id) DO UPDATE SET "
        + ", ".join(f"{field}=excluded.{field}" for field in fields[1:])
    )
    rows = []
    for record in records:
        source_id = record.get("id", record.get("_id"))
        if source_id is None:
            raise ValueError("Each legal source record requires an id.")
        values = {
            key: _json_value(value)
            for key, value in record.items()
            if key not in LEGAL_SOURCE_COLUMNS and key not in {"id", "_id"}
        }
        source = {
            "id": str(source_id),
            "title": record.get("title") or "Legal document",
            "content": record.get("content") or record.get("text") or "",
            "text": record.get("text") or record.get("content") or "",
            "source": (
                record.get("source")
                or record.get("source_file")
                or "Unknown source"
            ),
            "source_file": record.get("source_file"),
            "file_hash": record.get("file_hash"),
            "page": record.get("page"),
            "chunk_index": record.get("chunk_index"),
            "verification_status": (
                record.get("verification_status") or "needs_review"
            ),
            "source_url": record.get("source_url"),
            "source_type": record.get("source_type"),
            "jurisdiction": record.get("jurisdiction"),
            "act_name": record.get("act_name"),
            "section": record.get("section"),
            "publication_date": _json_value(record.get("publication_date")),
            "effective_date": _json_value(record.get("effective_date")),
            "amendment_information": _json_value(
                record.get("amendment_information")
            ),
            "updated_at": _json_value(record.get("updated_at")),
            "metadata_json": json.dumps(values, ensure_ascii=False),
        }
        rows.append(tuple(source[field] for field in fields))

    with connection() as conn:
        conn.executemany(sql, rows)
    return len(rows)


def get_legal_source(source_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM legal_sources WHERE id = ?",
            (source_id,),
        ).fetchone()
    return _row_to_source(row)


def update_legal_source(source_id: str, updates: dict) -> bool:
    """Update supported source fields and preserve unrecognized metadata."""
    if not updates:
        return False
    unknown = set(updates) - LEGAL_SOURCE_COLUMNS
    if unknown:
        raise ValueError("Unsupported legal source field.")

    assignments = ", ".join(f"{field} = ?" for field in updates)
    values = [_json_value(value) for value in updates.values()]
    with connection() as conn:
        cursor = conn.execute(
            f"UPDATE legal_sources SET {assignments} WHERE id = ?",
            (*values, source_id),
        )
    return cursor.rowcount > 0


def delete_legal_source(source_id: str) -> bool:
    with connection() as conn:
        cursor = conn.execute(
            "DELETE FROM legal_sources WHERE id = ?",
            (source_id,),
        )
    return cursor.rowcount > 0
