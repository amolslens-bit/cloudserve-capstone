"""Scan the retrieval "no article covers it" cut-off (MAX_SCORE) on the 500 dev tickets.

No AI calls, no API keys, nothing written to storage/. Chroma is only read.
It reuses src/retrieve.py (its db object, build_query and MAX_SCORE), so the
search is exactly the one the pipeline runs. Chroma distance: lower = closer.
A hit is kept when score <= cut-off (same rule as retrieve.py).

Run from C:\\capstone:
    python src\\scan_cutoff.py
    python src\\scan_cutoff.py --intent-from outputs\\dev500_claude.json

This is a tuning scan on labelled development tickets. By default the intent
put in front of the query is the LABELLED intent (labels.intent), not the
model's prediction. Use --intent-from to use the predicted intent instead.
It changes no routing and no settings.
"""
import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

DEFAULT_TICKETS = "data/development_tickets.json"
DEFAULT_CSV = "outputs/cutoff_scan.csv"
DEFAULT_MD = "outputs/cutoff_scan.md"
RECALL_TARGET = 0.95


# ---------------------------------------------------------------- pure part
# Everything in this section is plain Python (no Chroma, no AI), so it can be tested.

def candidate_cutoffs(current=None, start=0.60, stop=1.60, step=0.05):
    """0.60, 0.65 ... 1.60, plus the current MAX_SCORE if given. Sorted, no duplicates."""
    vals, n = set(), int(round((stop - start) / step))
    for i in range(n + 1):
        vals.add(round(start + i * step, 4))
    if current is not None:
        vals.add(round(float(current), 4))
    return sorted(vals)


def _kept(score, cutoff):
    return score is not None and score <= cutoff


def threshold_table(rows, cutoffs):
    """One line per cut-off.

    Each row needs:
      best_score           lowest distance of any article (None = nothing found)
      best_expected_score  lowest distance of an expected article within the
                           articles the pipeline would take (None = not among them)
      answerable           labels.answerable_from_docs (bool)
    """
    ans = [r for r in rows if r["answerable"]]
    ans_exp = [r for r in ans if r.get("best_expected_score") is not None]
    unans = [r for r in rows if not r["answerable"]]
    table = []
    for c in cutoffs:
        ans_kept = sum(_kept(r["best_score"], c) for r in ans)
        ans_exp_kept = sum(_kept(r["best_expected_score"], c) for r in ans_exp)
        ans_any_exp_kept = sum(_kept(r.get("best_expected_score"), c) for r in ans)
        unans_kept = sum(_kept(r["best_score"], c) for r in unans)
        recall = ans_exp_kept / len(ans_exp) if ans_exp else 0.0
        false_keep = unans_kept / len(unans) if unans else 0.0
        table.append({
            "cutoff": c,
            "answerable": len(ans),
            "answerable_kept": ans_kept,
            "answerable_kept_expected": ans_any_exp_kept,
            "answerable_with_expected": len(ans_exp),
            "answerable_with_expected_kept": ans_exp_kept,
            "unanswerable": len(unans),
            "unanswerable_kept": unans_kept,
            "unanswerable_blocked": len(unans) - unans_kept,
            "recall_expected": recall,
            "false_keep_rate": false_keep,
            "youden": recall - false_keep,
        })
    return table


def best_youden(table):
    """Cut-off with the best balance (recall of expected articles minus false-keep rate).
    Ties go to the higher (looser, safer for answers) cut-off."""
    if not table:
        return None
    return max(table, key=lambda t: (round(t["youden"], 9), t["cutoff"]))


def best_at_recall(table, target=RECALL_TARGET):
    """Strictest cut-off that still keeps >= target of answerable-with-expected-article
    tickets, i.e. the one that blocks the most unanswerable tickets. None if no cut-off reaches it."""
    ok = [t for t in table if t["answerable_with_expected"] and t["recall_expected"] >= target]
    if not ok:
        return None
    return max(ok, key=lambda t: (t["unanswerable_blocked"], -t["cutoff"]))


def summarize(values):
    """min / median / p90 / max of the non-missing values (nearest-rank p90)."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return {"n": 0, "min": None, "median": None, "p90": None, "max": None}
    idx = max(0, min(len(vals) - 1, -(-90 * len(vals) // 100) - 1))
    return {"n": len(vals), "min": vals[0], "median": statistics.median(vals),
            "p90": vals[idx], "max": vals[-1]}


def distinct_hits(hits):
    """[(doc_id, score)] best first, one entry per doc_id (like retrieve.py's loop)."""
    seen, out = set(), []
    for doc_id, score in sorted(hits, key=lambda h: h[1]):
        if doc_id in seen:
            continue
        seen.add(doc_id)
        out.append((doc_id, float(score)))
    return out


def scan_row(ticket, hits, k, intent_used, intent_source, reached_search=None):
    """Turn one ticket's raw hits into a CSV row. hits = [(doc_id, score)]."""
    lab = ticket.get("labels") or {}
    expected = set(lab.get("expected_doc_ids") or [])
    d = distinct_hits(hits)
    taken = d[:k]                       # what retrieve(k=...) could return at a loose cut-off
    exp_scores = [s for doc, s in taken if doc in expected]
    return {
        "ticket_id": ticket.get("ticket_id"),
        "intent_used": intent_used or "",
        "intent_source": intent_source,
        "best_score": round(d[0][1], 4) if d else None,
        "second_score": round(d[1][1], 4) if len(d) > 1 else None,
        "top_doc_id": d[0][0] if d else "",
        "second_doc_id": d[1][0] if len(d) > 1 else "",
        "top_in_expected": bool(d) and d[0][0] in expected,
        "best_expected_score": round(min(exp_scores), 4) if exp_scores else None,
        "expected_doc_ids": ";".join(sorted(expected)),
        "answerable": bool(lab.get("answerable_from_docs")),
        "expected_route": lab.get("expected_route", ""),
        "reached_search": reached_search,
    }


def _f(v, nd=3):
    return "-" if v is None else f"{v:.{nd}f}"


def report_lines(rows, cutoffs, current, k, intent_note, title_extra=""):
    """Markdown lines for one group of rows: distributions, table, recommendations."""
    table = threshold_table(rows, cutoffs)
    out = []
    ans = [r for r in rows if r["answerable"]]
    unans = [r for r in rows if not r["answerable"]]
    out.append(f"Tickets: {len(rows)} ({len(ans)} answerable from docs, {len(unans)} not){title_extra}")
    out.append("")
    out.append("Best-score distribution (lowest distance per ticket; lower = closer):")
    out.append("")
    out.append("| Group | n | min | median | p90 | max |")
    out.append("|---|---|---|---|---|---|")
    for name, grp, key in [("answerable, best article", ans, "best_score"),
                           ("answerable, best expected article", ans, "best_expected_score"),
                           ("not answerable, best article", unans, "best_score")]:
        s = summarize(r[key] for r in grp)
        out.append(f"| {name} | {s['n']} | {_f(s['min'])} | {_f(s['median'])} | {_f(s['p90'])} | {_f(s['max'])} |")
    out.append("")
    out.append("| Cut-off | Answerable keep >=1 article | Answerable keep an expected article "
               "| Not answerable wrongly kept | Not answerable blocked | Balance (Youden) |")
    out.append("|---|---|---|---|---|---|")
    for t in table:
        mark = " (current)" if current is not None and abs(t["cutoff"] - current) < 1e-9 else ""
        out.append(
            f"| {t['cutoff']:.2f}{mark} | {t['answerable_kept']}/{t['answerable']} "
            f"| {t['answerable_with_expected_kept']}/{t['answerable_with_expected']} "
            f"({t['recall_expected']:.0%}) "
            f"| {t['unanswerable_kept']}/{t['unanswerable']} ({t['false_keep_rate']:.0%}) "
            f"| {t['unanswerable_blocked']} | {t['youden']:.2f} |")
    out.append("")
    if not unans or not any(t["answerable_with_expected"] for t in table):
        out.append("- No recommendation for this group: it needs both answerable and not-answerable tickets.")
        return out
    y = best_youden(table)
    r95 = best_at_recall(table)
    if y:
        out.append(f"- Best balance (Youden): cut-off {y['cutoff']:.2f} keeps an expected article for "
                   f"{y['answerable_with_expected_kept']}/{y['answerable_with_expected']} "
                   f"({y['recall_expected']:.0%}) and blocks {y['unanswerable_blocked']}/{y['unanswerable']} "
                   f"not-answerable tickets.")
    if r95:
        out.append(f"- Keeps >={RECALL_TARGET:.0%} of answerable-with-expected-article while blocking the most: "
                   f"cut-off {r95['cutoff']:.2f} keeps {r95['answerable_with_expected_kept']}/"
                   f"{r95['answerable_with_expected']} ({r95['recall_expected']:.0%}) and blocks "
                   f"{r95['unanswerable_blocked']}/{r95['unanswerable']}.")
    else:
        out.append(f"- No cut-off in the list keeps >={RECALL_TARGET:.0%} of answerable-with-expected-article tickets.")
    return out


# ---------------------------------------------------------------- I/O part

def load_tickets(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "tickets" in data:
        data = data["tickets"]
    if not isinstance(data, list):
        raise SystemExit(f"{path}: expected a list of tickets or a dict with 'tickets'")
    return data


def load_predictions(path):
    """ticket_id -> (intent, reached_search) from a run.py / merge_runs.py results file."""
    data = load_tickets(path)
    out = {}
    for r in data:
        steps = r.get("steps") or []
        names = [s if isinstance(s, str) else (s or {}).get("step") for s in steps]
        out[r.get("ticket_id")] = (r.get("intent"), ("retrieve" in names) if steps else None)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scan the retrieval cut-off (no AI, read-only).")
    ap.add_argument("--tickets", default=DEFAULT_TICKETS)
    ap.add_argument("--intent-from", default=None,
                    help="results file (e.g. outputs\\dev500_claude.json): use its predicted 'intent'")
    ap.add_argument("--k", type=int, default=2,
                    help="articles the pipeline asks for (pipeline.py calls retrieve(k=2))")
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--md", default=DEFAULT_MD)
    args = ap.parse_args(argv)

    import retrieve  # the project's own module: same Chroma store, collection and embedding
    if not hasattr(retrieve, "db"):
        raise SystemExit("src/retrieve.py has no 'db' object, so the scan cannot reuse it. Send me retrieve.py.")
    current = getattr(retrieve, "MAX_SCORE", None)

    def query_for(ticket, intent):
        if hasattr(retrieve, "build_query"):
            return retrieve.build_query(ticket, intent)
        q = f"{ticket.get('subject') or ''} {ticket['body']}"   # same text retrieve.py builds
        if intent and intent != "unclear_request":
            q = f"{intent.replace('_', ' ')}: {q}"
        return q

    tickets = load_tickets(args.tickets)
    preds = load_predictions(args.intent_from) if args.intent_from else None
    if preds is not None:
        intent_note = f"predicted intent from {args.intent_from} (field 'intent', matched by ticket_id)"
    else:
        intent_note = "LABELLED intent (labels.intent). This is a tuning scan, not what the live system sees"

    rows, missing = [], 0
    for i, t in enumerate(tickets, 1):
        lab = t.get("labels") or {}
        if preds is not None:
            if t.get("ticket_id") in preds:
                intent, reached = preds[t["ticket_id"]]
                src = "predicted"
            else:
                intent, reached, src = lab.get("intent"), None, "label (no prediction)"
                missing += 1
        else:
            intent, reached, src = lab.get("intent"), None, "label"
        raw = retrieve.db.similarity_search_with_score(query_for(t, intent), k=12)
        hits = [(doc.metadata["doc_id"], score) for doc, score in raw]
        rows.append(scan_row(t, hits, args.k, intent, src, reached))
        if i % 100 == 0:
            print(f"  scanned {i}/{len(tickets)}")

    Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    cutoffs = candidate_cutoffs(current)
    lines = ["# Retrieval cut-off scan (dev tickets, no AI)", "",
             f"- Tickets file: {args.tickets}",
             f"- Intent in the query: {intent_note}",
             f"- Current MAX_SCORE read from src/retrieve.py: {current}",
             f"- Articles per ticket (k): {args.k}; Chroma distance, lower = closer; kept when score <= cut-off",
             "- Read-only on storage/chroma. No AI calls. This changes no routing or settings.",
             "- Dev tickets the system was tuned on: not an official result (that stays the 20 Nov holdout, T45).",
             ""]
    if missing:
        lines.append(f"- {missing} tickets had no prediction in the results file; their labelled intent was used.")
        lines.append("")
    lines.append("## All tickets")
    lines.append("")
    lines += report_lines(rows, cutoffs, current, args.k, intent_note)
    searched = [r for r in rows if r["reached_search"]]
    if searched:
        lines += ["", "## Only tickets that reached the search step in that run",
                  "(must-not intents and other early escalations never reach search, so the cut-off "
                  "cannot affect them)", ""]
        lines += report_lines(searched, cutoffs, current, args.k, intent_note)
    lines += ["", f"Per-ticket rows: {args.csv}"]
    text = "\n".join(lines) + "\n"
    Path(args.md).write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {args.csv} and {args.md}")


if __name__ == "__main__":
    sys.exit(main())
