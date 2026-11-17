"""FR-04 queue order: impact, then urgency, then waiting time. No waiting-limit bump yet."""
from priority import queue_order


def _row(tid, route="escalate", impact="low", urgency="low", created_at=None, received_at=None):
    r = {"ticket_id": tid, "route": route, "impact": impact, "urgency": urgency}
    if created_at is not None:
        r["created_at"] = created_at
    if received_at is not None:
        r["received_at"] = received_at
    return r


def test_impact_then_urgency_then_wait():
    rows = [
        _row("auto", route="auto_respond", impact="high", urgency="high", created_at="2026-01-01T00:00:00Z"),
        _row("low-old", impact="low", urgency="high", created_at="2026-01-01T00:00:00Z"),
        _row("high-late", impact="high", urgency="high", created_at="2026-03-01T00:00:00Z"),
        _row("high-early", impact="high", urgency="high", created_at="2026-02-01T00:00:00Z"),
        _row("high-med-urg", impact="high", urgency="medium", created_at="2026-01-01T00:00:00Z"),
        _row("medium", impact="medium", urgency="high", created_at="2026-01-01T00:00:00Z"),
        _row("unknown", impact="not assessed", urgency="high", created_at="2026-01-01T00:00:00Z"),
    ]
    got = [r["ticket_id"] for r in queue_order(rows)]
    assert got == ["high-early", "high-late", "high-med-urg", "medium", "low-old", "unknown"]


def test_received_at_used_when_no_created_at():
    rows = [
        _row("newer", impact="high", urgency="high", received_at="2026-04-01T00:00:00Z"),
        _row("older", impact="high", urgency="high", received_at="2026-03-01T00:00:00Z"),
    ]
    assert [r["ticket_id"] for r in queue_order(rows)] == ["older", "newer"]


def test_missing_timestamp_sorts_last():
    rows = [
        _row("no-time", impact="high", urgency="high"),
        _row("has-time", impact="high", urgency="high", created_at="2026-03-01T00:00:00Z"),
    ]
    assert [r["ticket_id"] for r in queue_order(rows)] == ["has-time", "no-time"]


def test_invalid_impact_sorts_with_not_assessed():
    rows = [
        _row("bad", impact="critical", urgency="high", created_at="2026-01-01T00:00:00Z"),
        _row("low", impact="low", urgency="high", created_at="2026-01-01T00:00:00Z"),
    ]
    assert [r["ticket_id"] for r in queue_order(rows)] == ["low", "bad"]
