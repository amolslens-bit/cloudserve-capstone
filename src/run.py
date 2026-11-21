"""One command for the full run (A9, A10).

    python src/run.py <input tickets file> <output results file>
    e.g. python src/run.py data/development_tickets.json outputs/results.json

- Processes EVERY ticket in the file, however many. Never stops, never skips.
- If both AI models fail (rate limit, outage), it waits and retries. If they
  are still down, the ticket is escalated to a person with the reason logged.
- Any unexpected error on one ticket escalates that ticket; the run carries on.
- Every decision goes to the decision log (storage/decisions.db).
- At the end it writes a metrics report next to the output file, with the A10
  figures (volume, business, technical, governance) worked out by code.
Labels, if the file has them, are used ONLY for the scores in the report."""
import argparse
import json
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from decision_log import connect, log_decision
from pipeline import process

PROMPT_VERSION = "PR-01 1.3, PR-05 1.2, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1"
PAUSE_S = 3.5               # gap between tickets, keeps under per-minute limits
RETRY_WAITS_S = [30, 60, 120]  # waits before retrying when both models fail
DOWN_AFTER = 3              # this many tickets in a row with no model = provider down


def original_ticket(raw):
    """Unmasked subject and body, for the agent handover only (NFR-04)."""
    if not isinstance(raw, dict):
        return {"subject": "", "body": ""}
    return {"subject": raw.get("subject") or "", "body": raw.get("body") or ""}


def escalation(ticket_id, tier, reason, tier_name=None, raw=None):
    """A safe escalation record for a ticket the pipeline could not handle."""
    return {"ticket_id": ticket_id, "channel": None, "customer_tier": tier_name, "intent": "unclear_request",
            "urgency": "high", "confidence": 0.0, "alternatives": [], "billing_dispute": None,
            "data_commitment_request": None, "retrieved_docs": [], "route": "escalate",
            "tier": tier, "reason": reason, "checks": [], "draft": "", "cited": "",
            "answer_confidence": None, "review": None, "model_used": "none",
            "package": {"summary": "Summary not available; please read the ticket.",
                        "unsure_about": f"Escalated because: {reason}.", "summary_by": "code fallback",
                        "reason": reason, "articles_checked": [], "draft": "",
                        "original_ticket": original_ticket(raw)},
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
                              raw.get("customer_tier"), raw=raw)
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


# ---- A10 metrics helpers (pure code, no AI calls; tested in tests/test_metrics.py) ----

# Plain-English names for the routing checks in route.py (the last check in a record's
# "checks" list is the one that stopped an escalated ticket)
CHECK_NAMES = {
    "missing_fields": "missing details (customer ID, tier, region or body)",
    "instruction_check": "possible instruction in ticket (prompt-injection check)",
    "must_not": "must-not-auto-respond intent",
    "warning_words": "warning words (breach, lawyer, audit ...)",
    "dispute_commitment_flags": "billing dispute or data commitment",
    "classify_cutoff": "low classification confidence",
    "coverage_and_answer_cutoff": "no article covers it, or answer confidence too low",
    "citation": "no valid citation",
    "banned_claims": "draft contains a must-not claim",
    "reply_review": "reply review (PR-04) blocked the draft or did not run",
}
# Checks that look at a finished draft. A draft stopped by one of these = "blocked by guardrails".
DRAFT_GUARDRAILS = {"citation", "banned_claims", "reply_review"}
NOT_A_GUARDRAIL = ("AI service unavailable", "system error", "malformed")

# Private data a reply must never contain (brief, governance: zero occurrences)
PRIVATE_PATTERNS = {
    "email address": r"[\w.+-]+@[\w-]+\.[\w.-]+",
    "phone number": r"\+?\d[\d\s().-]{8,}\d",   # counted only if it has 10+ digits
    "API key or secret": r"\b(?:sk|pk|api|key|tok)[_-][A-Za-z0-9_-]{12,}\b",
}


def percentile(values, p):
    """p-th percentile (0-100), straight-line between the two nearest values
    (the same method as numpy's default). None if there are no values."""
    v = sorted(values)
    if not v:
        return None
    pos = (len(v) - 1) * p / 100
    lo = int(pos)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def stop_check(r):
    """Which check stopped an escalated ticket: the last check route.py ran.
    None for auto-answers, and for tickets the system itself could not process."""
    if r["route"] != "escalate" or not r.get("checks"):
        return None
    if (r.get("reason") or "").startswith(NOT_A_GUARDRAIL):
        return None
    return r["checks"][-1]


def is_blocked(r):
    """Blocked by guardrails = a draft was written but a draft check stopped it
    (citation, must-not claim, or the PR-04 reply review)."""
    return stop_check(r) in DRAFT_GUARDRAILS


def timed(results):
    """Records with a real measured time. Code fallback records (steps == ["error"])
    carry latency_ms 0 because no time was measured, so they are left out."""
    return [r["latency_ms"] for r in results if r.get("steps") != ["error"]]


def intent_scores(pairs):
    """pairs = [(predicted intent, labelled intent), ...]
    Returns {intent: (precision, recall, labelled count)}; precision/recall None if undefined."""
    classes = sorted({p for p, _ in pairs} | {g for _, g in pairs})
    out = {}
    for c in classes:
        tp = sum(p == c and g == c for p, g in pairs)
        predicted = sum(p == c for p, _ in pairs)
        actual = sum(g == c for _, g in pairs)
        out[c] = (tp / predicted if predicted else None, tp / actual if actual else None, actual)
    return out


def private_data_in_reply(text):
    """Counts of private-data patterns found in a reply text, by type."""
    found = Counter()
    for name, pattern in PRIVATE_PATTERNS.items():
        hits = re.findall(pattern, text or "")
        if name == "phone number":       # skip dates, prices and IDs: a phone has 10+ digits
            hits = [h for h in hits if sum(ch.isdigit() for ch in h) >= 10
                    and not re.match(r"\d{4}-\d{2}-\d{2}", h)]
        found[name] += len(hits)
    return +found


def write_report(results, raw_tickets, out_path, started, finished, logged):
    n = len(results)
    routes = Counter(r["route"] for r in results)
    share = lambda a: f"{a} ({a/max(n,1):.0%})"
    pct = lambda a, b: f"{a}/{b} = {a/b:.0%}" if b else "n/a"
    sec = lambda ms: f"{ms/1000:.1f} s" if ms is not None else "n/a"
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

    # Labels, if the file has them, are used ONLY for scores (dev / validation files do, hidden set may not)
    labels = {t["ticket_id"]: t["labels"] for t in raw_tickets
              if isinstance(t, dict) and isinstance(t.get("labels"), dict) and t.get("ticket_id")}
    scored = [r for r in results if r["ticket_id"] in labels]
    L = lambda r: labels[r["ticket_id"]]

    # ---- A10: Volume ----
    blocked = [r for r in results if is_blocked(r)]
    lines += ["", "## A10 Volume", "",
              f"- Tickets processed: {n}",
              f"- Answered automatically: {share(routes['auto_respond'])}",
              f"- Escalated: {share(routes['escalate'])}",
              f"- Blocked by guardrails: {share(len(blocked))}",
              "  - (a draft was written but stopped by a draft check: no valid citation, "
              "a must-not claim, or the PR-04 reply review)"]

    # ---- A10: Business ----
    times = timed(results)
    lines += ["", "## A10 Business", "",
              f"- First contact resolution: {share(routes['auto_respond'])}",
              "  - (brief's definition: tickets closed without escalation, divided by total tickets; "
              "here = auto-answered / processed)"]
    if scored:
        right_auto = sum(r["route"] == "auto_respond" and L(r).get("expected_route") == "auto_respond"
                         for r in scored)
        lines += [f"- First contact resolution, correct answers only: {pct(right_auto, len(scored))}",
                  "  - (auto-answered AND the label says it should be auto-answered, "
                  "divided by labelled tickets)"]
    lines += [f"- Response time, mean: {sec(sum(times)/len(times) if times else None)}",
              f"- Response time, median: {sec(percentile(times, 50))}",
              f"  - (system processing time per ticket from latency_ms; {len(times)} of {n} tickets timed, "
              "code fallback records with no measured time left out)",
              f"- Escalation rate: {share(routes['escalate'])} (target 30% or lower)"]

    # ---- A10: Technical ----
    lines += ["", "## A10 Technical", ""]
    if scored:
        scores = intent_scores([(r["intent"], L(r).get("intent")) for r in scored])
        f = lambda x: f"{x:.0%}" if x is not None else "n/a"
        lines += [f"Intent precision and recall per class ({len(scored)} labelled tickets):", "",
                  "| Intent | Precision | Recall | Labelled tickets |", "|---|---|---|---|"]
        for c, (p, rc, k) in scores.items():
            lines.append(f"| {c} | {f(p)} | {f(rc)} | {k} |")
        ps = [p for p, _, _ in scores.values() if p is not None]
        rs = [rc for _, rc, _ in scores.values() if rc is not None]
        lines += ["",
                  f"- Average precision across classes: {f(sum(ps)/len(ps) if ps else None)} (target 85%)",
                  f"- Average recall across classes: {f(sum(rs)/len(rs) if rs else None)}",
                  "  - (precision = of the tickets we put in a class, share that were really that class; "
                  "recall = of the tickets really in a class, share we found)"]
    else:
        lines.append("- Intent precision and recall per class: n/a (input file has no labels)")
    searched = [r for r in results if "retrieve" in (r.get("steps") or [])]
    hit = sum(bool(r.get("retrieved_docs")) for r in searched)
    lines += [f"- Retrieval hit rate: {pct(hit, len(searched))}",
              "  - (of the tickets that reached the search step, share with at least one article "
              "kept under the MAX_SCORE cut-off)"]
    if scored:
        want = [r for r in searched if r["ticket_id"] in labels and L(r).get("expected_doc_ids")]
        right_doc = sum(bool(set(r.get("retrieved_docs") or []) & set(L(r)["expected_doc_ids"])) for r in want)
        lines += [f"- Retrieval hit rate, right article: {pct(right_doc, len(want))}",
                  "  - (of searched tickets whose label lists expected articles, share where one of "
                  "them was among the articles retrieved)"]
    lines += [f"- Latency, median (p50): {sec(percentile(times, 50))}",
              f"- Latency, 95th percentile (p95): {sec(percentile(times, 95))} (target under 3 s)"]

    # ---- A10: Governance ----
    acts = Counter(stop_check(r) for r in results if stop_check(r))
    review_blocks = sum((r.get("review") or {}).get("verdict") == "block" for r in results)
    lines += ["", "## A10 Governance", "",
              f"- Decisions logged: {logged} of {n} processed "
              f"({'reconciles' if logged == n else 'DOES NOT reconcile'})",
              f"- Guardrail activations by type (the check that stopped each escalated ticket): "
              f"{sum(acts.values())}"]
    for chk, c in acts.most_common():
        lines.append(f"  - {c}  {CHECK_NAMES.get(chk, chk)}")
    lines.append(f"- Reply review (PR-04) verdicts of block, including tickets stopped earlier "
                 f"by another check: {review_blocks}")
    red = [r["redactions"] for r in results if isinstance(r.get("redactions"), dict)]
    if red:
        total = Counter()
        for d in red:
            total.update({k: v for k, v in d.items() if isinstance(v, int)})
        lines.append(f"- Private data detected and masked in incoming tickets: {sum(total.values())} "
                     f"({', '.join(f'{k} {v}' for k, v in total.most_common()) or 'none'})")
    else:
        lines.append("- Private data detected and masked in incoming tickets: not recorded "
                     "(the results do not carry redaction counts)")
    leaks = Counter()
    for r in results:
        if r["route"] == "auto_respond":
            leaks.update(private_data_in_reply(r.get("draft")))
    lines.append(f"- Private data found in auto-answered replies: {sum(leaks.values())} (must be 0) "
                 f"{dict(leaks) if leaks else ''}".rstrip())
    lines.append("  - (code scan of each auto-answered draft for email addresses, phone numbers "
                 "and API-key-like strings)")

    if scored:
        k = len(scored)
        must_not = [r for r in scored if L(r).get("must_not_auto_respond")]
        unsafe = [r["ticket_id"] for r in must_not if r["route"] == "auto_respond"]
        should = [r for r in scored if L(r).get("expected_route") == "auto_respond"]
        sent = [r for r in scored if r["route"] == "auto_respond"]
        cite = sum(r["cited"] in (L(r).get("expected_doc_ids") or []) for r in sent)
        lines += ["", "## Scores against labels (labels used only here)", "",
                  f"- Intent right: {pct(sum(r['intent'] == L(r).get('intent') for r in scored), k)} (target 85%)",
                  f"- Urgency right: {pct(sum(r['urgency'] == L(r).get('urgency') for r in scored), k)} (target 80%)",
                  f"- Route right: {pct(sum(r['route'] == L(r).get('expected_route') for r in scored), k)} (target 85%)",
                  f"- Must-not tickets auto-answered: {len(unsafe)} of {len(must_not)} (must be 0) {unsafe}",
                  f"- Auto-answered of those that should be: {pct(sum(r['route'] == 'auto_respond' for r in should), len(should))}",
                  f"- Auto-answers citing an expected article: {pct(cite, len(sent))} (target 85%)"]
        lines += citation_lines(sent, L, pct)
    report = out_path.with_name(out_path.stem + "_metrics.md")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def cited_ids(r):
    """Doc ids a result cites: the PR-05 1.2 citations list, or the 1.1 single `cited`."""
    cs = r.get("citations")
    if cs:
        return [c.get("doc_id") for c in cs if isinstance(c, dict)]
    return [r["cited"]] if r.get("cited") else []


def citation_lines(sent, L, pct):
    """PR-05 1.2 citation measures. The metric above (primary `cited`) is unchanged."""
    want = [r for r in sent if L(r).get("expected_doc_ids")]
    full = sum(set(L(r)["expected_doc_ids"]) <= set(cited_ids(r)) for r in want)
    two = [r for r in want if len(L(r)["expected_doc_ids"]) > 1]
    two_full = sum(set(L(r)["expected_doc_ids"]) <= set(cited_ids(r)) for r in two)
    cits = [c for r in sent for c in (r.get("citations") or []) if isinstance(c, dict)]
    with_sec = sum(bool(c.get("section")) for c in cits)
    extra = sum(max(len(r.get("citations") or []) - 1, 0) for r in sent)
    dropped = sum(sum(n.startswith("dropped") for n in (r.get("citation_notes") or [])) for r in sent)
    return [f"- Auto-answers citing ALL expected articles: {pct(full, len(want))}",
            f"  - of those expecting 2 or more articles: {pct(two_full, len(two))}",
            f"- Citations with a valid section heading: {pct(with_sec, len(cits))}",
            "  - (code checks every section against the article's ## headings; an invalid primary "
            "section keeps the article with no section)",
            f"- Extra (related) sources kept: {extra}; dropped by the code check: {dropped}"]


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
                         guardrail_result=json.dumps({"checks": r["checks"], "review": r["review"],
                                                     "citation_notes": r.get("citation_notes", [])}),
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
