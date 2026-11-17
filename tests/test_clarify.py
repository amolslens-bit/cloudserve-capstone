"""PR-02 clarifying question (FR-03): parsed when valid, otherwise a safe fallback.
Pipeline runs it only for unclear tickets, not for other escalations or auto answers."""
import pipeline
from clarify import clarify, is_unclear_escalation

T = {"subject": "", "body": "it not working. Please help.", "customer_tier": "business"}
CLS = {"intent": "unclear_request", "confidence": 0.30, "urgency": "medium",
       "reason": "Does not say what is not working.", "model_used": "fake",
       "billing_dispute": False, "data_commitment_request": False}

GOOD = ('{"unclear_because": "The customer does not say what is failing.",'
        ' "clarifying_question": "Which part of CloudServe is not working?"}')

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
    out = clarify(T, CLS)
    assert out["question_by"] == "PR-02 1.0"
    assert out["unclear_because"] == "The customer does not say what is failing."
    assert out["clarifying_question"] == "Which part of CloudServe is not working?"
    prompt = ai.prompts[0]
    assert "it not working. Please help." in prompt
    assert 'Classifier: unclear_request, 0.3, "Does not say what is not working."' in prompt
    assert "business" in prompt


def test_bad_json_uses_fallback(ai):
    ai.replies = ["I think you should ask what is broken"]
    out = clarify(T, CLS)
    assert out["question_by"] == "code fallback"
    assert out["clarifying_question"].endswith("?") and out["clarifying_question"].count("?") == 1


def test_multi_question_uses_fallback(ai):
    ai.replies = ['{"unclear_because": "Two things are missing.",'
                  ' "clarifying_question": "Which service is this? What error do you see?"}']
    assert clarify(T, CLS)["question_by"] == "code fallback"


def test_no_question_mark_uses_fallback(ai):
    ai.replies = ['{"unclear_because": "The service is not named.",'
                  ' "clarifying_question": "Please name the service"}']
    assert clarify(T, CLS)["question_by"] == "code fallback"


def test_error_uses_fallback(ai):
    ai.replies = [ConnectionError("down")]
    out = clarify(T, CLS)
    assert out["question_by"] == "code fallback" and out["clarifying_question"].endswith("?")


def test_provider_down_skips_ai(ai):
    out = clarify(T, CLS | {"model_used": "none"})
    assert out["question_by"] == "code fallback" and ai.prompts == []


def _setup(monkeypatch, cls, review_verdict="pass"):
    calls = []
    monkeypatch.setattr(pipeline, "prepare", lambda r: dict(PREP))
    monkeypatch.setattr(pipeline, "classify", lambda t: dict(cls))
    monkeypatch.setattr(pipeline, "retrieve", lambda t, k=3, intent=None: calls.append(k) or [ART])
    monkeypatch.setattr(pipeline, "draft_answer", lambda t, i, a: dict(ANS))
    monkeypatch.setattr(pipeline, "review", lambda reply, art: {"verdict": review_verdict, "problems": []})
    monkeypatch.setitem(pipeline.DOCS, "DOC-1", {"content": "full"})
    monkeypatch.setattr(pipeline, "summarize",
                        lambda *a, **k: {"summary": "s", "unsure_about": "u", "summary_by": "fake"})
    monkeypatch.setattr(pipeline, "assess",
                        lambda *a, **k: {"impact": "not assessed", "reason": "mocked", "impact_by": "fake"})
    return calls


def test_pipeline_runs_pr02_for_unclear(monkeypatch, ai):
    _setup(monkeypatch, CLS)
    ai.replies = [GOOD]
    r = pipeline.process(T_RAW)
    assert r["route"] == "escalate" and r["tier"] == 1
    assert r["clarifying_question"] == "Which part of CloudServe is not working?"
    assert r["package"]["clarifying_question"] == r["clarifying_question"]
    assert r["package"]["unclear_because"] == "The customer does not say what is failing."
    assert "clarify" in r["steps"]
    assert ai.prompts  # PR-02 was called


def test_pipeline_skips_pr02_for_must_not_and_billing(monkeypatch, ai):
    _setup(monkeypatch, OK_CLS | {"intent": "security_incident"})
    r = pipeline.process(T_RAW)
    assert r["route"] == "escalate" and r["package"]["reason"].startswith("must-not")
    assert r["clarifying_question"] is None and "clarify" not in r["steps"]
    assert ai.prompts == []

    _setup(monkeypatch, OK_CLS | {"billing_dispute": True})
    r = pipeline.process(T_RAW)
    assert r["route"] == "escalate" and "billing" in r["package"]["reason"]
    assert r["clarifying_question"] is None and "clarify" not in r["steps"]
    assert ai.prompts == []


def test_pipeline_skips_pr02_for_auto_answer(monkeypatch, ai):
    _setup(monkeypatch, OK_CLS)
    r = pipeline.process(T_RAW)
    assert r["route"] == "auto_respond" and r["package"] is None
    assert r["clarifying_question"] is None and "clarify" not in r["steps"]
    assert ai.prompts == []


def test_is_unclear_escalation_reasons():
    assert is_unclear_escalation({"route": "escalate", "reason": "must-not-auto-respond intent: unclear_request"},
                                 {"intent": "unclear_request"})
    assert is_unclear_escalation({"route": "escalate", "reason": "low classification confidence 0.3"},
                                 {"intent": "api_key_issue"})
    assert not is_unclear_escalation({"route": "escalate", "reason": "must-not-auto-respond intent: security_incident"},
                                     {"intent": "security_incident"})
    assert not is_unclear_escalation({"route": "auto_respond", "reason": "all checks passed"},
                                     {"intent": "api_key_issue"})
