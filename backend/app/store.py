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
from app.redline import Change, apply_changes

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Not a contract: house positions the AI follows (used in Phase 4).
PLAYBOOK_FILE = "playbook.md"

# id -> document dict (see _new_document for the shape)
documents: dict[str, dict] = {}

# FastAPI runs plain `def` routes in a thread pool, so two requests can edit at
# once. Every write holds this lock from "read current version" to "save".
_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed() -> None:
    """Load the sample contracts from backend/data/. Called on startup and in tests."""
    with _lock:
        documents.clear()
        for path in sorted(DATA_DIR.glob("*.md")):
            if path.name == PLAYBOOK_FILE:
                continue
            text = path.read_text(encoding="utf-8")
            doc_id = path.stem  # "mutual-nda.md" -> "mutual-nda"
            documents[doc_id] = _new_document(doc_id, title_from_text(text, path.stem), text, "md")


def list_documents() -> list[dict]:
    return list(documents.values())


def get_document(doc_id: str) -> dict:
    document = documents.get(doc_id)
    if document is None:
        raise NotFound(f'There is no document with id "{doc_id}".')
    return document


def create_document(title: str, text: str, file_type: str, author: str = "Anonymous") -> dict:
    """Add a new document (from JSON or an upload). Its id is the title as a slug plus a short random suffix."""
    doc_id = f"{slugify(title)}-{secrets.token_hex(3)}"
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
    """
    with _lock:
        document = get_document(doc_id)
        check_version(document, expected_version)
        new_text, applied = apply_changes(document["text"], changes)  # raises before saving if any change fails
        _add_version(document, new_text, author, applied)
        return document, applied


def get_version(doc_id: str, version: int) -> dict:
    document = get_document(doc_id)
    for entry in document["versions"]:
        if entry["version"] == version:
            return entry
    raise NotFound(f"Version {version} of this document doesn't exist.")


def check_version(document: dict, expected_version: int | None) -> None:
    if expected_version is not None and expected_version != document["version"]:
        raise VersionConflict(
            f"This document changed since you opened it (now v{document['version']}). Reload to see the latest.",
            {"current_version": document["version"], "expected_version": expected_version},
        )


def read_playbook() -> str:
    return (DATA_DIR / PLAYBOOK_FILE).read_text(encoding="utf-8")


def _new_document(doc_id: str, title: str, text: str, file_type: str, author: str = "System") -> dict:
    timestamp = now()
    return {
        "id": doc_id,
        "title": title,
        "file_type": file_type,  # md | txt | docx
        "text": text,
        "version": 1,
        "created_at": timestamp,
        "updated_at": timestamp,
        # Full-text snapshot per version: simple, and makes "restore" trivial.
        # Production would store diffs instead to save memory.
        "versions": [{"version": 1, "timestamp": timestamp, "author": author, "text": text, "changes": []}],
    }


def _add_version(document: dict, new_text: str, author: str, applied: list[dict]) -> None:
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
    """Use the first Markdown heading ("# Mutual NDA") as the title, if there is one."""
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback.replace("-", " ").title()


def slugify(title: str) -> str:
    """"Master Services Agreement" -> "master-services-agreement"."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "document"
