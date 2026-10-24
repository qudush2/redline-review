"""Low-level text helpers shared by editing (redline.py) and search (search.py).

They live in their own module so redline.py and search.py don't import each other.
"""

import re

from app.errors import InvalidRequest


def find_matches(text: str, find: str, whole_word: bool = True, case_sensitive: bool = True) -> list[int]:
    """Return the start position of every match of `find` in `text`, in order.

    One linear pass with a regex. The user's text is escaped, so characters like
    "(" or "." are matched literally, never treated as regex syntax.
    """
    if not find:
        raise InvalidRequest("The text to find can't be empty.")

    pattern = re.escape(find)

    # Whole-word: a match can't have a letter or digit glued to either side,
    # so "Licensee" won't match inside "Sublicensee".
    # We only add the check on a side that is itself a word character. That way
    # "(a)" still matches in "1(a)": its edges are punctuation, not words.
    # (We avoid \b because it behaves oddly next to punctuation.)
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
    """
    snippet_start = max(0, start - radius)
    snippet_end = min(len(text), end + radius)

    # Newlines become spaces so the snippet reads as one line. Same length, so offsets still line up.
    body = text[snippet_start:snippet_end].replace("\n", " ")
    prefix = "…" if snippet_start > 0 else ""
    suffix = "…" if snippet_end < len(text) else ""

    return {
        "snippet": prefix + body + suffix,
        "match_start": len(prefix) + (start - snippet_start),
        "match_end": len(prefix) + (end - snippet_start),
    }
