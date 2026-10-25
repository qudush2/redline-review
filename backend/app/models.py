"""Request and response shapes for the API (Pydantic models).

FastAPI uses these to:
  - check incoming JSON automatically (wrong types or missing fields -> 400), and
  - draw the interactive docs at http://localhost:8000/docs.

They only describe data. The logic lives in redline.py, search.py, and store.py.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.redline import Change

# --- Requests ---------------------------------------------------------------


class Target(BaseModel):
    """What text to change.

    Examples:
        {"text": "State of California"}                       # must appear exactly once
        {"text": "thirty (30) days", "occurrence": 2}         # only the 2nd match
        {"text": "Licensee", "occurrence": "all"}             # every match
        {"text": "Term", "occurrence": "all", "whole_word": false}   # would also hit "Termination"
    """

    text: str = Field(min_length=1, description="The exact text to find (case-sensitive).")
    occurrence: Annotated[int, Field(ge=1)] | Literal["all"] | None = Field(
        default=None,
        description='Which match to change: 1, 2, … or "all". Leave out if the text appears once.',
    )
    whole_word: bool = Field(default=True, description='If true, "Licensee" won\'t match inside "Sublicensee".')


class ChangeRequest(BaseModel):
    """One edit, in the shape the brief suggested.

    Example:
        {
          "operation": "replace",
          "target": {"text": "Licensee", "occurrence": "all"},
          "replacement": "Customer",
          "reason": "Align with the order form",
          "source": "human"
        }
    """

    # Only "replace" for now. A deletion is a replace with "". Keeping the field
    # leaves room for future operations (e.g. "insert_after") without breaking clients.
    operation: Literal["replace"] = "replace"
    target: Target
    replacement: str = Field(description='The new text. Use "" to delete.')
    reason: str | None = Field(default=None, description="Why: shown in the history.")
    source: Literal["human", "ai"] = "human"

    def to_change(self) -> Change:
        """Convert the API shape into the plain Change that redline.py works with."""
        return Change(
            find=self.target.text,
            replace=self.replacement,
            occurrence=self.target.occurrence,
            whole_word=self.target.whole_word,
            reason=self.reason,
            source=self.source,
        )


class EditRequest(BaseModel):
    """Body for PATCH /documents/{id} and POST /documents/{id}/preview.

    Example:
        {
          "expected_version": 1,
          "author": "Qudus",
          "changes": [
            {"target": {"text": "State of California"}, "replacement": "State of Delaware"},
            {"target": {"text": "thirty (30) days", "occurrence": 2}, "replacement": "sixty (60) days"}
          ]
        }
    """

    changes: list[ChangeRequest] = Field(min_length=1)
    expected_version: int | None = Field(
        default=None,
        description="The version you were looking at. If someone saved since, you get a 409 instead of overwriting.",
    )
    author: str = "Anonymous"


class CreateDocumentRequest(BaseModel):
    """Body for POST /documents.

    Example: {"title": "Vendor Terms", "text": "# Vendor Terms\\n\\n1. Payment is due Net 45."}
    """

    title: str = Field(min_length=1)
    text: str
    author: str = "Anonymous"


# --- Responses --------------------------------------------------------------


class DocumentSummary(BaseModel):
    """One row in the document list (no full text, so the list stays small)."""

    id: str
    title: str
    file_type: str
    version: int
    updated_at: str
    size_chars: int


class DocumentOut(BaseModel):
    """A full document."""

    id: str
    title: str
    file_type: str
    version: int
    text: str
    created_at: str
    updated_at: str


class AppliedChange(BaseModel):
    """What one change actually did, e.g. {"find": "Licensee", "replace": "Customer", "count": 24}."""

    find: str
    replace: str
    occurrence: int | str | None
    count: int
    reason: str | None
    source: str


class EditResponse(BaseModel):
    """Result of PATCH: the saved document's new version and text."""

    id: str
    version: int
    text: str
    applied: list[AppliedChange]


class PreviewResponse(BaseModel):
    """Result of preview: what the text WOULD be. Nothing is saved."""

    id: str
    version: int  # the current (unchanged) version
    text_after: str
    redline_markdown: str | None  # None if the document is too large to diff
    applied: list[AppliedChange]


class SearchResult(BaseModel):
    document_id: str
    document_title: str
    position: int
    line: int
    occurrence_in_document: int
    snippet: str
    match_start: int  # where the match starts inside `snippet`
    match_end: int


class SearchResponse(BaseModel):
    query: str
    total: int
    limit: int
    offset: int
    results: list[SearchResult]


class HistoryEntry(BaseModel):
    """One version in the history (without its full text)."""

    version: int
    timestamp: str
    author: str
    changes: list[AppliedChange]


class ErrorResponse(BaseModel):
    """Every error has this shape.

    Example:
        {"error": "\\"Licensee\\" appears 24 times. Choose which one to change, or choose all.",
         "code": 422, "type": "ambiguous_match",
         "details": {"change_index": 0, "count": 24, "matches": [...]}}
    """

    error: str
    code: int
    type: str
    details: dict = {}
