import pytest

from app.errors import AmbiguousTarget, InvalidRequest, OccurrenceOutOfRange, TargetNotFound
from app.matching import find_matches
from app.redline import Change, apply_change, apply_changes, build_redline

CONTRACT = (
    "Fees are due within thirty (30) days of the invoice date.\n"
    "Either Party may terminate on thirty (30) days' notice.\n"
    "Licensee may appoint a Sublicensee. Licensee remains liable."
)


# --- find_matches ---------------------------------------------------------

def test_find_matches_returns_start_positions():
    assert find_matches("a cat and a cat", "cat") == [2, 12]


def test_whole_word_skips_matches_inside_longer_words():
    text = "the Term and its Termination"
    assert len(find_matches(text, "Term")) == 1
    assert len(find_matches(text, "Term", whole_word=False)) == 2


def test_whole_word_works_for_text_with_punctuation_edges():
    # "(a)" starts and ends with punctuation; it should still match after "1".
    assert find_matches("Section 1(a) applies", "(a)") == [9]


def test_find_is_case_sensitive_by_default():
    text = "the Company and a company"
    assert len(find_matches(text, "Company")) == 1
    assert len(find_matches(text, "Company", case_sensitive=False)) == 2


def test_special_regex_characters_are_matched_literally():
    assert find_matches("costs $5.00 or $5x00", "$5.00", whole_word=False) == [6]


def test_empty_find_is_rejected():
    with pytest.raises(InvalidRequest):
        find_matches("anything", "")


# --- apply_change ---------------------------------------------------------

def test_single_match_is_replaced():
    new_text, summary = apply_change(CONTRACT, Change(find="invoice date", replace="receipt date"))
    assert "within thirty (30) days of the receipt date" in new_text
    assert summary["count"] == 1


def test_specific_occurrence_is_replaced():
    new_text, _ = apply_change(CONTRACT, Change(find="thirty (30) days", replace="sixty (60) days", occurrence=2))
    assert "due within thirty (30) days" in new_text  # first one untouched
    assert "terminate on sixty (60) days' notice" in new_text


def test_all_occurrences_are_replaced_and_counted():
    new_text, summary = apply_change(CONTRACT, Change(find="Licensee", replace="Customer", occurrence="all"))
    assert summary["count"] == 2
    assert "Customer may appoint" in new_text
    assert "Customer remains liable" in new_text
    assert "Sublicensee" in new_text  # whole-word matching left this alone


def test_ambiguous_match_is_rejected_with_count_and_snippets():
    with pytest.raises(AmbiguousTarget) as caught:
        apply_change(CONTRACT, Change(find="thirty (30) days", replace="sixty (60) days"))
    details = caught.value.details
    assert details["count"] == 2
    assert [m["occurrence"] for m in details["matches"]] == [1, 2]
    first = details["matches"][0]
    assert first["snippet"][first["match_start"] : first["match_end"]] == "thirty (30) days"


def test_missing_text_is_rejected():
    with pytest.raises(TargetNotFound) as caught:
        apply_change(CONTRACT, Change(find="State of Delaware", replace="State of New York"))
    assert 'Couldn\'t find "State of Delaware"' in caught.value.message


def test_occurrence_out_of_range_is_rejected():
    with pytest.raises(OccurrenceOutOfRange):
        apply_change(CONTRACT, Change(find="Licensee", replace="Customer", occurrence=3))


def test_case_sensitive_edit_leaves_other_casing_alone():
    text = "the Company hired a company"
    new_text, _ = apply_change(text, Change(find="Company", replace="Employer"))
    assert new_text == "the Employer hired a company"


def test_empty_replacement_deletes_text():
    new_text, _ = apply_change("one two three", Change(find=" two", replace="", whole_word=False))
    assert new_text == "one three"


def test_backslashes_in_replacement_are_inserted_literally():
    # With a regex replacement, "\1" or "\n" would be interpreted. We use slicing, so they aren't.
    new_text, _ = apply_change("path: here", Change(find="here", replace=r"C:\new\1"))
    assert new_text == r"path: C:\new\1"


# --- apply_changes (bulk, all-or-nothing) ---------------------------------

def test_multiple_changes_apply_in_order():
    changes = [
        Change(find="Licensee", replace="Customer", occurrence="all"),
        Change(find="Customer remains", replace="Customer stays"),  # sees the result of change 1
    ]
    new_text, applied = apply_changes(CONTRACT, changes)
    assert "Customer stays liable" in new_text
    assert [a["count"] for a in applied] == [2, 1]


def test_failing_change_stops_everything_and_reports_which_one():
    changes = [
        Change(find="invoice date", replace="receipt date"),
        Change(find="does not exist", replace="anything"),
    ]
    with pytest.raises(TargetNotFound) as caught:
        apply_changes(CONTRACT, changes)
    assert caught.value.details["change_index"] == 1
    assert caught.value.message.startswith("Change 2:")
    # Nothing is returned on failure, so there is no partially edited text to save.


# --- build_redline --------------------------------------------------------

def test_redline_marks_deleted_and_inserted_words():
    redline = build_redline("Payment is due in thirty days.", "Payment is due in sixty days.")
    assert redline == "Payment is due in <del>thirty</del> <ins>sixty</ins> days."


def test_redline_groups_a_multi_word_edit_into_one_mark():
    redline = build_redline("upon thirty (30) days' notice", "upon sixty (60) days' notice")
    assert redline == "upon <del>thirty (30)</del> <ins>sixty (60)</ins> days' notice"


def test_redline_keeps_bold_markers_outside_the_tags():
    redline = build_redline('a company (**"Licensee"**). Next', 'a company (**"Customer"**). Next')
    assert redline == 'a company (**"<del>Licensee</del> <ins>Customer</ins>"**). Next'


def test_redline_keeps_a_replacement_at_the_end_of_a_paragraph_in_that_paragraph():
    # The paragraph break must come after both tags, not between them.
    redline = build_redline("Liability shall be unlimited.\n\nNext clause.", "Liability shall be capped at 2x fees.\n\nNext clause.")
    assert redline == "Liability shall be <del>unlimited.</del> <ins>capped at 2x fees.</ins>\n\nNext clause."


def test_redline_never_puts_a_newline_inside_a_tag():
    redline = build_redline("keep\nold line\nend", "keep\nend")
    assert "<del>old line</del>" in redline
    for tag_text in redline.split("<del>")[1:]:
        assert "\n" not in tag_text.split("</del>")[0]


def test_redline_is_skipped_for_huge_documents():
    huge = "word " * 100_000  # 500k characters
    assert build_redline(huge, huge + "more") is None
