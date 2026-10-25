"""Build a small .docx file in memory, for tests and the sample upload.

A .docx is just a zip file of XML documents. Writing the few XML parts Word needs
by hand avoids adding a dependency just for tests.

Example:
    data = build_docx([
        ("heading", "Vendor Agreement"),
        ("paragraph", [("1. Payment. ", True), ("Fees are due Net 45.", False)]),
    ])
    # data is the bytes of a Word file with a heading and a paragraph whose
    # first part is bold. Converting it gives:
    #   "# Vendor Agreement\n\n**1. Payment.** Fees are due Net 45."
"""

import io
import zipfile
from xml.sax.saxutils import escape

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

PACKAGE_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOCUMENT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

# Declares the "Heading 1" style so converters know Heading1 paragraphs are headings.
STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>
</w:styles>"""

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def build_docx(blocks: list[tuple]) -> bytes:
    """Return .docx bytes. Each block is ("heading", text) or ("paragraph", [(text, is_bold), ...])."""
    paragraphs = []
    for kind, content in blocks:
        if kind == "heading":
            paragraphs.append(f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>{run(content, False)}</w:p>')
        else:
            runs = "".join(run(text, is_bold) for text, is_bold in content)
            paragraphs.append(f"<w:p>{runs}</w:p>")

    body = "".join(paragraphs)
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{WORD_NAMESPACE}"><w:body>{body}</w:body></w:document>'

    # The zip of these parts is the .docx file.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", PACKAGE_RELS)
        archive.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS)
        archive.writestr("word/styles.xml", STYLES)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def run(text: str, is_bold: bool) -> str:
    """One stretch of text with the same formatting (Word calls this a "run")."""
    bold = "<w:rPr><w:b/></w:rPr>" if is_bold else ""
    # xml:space="preserve" keeps leading/trailing spaces, which Word would otherwise drop.
    return f'<w:r>{bold}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


# The sample Word contract used by samples/requests.sh and the demo upload.
SAMPLE_VENDOR_AGREEMENT = [
    ("heading", "Vendor Agreement"),
    ("paragraph", [("This Vendor Agreement is between ", False), ("Northwind Labs, Inc.", True),
                   (' ("Company") and ', False), ("Blue Heron Supply Co.", True), (' ("Vendor").', False)]),
    ("paragraph", [("1. Payment. ", True), ("Company shall pay each undisputed invoice within forty-five (45) days.", False)]),
    ("paragraph", [("2. Term. ", True), ("This Agreement lasts one (1) year and renews automatically.", False)]),
    ("paragraph", [("3. Liability. ", True), ("Vendor's liability shall be unlimited.", False)]),
    ("paragraph", [("4. Governing Law. ", True), ("This Agreement is governed by the laws of the State of Texas.", False)]),
]
