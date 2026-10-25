"""AI-suggested edits, with a guardrail.

The AI only SUGGESTS. It never changes a document. Every suggestion comes back
in the same shape as a human edit (find / replace / reason), and before anyone
sees it we check it against the real document text:
  - "find" text that isn't in the document (a hallucination) -> dropped
  - "find" text that appears more than once (ambiguous)      -> dropped
We tell the user how many were dropped and why.

Tests never call the real API: they replace `ask_claude` with a fake.
"""

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from app.errors import AINotConfigured, AIServiceError, AppError, TooLarge
from app.redline import Change, apply_change

# Read backend/.env (if it exists) into environment variables.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DEFAULT_MODEL = "claude-sonnet-5-5"
PLACEHOLDER_KEY_PREFIX = "sk-ant-placeholder"

# Above this size we don't send the document to the AI (next step: review long contracts by section).
MAX_AI_CHARS = 150_000

# The JSON shape the AI must reply with; structured outputs make the API guarantee it.
# Example: {"changes": [{"find": "State of California", "replace": "State of Delaware",
#                         "reason": "Playbook: governing law must be Delaware."}]}
SUGGESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "find": {"type": "string"},
                    "replace": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["find", "replace", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["changes"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are a contract-redlining assistant for an in-house legal team.

You propose edits to a contract. A lawyer reviews every edit before anything changes, so be precise and conservative.

Follow the user's instruction AND the company's playbook (house positions). When the playbook covers a topic, use the playbook's position rather than a generic one.

Rules for each edit:
- "find" must be copied EXACTLY from the contract: same words, punctuation, capitalization, and Markdown symbols. Our system matches it character for character, and an edit whose "find" text doesn't match is discarded.
- "find" must appear only once in the contract. Include a few surrounding words if needed to make it unique.
- Keep "find" within a single sentence, and don't let it start or end in the middle of **bold** markers.
- Keep edits minimal and surgical: change only the words that need to change, not whole paragraphs.
- "reason" is one short sentence explaining the edit. Cite the playbook when it applies (e.g. "Playbook: cap liability at 2x annual fees.").
- If nothing needs to change, return an empty list."""


def suggest_changes(document_text: str, instruction: str, playbook: str) -> dict:
    """Ask the AI for edits, then keep only the ones that apply cleanly.

    Returns {"suggestions": [...], "dropped": [...], "model": "..."}. Each suggestion
    is in the same shape as a human change request, with "source": "ai".

    Example (instruction "Bring this in line with our playbook", MSA text):
        -> {"suggestions": [
               {"operation": "replace", "target": {"text": "shall be unlimited"},
                "replacement": "shall not exceed two times (2x) the fees paid ...",
                "reason": "Playbook: cap liability at 2x annual fees.", "source": "ai"},
               ...],
            "dropped": [{"find": "State of Nevada", "why": "This text isn't in the document."}],
            "model": "claude-sonnet-5-5"}
    """
    if len(document_text) > MAX_AI_CHARS:
        raise TooLarge(
            "This document is too large for AI suggestions in this version.",
            {"size_chars": len(document_text), "max_chars": MAX_AI_CHARS},
        )

    raw_changes, model = ask_claude(document_text, instruction, playbook)
    suggestions, dropped = validate_suggestions(document_text, raw_changes)
    return {"suggestions": suggestions, "dropped": dropped, "model": model}


def validate_suggestions(document_text: str, raw_changes: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep suggestions that apply cleanly; explain why the others were dropped.

    Suggestions are checked in order, each against the text as the previous kept
    ones would leave it. That way "Accept all" on what we return always works.

    Examples (text = "Fees are due Net 45. Notice is 30 days. Notice is 30 days."):
        [{"find": "Net 45", "replace": "Net 30", ...}]
            -> kept
        [{"find": "Net 60", "replace": "Net 30", ...}]
            -> dropped: "This text isn't in the document."      (hallucinated)
        [{"find": "Notice is 30 days", "replace": "Notice is 60 days", ...}]
            -> dropped: "This text appears 2 times, so the edit is ambiguous."
        [{"find": "Net 45", "replace": "Net 45", ...}]
            -> dropped: "The suggestion doesn't change anything."
    """
    current_text = document_text
    kept = []
    dropped = []

    for raw in raw_changes:
        find = raw.get("find", "")
        replace = raw.get("replace", "")
        reason = raw.get("reason", "")

        if not find or find == replace:
            dropped.append({"find": find, "why": "The suggestion doesn't change anything."})
            continue

        # Same rules as a human edit: must match exactly once, whole words only.
        change = Change(find=find, replace=replace, occurrence=None, whole_word=True, reason=reason, source="ai")
        try:
            current_text, summary = apply_change(current_text, change)
        except AppError as error:
            dropped.append({"find": find, "why": why_dropped(error)})
            continue

        kept.append(
            {
                "operation": "replace",
                "target": {"text": find, "occurrence": None, "whole_word": True},
                "replacement": replace,
                "reason": reason,
                "source": "ai",
            }
        )

    return kept, dropped


def why_dropped(error: AppError) -> str:
    """Turn a matching error into a short reason for the user."""
    if error.type == "target_not_found":
        return "This text isn't in the document."
    if error.type == "ambiguous_match":
        return f"This text appears {error.details.get('count')} times, so the edit is ambiguous."
    return error.message


def ask_claude(document_text: str, instruction: str, playbook: str) -> tuple[list[dict], str]:
    """The one function that calls the Anthropic API. Returns (changes, model name).

    Kept small and separate so tests can swap it for a fake.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key.startswith(PLACEHOLDER_KEY_PREFIX):
        raise AINotConfigured("AI suggestions aren't set up yet. Add ANTHROPIC_API_KEY to backend/.env.")
    model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL

    user_message = (
        f"<contract>\n{document_text}\n</contract>\n\n"
        f"<instruction>\n{instruction}\n</instruction>\n\n"
        "Propose the edits as JSON."
    )
    system = f"{SYSTEM_PROMPT}\n\n<playbook>\n{playbook}\n</playbook>"

    # output_config.format guarantees JSON matching SUGGESTIONS_SCHEMA.
    # fallbacks="default": if the model declines, the API retries on a fallback model.
    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.beta.messages.create(
            model=model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": user_message}],
            output_config={"format": {"type": "json_schema", "schema": SUGGESTIONS_SCHEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as error:
        raise AINotConfigured("The API key in backend/.env was rejected. Check that it's correct.") from error
    except anthropic.RateLimitError as error:
        raise AIServiceError("The AI service is busy right now. Try again in a minute.") from error
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as error:
        raise AIServiceError("The AI service didn't respond. Try again.") from error

    if response.stop_reason == "refusal":
        raise AIServiceError("The AI declined to review this document.")
    if response.stop_reason == "max_tokens":
        raise AIServiceError("The AI's answer was cut off. Try a narrower instruction.")

    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)["changes"], response.model
