"""PR-03 business impact (FR-04). For an escalated ticket, judges how much of
the customer's work is affected. Never crashes.

Fallback is 'not assessed' (safer than guessing medium) when the AI is
down or its answer is unusable.
"""
import json
import re
from pathlib import Path

from llm import llm

PROMPT = Path("prompts/pr03_impact_v1.1.txt").read_text(encoding="utf-8")
ALLOWED = {"high", "medium", "low"}


def fallback():
    """Used when the AI is down or its answer is unusable: do not guess a level."""
    return {"impact": "not assessed",
            "reason": "Impact could not be assessed.",
            "impact_by": "code fallback"}


def assess(ticket, cls=None):
    if (cls or {}).get("model_used") == "none":        # models already down: don't wait again
        return fallback()
    prompt = (PROMPT.replace("{subject}", ticket.get("subject") or "")
                    .replace("{body}", ticket.get("body") or "")
                    .replace("{tier}", ticket.get("customer_tier") or ""))
    try:
        raw = llm.invoke(prompt).content
        out = json.loads(re.search(r"\{.*\}", raw, re.S).group())
        impact = str(out.get("impact", "")).strip().lower()
        reason = str(out.get("reason", "")).strip()
    except Exception:
        return fallback()
    if impact not in ALLOWED or not reason:
        return fallback()
    return {"impact": impact, "reason": reason, "impact_by": "PR-03 1.1"}
