"""PR-01 ticket classification (FR-02). Labels are used only to score, never sent to the AI."""
import json
import random
import re
from pathlib import Path

from llm import llm
from load_data import load
from prepare import prepare

PROMPT = Path("prompts/pr01_classify_v1.1.txt").read_text(encoding="utf-8")
INTENTS = {"data_export", "data_residency", "rollback_request", "deployment_failure",
           "compliance_request", "sso_configuration", "security_incident", "database_issue",
           "api_usage_question", "billing_query", "performance_degradation", "quota_or_overage",
           "account_access", "onboarding", "integration_help", "webhook_issue", "feature_request",
           "authentication_failure", "api_key_issue", "configuration_help", "unclear_request",
           "rate_limit"}


def check(raw):
    """Code checks PR-01's answer. Anything broken is made safe, never trusted."""
    try:
        out = json.loads(re.search(r"\{.*\}", raw, re.S).group())
    except (AttributeError, ValueError):
        out = {}
    if out.get("intent") not in INTENTS:
        out["intent"], out["confidence"] = "unclear_request", 0.0
    if out.get("urgency") not in {"high", "medium", "low"}:
        out["urgency"] = "high"
    # Missing or invalid flag counts as true, so the ticket goes to tier 2 (FR-06)
    for flag in ["billing_dispute", "data_commitment_request"]:
        if not isinstance(out.get(flag), bool):
            out[flag] = True
    try:
        out["confidence"] = float(out.get("confidence", 0))
    except (TypeError, ValueError):
        out["confidence"] = 0.0
    return out


def classify(ticket):
    prompt = (PROMPT.replace("{subject}", ticket["subject"] or "")
                    .replace("{body}", ticket["body"])
                    .replace("{tier}", ticket["customer_tier"] or ""))
    try:
        reply = llm.invoke(prompt)
    except Exception as e:
        # Both models failed: never guess, send to a human (NFR-02)
        result = check("")
        result["model_used"] = "none"
        result["error"] = str(e)[:200]
        return result
    result = check(reply.content)
    result["model_used"] = reply.response_metadata.get("model_name")
    return result


if __name__ == "__main__":
    raw = load("development_tickets.json")
    sample = random.Random(42).sample(raw, 10)   # small test: free tier allows few calls a day
    hit_i = hit_u = 0
    for t in sample:
        r = classify(prepare(t))
        lab = t["labels"]
        hit_i += r["intent"] == lab["intent"]
        hit_u += r["urgency"] == lab["urgency"]
        mark = "OK " if r["intent"] == lab["intent"] else "XX "
        print(mark, t["ticket_id"], "| got", r["intent"], r["urgency"],
              "| label", lab["intent"], lab["urgency"], "|", r["confidence"], r["model_used"])
    print(f"\nIntent right: {hit_i}/10   Urgency right: {hit_u}/10")
