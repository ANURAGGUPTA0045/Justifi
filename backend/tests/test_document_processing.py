import zipfile
from io import BytesIO

import pymupdf
import pytest

from document_processing import DocumentExtractionError, extract_document
from document_processing import extract_explicit_dates


def create_pdf(text: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((50, 50), text)
    content = document.tobytes()
    document.close()
    return content


def create_docx(text: str) -> bytes:
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>'
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body><w:p><w:r><w:t>'
        f"{text}"
        '</w:t></w:r></w:p></w:body></w:document>'
    )
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("word/document.xml", document_xml)
    return output.getvalue()


@pytest.mark.parametrize(
    ("filename", "content", "expected"),
    [
        (
            "notice.pdf",
            create_pdf("This legal notice contains enough readable text."),
            "legal notice",
        ),
        (
            "notice.docx",
            create_docx("This document contains enough readable text."),
            "document contains",
        ),
        (
            "notice.txt",
            b"This text document contains enough readable words.",
            "text document",
        ),
    ],
)
def test_extracts_supported_document_formats(filename, content, expected):
    pages = extract_document(filename, content)
    assert len(pages) == 1
    assert expected in pages[0]["text"]


def test_rejects_mismatched_signature_empty_and_corrupt_documents():
    with pytest.raises(DocumentExtractionError, match="signature"):
        extract_document("notice.pdf", b"not a pdf document")
    with pytest.raises(DocumentExtractionError, match="empty"):
        extract_document("notice.txt", b"")
    with pytest.raises(DocumentExtractionError, match="DOCX container"):
        extract_document("notice.docx", b"not a zip archive")


def test_rejects_scanned_pdf_without_ocr():
    document = pymupdf.open()
    document.new_page()
    content = document.tobytes()
    document.close()

    with pytest.raises(DocumentExtractionError, match="OCR"):
        extract_document("scan.pdf", content)


def test_rejects_non_utf8_text_and_unsupported_extension():
    with pytest.raises(DocumentExtractionError, match="plain-text"):
        extract_document("notice.txt", b"\x00\x00\x00\x00")
    with pytest.raises(DocumentExtractionError, match="UTF-8"):
        extract_document("notice.txt", b"\xff\xffThis is valid length")
    with pytest.raises(DocumentExtractionError, match="PDF, DOCX"):
        extract_document("notice.rtf", b"legal text content")


def test_date_extraction_rejects_invalid_dates_and_flags_ambiguous_dates():
    dates = extract_explicit_dates(
        [
            {
                "page": 2,
                "text": (
                    "Notice issued 2026-02-29 and received on 04/05/2026. "
                    "The hearing is on 17/08/2026."
                ),
            }
        ]
    )
    assert [item["source_text"] for item in dates] == [
        "04/05/2026",
        "17/08/2026",
    ]
    assert dates[0]["ambiguous_format"] is True
    assert dates[0]["requires_confirmation"] is True
    assert dates[1]["date"] == "2026-08-17"
