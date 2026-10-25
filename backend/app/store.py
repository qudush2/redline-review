"""In-memory document storage.

Documents live in a plain dictionary for as long as the server runs. Every read
and write goes through the functions in this file, so swapping in a real
database later only means changing this module.
"""

import re
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.errors import NotFound, VersionConflict
from app.redline import Change, apply_changes, build_redline

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Not a contract: the house positions the AI follows (see llm.py).
PLAYBOOK_FILE = "playbook.md"

# id -> document dict (see _new_document for the shape)
documents: dict[str, dict] = {}

# FastAPI runs plain `def` routes in a thread pool, so two requests can edit at
# once. Every write holds this lock from "read current version" to "save".
_lock = threading.Lock()


def now() -> str:
    """Current time as text, e.g. "2026-10-25T14:03:11.123456+00:00" (UTC)."""
    return datetime.now(timezone.utc).isoformat()


def seed() -> None:
    """Load the sample contracts from backend/data/. Called on startup and in tests.

    Example:
        backend/data/mutual-nda.md  ->  documents["mutual-nda"], version 1,
                                        title "Mutual Non-Disclosure Agreement"
        backend/data/playbook.md    ->  skipped (it's not a contract)
    """
    with _lock:
        documents.clear()
        for path in sorted(DATA_DIR.glob("*.md")):
            if path.name == PLAYBOOK_FILE:
                continue
            text = path.read_text(encoding="utf-8")
            doc_id = path.stem  # "mutual-nda.md" -> "mutual-nda"
            documents[doc_id] = _new_document(doc_id, title_from_text(text, path.stem), text, "md")


def list_documents() -> list[dict]:
    """All documents, in the order they were added."""
    return list(documents.values())


def get_document(doc_id: str) -> dict:
    """Look up one document by id.

    Examples:
        get_document("mutual-nda")  -> {"id": "mutual-nda", "title": ..., "text": ..., ...}
        get_document("nope")        -> raises NotFound (becomes a 404)
    """
    document = documents.get(doc_id)
    if document is None:
        raise NotFound(f'There is no document with id "{doc_id}".')
    return document


def create_document(title: str, text: str, file_type: str, author: str = "Anonymous") -> dict:
    """Add a new document (from JSON or an upload).

    Its id is the title as a slug plus a short random suffix, so two uploads with
    the same title don't overwrite each other.

    Example:
        create_document("Vendor Agreement (Draft)", "Hello", "txt")
            -> {"id": "vendor-agreement-draft-3f9a1c", "version": 1, ...}
    """
    doc_id = f"{slugify(title)}-{secrets.token_hex(3)}"  # token_hex(3) -> 6 random hex characters
    document = _new_document(doc_id, title, text, file_type, author)
    with _lock:
        documents[doc_id] = document
    return document


def save_changes(
    doc_id: str,
    changes: list[Change],
    author: str = "Anonymous",
    expected_version: int | None = None,
) -> tuple[dict, list[dict]]:
    """Apply changes and save them as a new version, all inside the lock.

    If the caller says which version they were looking at (expected_version) and
    someone else has saved since, we refuse with a 409 instead of overwriting.

    Examples (the MSA is at version 1):
        save_changes("master-services-agreement",
                     [Change("State of California", "State of Delaware")],
                     author="Qudus", expected_version=1)
            -> (document now at version 2, [{"find": "State of California", "count": 1, ...}])

        save_changes("master-services-agreement", [...], expected_version=1)   # called again
            -> raises VersionConflict   # the document is at version 2 now

        save_changes("master-services-agreement", [Change("not there", "x")])
            -> raises TargetNotFound; still version 2, nothing saved
    """
    # The whole read -> check -> apply -> save runs under the lock, so no other
    # request can save in between and be silently overwritten.
    with _lock:
        document = get_document(doc_id)
        check_version(document, expected_version)
        new_text, applied = apply_changes(document["text"], changes)  # raises before saving if any change fails
        _add_version(document, new_text, author, applied)
        return document, applied


def preview_changes(
    doc_id: str,
    changes: list[Change],
    expected_version: int | None = None,
) -> tuple[dict, str, str | None, list[dict]]:
    """Run the same changes as save_changes, but save nothing.

    Returns (document, text_after, redline_markdown, applied). This powers the
    accept/reject screen: the user sees the redline before anything is saved, and
    problems (ambiguous or missing text) show up while reviewing, not after clicking Accept.

    Example (MSA at version 1):
        preview_changes("master-services-agreement", [Change("State of California", "State of Delaware")])
            -> (document still at version 1,
                "...governed by the laws of the State of Delaware...",
                "...governed by the laws of the State of <del>California,</del> <ins>Delaware,</ins>...",
                [{"find": "State of California", "count": 1, ...}])
    """
    document = get_document(doc_id)
    check_version(document, expected_version)
    text_after, applied = apply_changes(document["text"], changes)
    redline_markdown = build_redline(document["text"], text_after)
    return document, text_after, redline_markdown, applied


def get_version(doc_id: str, version: int) -> dict:
    """One saved version of a document, including its full text.

    Examples:
        get_version("mutual-nda", 1)   -> {"version": 1, "author": "System", "text": ..., "changes": []}
        get_version("mutual-nda", 99)  -> raises NotFound
    """
    document = get_document(doc_id)
    for entry in document["versions"]:
        if entry["version"] == version:
            return entry
    raise NotFound(f"Version {version} of this document doesn't exist.")


def check_version(document: dict, expected_version: int | None) -> None:
    """Raise VersionConflict if the document has moved on since the caller looked.

    Examples (document is at version 3):
        check_version(document, None)  -> OK (caller didn't ask for a check)
        check_version(document, 3)     -> OK
        check_version(document, 2)     -> raises VersionConflict (becomes a 409)
    """
    if expected_version is not None and expected_version != document["version"]:
        raise VersionConflict(
            f"This document changed since you opened it (now v{document['version']}). Reload to see the latest.",
            {"current_version": document["version"], "expected_version": expected_version},
        )


def read_playbook() -> str:
    """The house playbook text, which the AI follows when suggesting edits (see llm.py)."""
    return (DATA_DIR / PLAYBOOK_FILE).read_text(encoding="utf-8")


def _new_document(doc_id: str, title: str, text: str, file_type: str, author: str = "System") -> dict:
    """Build the dictionary for a brand-new document at version 1."""
    timestamp = now()
    return {
        "id": doc_id,
        "title": title,
        "file_type": file_type,  # md | txt | docx
        "text": text,  # always the latest text
        "version": 1,
        "created_at": timestamp,
        "updated_at": timestamp,
        # Full-text snapshot per version: simple, and makes "restore" trivial.
        # Production would store diffs instead to save memory.
        "versions": [{"version": 1, "timestamp": timestamp, "author": author, "text": text, "changes": []}],
    }


def _add_version(document: dict, new_text: str, author: str, applied: list[dict]) -> None:
    """Bump the version number and record the new text plus who changed what.

    Example: a document at version 2 becomes version 3, and versions[-1] is
        {"version": 3, "author": "Qudus", "text": <new text>,
         "changes": [{"find": "Licensee", "replace": "Customer", "count": 24, "source": "human", ...}]}
    """
    timestamp = now()
    document["version"] += 1
    document["text"] = new_text
    document["updated_at"] = timestamp
    document["versions"].append(
        {
            "version": document["version"],
            "timestamp": timestamp,
            "author": author,
            "text": new_text,
            "changes": applied,
        }
    )


def title_from_text(text: str, fallback: str) -> str:
    """Use the first Markdown heading as the title, if there is one.

    Examples:
        title_from_text("# Mutual NDA\\n\\nBody...", "mutual-nda")  -> "Mutual NDA"
        title_from_text("No heading here", "vendor-terms")         -> "Vendor Terms"
    """
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()

    return fallback.replace("-", " ").title()


def slugify(title: str) -> str:
    """Turn a title into a URL-safe id.

    Examples:
        slugify("Master Services Agreement")  -> "master-services-agreement"
        slugify("Vendor Agreement (Draft)")   -> "vendor-agreement-draft"
        slugify("!!!")                        -> "document"
    """
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "document"
