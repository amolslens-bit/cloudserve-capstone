"""PR-02 clarifying question (FR-03). For an unclear ticket, writes one short
question a tier 1 agent can use or edit. Never crashes.

Known weakness (Stage 3 text kept as written): the Classifier: line sits
inside <ticket>, so a customer could fake one in the body. Do not change
the prompt to 'fix' this silently.
"""
import json
import re
from pathlib import Path

from llm import llm

PROMPT = Path("prompts/pr02_clarify_v1.0.txt").read_text(encoding="utf-8")
FALLBACK_QUESTION = ("Which CloudServe service or feature is affected, "
                     "and what happens when it goes wrong?")
FALLBACK_BECAUSE = "The ticket does not have enough detail to answer safely."


def fallback():
    """Used when the AI is down or its answer is unusable: code writes a plain question."""
    return {"unclear_because": FALLBACK_BECAUSE,
            "clarifying_question": FALLBACK_QUESTION,
            "question_by": "code fallback"}


def is_unclear_escalation(result, cls):
    """True only when the ticket is escalated because it is unclear (FR-03).

    That is: PR-01 intent is unclear_request, or confidence is below the
    PR-01 cut-off. Other escalations (must-not, billing, coverage, etc.) skip this.
    """
    if result.get("route") != "escalate":
        return False
    if cls.get("intent") == "unclear_request":
        return True
    return str(result.get("reason") or "").startswith("low classification confidence")


def _valid(because, question):
    if not because or not question:
        return False
    if not question.endswith("?") or question.count("?") != 1:
        return False
    if len(question.split()) > 25:
        return False
    return True


def clarify(ticket, cls):
    if cls.get("model_used") == "none":        # models already down: don't wait again
        return fallback()
    reason = str(cls.get("reason") or "").replace('"', "'")
    prompt = (PROMPT.replace("{subject}", ticket.get("subject") or "")
                    .replace("{body}", ticket.get("body") or "")
                    .replace("{tier}", ticket.get("customer_tier") or "")
                    .replace("{intent}", str(cls.get("intent") or ""))
                    .replace("{confidence}", str(cls.get("confidence") or ""))
                    .replace("{reason}", reason))
    try:
        raw = llm.invoke(prompt).content
        out = json.loads(re.search(r"\{.*\}", raw, re.S).group())
        because = str(out.get("unclear_because", "")).strip()
        question = str(out.get("clarifying_question", "")).strip()
    except Exception:
        return fallback()
    if not _valid(because, question):
        return fallback()
    return {"unclear_because": because, "clarifying_question": question,
            "question_by": "PR-02 1.0"}
