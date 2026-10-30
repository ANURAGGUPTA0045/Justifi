"""SQLite-backed legal source retrieval."""

import re
import sqlite3
from urllib.parse import urlparse

try:
    from . import database
except ImportError:
    import database


class RetrievalUnavailable(RuntimeError):
    """Raised when the legal-source database cannot answer a search."""


_SECTION_MARKER = re.compile(r"\bsections?\b", re.IGNORECASE)


def _tokens(query: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\w+", query.casefold(), flags=re.UNICODE)))


def _like_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _source_from_row(row: sqlite3.Row) -> dict:
    source = database._row_to_source(row)
    if source is None:
        return {}
    source["source"] = (
        source.get("source") or source.get("source_file") or "Unknown source"
    )
    source["content"] = source.get("content") or source.get("text") or ""
    source["text"] = source.get("text") or source["content"]
    source.setdefault("title", "Legal document")
    source.setdefault("verification_status", "needs_review")
    source["source_url"] = _safe_source_url(source.get("source_url"))
    return source


def _safe_source_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value


def _explicit_section_numbers(query: str) -> list[str]:
    sections = []
    for marker in _SECTION_MARKER.finditer(query):
        remainder = query[marker.end():]
        first = re.match(r"\s*(\d{1,3}[A-Za-z]?)", remainder)
        if not first:
            continue
        sections.append(first.group(1).upper())
        remainder = remainder[first.end():]
        while connector := re.match(r"\s*(?:,|and|&)\s*(\d{1,3}[A-Za-z]?)", remainder, re.I):
            sections.append(connector.group(1).upper())
            remainder = remainder[connector.end():]
    return list(dict.fromkeys(sections))


def _statutory_intent(query: str) -> tuple[str, list[str]] | None:
    normalized = query.casefold()
    explicit_sections = _explicit_section_numbers(query)
    if "bharatiya nagarik suraksha sanhita" in normalized or re.search(
        r"\bbnss\b", normalized
    ):
        return "Bharatiya Nagarik Suraksha Sanhita, 2023", explicit_sections
    if "bharatiya sakshya adhiniyam" in normalized or re.search(
        r"\bbsa\b", normalized
    ):
        return "Bharatiya Sakshya Adhiniyam, 2023", explicit_sections

    is_bns = (
        "bharatiya nyaya sanhita" in normalized
        or re.search(r"\bbns\b", normalized) is not None
        or "murder" in normalized
        or "culpable homicide" in normalized
    )
    if not is_bns:
        return None
    if explicit_sections:
        return "Bharatiya Nyaya Sanhita, 2023", explicit_sections

    has_murder = "murder" in normalized
    has_homicide = "culpable homicide" in normalized
    punishment_requested = any(
        word in normalized
        for word in ("punish", "penalty", "sentence", "punishment")
    )
    sections = []
    if has_homicide:
        sections.append("100")
    if has_murder or has_homicide:
        sections.append("101")
    if punishment_requested and has_murder:
        sections.append("103")
    if punishment_requested and has_homicide:
        sections.append("105")
    return "Bharatiya Nyaya Sanhita, 2023", sections


def _section_numbers(value: str | None) -> set[str]:
    if not value:
        return set()
    return {
        number.upper()
        for number in re.findall(r"(?<!\d)(\d{1,3}[A-Z]?)\.\s", value, re.I)
    }


def _search_statutory_sections(
    act_name: str,
    sections: list[str],
    limit: int,
) -> list[dict]:
    if not sections:
        return []
    try:
        with database.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM legal_sources
                WHERE act_name = ? AND source_type = 'statute'
                ORDER BY page, chunk_index
                """,
                (act_name,),
            ).fetchall()
    except (sqlite3.Error, OSError, ValueError) as exc:
        raise RetrievalUnavailable(
            "Legal source retrieval is currently unavailable."
        ) from exc

    section_order = {number: index for index, number in enumerate(sections)}
    matched = []
    for row in rows:
        source = _source_from_row(row)
        source_sections = _section_numbers(source.get("section"))
        matched_sections = source_sections.intersection(section_order)
        if not matched_sections or not source.get("content", "").strip():
            continue
        first_match = min(matched_sections, key=section_order.get)
        source["score"] = (
            1000
            - section_order[first_match] * 100
            + len(matched_sections)
        )
        matched.append((section_order[first_match], source))

    matched.sort(
        key=lambda item: (
            item[0],
            item[1].get("page") or 0,
            item[1].get("chunk_index") or 0,
        )
    )
    return [source for _, source in matched[:limit]]


def _build_filters(
    query: str,
    verification_status: str | None = None,
    jurisdiction: str | None = None,
) -> tuple[list[str], list[object], list[str]]:
    conditions: list[str] = []
    parameters: list[object] = []
    tokens = _tokens(query)

    if verification_status:
        conditions.append("verification_status = ?")
        parameters.append(verification_status)
    if jurisdiction:
        conditions.append("lower(coalesce(jurisdiction, '')) LIKE ? ESCAPE '\\'")
        parameters.append(_like_pattern(jurisdiction.casefold()))
    if tokens:
        token_conditions = []
        for token in tokens:
            pattern = _like_pattern(token)
            token_conditions.append(
                "("
                "lower(content) LIKE ? ESCAPE '\\' OR "
                "lower(title) LIKE ? ESCAPE '\\' OR "
                "lower(coalesce(act_name, '')) LIKE ? ESCAPE '\\' OR "
                "lower(coalesce(section, '')) LIKE ? ESCAPE '\\' OR "
                "lower(source) LIKE ? ESCAPE '\\' OR "
                "lower(coalesce(source_file, '')) LIKE ? ESCAPE '\\'"
                ")"
            )
            parameters.extend([pattern] * 6)
        conditions.append("(" + " OR ".join(token_conditions) + ")")
    return conditions, parameters, tokens


def _rank_expression(tokens: list[str]) -> tuple[str, list[str]]:
    if not tokens:
        return "0", []
    fields = ("content", "title", "act_name", "section", "source", "source_file")
    expressions = []
    params: list[str] = []
    for token in tokens:
        pattern = _like_pattern(token)
        for field in fields:
            value = f"coalesce({field}, '')" if field in {"act_name", "section", "source_file"} else field
            weight = 3 if field == "content" else 5 if field == "title" else 1
            expressions.append(
                f"CASE WHEN lower({value}) LIKE ? ESCAPE '\\' "
                f"THEN {weight} ELSE 0 END"
            )
            params.append(pattern)
    return " + ".join(expressions), params


def search_legal_sources(query: str, limit: int = 5) -> list[dict]:
    """Return matching legal passages with their stored source metadata."""
    query = (query or "").strip()
    if not query:
        return []
    limit = max(1, min(int(limit), 20))
    intent = _statutory_intent(query)
    if intent is not None:
        act_name, sections = intent
        if sections:
            return _search_statutory_sections(act_name, sections, limit)

    conditions, parameters, tokens = _build_filters(query)
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    score, score_parameters = _rank_expression(tokens)
    sql = (
        f"SELECT *, ({score}) AS relevance FROM legal_sources"
        f"{where_clause} ORDER BY relevance DESC, title COLLATE NOCASE, page LIMIT ?"
    )
    try:
        with database.connection() as conn:
            rows = conn.execute(
                sql,
                (*score_parameters, *parameters, limit),
            ).fetchall()
    except (sqlite3.Error, OSError, ValueError) as exc:
        raise RetrievalUnavailable(
            "Legal source retrieval is currently unavailable."
        ) from exc

    documents = []
    for row in rows:
        source = _source_from_row(row)
        if source.get("content", "").strip():
            source["score"] = row["relevance"]
            documents.append(source)
    return documents


def search_source_records(
    query: str = "",
    verification_status: str | None = None,
    jurisdiction: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Search stored sources and return a page plus matching result count."""
    query = (query or "").strip()
    conditions, parameters, tokens = _build_filters(
        query,
        verification_status,
        jurisdiction,
    )
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    score, score_parameters = _rank_expression(tokens)

    try:
        with database.connection() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM legal_sources{where_clause}",
                parameters,
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT *, ({score}) AS relevance FROM legal_sources"
                f"{where_clause} "
                "ORDER BY relevance DESC, title COLLATE NOCASE, page "
                "LIMIT ? OFFSET ?",
                (*score_parameters, *parameters, max(1, min(int(limit), 50)), max(0, int(offset))),
            ).fetchall()
    except (sqlite3.Error, OSError, ValueError) as exc:
        raise RetrievalUnavailable(
            "Legal source search is currently unavailable."
        ) from exc
    return [_source_from_row(row) for row in rows], total


def get_source_record(source_id: str) -> dict | None:
    """Read one source record by its stable identifier."""
    try:
        with database.connection() as conn:
            row = conn.execute(
                "SELECT * FROM legal_sources WHERE id = ?",
                (source_id,),
            ).fetchone()
    except (sqlite3.Error, OSError, ValueError) as exc:
        raise RetrievalUnavailable(
            "Legal source lookup is currently unavailable."
        ) from exc
    return _source_from_row(row) if row else None


def retrieve_relevant_sources(query: str, limit: int = 5) -> list[dict]:
    return search_legal_sources(query, limit)


def retrieve_sources(query: str, limit: int = 5) -> list[dict]:
    return search_legal_sources(query, limit)


if __name__ == "__main__":
    question = input("Enter a legal question to test retrieval: ").strip()
    if question:
        matches = search_legal_sources(question, limit=5)
        if not matches:
            print("No matching passages found in the local database.")
        for number, item in enumerate(matches, start=1):
            print(f"\n--- Result {number} ---")
            print(f"Title: {item['title']}")
            print(f"Source: {item['source']}")
            print(f"Page: {item['page']}")
            print(f"Verification: {item['verification_status']}")
            print(f"Content:\n{item['content'][:1000]}")
