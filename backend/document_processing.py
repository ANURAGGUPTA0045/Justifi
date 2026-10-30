import re
import os
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import PurePath
from xml.etree import ElementTree

import pymupdf


MAX_DOCUMENT_BYTES = int(
    os.getenv("JUSTIFI_MAX_UPLOAD_BYTES", str(8 * 1024 * 1024))
)
if not 1024 * 1024 <= MAX_DOCUMENT_BYTES <= 32 * 1024 * 1024:
    raise ValueError(
        "JUSTIFI_MAX_UPLOAD_BYTES must be between 1 MiB and 32 MiB."
    )
MAX_DOCX_EXPANDED_BYTES = 64 * 1024 * 1024
MAX_DOCUMENT_PAGES = 200
MIN_EXTRACTED_TEXT_LENGTH = 24
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

_DATE_PATTERNS = (
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
    re.compile(
        r"\b\d{1,2}\s+"
        r"(?:January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{4}\b",
        re.IGNORECASE,
    ),
)


class DocumentExtractionError(ValueError):
    """Raised when an uploaded document is invalid or cannot be extracted."""


def _extract_pdf(content: bytes) -> list[dict]:
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.page_count == 0:
                raise DocumentExtractionError("The PDF contains no pages.")
            if document.is_encrypted:
                raise DocumentExtractionError(
                    "Password-protected PDFs are not supported."
                )
            if document.page_count > MAX_DOCUMENT_PAGES:
                raise DocumentExtractionError(
                    "The PDF exceeds the 200-page processing limit."
                )
            pages = [
                {"page": number, "text": page.get_text("text").strip()}
                for number, page in enumerate(document, start=1)
            ]
    except DocumentExtractionError:
        raise
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise DocumentExtractionError(
            "The PDF is corrupt or could not be opened."
        ) from exc

    return [page for page in pages if page["text"]]


def _extract_docx(content: bytes) -> list[dict]:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise DocumentExtractionError(
                    "The DOCX file is missing required document parts."
                )
            if sum(item.file_size for item in archive.infolist()) > MAX_DOCX_EXPANDED_BYTES:
                raise DocumentExtractionError(
                    "The DOCX expands beyond the supported processing size."
                )
            document_part = archive.getinfo("word/document.xml")
            if document_part.file_size > MAX_DOCX_EXPANDED_BYTES:
                raise DocumentExtractionError(
                    "The DOCX document content exceeds the processing limit."
                )
            root = ElementTree.fromstring(
                archive.read("word/document.xml")
            )
    except DocumentExtractionError:
        raise
    except (
        OSError,
        zipfile.BadZipFile,
        ElementTree.ParseError,
        KeyError,
    ) as exc:
        raise DocumentExtractionError(
            "The DOCX is corrupt or could not be opened."
        ) from exc

    paragraphs = []
    for paragraph in root.iter(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
    ):
        text = "".join(
            node.text or ""
            for node in paragraph.iter(
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
            )
        ).strip()
        if text:
            paragraphs.append(text)

    text = "\n".join(paragraphs)
    return [{"page": None, "text": text}] if text else []


def _extract_txt(content: bytes) -> list[dict]:
    try:
        text = content.decode("utf-8-sig").strip()
    except UnicodeDecodeError as exc:
        raise DocumentExtractionError(
            "The TXT file must use UTF-8 encoding."
        ) from exc
    return [{"page": None, "text": text}] if text else []


def extract_document(filename: str, content: bytes) -> list[dict]:
    """Validate a supported document and extract its text by page."""
    if not content:
        raise DocumentExtractionError("The uploaded file is empty.")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise DocumentExtractionError(
            "The document exceeds the configured upload limit."
        )

    extension = PurePath(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentExtractionError(
            "Upload a PDF, DOCX, or UTF-8 TXT document."
        )

    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise DocumentExtractionError(
                "The uploaded file does not have a valid PDF signature."
            )
        pages = _extract_pdf(content)
    elif extension == ".docx":
        if not content.startswith(b"PK"):
            raise DocumentExtractionError(
                "The uploaded file does not have a valid DOCX container."
            )
        pages = _extract_docx(content)
    else:
        if b"\x00" in content[:4096]:
            raise DocumentExtractionError(
                "The uploaded file is not a supported plain-text document."
            )
        pages = _extract_txt(content)

    total_length = sum(len(page["text"]) for page in pages)
    if total_length < MIN_EXTRACTED_TEXT_LENGTH:
        if extension == ".pdf":
            raise DocumentExtractionError(
                "The PDF contains too little selectable text. Scanned PDFs "
                "need OCR, which is not configured in this application."
            )
        raise DocumentExtractionError(
            "No usable text could be extracted from this document."
        )

    return pages


def extract_explicit_dates(pages: list[dict]) -> list[dict]:
    """Find explicit supported date formats without inferring deadlines."""
    dates = []
    seen = set()
    for page in pages:
        text = page["text"]
        for pattern in _DATE_PATTERNS:
            for match in pattern.finditer(text):
                original = match.group(0)
                normalized = original
                ambiguous = False
                try:
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", original):
                        normalized = datetime.strptime(
                            original, "%Y-%m-%d"
                        ).date().isoformat()
                    elif "/" in original or re.fullmatch(
                        r"\d{1,2}-\d{1,2}-\d{2,4}",
                        original,
                    ):
                        separator = "/" if "/" in original else "-"
                        day_text, month_text, year_text = original.split(separator)
                        day, month, year = (
                            int(day_text),
                            int(month_text),
                            int(year_text),
                        )
                        if year_text and len(year_text) == 2:
                            year += 2000 if year <= 68 else 1900
                        if day <= 12 and month <= 12:
                            ambiguous = True
                            normalized = original
                        else:
                            normalized = datetime(
                                year, month, day
                            ).date().isoformat()
                    else:
                        normalized = datetime.strptime(
                            original, "%d %B %Y"
                        ).date().isoformat()
                except (ValueError, OverflowError):
                    continue
                key = (normalized, page.get("page"))
                if key in seen:
                    continue
                seen.add(key)
                start = max(0, match.start() - 70)
                end = min(len(text), match.end() + 70)
                dates.append(
                    {
                        "date": normalized,
                        "source_text": original,
                        "context": text[start:end].strip(),
                        "page": page.get("page"),
                        "explicit": True,
                        "ambiguous_format": ambiguous,
                        "requires_confirmation": True,
                    }
                )
                if len(dates) >= 100:
                    return dates
    return dates
