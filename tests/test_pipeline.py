"""End-to-end flow with fakes: early escalations skip search; escalations carry a package."""
import pipeline

T_RAW = {"ticket_id": "T-1"}
PREP = {"ticket_id": "T-1", "subject": "Hi", "body": "How do I rotate my key?",
        "customer_tier": "pro", "missing_fields": []}
CLS = {"intent": "api_key_issue", "urgency": "low", "billing_dispute": False,
       "data_commitment_request": False, "confidence": 0.9, "model_used": "fake"}
ART = {"doc_id": "DOC-1", "title": "Keys", "text": "x", "score": 0.9}
ANS = {"covered": True, "article_id": "DOC-1", "confidence": 0.9, "answer": "Go to Settings."}


def setup(monkeypatch, cls, review_verdict="pass"):
    calls = []
    monkeypatch.setattr(pipeline, "prepare", lambda r: dict(PREP))
    monkeypatch.setattr(pipeline, "classify", lambda t: dict(cls))
    monkeypatch.setattr(pipeline, "retrieve", lambda t, k=3: calls.append(k) or [ART])
    monkeypatch.setattr(pipeline, "draft_answer", lambda t, i, a: dict(ANS))
    monkeypatch.setattr(pipeline, "review", lambda reply, art: {"verdict": review_verdict, "problems": []})
    monkeypatch.setitem(pipeline.DOCS, "DOC-1", {"content": "full"})
    monkeypatch.setattr(pipeline, "summarize",
                        lambda *a: {"summary": "s", "unsure_about": "u", "summary_by": "fake"})
    return calls


def test_auto_answer_path(monkeypatch):
    calls = setup(monkeypatch, CLS)
    r = pipeline.process(T_RAW)
    assert r["route"] == "auto_respond" and r["cited"] == "DOC-1" and r["package"] is None
    assert calls == [2]                       # k=2 (T9)


def test_must_not_skips_search_and_has_package(monkeypatch):
    calls = setup(monkeypatch, CLS | {"intent": "security_incident"})
    r = pipeline.process(T_RAW)
    assert r["route"] == "escalate" and r["tier"] == 2 and calls == []
    assert r["package"]["summary"] == "s" and r["package"]["reason"].startswith("must-not")


def test_review_block_escalates_with_draft(monkeypatch):
    setup(monkeypatch, CLS, review_verdict="block")
    r = pipeline.process(T_RAW)
    assert r["route"] == "escalate" and r["package"]["draft"] == "Go to Settings."
    assert r["package"]["articles_checked"] == ["DOC-1 Keys"]
