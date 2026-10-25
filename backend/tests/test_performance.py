"""Performance on a ~10MB contract.

The document is generated here (not committed). Limits are generous (2 seconds)
so the tests don't fail on a slow laptop; the point is to catch anything that
isn't roughly linear. Run with `-s` to see the timings:

    cd backend && .venv/bin/pytest tests/test_performance.py -s
"""

import time

import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app
from app.redline import Change, apply_change, build_redline
from app.matching import find_matches
from app.search import search_documents

TARGET_SIZE = 10 * 1024 * 1024  # 10MB
LIMIT_SECONDS = 2.0
UNIQUE_PHRASE = "Section 9999.9 Special Indemnity for Orbital Data Centers"

# One numbered clause, repeated to build a big contract. "Customer" appears 3
# times per clause, so a 10MB document has tens of thousands of matches.
CLAUSE = (
    "## {n}. Obligations\n\n"
    "{n}.1 Customer shall pay all undisputed fees within thirty (30) days of the invoice date. "
    "Provider shall maintain commercially reasonable safeguards to protect Customer Data against "
    "unauthorized access, use, or disclosure, and shall notify Customer of any security incident.\n\n"
)


@pytest.fixture(scope="module")
def big_text():
    pieces = []
    size = 0
    n = 1
    while size < TARGET_SIZE:
        clause = CLAUSE.format(n=n)
        pieces.append(clause)
        size += len(clause)
        n += 1

    # A unique phrase near the end, so finding it means scanning almost everything.
    pieces.insert(len(pieces) - 5, f"{UNIQUE_PHRASE}.\n\n")
    return "".join(pieces)


def timed(label, function):
    """Run `function`, print how long it took, and return (result, seconds)."""
    start = time.perf_counter()
    result = function()
    seconds = time.perf_counter() - start
    print(f"\n  {label:<55} {seconds * 1000:8.1f} ms")
    return result, seconds


def test_document_is_about_10mb(big_text):
    assert len(big_text) >= TARGET_SIZE
    print(f"\n  document size: {len(big_text) / 1024 / 1024:.1f} MB")


def test_find_all_matches_of_a_common_term(big_text):
    matches, seconds = timed("find_matches('Customer'), whole word", lambda: find_matches(big_text, "Customer"))
    assert len(matches) > 50_000
    assert seconds < LIMIT_SECONDS


def test_find_a_unique_phrase_near_the_end(big_text):
    matches, seconds = timed("find_matches(unique phrase near the end)", lambda: find_matches(big_text, UNIQUE_PHRASE))
    assert len(matches) == 1
    assert seconds < LIMIT_SECONDS


def test_replace_a_single_unique_phrase(big_text):
    change = Change(find=UNIQUE_PHRASE, replace="Section 9999.9 Mutual Indemnity")
    (new_text, summary), seconds = timed("apply_change: one unique phrase", lambda: apply_change(big_text, change))
    assert summary["count"] == 1
    assert "Mutual Indemnity" in new_text
    assert seconds < LIMIT_SECONDS


def test_replace_every_occurrence_of_a_common_term(big_text):
    change = Change(find="Customer", replace="Client", occurrence="all")
    (new_text, summary), seconds = timed("apply_change: rename 'Customer' everywhere", lambda: apply_change(big_text, change))
    assert summary["count"] > 50_000
    assert "Customer" not in new_text
    assert seconds < LIMIT_SECONDS


def test_search_across_documents_with_paging(big_text):
    documents = [{"id": "big", "title": "Big MSA", "text": big_text}]
    result, seconds = timed(
        "search_documents('customer data'), page 1",
        lambda: search_documents(documents, "customer data", limit=10),
    )
    assert result["total"] > 10_000
    assert len(result["results"]) == 10
    assert seconds < LIMIT_SECONDS


def test_search_deep_page_near_the_end(big_text):
    documents = [{"id": "big", "title": "Big MSA", "text": big_text}]
    # Counting line numbers is the slowest part for hits far into the document.
    first = search_documents(documents, "customer data", limit=1)
    result, seconds = timed(
        "search_documents('customer data'), last page",
        lambda: search_documents(documents, "customer data", limit=10, offset=first["total"] - 10),
    )
    assert len(result["results"]) == 10
    assert seconds < LIMIT_SECONDS


def test_redline_is_skipped_for_huge_documents(big_text):
    # The word-by-word diff is capped at 300k characters; above that it returns None
    # immediately and the UI falls back to change cards.
    redline, seconds = timed("build_redline on 10MB (skipped by design)", lambda: build_redline(big_text, big_text + "x"))
    assert redline is None
    assert seconds < 0.01


def test_full_api_round_trip_on_10mb(big_text):
    # Upload, rename a term everywhere via PATCH (JSON in and out), then search.
    store.seed()
    client = TestClient(app)

    response, upload_seconds = timed(
        "API: upload 10MB .md",
        lambda: client.post("/documents/upload", files={"file": ("big.md", big_text.encode(), "text/markdown")}),
    )
    assert response.status_code == 201
    doc_id = response.json()["id"]

    body = {"changes": [{"target": {"text": "Customer", "occurrence": "all"}, "replacement": "Client"}]}
    response, patch_seconds = timed("API: PATCH rename term everywhere", lambda: client.patch(f"/documents/{doc_id}", json=body))
    assert response.status_code == 200

    response, search_seconds = timed(
        "API: search one document",
        lambda: client.get(f"/documents/{doc_id}/search", params={"q": "client data"}),
    )
    assert response.json()["total"] > 10_000

    assert upload_seconds < LIMIT_SECONDS
    assert patch_seconds < LIMIT_SECONDS
    assert search_seconds < LIMIT_SECONDS
    store.seed()  # leave the store clean for other tests
