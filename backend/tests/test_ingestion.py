import pymupdf

import database
import fetch_legal_sources
from fetch_legal_sources import build_records, extract_pages, split_into_chunks
from retrieval import search_legal_sources


def create_pdf(path, text):
    document = pymupdf.open()
    page = document.new_page()
    if text:
        page.insert_text((50, 50), text)
    document.save(path)
    document.close()


def test_extracts_pdf_text_and_builds_repeatable_unverified_records(tmp_path):
    pdf_path = tmp_path / "legal-reference.pdf"
    create_pdf(pdf_path, "Section 12. This is a sample legal passage.")

    pages = extract_pages(pdf_path)
    first_import = build_records(pdf_path)
    second_import = build_records(pdf_path)

    assert pages[0]["page"] == 1
    assert "Section 12" in pages[0]["text"]
    assert first_import
    assert first_import[0]["_id"] == second_import[0]["_id"]
    assert first_import[0]["verification_status"] == "needs_review"


def test_pdf_without_extractable_text_is_reported_as_empty(tmp_path):
    pdf_path = tmp_path / "empty-reference.pdf"
    create_pdf(pdf_path, "")

    assert extract_pages(pdf_path) == []
    assert build_records(pdf_path) == []


def test_act_identity_and_section_metadata_come_from_document_text(tmp_path):
    pdf_path = tmp_path / "misleading-bnss-name.pdf"
    create_pdf(
        pdf_path,
        "THE BHARATIYA NYAYA SANHITA, 2023\n"
        "100. Culpable homicide.\n"
        "101. Murder.\n"
        "Culpable homicide.\n"
        "100. Whoever causes death with the required intention commits "
        "culpable homicide under this provision.\n"
        "Murder.\n"
        "101. Except in the cases hereinafter excepted, culpable homicide "
        "is murder under this provision.",
    )

    records = build_records(pdf_path)

    assert records
    assert {record["act_name"] for record in records} == {
        "Bharatiya Nyaya Sanhita, 2023"
    }
    assert {record["source_type"] for record in records} == {"statute"}
    assert {record["jurisdiction"] for record in records} == {"India"}
    assert any("100. Culpable homicide" in (record["section"] or "") for record in records)
    assert any("101. Murder" in (record["section"] or "") for record in records)
    assert all(record["verification_status"] == "needs_review" for record in records)
    assert all(record["publication_date"] is None for record in records)
    assert all(record["effective_date"] is None for record in records)


def test_bnss_document_is_not_classified_as_bns():
    metadata = fetch_legal_sources._document_metadata(
        [
            {
                "page": 1,
                "text": (
                    "THE BHARATIYA NAGARIK SURAKSHA SANHITA, 2023 "
                    "Bharatiya Nyaya Sanhita offences are tried under this law."
                ),
            }
        ],
        fetch_legal_sources.BASE_DIR / "not-a-source-of-truth.pdf",
    )

    assert metadata["act_name"] == "Bharatiya Nagarik Suraksha Sanhita, 2023"
    assert metadata["source_type"] == "statute"


def test_comparison_table_chunks_are_not_treated_as_statute_text():
    comparison_chunk = (
        "36. Right of private defence.\n98. Right of private defence.\n"
        "37. Acts against which there is no right.\n"
        "99. Acts against which there is no right.\n"
        "38. When right extends to causing death.\n"
        "100. When right extends to causing death.\n"
        "39. When the right extends to harm.\n"
        "101. When the right extends to harm."
    )

    metadata = fetch_legal_sources._chunk_source_metadata(
        comparison_chunk,
        {
            "title": "Bharatiya Nyaya Sanhita, 2023",
            "act_name": "Bharatiya Nyaya Sanhita, 2023",
            "source_type": "statute",
            "jurisdiction": "India",
        },
    )

    assert metadata["source_type"] == "comparative_section_table"
    assert metadata["act_name"] == (
        "Bharatiya Nyaya Sanhita, 2023; Indian Penal Code, 1860"
    )


def test_contents_chunk_with_referenced_old_section_is_only_an_index():
    contents_chunk = (
        "3. Procedure when bond has been forfeited.\n"
        "494. Cancellation of bond and bail bond.\n"
        "495. Procedure in case a bond is forfeited.\n"
        "496. Bond required from minor.\n"
        "497. Appeal from orders under section 446.\n"
        "498. Power to direct levy of amount due.\n"
        "499. Order for custody of property.\n"
        "500. Disposal of property at conclusion of trial."
    )

    metadata = fetch_legal_sources._chunk_source_metadata(
        contents_chunk,
        {
            "title": "Bharatiya Nagarik Suraksha Sanhita, 2023",
            "act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
            "source_type": "statute",
            "jurisdiction": "India",
        },
    )

    assert metadata["source_type"] == "statutory_index"
    assert metadata["act_name"] == "Bharatiya Nagarik Suraksha Sanhita, 2023"


def test_html_legal_table_is_extracted_without_script_or_navigation_text(
    tmp_path,
):
    html_path = tmp_path / "section-table.html"
    html_path.write_text(
        """
        <html><head><title>Ignored title</title>
        <script>ignored_script_marker</script></head>
        <body><nav>Ignored navigation</nav>
        <table><tr><th>IPC</th><th>BNS</th></tr>
        <tr><td>Section 1</td><td>Section 2</td></tr></table>
        </body></html>
        """,
        encoding="utf-8",
    )

    pages = extract_pages(html_path)
    records = build_records(html_path)

    assert len(pages) == 1
    assert "Section 1" in pages[0]["text"]
    assert "Section 2" in pages[0]["text"]
    assert "ignored_script_marker" not in pages[0]["text"]
    assert "Ignored navigation" not in pages[0]["text"]
    assert records[0]["verification_status"] == "needs_review"
    assert {record["source_type"] for record in records} == {
        "comparative_section_table"
    }


def test_chunking_preserves_content_and_overlap():
    text = ("Legal words. " * 300).strip()
    chunks = split_into_chunks(text)

    assert len(chunks) > 1
    assert all(chunk in text for chunk in chunks)
    assert chunks[0][-40:] in chunks[1]


def test_importer_persists_extracted_source_chunks_to_sqlite(
    tmp_path,
    monkeypatch,
    capsys,
):
    documents = tmp_path / "documents"
    documents.mkdir()
    (documents / "sample-law.txt").write_text(
        "Section 1 provides a sample legal rule.",
        encoding="utf-8",
    )
    db_path = tmp_path / "persistent" / "justifi.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(fetch_legal_sources, "DOCUMENTS_DIR", documents)

    assert fetch_legal_sources.main() == 0
    assert db_path.is_file()
    assert "Local SQLite database is ready" in capsys.readouterr().out
    matches = search_legal_sources("sample legal rule")
    assert len(matches) == 1
    assert matches[0]["source"] == "sample-law.txt"
    assert matches[0]["page"] == 1
    assert matches[0]["verification_status"] == "needs_review"
