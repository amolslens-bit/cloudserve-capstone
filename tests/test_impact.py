"""PR-03 business impact (FR-04): parsed when valid, otherwise 'not assessed'.
Runs for every escalation, not for auto answers, and feeds PR-06's {impact} slot."""
import pipeline
from escalate import summarize
from impact import assess

T = {"subject": "Site down", "body": "Our production app has returned errors for all users since 10am.",
     "customer_tier": "business"}
CLS = {"intent": "security_incident", "confidence": 0.9, "urgency": "high",
       "reason": "Possible credential exposure.", "model_used": "fake",
       "billing_dispute": False, "data_commitment_request": False}

GOOD = '{"impact": "high", "reason": "Production is down for all users."}'

T_RAW = {"ticket_id": "T-1"}
PREP = {"ticket_id": "T-1", "subject": "Hi", "body": "How do I rotate my key?",
        "customer_tier": "pro", "missing_fields": []}
OK_CLS = {"intent": "api_key_issue", "urgency": "low", "billing_dispute": False,
          "data_commitment_request": False, "confidence": 0.9, "reason": "Key rotation how-to.",
          "model_used": "fake"}
ART = {"doc_id": "DOC-1", "title": "Keys", "text": "x", "score": 0.9}
ANS = {"covered": True, "article_id": "DOC-1", "confidence": 0.9, "answer": "Go to Settings."}


def test_good_reply_parsed(ai):
    ai.replies = [GOOD]
    out = assess(T, CLS)
    assert out["impact_by"] == "PR-03 1.1"
    assert out["impact"] == "high" and out["reason"] == "Production is down for all users."
    prompt = ai.prompts[0]
    assert "Our production app has returned errors for all users since 10am." in prompt
    assert "Tier: business" in prompt


def test_bad_json_uses_fallback(ai):
    ai.replies = ["this looks serious"]
    out = assess(T, CLS)
    assert out["impact_by"] == "code fallback" and out["impact"] == "not assessed"


def test_invalid_value_uses_fallback(ai):
    ai.replies = ['{"impact": "critical", "reason": "Everything is down."}']
    assert assess(T, CLS)["impact"] == "not assessed"


def test_error_uses_fallback(ai):
    ai.replies = [ConnectionError("down")]
    out = assess(T, CLS)
    assert out["impact_by"] == "code fallback" and out["impact"] == "not assessed"


def test_provider_down_skips_ai(ai):
    out = assess(T, CLS | {"model_used": "none"})
    assert out["impact"] == "not assessed" and ai.prompts == []


def _setup(monkeypatch, cls, review_verdict="pass", mock_summarize=True):
    monkeypatch.setattr(pipeline, "prepare", lambda r: dict(PREP))
    monkeypatch.setattr(pipeline, "classify", lambda t: dict(cls))
    monkeypatch.setattr(pipeline, "retrieve", lambda t, k=3, intent=None: [ART])
    monkeypatch.setattr(pipeline, "draft_answer", lambda t, i, a: dict(ANS))
    monkeypatch.setattr(pipeline, "review", lambda reply, art: {"verdict": review_verdict, "problems": []})
    monkeypatch.setitem(pipeline.DOCS, "DOC-1", {"content": "full"})
    if mock_summarize:
        monkeypatch.setattr(pipeline, "summarize",
                            lambda *a, **k: {"summary": "s", "unsure_about": "u", "summary_by": "fake"})


def test_pipeline_runs_pr03_for_escalation(monkeypatch, ai):
    _setup(monkeypatch, OK_CLS | {"intent": "security_incident"})
    ai.replies = [GOOD]
    r = pipeline.process(T_RAW)
    assert r["route"] == "escalate"
    assert r["impact"] == "high" and r["impact_reason"] == "Production is down for all users."
    assert r["package"]["impact"] == "high" and r["package"]["impact_by"] == "PR-03 1.1"
    assert "impact" in r["steps"]
    assert ai.prompts  # PR-03 was called


def test_pipeline_skips_pr03_for_auto_answer(monkeypatch, ai):
    _setup(monkeypatch, OK_CLS)
    r = pipeline.process(T_RAW)
    assert r["route"] == "auto_respond" and r["package"] is None
    assert r["impact"] is None and "impact" not in r["steps"]
    assert ai.prompts == []


def test_impact_reaches_pr06_context(monkeypatch, ai):
    _setup(monkeypatch, OK_CLS | {"intent": "security_incident"}, mock_summarize=False)
    ai.replies = [
        GOOD,
        '{"summary": "Customer production is down.", "unsure_about": "Security incident."}',
    ]
    r = pipeline.process(T_RAW)
    assert r["package"]["summary_by"] == "PR-06 1.0"
    assert r["package"]["impact"] == "high"
    assert "Impact: high" in ai.prompts[1]
    # summarize still accepts the default when impact is omitted
    ai.replies = ['{"summary": "s", "unsure_about": "u"}']
    out = summarize(T, CLS, [], None, "must-not-auto-respond intent: security_incident")
    assert "Impact: not assessed" in ai.prompts[-1] and out["summary_by"] == "PR-06 1.0"
