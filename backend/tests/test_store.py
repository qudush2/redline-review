import pytest

from app import store
from app.errors import NotFound, TargetNotFound, VersionConflict
from app.redline import Change


@pytest.fixture(autouse=True)
def fresh_store():
    store.seed()


def test_seed_loads_sample_contracts_but_not_the_playbook():
    ids = {doc["id"] for doc in store.list_documents()}
    assert ids == {"master-services-agreement", "mutual-nda", "employment-agreement"}
    assert store.get_document("mutual-nda")["title"] == "Mutual Non-Disclosure Agreement"


def test_unknown_document_raises_not_found():
    with pytest.raises(NotFound):
        store.get_document("nope")


def test_saving_changes_creates_a_new_version_with_attribution():
    change = Change(find="State of California", replace="State of Delaware", reason="Playbook", source="ai")
    document, applied = store.save_changes("master-services-agreement", [change], author="Qudus", expected_version=1)

    assert document["version"] == 2
    assert "State of Delaware" in document["text"]
    latest = document["versions"][-1]
    assert latest["author"] == "Qudus"
    assert latest["changes"][0]["source"] == "ai"
    assert latest["changes"][0]["reason"] == "Playbook"
    # The original is kept as version 1.
    assert "State of California" in store.get_version("master-services-agreement", 1)["text"]


def test_stale_expected_version_is_a_conflict():
    store.save_changes("master-services-agreement", [Change(find="State of California", replace="State of Delaware")])
    with pytest.raises(VersionConflict) as caught:
        store.save_changes("master-services-agreement", [Change(find="Net", replace="Gross")], expected_version=1)
    assert caught.value.details["current_version"] == 2


def test_failed_change_saves_nothing():
    before = store.get_document("master-services-agreement")["text"]
    changes = [
        Change(find="State of California", replace="State of Delaware"),
        Change(find="text that is not there", replace="x"),
    ]
    with pytest.raises(TargetNotFound):
        store.save_changes("master-services-agreement", changes)

    document = store.get_document("master-services-agreement")
    assert document["version"] == 1
    assert document["text"] == before


def test_created_documents_get_a_readable_unique_id():
    document = store.create_document("Vendor Agreement (Draft)", "Hello", "txt")
    assert document["id"].startswith("vendor-agreement-draft-")
    assert store.get_document(document["id"])["text"] == "Hello"
