"""PR-06 handover package (FR-11): always produced, never crashes."""
from escalate import summarize

T = {"subject": "Export", "body": "Need 6 months of access logs", "customer_tier": "enterprise"}
CLS = {"intent": "compliance_request", "confidence": 0.9, "urgency": "medium", "model_used": "fake"}


def test_good_summary(ai):
    ai.replies = ['{"summary": "Customer needs access logs.", "unsure_about": "Retention period."}']
    out = summarize(T, CLS, [], None, "warning words: audit")
    assert out["summary_by"] == "PR-06 1.0" and out["summary"] == "Customer needs access logs."
    assert "warning words: audit" in ai.prompts[0]


def test_missing_field_uses_fallback(ai):
    ai.replies = ['{"summary": "Customer needs access logs."}']
    assert summarize(T, CLS, [], None, "x")["summary_by"] == "code fallback"


def test_error_uses_fallback(ai):
    ai.replies = [ConnectionError("down")]
    out = summarize(T, CLS, [], None, "warning words: audit")
    assert out["summary_by"] == "code fallback" and "warning words: audit" in out["unsure_about"]


def test_provider_down_skips_ai(ai):
    out = summarize(T, CLS | {"model_used": "none"}, [], None, "x")
    assert out["summary_by"] == "code fallback" and ai.prompts == []
