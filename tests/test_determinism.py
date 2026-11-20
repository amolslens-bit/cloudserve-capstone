"""A5: the same ticket always gets the same decision.

Runs each ticket through the pipeline twice (fake AI, no API calls) and checks
that everything except the timing comes out identical. Also checks the two
setting that makes the real AI repeatable: temperature 0 on every model.
(The reply cache in llm.py also reuses the saved reply for a repeat prompt.)"""
import json

import pytest

import pipeline
from test_llm import load_llm

T_RAW = {"ticket_id": "T-1"}
PREP = {"ticket_id": "T-1", "subject": "Hi", "body": "How do I rotate my key?",
        "customer_tier": "pro", "missing_fields": []}
CLS = {"intent": "api_key_issue", "urgency": "low", "billing_dispute": False,
       "data_commitment_request": False, "confidence": 0.9, "model_used": "fake"}
ART = {"doc_id": "DOC-1", "title": "Keys", "text": "x", "score": 0.9}
ANS = {"covered": True, "article_id": "DOC-1", "confidence": 0.9, "answer": "Go to Settings."}

CASES = {
    "auto answer": (CLS, "pass"),
    "must-not intent": (CLS | {"intent": "security_incident"}, "pass"),
    "reply review blocks": (CLS, "block"),
    "low confidence": (CLS | {"confidence": 0.3}, "pass"),
    "billing dispute flag": (CLS | {"billing_dispute": True}, "pass"),
}


def fake_everything(monkeypatch, cls, verdict):
    monkeypatch.setattr(pipeline, "prepare", lambda r: dict(PREP))
    monkeypatch.setattr(pipeline, "classify", lambda t: dict(cls))
    monkeypatch.setattr(pipeline, "retrieve", lambda t, k=3, intent=None: [dict(ART)])
    monkeypatch.setattr(pipeline, "draft_answer", lambda t, i, a: dict(ANS))
    monkeypatch.setattr(pipeline, "review", lambda reply, art: {"verdict": verdict, "problems": []})
    monkeypatch.setitem(pipeline.DOCS, "DOC-1", {"content": "full"})
    monkeypatch.setattr(pipeline, "summarize",
                        lambda *a, **k: {"summary": "s", "unsure_about": "u", "summary_by": "fake"})
    monkeypatch.setattr(pipeline, "assess",
                        lambda *a, **k: {"impact": "not assessed", "reason": "mocked", "impact_by": "fake"})


def without_timing(record):
    r = dict(record)
    r.pop("latency_ms", None)
    return json.dumps(r, sort_keys=True, default=str)


@pytest.mark.parametrize("name", CASES)
def test_same_ticket_same_decision(monkeypatch, name):
    cls, verdict = CASES[name]
    fake_everything(monkeypatch, cls, verdict)
    first = pipeline.process(T_RAW)
    second = pipeline.process(T_RAW)
    assert without_timing(first) == without_timing(second), name


def test_every_model_uses_temperature_zero():
    _, calls = load_llm()
    for c in calls["openai"] + calls["groq"]:
        assert c.get("temperature") == 0, c["model"]
