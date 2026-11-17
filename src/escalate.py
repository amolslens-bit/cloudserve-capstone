"""PR-06 escalation summary (FR-11). Every escalation carries a handover package,
so tier 1 and tier 2 never have to re-read the whole ticket. Never crashes."""
import json
import re
from pathlib import Path

from llm import llm

PROMPT = Path("prompts/pr06_escalation_v1.0.txt").read_text(encoding="utf-8")


def fallback(reason):
    """Used when the AI is down or its answer is unusable: code writes a plain note."""
    return {"summary": "AI summary could not be produced; please read the ticket.",
            "unsure_about": f"Escalated because: {reason}.", "summary_by": "code fallback"}


def summarize(ticket, cls, articles, ans, reason, impact="not assessed"):
    if cls.get("model_used") == "none":        # models already down: don't wait again
        return fallback(reason)
    draft = "yes" if ans and ans.get("answer") else "none"
    prompt = (PROMPT.replace("{subject}", ticket["subject"] or "")
                    .replace("{body}", ticket["body"] or "")
                    .replace("{tier}", ticket["customer_tier"] or "")
                    .replace("{intent}", cls["intent"])
                    .replace("{confidence}", str(cls["confidence"]))
                    .replace("{urgency}", cls["urgency"])
                    .replace("{impact}", impact or "not assessed")
                    .replace("{articles}", ", ".join(a["doc_id"] for a in articles) or "none")
                    .replace("{draft}", draft)
                    .replace("{reason}", reason))
    try:
        raw = llm.invoke(prompt).content
        out = json.loads(re.search(r"\{.*\}", raw, re.S).group())
        summary, unsure = str(out.get("summary", "")).strip(), str(out.get("unsure_about", "")).strip()
    except Exception:
        return fallback(reason)
    if not summary or not unsure:
        return fallback(reason)
    return {"summary": summary, "unsure_about": unsure, "summary_by": "PR-06 1.0"}
