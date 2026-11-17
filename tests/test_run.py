"""One-command harness (A9, A10, A11): every ticket gets a record, nothing crashes."""
import json
import sqlite3

import run

GOOD = {"ticket_id": "T-1", "customer_tier": "pro", "intent": "billing_query", "urgency": "low",
        "confidence": 0.9, "billing_dispute": False, "data_commitment_request": False,
        "retrieved_docs": [], "route": "auto_respond", "tier": None, "reason": "all checks passed",
        "checks": ["x"], "draft": "hi", "cited": "D1", "answer_confidence": 0.9, "review": None,
        "package": None, "model_used": "fake", "steps": ["prepare"], "latency_ms": 10}


def test_malformed_ticket():
    r = run.handle("not a ticket", 1, provider_down=False)
    assert r["route"] == "escalate" and r["reason"].startswith("malformed")


def test_crash_escalates(monkeypatch):
    def boom(t):
        raise ValueError("bug")
    monkeypatch.setattr(run, "process", boom)
    r = run.handle({"ticket_id": "T-9"}, 1, provider_down=False)
    assert r["ticket_id"] == "T-9" and r["route"] == "escalate" and r["package"]


def test_provider_down_escalates(monkeypatch):
    monkeypatch.setattr(run, "process", lambda t: dict(GOOD, model_used="none", package={"reason": "x"}))
    monkeypatch.setattr(run, "RETRY_WAITS_S", [0, 0])
    r = run.handle({"ticket_id": "T-1"}, 1, provider_down=False)
    assert r["reason"] == "AI service unavailable, sent to a person" and r["tier"] == 1


def test_load_tickets_both_shapes(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps([{"ticket_id": "1"}]))
    b.write_text(json.dumps({"tickets": [{"ticket_id": "1"}, {"ticket_id": "2"}]}))
    assert len(run.load_tickets(a)) == 1 and len(run.load_tickets(b)) == 2


def test_full_run_every_ticket_logged(monkeypatch, tmp_path):
    """3 tickets: one fine, one crashes, one malformed. All 3 come out and all 3 are logged."""
    def fake_process(t):
        if t["ticket_id"] == "BOOM":
            raise RuntimeError("bug")
        return dict(GOOD, ticket_id=t["ticket_id"])
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE decisions (ticket_id TEXT)")
    monkeypatch.setattr(run, "process", fake_process)
    monkeypatch.setattr(run, "connect", lambda: conn)
    monkeypatch.setattr(run, "log_decision", lambda c, tid, **kw: c.execute("INSERT INTO decisions VALUES (?)", (tid,)))
    monkeypatch.setattr(run, "PAUSE_S", 0)
    inp, out = tmp_path / "in.json", tmp_path / "out" / "results.json"
    inp.write_text(json.dumps([{"ticket_id": "OK-1", "labels": {"intent": "billing_query"}},
                               {"ticket_id": "BOOM"}, "garbage"]))
    monkeypatch.setattr("sys.argv", ["run.py", str(inp), str(out)])
    run.main()
    results = json.loads(out.read_text())
    assert [r["ticket_id"] for r in results] == ["OK-1", "BOOM", "UNKNOWN-3"]
    report = (tmp_path / "out" / "results_metrics.md").read_text()
    assert "3 (reconciles)" in report and "Intent right: 1/1" in report
