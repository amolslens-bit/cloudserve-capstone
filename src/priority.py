"""FR-04 queue order for escalations: impact, then urgency, then waiting time.

The waiting-limit bump (a ticket that waits longer than the limit moves up
one level) and any weights are starting values, to be set during testing.
They are not applied here yet.
"""
from datetime import datetime, timezone

IMPACT_RANK = {"high": 0, "medium": 1, "low": 2, "not assessed": 3}
URGENCY_RANK = {"high": 0, "medium": 1, "low": 2}


def _waiting_key(row):
    """Earlier created_at / received_at = longer wait = higher in the queue.
    A missing timestamp is treated as newest, so it does not jump the queue."""
    raw = row.get("created_at") or row.get("received_at")
    if not raw:
        return datetime.max.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return datetime.max.replace(tzinfo=timezone.utc)


def queue_order(results):
    """Return escalations only, sorted by impact, then urgency, then wait time."""
    def key(row):
        impact = row.get("impact") if row.get("impact") in IMPACT_RANK else "not assessed"
        urgency = URGENCY_RANK.get(row.get("urgency"), 3)
        return (IMPACT_RANK[impact], urgency, _waiting_key(row))

    return sorted((r for r in results if r.get("route") == "escalate"), key=key)
