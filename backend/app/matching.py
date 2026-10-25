"""Low-level text helpers shared by editing (redline.py) and search (search.py).

They live in their own module so redline.py and search.py don't import each other.
"""

import re

from app.errors import InvalidRequest


def find_matches(text: str, find: str, whole_word: bool = True, case_sensitive: bool = True) -> list[int]:
    """Return the start position of every match of `find` in `text`, in order.

    Positions are character offsets, counting from 0.

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
    # 1. An empty search would "match" everywhere, so refuse it.
    if not find:
        raise InvalidRequest("The text to find can't be empty.")

    # 2. Turn the user's text into a regex pattern. re.escape makes special
    #    characters literal: "(30)" becomes "\(30\)", "$5.00" becomes "\$5\.00".
    pattern = re.escape(find)

    # 3. Whole-word rule: no letter, digit, or underscore may touch the match.
    #    (?<!\w) means "the character before is not a word character".
    #    (?!\w)  means "the character after is not a word character".
    #    So "Licensee" can't match inside "Sublicensee" or "Licensees".
    #    We only add a check on a side that is itself a letter or digit. That way
    #    "(a)" still matches in "1(a)": its edges are punctuation, not words.
    #    (We avoid \b because it behaves oddly next to punctuation.)
    if whole_word:
        if re.match(r"\w", find[0]):
            pattern = r"(?<!\w)" + pattern
        if re.match(r"\w", find[-1]):
            pattern = pattern + r"(?!\w)"

    # 4. Case-sensitive unless asked otherwise ("Company" is not "company").
    flags = 0 if case_sensitive else re.IGNORECASE

    # 5. One pass over the text; collect where each match starts.
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
    # 1. Pick the window: `radius` characters on each side of the match,
    #    without running past the start or end of the text.
    snippet_start = max(0, start - radius)
    snippet_end = min(len(text), end + radius)

    # 2. Cut it out. Newlines become spaces so the snippet reads as one line.
    #    A newline and a space are both 1 character, so offsets still line up.
    body = text[snippet_start:snippet_end].replace("\n", " ")

    # 3. Add "…" on a side only if we actually cut text off on that side.
    prefix = "…" if snippet_start > 0 else ""
    suffix = "…" if snippet_end < len(text) else ""

    # 4. Work out where the match sits inside the final snippet string.
    #    Shift by the "…" we may have added at the front.
    return {
        "snippet": prefix + body + suffix,
        "match_start": len(prefix) + (start - snippet_start),
        "match_end": len(prefix) + (end - snippet_start),
    }
