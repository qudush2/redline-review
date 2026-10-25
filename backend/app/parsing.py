"""Turn an uploaded file into Markdown text.

Everything becomes Markdown because it keeps headings, bold, and numbering while
still being plain text underneath. That means the edit and search logic works
the same no matter what was uploaded.
"""

import io
import tempfile
import zipfile
from pathlib import Path

from markitdown import MarkItDown

from app.errors import InvalidRequest, TooLarge, UnsupportedFileType

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB

# File extension -> the file_type we store.
SUPPORTED_TYPES = {
    ".txt": "txt",
    ".md": "md",
    ".markdown": "md",
    ".docx": "docx",
}


def parse_upload(filename: str, data: bytes) -> tuple[str, str]:
    """Check an upload and convert it to Markdown. Returns (text, file_type).

    Examples:
        parse_upload("terms.txt", b"Payment is due Net 30.")
            -> ("Payment is due Net 30.", "txt")

        parse_upload("msa.docx", <bytes of a Word file>)
            -> ("# Vendor Agreement\\n\\n**1. Payment.** ...", "docx")

        parse_upload("signed.pdf", ...)     -> raises UnsupportedFileType (415)
        parse_upload("huge.txt", <25MB>)    -> raises TooLarge (413)
        parse_upload("empty.txt", b"")      -> raises InvalidRequest (400)
    """
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_TYPES:
        raise UnsupportedFileType(
            "That file type isn't supported yet. Upload .docx, .md, or .txt (PDF support is planned).",
            {"filename": filename},
        )
    file_type = SUPPORTED_TYPES[extension]

    if len(data) > MAX_UPLOAD_BYTES:
        raise TooLarge(
            "That file is larger than 20MB. Try splitting it, or upload the main agreement on its own.",
            {"size_bytes": len(data), "max_bytes": MAX_UPLOAD_BYTES},
        )
    if not data:
        raise InvalidRequest("That file is empty.")

    if file_type == "docx":
        text = docx_to_markdown(data)
    else:
        text = data.decode("utf-8", errors="replace")  # a stray bad byte becomes "�", not a failed upload

    # Windows line endings would throw off search and line numbers.
    text = text.replace("\r\n", "\n")
    if not text.strip():
        raise InvalidRequest("We couldn't find any text in that file.")

    return text, file_type


def docx_to_markdown(data: bytes) -> str:
    """Convert Word file bytes to Markdown using Microsoft's markitdown library.

    Example: a Word heading "Payment" becomes "# Payment", bold text becomes **bold**.
    """
    # Every real .docx is a zip archive. Without this check, markitdown quietly
    # imports a damaged or mislabeled file's raw bytes as text.
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise InvalidRequest("We couldn't read that .docx file. It may be damaged.")

    # markitdown reads from a path; the temporary folder is deleted when the block ends.
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "upload.docx"
        path.write_bytes(data)
        try:
            result = MarkItDown().convert(str(path))
        except Exception as error:
            raise InvalidRequest("We couldn't read that .docx file. It may be damaged.") from error
    return result.text_content


def title_from_filename(filename: str) -> str:
    """Default title for an upload.

    Examples:
        title_from_filename("Vendor Agreement v2.docx")  -> "Vendor Agreement v2"
        title_from_filename("msa.txt")                   -> "msa"
    """
    return Path(filename).stem or "Untitled document"
