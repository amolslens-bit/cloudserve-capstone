"""Redaction counts (A10 governance: private-data detections). No API calls."""
import sys
import types

sys.modules.setdefault("load_data", types.SimpleNamespace(load=lambda *a, **k: []))
from prepare import prepare, redact


def test_counts_each_kind():
    t = prepare({"ticket_id": "T-1", "subject": "Mail me at a.b@x.com",
                 "body": "Call +91 98765 43210, key sk-ABCDEFGHIJKLMNOP and c@y.org",
                 "customer_id": "C1", "customer_tier": "pro", "customer_region": "eu"})
    assert t["redactions"] == {"email": 2, "phone": 1, "api_key": 1}
    assert "a.b@x.com" not in t["subject"] and "[EMAIL]" in t["subject"]
    assert "[PHONE]" in t["body"] and "[KEY]" in t["body"]


def test_clean_ticket_counts_zero():
    t = prepare({"ticket_id": "T-2", "subject": "Hello", "body": "My dashboard is slow",
                 "customer_id": "C1", "customer_tier": "pro", "customer_region": "eu"})
    assert t["redactions"] == {"email": 0, "phone": 0, "api_key": 0}


def test_redact_without_counts_still_works():
    assert redact("x@y.com") == "[EMAIL]"
