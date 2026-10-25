"""Low-level text helpers shared by editing (redline.py) and search (search.py).

They live in their own module so redline.py and search.py don't import each other.
"""

import re

from app.errors import InvalidRequest


def find_matches(text: str, find: str, whole_word: bool = True, case_sensitive: bool = True) -> list[int]:
    """Return the start position of every match of `find` in `text`, in order.

    Positions are character offsets, counting from 0. One linear pass with a
    regex; the user's text is escaped, so "(30)" or "$5.00" match literally.

    Examples:
        find_matches("a cat and a cat", "cat")
            -> [2, 12]           # "cat" starts at index 2 and at index 12

        find_matches("the Term and its Termination", "Term")
            -> [4]               # whole_word=True skips "Termination"

        find_matches("the Term and its Termination", "Term", whole_word=False)
            -> [4, 17]           # without whole_word, "Termination" counts too

        find_matches("the Company and a company", "Company")
            -> [4]               # case-sensitive by default: "company" is skipped

        find_matches("the Company and a company", "Company", case_sensitive=False)
            -> [4, 18]

        find_matches("Section 1(a) applies", "(a)")
            -> [9]               # "(" and ")" are matched literally, not as regex syntax

        find_matches("anything", "")
            -> raises InvalidRequest
    """
    if not find:
        raise InvalidRequest("The text to find can't be empty.")

    pattern = re.escape(find)

    # Whole word: no letter or digit may touch the match, so "Licensee" can't
    # match inside "Sublicensee". The check is only added on an edge that is
    # itself a word character, so "(a)" still matches in "1(a)". (\b behaves
    # oddly next to punctuation, so we use lookarounds instead.)
    if whole_word:
        if re.match(r"\w", find[0]):
            pattern = r"(?<!\w)" + pattern
        if re.match(r"\w", find[-1]):
            pattern = pattern + r"(?!\w)"

    flags = 0 if case_sensitive else re.IGNORECASE
    return [match.start() for match in re.finditer(pattern, text, flags)]


def make_snippet(text: str, start: int, end: int, radius: int = 80) -> dict:
    """Cut a short window of text around a match, for display.

    Returns the snippet plus where the match sits *inside the snippet*, so the
    frontend can bold it without the API sending any HTML.

    Examples:
        make_snippet("a MATCH b", 2, 7)
            -> {"snippet": "a MATCH b", "match_start": 2, "match_end": 7}
               # short text: nothing is cut, so no "…"

        make_snippet("xxxxxxxxxxMATCHyyyyyyyyyy", 10, 15, radius=3)
            -> {"snippet": "…xxxMATCHyyy…", "match_start": 4, "match_end": 9}
               # cut on both sides, so both ends get "…"
               # snippet[4:9] == "MATCH"

        make_snippet("line one\\nMATCH here", 9, 14)
            -> {"snippet": "line one MATCH here", ...}
               # the newline becomes a space so it reads as one line
    """
    snippet_start = max(0, start - radius)
    snippet_end = min(len(text), end + radius)

    # A newline and a space are both one character, so offsets still line up.
    body = text[snippet_start:snippet_end].replace("\n", " ")
    prefix = "…" if snippet_start > 0 else ""
    suffix = "…" if snippet_end < len(text) else ""

    return {
        "snippet": prefix + body + suffix,
        "match_start": len(prefix) + (start - snippet_start),
        "match_end": len(prefix) + (end - snippet_start),
    }
