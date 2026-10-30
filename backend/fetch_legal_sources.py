
"""
JustiFi - Local Legal Document Importer

Reads PDF, TXT, and HTML files from backend/legal_documents/
Extracts text, creates overlapping chunks, and stores them in local SQLite.
Does not download documents from the internet.
"""

import hashlib
import re
import sqlite3
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import pymupdf

try:
    from . import database
except ImportError:
    import database


# ==================================================
# 1. CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIR = BASE_DIR / "legal_documents"

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200
_SECTION_INDEX_LINE = re.compile(
    r"(?m)^[ \t]*(?P<number>\d{1,3}[A-Z]?)\.\s+"
    r"(?P<heading>[^\n]{3,160})"
)
_STATUTORY_SECTION_LINE = re.compile(
    r"(?m)^[ \t]*(?P<number>\d{1,3}[A-Z]?)\.\s+"
    r"(?P<body>[^\n]{20,})"
)
_STATUTORY_OPENING = re.compile(
    r"^(?:\(\d+\)|whoever\b|except\b|if\b|where\b|when\b|"
    r"any person\b|a person\b|every\b|nothing\b|no person\b)",
    re.IGNORECASE,
)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".html", ".htm"}


class _LegalHTMLTextParser(HTMLParser):
    ignored_tags = {"head", "script", "style", "nav", "footer"}
    block_tags = {"br", "p", "h1", "h2", "h3", "h4", "li", "tr"}
    cell_tags = {"td", "th"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.ignored_tags:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag in self.block_tags:
            self.parts.append("\n")
        elif tag in self.cell_tags:
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if tag in self.ignored_tags:
            self._ignored_depth = max(0, self._ignored_depth - 1)
            return
        if self._ignored_depth:
            return
        if tag in self.block_tags:
            self.parts.append("\n")
        elif tag in self.cell_tags:
            self.parts.append(" | ")

    def handle_data(self, data):
        if not self._ignored_depth:
            self.parts.append(data)

    def get_text(self):
        return clean_text("".join(self.parts))


# ==================================================
# 2. TEXT CLEANING
# ==================================================

def clean_text(text: str) -> str:
    """Clean extracted text while preserving paragraph breaks."""
    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ==================================================
# 3. DOCUMENT TITLE
# ==================================================

def make_title(file_path: Path) -> str:
    """Create a readable title from a filename."""
    title = file_path.stem.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", title).strip()


# ==================================================
# 4. EXTRACT TEXT FROM LOCAL DOCUMENTS
# ==================================================

def extract_pages(file_path: Path) -> list[dict]:
    """Extract text from each PDF page or from a TXT file."""
    pages = []

    if file_path.suffix.lower() == ".pdf":
        try:
            with pymupdf.open(file_path) as pdf:
                if pdf.is_encrypted:
                    print(f"  SKIPPED: Encrypted PDF: {file_path.name}")
                    return []

                for page_number, page in enumerate(pdf, start=1):
                    page_text = clean_text(page.get_text("text"))

                    if page_text:
                        pages.append({
                            "page": page_number,
                            "text": page_text,
                        })

        except Exception as exc:
            print(f"  ERROR reading PDF {file_path.name}: {exc}")
            return []

    elif file_path.suffix.lower() == ".txt":
        try:
            text = file_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
            text = clean_text(text)

            if text:
                pages.append({
                    "page": 1,
                    "text": text,
                })

        except OSError as exc:
            print(f"  ERROR reading TXT {file_path.name}: {exc}")
            return []

    elif file_path.suffix.lower() in {".html", ".htm"}:
        try:
            parser = _LegalHTMLTextParser()
            parser.feed(file_path.read_text(encoding="utf-8-sig", errors="replace"))
            text = parser.get_text()
            if text:
                pages.append({"page": 1, "text": text})
        except (OSError, ValueError) as exc:
            print(f"  ERROR reading HTML {file_path.name}: {type(exc).__name__}")
            return []

    return pages


# ==================================================
# 5. SPLIT TEXT INTO OVERLAPPING CHUNKS
# ==================================================

def split_into_chunks(text: str) -> list[str]:
    """Split document text into overlapping chunks."""
    text = clean_text(text)

    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + CHUNK_SIZE, text_length)

        if end < text_length:
            boundary = max(
                text.rfind("\n", start, end),
                text.rfind(". ", start, end),
                text.rfind("।", start, end),
            )

            if boundary > start + int(CHUNK_SIZE * 0.6):
                end = boundary + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = max(end - CHUNK_OVERLAP, start + 1)

    return chunks


def _document_metadata(pages: list[dict], file_path: Path) -> dict:
    """Identify a source from its extracted contents, not its filename."""
    opening = "\n".join(page["text"] for page in pages[:8]).casefold()
    if (
        file_path.suffix.lower() in {".html", ".htm"}
        and "bns" in opening
        and "ipc" in opening
    ):
        return {
            "title": "BNS and IPC Section Comparison Table",
            "act_name": (
                "Bharatiya Nyaya Sanhita, 2023; Indian Penal Code, 1860"
            ),
            "source_type": "comparative_section_table",
            "jurisdiction": "India",
        }
    if "bharatiya nagarik suraksha sanhita" in opening:
        return {
            "title": "Bharatiya Nagarik Suraksha Sanhita, 2023",
            "act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
            "source_type": "statute",
            "jurisdiction": "India",
        }
    if "bharatiya nyaya sanhita" in opening:
        return {
            "title": "Bharatiya Nyaya Sanhita, 2023",
            "act_name": "Bharatiya Nyaya Sanhita, 2023",
            "source_type": "statute",
            "jurisdiction": "India",
        }
    if "bharatiya sakshya adhiniyam" in opening:
        return {
            "title": "Bharatiya Sakshya Adhiniyam, 2023",
            "act_name": "Bharatiya Sakshya Adhiniyam, 2023",
            "source_type": "statute",
            "jurisdiction": "India",
        }
    if "bns" in opening and "ipc" in opening and (
        file_path.suffix.lower() in {".html", ".htm"}
        or "corresponding section" in opening
    ):
        return {
            "title": "BNS and IPC Section Comparison Table",
            "act_name": (
                "Bharatiya Nyaya Sanhita, 2023; Indian Penal Code, 1860"
            ),
            "source_type": "comparative_section_table",
            "jurisdiction": "India",
        }
    return {
        "title": make_title(file_path),
        "act_name": None,
        "source_type": None,
        "jurisdiction": None,
    }


def _section_heading_map(pages: list[dict]) -> dict[str, str]:
    headings = {}
    for page in pages[:12]:
        for match in _SECTION_INDEX_LINE.finditer(page["text"]):
            number = match.group("number").upper()
            heading = re.sub(r"\s+", " ", match.group("heading")).strip()
            headings.setdefault(number, heading.rstrip("."))
    return headings


def _section_labels(text: str, headings: dict[str, str]) -> list[str]:
    labels = []
    for match in _STATUTORY_SECTION_LINE.finditer(text):
        body = match.group("body").strip()
        if not _STATUTORY_OPENING.match(body):
            continue
        number = match.group("number").upper()
        heading = headings.get(number)
        if heading:
            labels.append(f"{number}. {heading}")
    return labels


def _chunk_source_metadata(text: str, document_metadata: dict) -> dict:
    """Keep contents pages and crosswalks out of statute retrieval."""
    if document_metadata["source_type"] != "statute":
        return document_metadata

    numbers = [
        int(match.group(1))
        for match in re.finditer(
            r"(?m)^[ \t]*(\d{1,3})[A-Z]?\.\s+",
            text,
        )
    ]
    if len(numbers) < 8:
        return document_metadata

    section_number_jumps = sum(
        abs(left - right) >= 40
        for left, right in zip(numbers, numbers[1:])
    )
    is_comparison = section_number_jumps >= 3
    if is_comparison:
        return {
            **document_metadata,
            "act_name": (
                "Bharatiya Nyaya Sanhita, 2023; Indian Penal Code, 1860"
            ),
            "source_type": "comparative_section_table",
        }
    return {
        **document_metadata,
        "source_type": "statutory_index",
    }


# ==================================================
# 6. BUILD LEGAL SOURCE RECORDS
# ==================================================

def build_records(file_path: Path) -> list[dict]:
    """Convert a local document into searchable database records."""
    source_file = file_path.name

    file_hash = hashlib.sha256(
        file_path.read_bytes()
    ).hexdigest()

    pages = extract_pages(file_path)

    if not pages:
        print("  WARNING: No extractable text found.")
        print("  Scanned PDFs may require OCR.")
        return []

    document_metadata = _document_metadata(pages, file_path)
    title = document_metadata["title"]
    records = []
    chunk_number = 0
    active_section = None
    section_headings = _section_heading_map(pages)

    for page_data in pages:
        chunks = split_into_chunks(page_data["text"])

        for chunk in chunks:
            chunk_number += 1
            chunk_metadata = _chunk_source_metadata(chunk, document_metadata)
            section_labels = []
            if chunk_metadata["source_type"] == "statute":
                labels_in_chunk = _section_labels(chunk, section_headings)
                if active_section:
                    section_labels.append(active_section)
                for label in labels_in_chunk:
                    if label not in section_labels:
                        section_labels.append(label)
                    active_section = label
            else:
                active_section = None

            chunk_hash = hashlib.sha256(
                (
                    f"{file_hash}|{page_data['page']}|{chunk}"
                ).encode("utf-8")
            ).hexdigest()

            records.append({
                "_id": chunk_hash,
                "title": title,
                "source": source_file,
                "source_file": source_file,
                "file_hash": file_hash,
                "page": page_data["page"],
                "chunk_index": chunk_number,

                # Keep both fields for compatibility.
                "content": chunk,
                "text": chunk,

                # Importing a file does not verify its legal accuracy.
                "verification_status": "needs_review",
                "section": " | ".join(section_labels) or None,
                "act_name": chunk_metadata["act_name"],
                "source_type": chunk_metadata["source_type"],
                "jurisdiction": chunk_metadata["jurisdiction"],
                # The local copies do not provide reliable publication or
                # commencement metadata; leave both dates unset.
                "publication_date": None,
                "effective_date": None,
                "updated_at": datetime.now(timezone.utc),
            })

    print(
        f"  Pages extracted: {len(pages)} | "
        f"Chunks created: {len(records)}"
    )

    return records


# ==================================================
# 7. SAVE RECORDS TO SQLITE
# ==================================================

def save_records(records: list[dict]) -> int:
    """Insert new records or update matching records in SQLite."""
    return database.upsert_legal_sources(records)


# ==================================================
# 9. MAIN IMPORT PROCESS
# ==================================================

def main() -> int:
    print("\n======================================")
    print(" JustiFi Local Legal Document Importer")
    print("======================================\n")

    try:
        database.initialize_database()
        database.check_database()
    except (OSError, sqlite3.Error, RuntimeError, ValueError) as exc:
        print(
            "ERROR: Local SQLite database initialization failed "
            f"({type(exc).__name__})."
        )
        return 1

    if not DOCUMENTS_DIR.exists():
        print(f"ERROR: Folder not found: {DOCUMENTS_DIR}")
        print("Create the legal_documents folder and add your files.")
        return 1

    files = sorted(
        path
        for path in DOCUMENTS_DIR.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not files:
        print(f"No PDF or TXT files found in {DOCUMENTS_DIR}")
        return 1

    print(f"Document folder: {DOCUMENTS_DIR}")
    print(f"Documents found: {len(files)}")
    print("Internet downloads: DISABLED\n")

    try:
        print("Local SQLite database is ready.\n")

        total_chunks = 0
        failed_files = 0
        skipped_files = 0

        for file_path in files:
            print(f"\nProcessing: {file_path.name}")

            try:
                records = build_records(file_path)

                if not records:
                    skipped_files += 1
                    continue

                saved_count = save_records(records)
                total_chunks += len(records)

                print(f"  Records inserted/updated: {saved_count}")
                print("  Verification status: needs_review")

            except (OSError, ValueError, sqlite3.Error) as exc:
                failed_files += 1
                print(
                    "  ERROR processing file "
                    f"({type(exc).__name__})."
                )

            except Exception as exc:
                failed_files += 1
                print(
                    "  UNEXPECTED ERROR "
                    f"({type(exc).__name__})."
                )

        print("\n======================================")
        print(" IMPORT SUMMARY")
        print("======================================")
        print(f"Documents discovered: {len(files)}")
        print(f"Chunks processed: {total_chunks}")
        print(f"Files skipped: {skipped_files}")
        print(f"Files failed: {failed_files}")
        print(f"Database file: {database.DB_PATH}")
        print("Table: legal_sources")
        print("Verification status: needs_review")
        print("======================================")
        return 1 if failed_files else 0

    except (OSError, sqlite3.Error) as exc:
        print(
            "\nLOCAL DATABASE/IMPORT ERROR "
            f"({type(exc).__name__})."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
