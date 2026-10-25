"""End-to-end tests through HTTP, using FastAPI's TestClient (no real server needed)."""

import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app
from tests.docx_builder import build_docx

MSA = "master-services-agreement"

# raise_server_exceptions=False lets us test the 500 handler instead of the test crashing.
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def fresh_store():
    # Every test starts from the original sample contracts.
    store.seed()


def edit_body(text, replacement, occurrence=None, expected_version=None, **extra):
    """Build a one-change request body, so tests stay short."""
    target = {"text": text}
    if occurrence is not None:
        target["occurrence"] = occurrence
    body = {"changes": [{"operation": "replace", "target": target, "replacement": replacement, **extra}]}
    if expected_version is not None:
        body["expected_version"] = expected_version
    return body


def assert_error_shape(response, status, error_type):
    """Every error must look like {"error": str, "code": int, "type": str, "details": dict}."""
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error", "code", "type", "details"}
    assert body["code"] == status
    assert body["type"] == error_type
    assert isinstance(body["error"], str) and body["error"]
    return body


# --- Reads --------------------------------------------------------------------

def test_list_documents_returns_summaries_without_text():
    response = client.get("/documents")
    assert response.status_code == 200
    documents = response.json()
    assert {d["id"] for d in documents} == {MSA, "mutual-nda", "employment-agreement"}
    assert "text" not in documents[0]
    assert documents[0]["size_chars"] > 0


def test_get_document_returns_full_text_and_version():
    body = client.get(f"/documents/{MSA}").json()
    assert body["version"] == 1
    assert "State of California" in body["text"]


def test_unknown_document_is_404_in_our_error_shape():
    assert_error_shape(client.get("/documents/nope"), 404, "not_found")


def test_unknown_route_is_404_in_our_error_shape():
    assert_error_shape(client.get("/no-such-endpoint"), 404, "not_found")


# --- Edits --------------------------------------------------------------------

def test_patch_returns_updated_text_and_bumps_version():
    response = client.patch(f"/documents/{MSA}", json=edit_body("State of California", "State of Delaware"))
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2
    assert "State of Delaware" in body["text"]
    assert body["applied"][0]["count"] == 1


def test_patch_with_occurrence_all_renames_a_defined_term():
    body = client.patch(f"/documents/{MSA}", json=edit_body("Licensee", "Customer", occurrence="all")).json()
    assert body["applied"][0]["count"] == 24
    assert "Licensee" not in body["text"]
    assert "Sublicensee" in body["text"]


def test_patch_with_stale_version_is_409_with_current_version():
    client.patch(f"/documents/{MSA}", json=edit_body("State of California", "State of Delaware"))
    response = client.patch(f"/documents/{MSA}", json=edit_body("Net", "Gross", expected_version=1))
    body = assert_error_shape(response, 409, "version_conflict")
    assert body["details"]["current_version"] == 2


def test_ambiguous_edit_is_422_and_lists_the_matches():
    response = client.patch(f"/documents/{MSA}", json=edit_body("thirty (30) days", "sixty (60) days"))
    body = assert_error_shape(response, 422, "ambiguous_match")
    assert body["details"]["count"] == 2
    assert len(body["details"]["matches"]) == 2
    assert body["details"]["change_index"] == 0


def test_missing_text_is_422_target_not_found():
    response = client.patch(f"/documents/{MSA}", json=edit_body("State of Nevada", "State of Delaware"))
    assert_error_shape(response, 422, "target_not_found")


def test_occurrence_out_of_range_is_422():
    response = client.patch(f"/documents/{MSA}", json=edit_body("thirty (30) days", "x", occurrence=5))
    assert_error_shape(response, 422, "occurrence_out_of_range")


def test_failed_bulk_edit_saves_nothing():
    body = {"changes": [
        {"target": {"text": "State of California"}, "replacement": "State of Delaware"},
        {"target": {"text": "not in the contract"}, "replacement": "x"},
    ]}
    assert client.patch(f"/documents/{MSA}", json=body).status_code == 422
    document = client.get(f"/documents/{MSA}").json()
    assert document["version"] == 1
    assert "State of California" in document["text"]


def test_invalid_payload_is_400_with_readable_problems():
    response = client.patch(f"/documents/{MSA}", json={"changes": []})
    body = assert_error_shape(response, 400, "invalid_request")
    assert body["details"]["problems"][0]["field"] == "changes"


def test_occurrence_zero_is_rejected_as_invalid():
    response = client.patch(f"/documents/{MSA}", json=edit_body("Licensee", "Customer", occurrence=0))
    assert_error_shape(response, 400, "invalid_request")


def test_unexpected_errors_are_500_with_a_generic_message(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("database exploded")

    monkeypatch.setattr(store, "list_documents", broken)
    body = assert_error_shape(client.get("/documents"), 500, "server_error")
    assert "database exploded" not in body["error"]  # internal details are never shown


# --- Preview ------------------------------------------------------------------

def test_preview_returns_redline_and_does_not_save():
    response = client.post(f"/documents/{MSA}/preview", json=edit_body("State of California", "State of Delaware"))
    assert response.status_code == 200
    body = response.json()
    assert "<del>California,</del> <ins>Delaware,</ins>" in body["redline_markdown"]
    assert "State of Delaware" in body["text_after"]

    document = client.get(f"/documents/{MSA}").json()
    assert document["version"] == 1
    assert "State of California" in document["text"]


# --- History ------------------------------------------------------------------

def test_history_is_newest_first_with_attribution_and_no_full_text():
    client.patch(
        f"/documents/{MSA}",
        json={**edit_body("State of California", "State of Delaware", reason="Playbook", source="ai"), "author": "Qudus"},
    )
    history = client.get(f"/documents/{MSA}/history").json()
    assert [entry["version"] for entry in history] == [2, 1]
    assert history[0]["author"] == "Qudus"
    assert history[0]["changes"][0]["source"] == "ai"
    assert history[0]["changes"][0]["reason"] == "Playbook"
    assert "text" not in history[0]


# --- Search -------------------------------------------------------------------

def test_search_across_all_documents():
    body = client.get("/documents/search", params={"q": "governed by"}).json()
    assert body["total"] == 3  # one governing-law clause per contract
    assert {r["document_id"] for r in body["results"]} == {MSA, "mutual-nda", "employment-agreement"}


def test_search_within_one_document():
    body = client.get(f"/documents/{MSA}/search", params={"q": "thirty (30) days"}).json()
    assert body["total"] == 2
    assert all(r["document_id"] == MSA for r in body["results"])


def test_search_paging():
    body = client.get("/documents/search", params={"q": "Licensee", "limit": 5, "offset": 5}).json()
    assert body["total"] > 10
    assert len(body["results"]) == 5
    assert body["results"][0]["occurrence_in_document"] == 6


def test_empty_search_is_400():
    assert_error_shape(client.get("/documents/search", params={"q": " "}), 400, "invalid_request")


def test_search_limit_over_100_is_400():
    assert_error_shape(client.get("/documents/search", params={"q": "a", "limit": 500}), 400, "invalid_request")


# --- Create and upload --------------------------------------------------------

def test_create_document_from_json():
    response = client.post("/documents", json={"title": "Vendor Terms", "text": "Net 45."})
    assert response.status_code == 201
    created = response.json()
    assert created["id"].startswith("vendor-terms-")
    assert client.get(f"/documents/{created['id']}").status_code == 200


def test_upload_txt():
    response = client.post("/documents/upload", files={"file": ("side-letter.txt", b"Fees are due Net 45.", "text/plain")})
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "side-letter"
    assert body["file_type"] == "txt"
    assert body["text"] == "Fees are due Net 45."


def test_upload_docx_with_custom_title():
    data = build_docx([("heading", "Vendor Agreement"), ("paragraph", [("Net 45.", False)])])
    response = client.post(
        "/documents/upload",
        files={"file": ("vendor.docx", data, "application/octet-stream")},
        data={"title": "Blue Heron Vendor Agreement"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Blue Heron Vendor Agreement"
    assert body["file_type"] == "docx"
    assert "# Vendor Agreement" in body["text"]


def test_upload_pdf_is_415():
    response = client.post("/documents/upload", files={"file": ("signed.pdf", b"%PDF-1.4", "application/pdf")})
    assert_error_shape(response, 415, "unsupported_file_type")


def test_uploaded_document_can_be_edited_and_searched():
    created = client.post("/documents/upload", files={"file": ("terms.txt", b"Payment is due Net 45.", "text/plain")}).json()
    client.patch(f"/documents/{created['id']}", json=edit_body("Net 45", "Net 30"))
    body = client.get(f"/documents/{created['id']}/search", params={"q": "net 30"}).json()
    assert body["total"] == 1
