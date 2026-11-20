"""NFR-04: the handover package includes the original (unmasked) ticket
for the human agent; everything sent to the AI stays masked.

FakeLLM only: no network, no keys. The A10 'private data found in
auto-answered replies' scan is unchanged and still looks only at drafts.
"""
import json
import sqlite3
from datetime import datetime

import pipeline
import run

EMAIL = "jane.doe@example.com"
PHONE = "+91 98765 43210"

RAW = {
    "ticket_id": "T-ORIG-1",
    "channel": "email",
    "subject": f"Account issue for {EMAIL}",
    "body": f"Please call me on {PHONE}. I think we were hacked.",
    "received_at": "2026-11-19T00:00:00Z",
    "customer_id": "C-1",
    "customer_tier": "enterprise",
    "customer_region": "eu",
}

# security_incident is a must-not: classify, then impact, then PR-06 summary.
CLASSIFY = (
    '{"intent": "security_incident", "urgency": "high", "confidence": 0.95, '
    '"billing_dispute": false, "data_commitment_request": false, "alternatives": []}'
)
IMPACT = '{"impact": "high", "reason": "Possible security issue."}'
SUMMARY = '{"summary": "Customer reports a possible security issue.", "unsure_about": "Need more detail."}'


def _escalate(ai):
    ai.replies = [CLASSIFY, IMPACT, SUMMARY]
    return pipeline.process(RAW)


def test_package_keeps_original_email_and_phone(ai):
    r = _escalate(ai)
    assert r["route"] == "escalate"
    ot = r["package"]["original_ticket"]
    assert ot["subject"] == RAW["subject"]
    assert ot["body"] == RAW["body"]
    assert EMAIL in ot["body"] or EMAIL in ot["subject"]
    assert PHONE in ot["body"]


def test_llm_prompts_use_masks_not_raw_email(ai):
    r = _escalate(ai)
    assert len(ai.prompts) == 3          # classify, impact, summary
    for prompt in ai.prompts:
        assert EMAIL not in prompt
        assert PHONE not in prompt
        assert "[EMAIL]" in prompt
        assert "[PHONE]" in prompt
    # The masked ticket (not the original) is what PR-06 and PR-01 saw.
    assert EMAIL not in json.dumps({k: v for k, v in r.items() if k != "package"})


def test_decision_log_row_has_no_raw_email(ai, monkeypatch, tmp_path):
    """What run.py writes to the decision log must not include the raw email.
    The results JSON may include it, inside package.original_ticket only,
    because that package is the agent-facing handover."""
    ai.replies = [CLASSIFY, IMPACT, SUMMARY]
    logged = []
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE decisions (ticket_id TEXT, payload TEXT)")

    def fake_log(c, tid, **kw):
        payload = json.dumps({"ticket_id": tid, **kw}, default=str)
        logged.append(payload)
        c.execute("INSERT INTO decisions VALUES (?, ?)", (tid, payload))
        c.commit()

    monkeypatch.setattr(run, "connect", lambda: conn)
    monkeypatch.setattr(run, "log_decision", fake_log)
    monkeypatch.setattr(run, "PAUSE_S", 0)
    inp, out = tmp_path / "in.json", tmp_path / "out" / "results.json"
    inp.write_text(json.dumps([RAW]))
    monkeypatch.setattr("sys.argv", ["run.py", str(inp), str(out)])
    run.main()

    assert logged and EMAIL not in "".join(logged) and PHONE not in "".join(logged)
    db = str(conn.execute("SELECT * FROM decisions").fetchall())
    assert EMAIL not in db and PHONE not in db
    # package is never an argument to log_decision
    assert all("original_ticket" not in blob and "package" not in blob for blob in logged)

    results = json.loads(out.read_text())
    ot = results[0]["package"]["original_ticket"]
    assert ot["body"] == RAW["body"] and EMAIL in ot["subject"]


def test_a10_scan_still_only_looks_at_auto_answer_drafts(tmp_path):
    """An email in the handover package must not count as a leak in a reply."""
    auto = {
        "ticket_id": "A", "customer_tier": "pro", "intent": "billing_query", "urgency": "low",
        "confidence": 0.9, "billing_dispute": False, "data_commitment_request": False,
        "retrieved_docs": ["DOC-1"], "route": "auto_respond", "tier": None,
        "reason": "all checks passed", "checks": ["missing_fields", "reply_review"],
        "draft": "Go to Settings.", "cited": "DOC-1", "answer_confidence": 0.9,
        "review": {"verdict": "pass", "problems": []}, "package": None, "model_used": "fake",
        "steps": ["prepare"], "latency_ms": 1000, "redactions": {"email": 1, "phone": 1, "api_key": 0},
    }
    esc = dict(auto, ticket_id="E", route="escalate", tier=2, draft="",
               reason="must-not-auto-respond intent",
               package={"summary": "s", "original_ticket": {"subject": RAW["subject"], "body": RAW["body"]}},
               redactions={"email": 0, "phone": 0, "api_key": 0})
    out = tmp_path / "results.json"
    report = run.write_report([auto, esc], [{"ticket_id": "A"}, {"ticket_id": "E"}],
                              out, datetime(2026, 11, 19, 10, 0), datetime(2026, 11, 19, 10, 1), 2)
    text = report.read_text()
    assert "Private data found in auto-answered replies: 0 (must be 0)" in text


def test_crash_handover_still_has_original_ticket(monkeypatch):
    def boom(t):
        raise ValueError("bug")
    monkeypatch.setattr(run, "process", boom)
    r = run.handle(RAW, 1, provider_down=False)
    assert r["route"] == "escalate" and r["package"]["original_ticket"]["body"] == RAW["body"]
