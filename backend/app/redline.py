"""Core editing logic. Pure functions: text in, text out. No web framework here.

An edit targets *text* ("find 'Delaware', replace with 'New York'"), not character
positions. That's how lawyers and LLMs describe edits, and positions go stale
after any earlier edit. If the text isn't there, we fail loudly instead of guessing.
"""

import difflib
import re
from dataclasses import dataclass

from app.errors import AmbiguousTarget, AppError, InvalidRequest, OccurrenceOutOfRange, TargetNotFound
from app.matching import find_matches, make_snippet

# Above this size we skip building the inline redline (word-by-word comparison
# gets slow). The UI still shows each change as a card.
MAX_REDLINE_CHARS = 300_000

# Markdown characters for bold/italic/code. Kept outside redline tags when shared.
MARKDOWN_MARKERS = ("*", "_", "`")

# How many example matches to include when an edit is ambiguous.
MAX_AMBIGUOUS_EXAMPLES = 20


@dataclass
class Change:
    """One requested edit.

    occurrence: None  -> the text must appear exactly once
                1, 2… -> change only that match (1-based)
                "all" -> change every match (e.g. renaming a defined term)
    """

    find: str
    replace: str
    occurrence: int | str | None = None
    whole_word: bool = True
    reason: str | None = None
    source: str = "human"  # "human" or "ai"


def apply_change(text: str, change: Change) -> tuple[str, dict]:
    """Apply one change. Returns the new text and a summary of what happened."""
    matches = find_matches(text, change.find, whole_word=change.whole_word)
    count = len(matches)

    if count == 0:
        raise TargetNotFound(
            f'Couldn\'t find "{change.find}" in this document.',
            {"find": change.find},
        )

    if change.occurrence == "all":
        chosen = matches
    elif change.occurrence is None:
        # Editing the wrong clause is the worst failure, so we never guess.
        if count > 1:
            raise AmbiguousTarget(
                f'"{change.find}" appears {count} times. Choose which one to change, or choose all.',
                {"find": change.find, "count": count, "matches": describe_matches(text, change.find, matches)},
            )
        chosen = matches
    elif isinstance(change.occurrence, int):
        if change.occurrence < 1 or change.occurrence > count:
            raise OccurrenceOutOfRange(
                f'"{change.find}" appears {count} time(s), so there is no occurrence {change.occurrence}.',
                {"find": change.find, "count": count, "occurrence": change.occurrence},
            )
        chosen = [matches[change.occurrence - 1]]
    else:
        raise InvalidRequest('Occurrence must be a number (1, 2, …) or "all".')

    new_text = replace_at(text, chosen, len(change.find), change.replace)
    summary = {
        "find": change.find,
        "replace": change.replace,
        "occurrence": change.occurrence,
        "count": len(chosen),
        "reason": change.reason,
        "source": change.source,
    }
    return new_text, summary


def apply_changes(text: str, changes: list[Change]) -> tuple[str, list[dict]]:
    """Apply several changes in order, all-or-nothing.

    Each change sees the text as left by the previous one. If any change fails we
    raise, and the caller never saves anything: a half-applied redline is worse
    than none. (Strings are immutable, so the original text is never touched.)
    """
    current = text
    applied = []
    for index, change in enumerate(changes):
        try:
            current, summary = apply_change(current, change)
        except AppError as error:
            # Say which change failed, so the UI can point at the right card.
            error.details["change_index"] = index
            if len(changes) > 1:
                error.message = f"Change {index + 1}: {error.message}"
            raise
        applied.append(summary)
    return current, applied


def replace_at(text: str, positions: list[int], length: int, replacement: str) -> str:
    """Replace `length` characters at each position. Positions must be in order.

    Builds the result from pieces in one pass, so it stays fast on huge documents.
    Plain slicing (not a regex) means a backslash in the replacement stays a backslash.
    """
    pieces = []
    last_end = 0
    for start in positions:
        pieces.append(text[last_end:start])
        pieces.append(replacement)
        last_end = start + length
    pieces.append(text[last_end:])
    return "".join(pieces)


def describe_matches(text: str, find: str, positions: list[int]) -> list[dict]:
    """Short snippets for the first few matches, so the user can pick the right one."""
    examples = []
    for number, start in enumerate(positions[:MAX_AMBIGUOUS_EXAMPLES], start=1):
        snippet = make_snippet(text, start, start + len(find), radius=60)
        examples.append({"occurrence": number, **snippet})
    return examples


def build_redline(before: str, after: str) -> str | None:
    """Show the difference between two texts as Markdown with <del>/<ins> tags.

    We compare word by word (keeping the whitespace between words), which reads
    like track changes in Word. Returns None for very large documents.
    """
    if len(before) > MAX_REDLINE_CHARS or len(after) > MAX_REDLINE_CHARS:
        return None

    # Each token is a word plus the whitespace after it: ["thirty ", "(30) ", "days"].
    # Keeping the space attached means "thirty (30)" -> "sixty (60)" shows as ONE
    # edit, not two edits split by an "unchanged" space.
    old_tokens = re.findall(r"\S+\s*|\s+", before)
    new_tokens = re.findall(r"\S+\s*|\s+", after)
    matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens, autojunk=False)

    pieces = []
    for operation, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        old_chunk = "".join(old_tokens[old_start:old_end])
        new_chunk = "".join(new_tokens[new_start:new_end])
        if operation == "equal":
            pieces.append(old_chunk)
        elif operation == "delete":
            pieces.append(wrap_in_tag("del", old_chunk))
        elif operation == "insert":
            pieces.append(wrap_in_tag("ins", new_chunk))
        else:  # replace
            prefix, old_core, new_core, suffix = split_shared_formatting(old_chunk, new_chunk)
            pieces.append(prefix + wrap_in_tag("del", old_core) + wrap_in_tag("ins", new_core) + suffix)
    return "".join(pieces)


def split_shared_formatting(old: str, new: str) -> tuple[str, str, str, str]:
    """Keep shared Markdown markers outside the redline tags.

    Renaming **"Licensee"** to **"Customer"** should give
    **"<del>Licensee</del><ins>Customer</ins>"** and not split the ** pair across a
    tag, which would break the bold. We peel off punctuation that both sides
    share at the start and end, but only if it contains a formatting marker.
    """
    shortest = min(len(old), len(new))

    start = 0
    while start < shortest and old[start] == new[start] and not old[start].isalnum():
        start += 1

    end = 0
    while end < shortest - start and old[-1 - end] == new[-1 - end] and not old[-1 - end].isalnum():
        end += 1

    prefix = old[:start]
    suffix = old[len(old) - end :]
    if not any(marker in prefix for marker in MARKDOWN_MARKERS):
        prefix, start = "", 0
    if not any(marker in suffix for marker in MARKDOWN_MARKERS):
        suffix, end = "", 0

    return prefix, old[start : len(old) - end], new[start : len(new) - end], suffix


def wrap_in_tag(tag: str, chunk: str) -> str:
    """Wrap text in <tag>…</tag>, but never across a line break.

    A newline inside an HTML tag would break Markdown paragraphs, so we close
    the tag before each line break and reopen it after. Spaces at the edges also
    stay outside the tag, so the strikethrough/underline covers only the words.
    """
    pieces = []
    for part in re.split(r"(\n+)", chunk):
        if part.strip() == "":
            pieces.append(part)  # line breaks and bare spaces stay outside the tag
            continue
        words = part.strip()
        leading = part[: len(part) - len(part.lstrip())]
        trailing = part[len(part.rstrip()) :]
        pieces.append(f"{leading}<{tag}>{words}</{tag}>{trailing}")
    return "".join(pieces)
