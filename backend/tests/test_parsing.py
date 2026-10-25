from pathlib import Path

import pytest

from app.errors import InvalidRequest, TooLarge, UnsupportedFileType
from app.parsing import MAX_UPLOAD_BYTES, parse_upload, title_from_filename

# A real Word file, also used for the demo upload.
SAMPLE_DOCX = Path(__file__).resolve().parents[2] / "samples" / "sample-vendor-agreement.docx"


def test_txt_is_decoded_as_utf8():
    assert parse_upload("terms.txt", "Fees: €100".encode("utf-8")) == ("Fees: €100", "txt")


def test_md_keeps_markdown_and_windows_line_endings_are_normalized():
    text, file_type = parse_upload("terms.md", b"# Terms\r\n\r\n**Bold** clause")
    assert text == "# Terms\n\n**Bold** clause"
    assert file_type == "md"


def test_extension_check_ignores_case():
    assert parse_upload("TERMS.TXT", b"hello")[1] == "txt"


def test_docx_is_converted_to_markdown_with_headings_and_bold():
    text, file_type = parse_upload("vendor.docx", SAMPLE_DOCX.read_bytes())
    assert file_type == "docx"
    assert "# Vendor Agreement" in text
    assert "**1. Payment.** Company shall pay each undisputed invoice" in text


def test_damaged_docx_gives_a_friendly_error():
    with pytest.raises(InvalidRequest):
        parse_upload("broken.docx", b"this is not really a zip file")


def test_pdf_is_not_supported_yet():
    with pytest.raises(UnsupportedFileType) as caught:
        parse_upload("signed.pdf", b"%PDF-1.4")
    assert "PDF support is planned" in caught.value.message


def test_files_over_20mb_are_rejected():
    with pytest.raises(TooLarge):
        parse_upload("huge.txt", b"a" * (MAX_UPLOAD_BYTES + 1))


def test_empty_files_are_rejected():
    with pytest.raises(InvalidRequest):
        parse_upload("empty.txt", b"")


def test_title_defaults_to_filename_without_extension():
    assert title_from_filename("Vendor Agreement v2.docx") == "Vendor Agreement v2"
