"""One command for the full run (A9, A10).

    python src/run.py <input tickets file> <output results file>
    e.g. python src/run.py data/development_tickets.json outputs/results.json

- Processes EVERY ticket in the file, however many. Never stops, never skips.
- If both AI models fail (rate limit, outage), it waits and retries. If they
  are still down, the ticket is escalated to a person with the reason logged.
- Any unexpected error on one ticket escalates that ticket; the run carries on.
- Every decision goes to the decision log (storage/decisions.db).
- At the end it writes a metrics report next to the output file.
Labels, if the file has them, are used ONLY for the scores in the report."""
import argparse
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from decision_log import connect, log_decision
from pipeline import process

PROMPT_VERSION = "PR-01 1.1, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1"
PAUSE_S = 3.5               # gap between tickets, keeps under per-minute limits
RETRY_WAITS_S = [30, 60, 120]  # waits before retrying when both models fail
DOWN_AFTER = 3              # this many tickets in a row with no model = provider down


def escalation(ticket_id, tier, reason, tier_name=None):
    """A safe escalation record for a ticket the pipeline could not handle."""
    return {"ticket_id": ticket_id, "channel": None, "customer_tier": tier_name, "intent": "unclear_request",
            "urgency": "high", "confidence": 0.0, "billing_dispute": None,
            "data_commitment_request": None, "retrieved_docs": [], "route": "escalate",
            "tier": tier, "reason": reason, "checks": [], "draft": "", "cited": "",
            "answer_confidence": None, "review": None, "model_used": "none",
            "package": {"summary": "Summary not available; please read the ticket.",
                        "unsure_about": f"Escalated because: {reason}.", "summary_by": "code fallback",
                        "reason": reason, "articles_checked": [], "draft": ""},
            "unclear_because": None, "clarifying_question": None,
            "impact": "not assessed", "impact_reason": None,
            "steps": ["error"], "latency_ms": 0}


def handle(raw, i, provider_down):
    """Process one ticket. Always returns a record, never raises."""
    if not isinstance(raw, dict):
        return escalation(f"UNKNOWN-{i}", 1, "malformed ticket: not a ticket record")
    tid = raw.get("ticket_id") or f"UNKNOWN-{i}"
    waits = [] if provider_down else RETRY_WAITS_S
    for attempt in range(len(waits) + 1):
        try:
            r = process(raw)
        except Exception as e:
            return escalation(tid, 1, f"system error, sent to a person: {type(e).__name__}",
                              raw.get("customer_tier"))
        if r["model_used"] != "none":
            return r
        if attempt < len(waits):
            print(f"    {tid}: both AI models failed, waiting {waits[attempt]}s and retrying")
            time.sleep(waits[attempt])
    r["route"], r["tier"] = "escalate", 1
    r["reason"] = "AI service unavailable, sent to a person"
    if r.get("package"):
        r["package"]["reason"] = r["reason"]
    return r


def load_tickets(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):            # allow {"tickets": [...]}
        data = data.get("tickets", [])
    return data if isinstance(data, list) else []


def write_report(results, raw_tickets, out_path, started, finished, logged):
    n = len(results)
    routes = Counter(r["route"] for r in results)
    lines = [f"# Metrics report", "",
             f"- Input tickets: {len(raw_tickets)}",
             f"- Tickets processed: {n}",
             f"- Decisions written to the log this run: {logged} "
             f"({'reconciles' if logged == n else 'DOES NOT reconcile'})",
             f"- Started {started:%Y-%m-%d %H:%M}, finished {finished:%Y-%m-%d %H:%M} "
             f"({(finished - started).total_seconds() / 60:.1f} min)",
             f"- Prompt versions: {PROMPT_VERSION}", "",
             "## What the system did", "",
             f"- Auto-answered (draft ready for agent): {routes['auto_respond']} ({routes['auto_respond']/max(n,1):.0%})",
             f"- Escalated: {routes['escalate']} ({routes['escalate']/max(n,1):.0%})",
             f"  - to tier 1: {sum(r['tier'] == 1 for r in results)}",
             f"  - to tier 2: {sum(r['tier'] == 2 for r in results)}",
             f"- AI service unavailable (escalated safely): "
             f"{sum(r['reason'].startswith('AI service unavailable') for r in results)}",
             f"- System errors (escalated safely): "
             f"{sum(r['reason'].startswith(('system error', 'malformed')) for r in results)}",
             f"- Escalations with a handover package: "
             f"{sum(bool(r.get('package')) for r in results if r['route'] == 'escalate')} of {routes['escalate']}",
             f"- Average time per ticket: {sum(r['latency_ms'] for r in results)/max(n,1)/1000:.1f} s", "",
             "## Why tickets escalated", ""]
    for reason, c in Counter(r["reason"].split(":")[0] for r in results
                             if r["route"] == "escalate").most_common():
        lines.append(f"- {c}  {reason}")
    lines += ["", "## Models used", ""]
    for m, c in Counter(r["model_used"] for r in results).most_common():
        lines.append(f"- {c}  {m}")

    # Scores only if the input file carries labels (dev / validation files do, hidden set may not)
    labels = {t["ticket_id"]: t["labels"] for t in raw_tickets
              if isinstance(t, dict) and isinstance(t.get("labels"), dict) and t.get("ticket_id")}
    scored = [r for r in results if r["ticket_id"] in labels]
    if scored:
        k = len(scored)
        L = lambda r: labels[r["ticket_id"]]
        must_not = [r for r in scored if L(r).get("must_not_auto_respond")]
        unsafe = [r["ticket_id"] for r in must_not if r["route"] == "auto_respond"]
        should = [r for r in scored if L(r).get("expected_route") == "auto_respond"]
        sent = [r for r in scored if r["route"] == "auto_respond"]
        cite = sum(r["cited"] in (L(r).get("expected_doc_ids") or []) for r in sent)
        pct = lambda a, b: f"{a}/{b} = {a/b:.0%}" if b else "n/a"
        lines += ["", "## Scores against labels (labels used only here)", "",
                  f"- Intent right: {pct(sum(r['intent'] == L(r).get('intent') for r in scored), k)} (target 85%)",
                  f"- Urgency right: {pct(sum(r['urgency'] == L(r).get('urgency') for r in scored), k)} (target 80%)",
                  f"- Route right: {pct(sum(r['route'] == L(r).get('expected_route') for r in scored), k)} (target 85%)",
                  f"- Must-not tickets auto-answered: {len(unsafe)} of {len(must_not)} (must be 0) {unsafe}",
                  f"- Auto-answered of those that should be: {pct(sum(r['route'] == 'auto_respond' for r in should), len(should))}",
                  f"- Auto-answers citing an expected article: {pct(cite, len(sent))} (target 85%)"]
    report = out_path.with_name(out_path.stem + "_metrics.md")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main():
    ap = argparse.ArgumentParser(description="Run the CloudServe pipeline on a ticket file.")
    ap.add_argument("input", help="path to the tickets JSON file")
    ap.add_argument("output", help="path for the results JSON file")
    ap.add_argument("--limit", type=int, help="development only: process just the first N tickets")
    args = ap.parse_args()

    raw_tickets = load_tickets(args.input)
    if args.limit:
        raw_tickets = raw_tickets[:args.limit]
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    conn = connect()
    before = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    started = datetime.now()
    print(f"Run started {started:%H:%M}: {len(raw_tickets)} tickets from {args.input}")

    results, no_model_in_row = [], 0
    for i, raw in enumerate(raw_tickets, 1):
        r = handle(raw, i, provider_down=no_model_in_row >= DOWN_AFTER)
        no_model_in_row = no_model_in_row + 1 if r["model_used"] == "none" else 0
        results.append(r)
        try:
            log_decision(conn, r["ticket_id"], intent=r["intent"], urgency=r["urgency"],
                         confidence=r["confidence"], retrieved_docs=r["retrieved_docs"],
                         route=r["route"], reason=r["reason"], model_used=r["model_used"],
                         latency_ms=r["latency_ms"], customer_tier=r["customer_tier"],
                         guardrails_run=int("review" in r["steps"] or bool(r["checks"])),
                         guardrail_result=json.dumps({"checks": r["checks"], "review": r["review"]}),
                         steps=json.dumps(r["steps"]), prompt_version=PROMPT_VERSION)
        except Exception as e:
            print(f"    {r['ticket_id']}: could not write to the decision log ({type(e).__name__})")
        # Save after every ticket, so nothing is lost if the machine dies
        out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"  [{i}/{len(raw_tickets)}] {r['ticket_id']} -> {r['route']} {r['tier'] or ''} | {r['reason']}")
        if i < len(raw_tickets):
            time.sleep(PAUSE_S)

    logged = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] - before
    report = write_report(results, raw_tickets, out_path, started, datetime.now(), logged)
    print(f"\nDone. {len(results)} of {len(raw_tickets)} tickets processed, {logged} decisions logged.")
    print(f"Results: {out_path}\nMetrics report: {report}")


if __name__ == "__main__":
    main()
