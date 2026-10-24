import pytest

from app.errors import InvalidRequest
from app.matching import make_snippet
from app.search import search_documents

DOCUMENTS = [
    {"id": "msa", "title": "MSA", "text": "Intro line\nLimitation of Liability applies.\nliability again"},
    {"id": "nda", "title": "NDA", "text": "No LIABILITY here.\nOther text."},
]


def test_search_is_case_insensitive_across_documents():
    result = search_documents(DOCUMENTS, "liability")
    assert result["total"] == 3
    assert [r["document_id"] for r in result["results"]] == ["msa", "msa", "nda"]


def test_results_include_line_and_occurrence_numbers():
    first, second, _ = search_documents(DOCUMENTS, "liability")["results"]
    assert first["line"] == 2
    assert second["line"] == 3
    assert second["occurrence_in_document"] == 2


def test_snippet_offsets_point_at_the_match():
    for hit in search_documents(DOCUMENTS, "liability")["results"]:
        assert hit["snippet"][hit["match_start"] : hit["match_end"]].lower() == "liability"


def test_paging_with_limit_and_offset_keeps_exact_total():
    result = search_documents(DOCUMENTS, "liability", limit=1, offset=1)
    assert result["total"] == 3
    assert len(result["results"]) == 1
    assert result["results"][0]["line"] == 3


def test_search_can_be_limited_to_one_document():
    result = search_documents(DOCUMENTS, "liability", document_ids=["nda"])
    assert result["total"] == 1
    assert result["results"][0]["document_title"] == "NDA"


def test_no_results_is_an_empty_list_not_an_error():
    result = search_documents(DOCUMENTS, "indemnification")
    assert result["total"] == 0
    assert result["results"] == []


def test_empty_query_is_rejected():
    with pytest.raises(InvalidRequest):
        search_documents(DOCUMENTS, "   ")


def test_snippet_adds_ellipses_only_when_text_is_cut():
    text = "x" * 200 + "MATCH" + "y" * 200
    snippet = make_snippet(text, 200, 205, radius=10)
    assert snippet["snippet"] == "…" + "x" * 10 + "MATCH" + "y" * 10 + "…"
    assert snippet["snippet"][snippet["match_start"] : snippet["match_end"]] == "MATCH"

    short = make_snippet("a MATCH b", 2, 7)
    assert short["snippet"] == "a MATCH b"
