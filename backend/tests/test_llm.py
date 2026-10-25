"""AI suggestions. The real Anthropic call is always replaced with a fake: no network, no API key."""

import pytest
from fastapi.testclient import TestClient

from app import llm, store
from app.errors import TooLarge
from app.main import app

MSA = "master-services-agreement"
client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_store():
    store.seed()


def fake_claude(changes):
    """Build a stand-in for llm.ask_claude that returns these changes."""

    def fake(document_text, instruction, playbook):
        return changes, "fake-model"

    return fake


# --- The guardrail -------------------------------------------------------------

def test_valid_suggestions_pass_through_as_ai_change_requests():
    text = "Fees are due Net 45. Governed by the laws of the State of Texas."
    kept, dropped = llm.validate_suggestions(text, [
        {"find": "Net 45", "replace": "Net 30", "reason": "Playbook: Net 30."},
        {"find": "State of Texas", "replace": "State of Delaware", "reason": "Playbook: Delaware law."},
    ])
    assert dropped == []
    assert [k["target"]["text"] for k in kept] == ["Net 45", "State of Texas"]
    assert all(k["source"] == "ai" for k in kept)
    assert kept[0]["reason"] == "Playbook: Net 30."


def test_hallucinated_text_is_dropped():
    kept, dropped = llm.validate_suggestions("Fees are due Net 45.", [
        {"find": "Net 60", "replace": "Net 30", "reason": "x"},
    ])
    assert kept == []
    assert dropped == [{"find": "Net 60", "why": "This text isn't in the document."}]


def test_ambiguous_text_is_dropped():
    text = "Notice is 30 days. Later, notice is 30 days."
    kept, dropped = llm.validate_suggestions(text, [{"find": "30 days", "replace": "60 days", "reason": "x"}])
    assert kept == []
    assert "appears 2 times" in dropped[0]["why"]


def test_no_op_suggestion_is_dropped():
    kept, dropped = llm.validate_suggestions("Net 45.", [{"find": "Net 45", "replace": "Net 45", "reason": "x"}])
    assert kept == []
    assert dropped[0]["why"] == "The suggestion doesn't change anything."


def test_whole_word_rule_applies_to_ai_suggestions_too():
    # "Term" appears once as a word, but also inside "Termination". Whole-word matching keeps it unique.
    kept, _ = llm.validate_suggestions("the Term and the Termination", [{"find": "Term", "replace": "Period", "reason": "x"}])
    assert len(kept) == 1


def test_suggestions_are_checked_in_order_so_accept_all_works():
    # The second suggestion edits text the first one already replaced, so it no longer applies.
    kept, dropped = llm.validate_suggestions("Payment is due Net 45.", [
        {"find": "Net 45", "replace": "Net 30", "reason": "x"},
        {"find": "due Net 45", "replace": "due Net 15", "reason": "x"},
    ])
    assert len(kept) == 1
    assert dropped[0]["find"] == "due Net 45"


def test_documents_over_the_ai_size_limit_are_rejected():
    with pytest.raises(TooLarge):
        llm.suggest_changes("x" * (llm.MAX_AI_CHARS + 1), "review", "playbook")


# --- The endpoint ---------------------------------------------------------------

def test_endpoint_returns_kept_and_dropped_suggestions(monkeypatch):
    monkeypatch.setattr(llm, "ask_claude", fake_claude([
        {"find": "shall be unlimited", "replace": "shall not exceed two times (2x) the fees paid", "reason": "Playbook: 2x cap."},
        {"find": "State of Nevada", "replace": "State of Delaware", "reason": "Made up."},
    ]))
    response = client.post(f"/documents/{MSA}/suggestions", json={"instruction": "Apply our playbook"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["suggestions"]) == 1
    assert body["suggestions"][0]["source"] == "ai"
    assert body["dropped"][0]["find"] == "State of Nevada"


def test_endpoint_saves_nothing(monkeypatch):
    monkeypatch.setattr(llm, "ask_claude", fake_claude([
        {"find": "State of California", "replace": "State of Delaware", "reason": "x"},
    ]))
    client.post(f"/documents/{MSA}/suggestions", json={"instruction": "Apply our playbook"})
    document = client.get(f"/documents/{MSA}").json()
    assert document["version"] == 1
    assert "State of California" in document["text"]


def test_ai_suggestions_can_be_applied_with_patch(monkeypatch):
    monkeypatch.setattr(llm, "ask_claude", fake_claude([
        {"find": "State of California", "replace": "State of Delaware", "reason": "Playbook"},
    ]))
    suggestions = client.post(f"/documents/{MSA}/suggestions", json={"instruction": "x"}).json()["suggestions"]
    response = client.patch(f"/documents/{MSA}", json={"changes": suggestions, "author": "Qudus"})
    assert response.status_code == 200
    history = client.get(f"/documents/{MSA}/history").json()
    assert history[0]["changes"][0]["source"] == "ai"


def test_placeholder_key_gives_a_friendly_503(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-placeholder")
    response = client.post(f"/documents/{MSA}/suggestions", json={"instruction": "Apply our playbook"})
    assert response.status_code == 503
    body = response.json()
    assert body["type"] == "ai_not_configured"
    assert "backend/.env" in body["error"]


def test_missing_key_gives_a_friendly_503(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = client.post(f"/documents/{MSA}/suggestions", json={"instruction": "Apply our playbook"})
    assert response.status_code == 503


def test_empty_instruction_is_400():
    response = client.post(f"/documents/{MSA}/suggestions", json={"instruction": ""})
    assert response.status_code == 400
