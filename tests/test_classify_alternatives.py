"""PR-01 1.2: classify records the alternatives it considered. No API calls."""
import json

import pipeline
from classify import check, clean_alternatives

BASE = {"intent": "billing_query", "urgency": "low", "billing_dispute": False,
        "data_commitment_request": False, "confidence": 0.8}


def reply(**extra):
    return json.dumps(BASE | extra)


def test_good_alternatives_kept_in_order():
    out = check(reply(alternatives=[{"intent": "quota_or_overage", "confidence": 0.15},
                                    {"intent": "account_access", "confidence": 0.05}]))
    assert out["alternatives"] == [{"intent": "quota_or_overage", "confidence": 0.15},
                                   {"intent": "account_access", "confidence": 0.05}]


def test_missing_alternatives_is_empty_list():
    assert check(reply())["alternatives"] == []


def test_bad_entries_dropped():
    alts = [{"intent": "pizza_order", "confidence": 0.5},      # not a real intent
            {"intent": "billing_query", "confidence": 0.4},    # same as the chosen intent
            "quota_or_overage",                                # not an object
            {"intent": "rate_limit", "confidence": "high"},    # bad number -> 0
            {"intent": "rate_limit", "confidence": 0.3},       # repeat
            {"intent": "onboarding", "confidence": 7}]         # capped at 1
    assert clean_alternatives(alts, "billing_query") == [
        {"intent": "rate_limit", "confidence": 0.0},
        {"intent": "onboarding", "confidence": 1.0}]


def test_at_most_two():
    alts = [{"intent": i, "confidence": 0.1} for i in ("rate_limit", "onboarding", "webhook_issue")]
    assert len(clean_alternatives(alts, "billing_query")) == 2


def test_not_a_list_is_empty():
    assert clean_alternatives("rate_limit", "billing_query") == []


def test_garbage_reply_still_safe():
    out = check("sorry, no JSON")
    assert out["intent"] == "unclear_request" and out["alternatives"] == []


def test_prompt_is_v12_and_asks_for_alternatives():
    import classify
    assert '"alternatives"' in classify.PROMPT


def test_alternatives_on_record_and_handover(monkeypatch):
    alts = [{"intent": "account_access", "confidence": 0.2}]
    cls = {"intent": "security_incident", "urgency": "high", "billing_dispute": False,
           "data_commitment_request": False, "confidence": 0.8, "model_used": "fake",
           "alternatives": alts}
    monkeypatch.setattr(pipeline, "prepare", lambda r: {"ticket_id": "T-1", "subject": "Hi",
                        "body": "Someone logged in", "customer_tier": "pro", "missing_fields": []})
    monkeypatch.setattr(pipeline, "classify", lambda t: dict(cls))
    monkeypatch.setattr(pipeline, "summarize",
                        lambda *a, **k: {"summary": "s", "unsure_about": "u", "summary_by": "fake"})
    monkeypatch.setattr(pipeline, "assess",
                        lambda *a, **k: {"impact": "high", "reason": "r", "impact_by": "fake"})
    r = pipeline.process({"ticket_id": "T-1"})
    assert r["route"] == "escalate"                 # alternatives never change the route
    assert r["alternatives"] == alts
    assert r["package"]["alternatives_considered"] == alts
