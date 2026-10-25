"""FastAPI app: routes and error handlers only.

Each route is a thin wrapper: read the request, call a function from store.py /
search.py / parsing.py, and shape the response. No business logic lives here.

API design in one paragraph:
  - Documents are REST resources: GET to read, POST to create, PATCH to edit.
  - Operations that aren't simple resource updates get "action" endpoints:
    POST /documents/{id}/preview runs edits without saving.
  - Reads never change anything; writes are PATCH/POST only.
"""

import logging

from fastapi import FastAPI, File, Form, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import parsing, store
from app.errors import AppError
from app.models import (
    CreateDocumentRequest,
    DocumentOut,
    DocumentSummary,
    EditRequest,
    EditResponse,
    ErrorResponse,
    HistoryEntry,
    PreviewResponse,
    SearchResponse,
)
from app.search import search_documents

logger = logging.getLogger("redline")

app = FastAPI(
    title="Redline Review API",
    description="Propose, preview, and apply contract edits, and search across documents.",
    # Show our error shape in the docs page for the common error codes.
    responses={code: {"model": ErrorResponse} for code in (400, 404, 409, 413, 415, 422, 500)},
)

# Load the sample contracts once, when the server starts.
store.seed()


# --- Error handlers: every error leaves the API in the same JSON shape ----------
# {"error": "<message for a person>", "code": 422, "type": "ambiguous_match", "details": {...}}


def error_response(status: int, error_type: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": message, "code": status, "type": error_type, "details": details or {}},
    )


@app.exception_handler(AppError)
def handle_app_error(request: Request, error: AppError):
    """Errors we raise on purpose (not found, ambiguous, conflict, ...)."""
    return error_response(error.status, error.type, error.message, error.details)


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, error: RequestValidationError):
    """FastAPI's built-in check failed (bad JSON, missing field, wrong type).

    FastAPI's default is a 422 with a developer-oriented list. We return a 400
    (it's a malformed request) in our own shape, with a readable list of problems.

    Example: {"changes": []} ->
        {"error": "The request is invalid: changes: List should have at least 1 item ...",
         "code": 400, "type": "invalid_request",
         "details": {"problems": [{"field": "changes", "problem": "List should have at least 1 item ..."}]}}
    """
    problems = []
    for item in error.errors():
        # item["loc"] is a path like ("body", "changes", 0, "target", "text"). Drop "body"/"query".
        field = ".".join(str(part) for part in item["loc"] if part not in ("body", "query", "path"))
        problems.append({"field": field, "problem": item["msg"]})

    summary = "; ".join(f"{p['field']}: {p['problem']}" for p in problems[:3])
    return error_response(400, "invalid_request", f"The request is invalid: {summary}", {"problems": problems})


@app.exception_handler(StarletteHTTPException)
def handle_http_error(request: Request, error: StarletteHTTPException):
    """Framework-level errors, e.g. a URL that doesn't exist (404) or wrong method (405)."""
    if error.status_code == 404:
        return error_response(404, "not_found", "There's no API endpoint at this address.")
    return error_response(error.status_code, "invalid_request", str(error.detail))


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, error: Exception):
    """Anything we didn't expect: log the real error, show the user a generic message."""
    logger.exception("Unexpected error on %s %s", request.method, request.url.path)
    return error_response(500, "server_error", "Something went wrong on our side. Please try again.")


# --- Routes -------------------------------------------------------------------


@app.get("/health")
def health():
    """Lets the frontend (and humans) check that the API is up."""
    return {"status": "ok"}


@app.get("/documents", response_model=list[DocumentSummary])
def list_documents():
    """All documents, without their full text."""
    return [summarize(document) for document in store.list_documents()]


# Note: this route must come BEFORE /documents/{doc_id}. FastAPI checks routes in
# order, and otherwise "search" would be treated as a document id.
@app.get("/documents/search", response_model=SearchResponse)
def search_all_documents(
    q: str = Query("", description="Text to search for (case-insensitive)."),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    whole_word: bool = Query(False),
):
    """Search every document. Example: GET /documents/search?q=liability&limit=10&offset=0"""
    return search_documents(store.list_documents(), q, limit=limit, offset=offset, whole_word=whole_word)


@app.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str):
    """One full document, including its current text and version."""
    return store.get_document(doc_id)


@app.post("/documents", response_model=DocumentOut, status_code=201)
def create_document(body: CreateDocumentRequest):
    """Create a document from JSON (title + Markdown or plain text)."""
    return store.create_document(body.title, body.text.replace("\r\n", "\n"), "md", body.author)


@app.post("/documents/upload", response_model=DocumentOut, status_code=201)
def upload_document(
    file: UploadFile = File(..., description="A .docx, .md, or .txt file, up to 20MB."),
    title: str | None = Form(None, description="Defaults to the file name."),
    author: str = Form("Anonymous"),
):
    """Upload a file. It's converted to Markdown and stored as a new document."""
    # 1. Read the file, but at most 1 byte past the limit. That's enough to know it's
    #    too big without loading a huge file into memory.
    filename = file.filename or "upload.txt"
    data = file.file.read(parsing.MAX_UPLOAD_BYTES + 1)

    # 2. Check the type/size and convert to Markdown (raises 413/415/400 on problems).
    text, file_type = parsing.parse_upload(filename, data)

    # 3. Save it.
    return store.create_document(title or parsing.title_from_filename(filename), text, file_type, author)


@app.patch("/documents/{doc_id}", response_model=EditResponse)
def edit_document(doc_id: str, body: EditRequest):
    """Apply one or more changes, all-or-nothing, and save a new version.

    Returns the updated text. Errors: 404 unknown document, 409 version conflict,
    422 text not found / ambiguous / occurrence out of range.
    """
    changes = [change.to_change() for change in body.changes]
    document, applied = store.save_changes(doc_id, changes, body.author, body.expected_version)
    return {"id": document["id"], "version": document["version"], "text": document["text"], "applied": applied}


@app.post("/documents/{doc_id}/preview", response_model=PreviewResponse)
def preview_edit(doc_id: str, body: EditRequest):
    """Same body as PATCH, but nothing is saved. Returns the would-be text and an inline redline."""
    changes = [change.to_change() for change in body.changes]
    document, text_after, redline_markdown, applied = store.preview_changes(doc_id, changes, body.expected_version)
    return {
        "id": document["id"],
        "version": document["version"],
        "text_after": text_after,
        "redline_markdown": redline_markdown,
        "applied": applied,
    }


@app.get("/documents/{doc_id}/search", response_model=SearchResponse)
def search_one_document(
    doc_id: str,
    q: str = Query("", description="Text to search for (case-insensitive)."),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    whole_word: bool = Query(False),
):
    """Search inside one document. Same logic as the all-documents search, filtered to one id."""
    store.get_document(doc_id)  # 404 if the document doesn't exist
    return search_documents(
        store.list_documents(), q, limit=limit, offset=offset, document_ids=[doc_id], whole_word=whole_word
    )


@app.get("/documents/{doc_id}/history", response_model=list[HistoryEntry])
def get_history(doc_id: str):
    """Every version, newest first: who changed what, when, why, and whether it was AI or human."""
    document = store.get_document(doc_id)
    # Pydantic drops the full "text" of each version, since HistoryEntry doesn't include it.
    return list(reversed(document["versions"]))


def summarize(document: dict) -> dict:
    """The short form of a document used in lists."""
    return {
        "id": document["id"],
        "title": document["title"],
        "file_type": document["file_type"],
        "version": document["version"],
        "updated_at": document["updated_at"],
        "size_chars": len(document["text"]),
    }
