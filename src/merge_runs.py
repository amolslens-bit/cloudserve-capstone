"""Merge part result files and write the standard metrics report plus extras.

    python src/merge_runs.py --tickets data/development_tickets.json --output outputs/dev500_claude.json outputs/dev500_part1.json outputs/dev500_part2.json outputs/dev500_part3.json outputs/dev500_part4.json

Reuses run.write_report for the usual metrics (pass the merged raw tickets so
labels are scored). Then appends: PRD first-contact resolution, current-process
baselines taken from each ticket's history block, miss lists by ticket ID,
recurring known issues, call/latency totals, and a cost estimate (estimate only).

This script does not call an AI.
"""
import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from run import (
    PROMPT_VERSION,
    cited_ids,
    load_tickets,
    percentile,
    private_data_in_reply,
    timed,
    write_report,
)

# Official Haiku 5.5 list prices used for the 20 Nov holdout estimate (prompts up to 100k).
# Thinking tokens are billed as output and are the main uncertainty.
PRICE_IN_PER_MTOK = 0.10
PRICE_OUT_PER_MTOK = 0.50
# 80-ticket official holdout estimate band (docs/HOLDOUT_RESULT.md), no measured bill.
HOLDOUT_TICKETS = 80
HOLDOUT_CALLS = 266
HOLDOUT_COST_LOW = 0.10
HOLDOUT_COST_HIGH = 0.40


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _as_ticket_list(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("tickets"), list):
        return data["tickets"]
    raise SystemExit(f"not a ticket or results list: expected a list or a dict with 'tickets'")


def _ticket_id_sort(tid):
    m = re.search(r"(\d+)$", str(tid) or "")
    prefix = str(tid)[: m.start()] if m else str(tid)
    return (prefix, int(m.group(1)) if m else 0, str(tid))


def merge_results(part_paths):
    """Combine part files. Keep first occurrence of a ticket_id; report duplicates and empties."""
    merged, seen, duplicates, empty = [], {}, [], []
    for path in part_paths:
        path = Path(path)
        rows = _as_ticket_list(_load_json(path))
        if not rows:
            empty.append(str(path))
        for row in rows:
            if not isinstance(row, dict):
                continue
            tid = row.get("ticket_id")
            if not tid:
                continue
            if tid in seen:
                duplicates.append((tid, seen[tid], str(path)))
                continue
            seen[tid] = str(path)
            merged.append(row)
    merged.sort(key=lambda r: _ticket_id_sort(r.get("ticket_id") or ""))
    return merged, duplicates, empty


def _labels(raw_tickets):
    return {
        t["ticket_id"]: t["labels"]
        for t in raw_tickets
        if isinstance(t, dict) and isinstance(t.get("labels"), dict) and t.get("ticket_id")
    }


def _history(raw_tickets):
    out = {}
    for t in raw_tickets:
        if isinstance(t, dict) and t.get("ticket_id") and isinstance(t.get("history"), dict):
            out[t["ticket_id"]] = t["history"]
    return out


def _reply_text(r):
    return r.get("customer_reply") or r.get("draft") or ""


def safety_break(r, lab):
    """A safety problem on an auto-answer, or a must-not ticket that was auto-answered."""
    reasons = []
    if lab.get("must_not_auto_respond") and r.get("route") == "auto_respond":
        reasons.append("must-not auto-answered")
    review = r.get("review") if isinstance(r.get("review"), dict) else {}
    if review.get("verdict") == "block":
        reasons.append("PR-04 block")
    # "checks" lists every check that RAN (route.py appends "banned_claims" before it
    # passes), so its presence is not a failure. A banned claim is only a failure when
    # the reason says so (route.py then escalates).
    if r.get("route") == "auto_respond" and "must-not claim" in (r.get("reason") or ""):
        reasons.append("banned claim")
    leaks = private_data_in_reply(_reply_text(r))
    if leaks:
        reasons.append("PII in reply")
    return reasons


def lexical_points(text, phrases):
    """Case-insensitive substring check. Not the PR-08 judge: paraphrases are missed."""
    low = (text or "").lower()
    phrases = [p for p in (phrases or []) if isinstance(p, str) and p.strip()]
    missing = [p for p in phrases if p.lower() not in low]
    return missing


def prd_fcr_ok(r, lab, truth=None, use_answer_key=False):
    """PRD rule: auto-answered AND labelled for a reply AND cites an expected article
    AND no safety break. On answer-key tickets, also lexical must_mention / must_not_claim
    when those fields are available and use_answer_key is True."""
    if r.get("route") != "auto_respond":
        return False, "not auto-answered"
    if lab.get("expected_route") != "auto_respond":
        return False, "not labelled for a reply"
    expected = lab.get("expected_doc_ids") or []
    if not expected or r.get("cited") not in expected:
        return False, "did not cite an expected article"
    breaks = safety_break(r, lab)
    if breaks:
        return False, "; ".join(breaks)
    if use_answer_key and truth:
        missing = lexical_points(_reply_text(r), truth.get("must_mention"))
        reply = _reply_text(r)
        hits = [p for p in (truth.get("must_not_claim") or []) if p.lower() in reply.lower()]
        if missing:
            return False, "must_mention missed (lexical check)"
        if hits:
            return False, "must_not_claim present (code check)"
    return True, "ok"


def current_process_baselines(raw_tickets):
    """Figures taken only from each ticket's history block (and labels for the
    143 not-coverable count). Returns None fields when history is missing."""
    rows = [t for t in raw_tickets if isinstance(t, dict)]
    if not rows:
        return None
    has_history = [t for t in rows if isinstance(t.get("history"), dict)]
    if not has_history:
        return None

    def rate(xs, key):
        n = len(xs)
        k = sum(bool((t.get("history") or {}).get(key)) for t in xs)
        return k, n, (k / n if n else None)

    def mean_min(xs):
        vals = [(t.get("history") or {}).get("resolution_time_minutes") for t in xs]
        vals = [v for v in vals if isinstance(v, (int, float))]
        return (sum(vals) / len(vals)) if vals else None

    overall_f, overall_n, overall_p = rate(has_history, "first_contact_resolution")
    esc_k, esc_n, esc_p = rate(has_history, "escalated")
    rep_k, rep_n, rep_p = rate(has_history, "repeat_contact")
    by_tier = {}
    for t in has_history:
        by_tier.setdefault(t.get("customer_tier") or "unknown", []).append(t)
    tier = {}
    for name, xs in sorted(by_tier.items()):
        k, n, p = rate(xs, "first_contact_resolution")
        ek, en, ep = rate(xs, "escalated")
        tier[name] = {
            "fcr": (k, n, p),
            "escalated": (ek, en, ep),
            "mean_resolution_min": mean_min(xs),
        }
    not_coverable = sum(
        (t.get("labels") or {}).get("answerable_from_docs") is False for t in rows
    )
    return {
        "n_with_history": len(has_history),
        "n_tickets": len(rows),
        "fcr": (overall_f, overall_n, overall_p),
        "escalated": (esc_k, esc_n, esc_p),
        "repeat_contact": (rep_k, rep_n, rep_p),
        "mean_resolution_min": mean_min(has_history),
        "by_tier": tier,
        "not_coverable": not_coverable,
    }


def _pct(a, b):
    return f"{a}/{b} = {a/b:.0%}" if b else "n/a"


def _pct1(a, b):
    """One decimal, for baselines such as 43.8%."""
    return f"{a}/{b} = {a/b*100:.1f}%" if b else "n/a"


def miss_lists(results, labels):
    should_auto_esc, should_esc_auto, wrong_cite, must_not_auto = [], [], [], []
    for r in results:
        tid = r.get("ticket_id")
        lab = labels.get(tid) or {}
        if not lab:
            continue
        if lab.get("expected_route") == "auto_respond" and r.get("route") == "escalate":
            should_auto_esc.append(tid)
        if lab.get("expected_route") == "escalate" and r.get("route") == "auto_respond":
            should_esc_auto.append(tid)
        if r.get("route") == "auto_respond":
            expected = lab.get("expected_doc_ids") or []
            if expected and r.get("cited") not in expected:
                wrong_cite.append(tid)
        if lab.get("must_not_auto_respond") and r.get("route") == "auto_respond":
            must_not_auto.append(tid)
    return {
        "should_auto_escalated": should_auto_esc,
        "should_escalate_auto_answered": should_esc_auto,
        "wrong_citations": wrong_cite,
        "must_not_auto_answered": must_not_auto,
    }


def _ids(xs, limit=None):
    if not xs:
        return "(none)"
    body = ", ".join(xs if limit is None else xs[:limit])
    if limit is not None and len(xs) > limit:
        body += f", … +{len(xs) - limit} more"
    return body


def identical_body_twins(raw_tickets, labels):
    """Tickets that share subject+body but differ on route or expected articles."""
    groups = defaultdict(list)
    for t in raw_tickets:
        if not isinstance(t, dict):
            continue
        key = ((t.get("subject") or "").strip(), (t.get("body") or "").strip())
        if not key[1] and not key[0]:
            continue
        groups[key].append(t.get("ticket_id"))
    conflicts = []
    for ids in groups.values():
        ids = [i for i in ids if i]
        if len(ids) < 2:
            continue
        routes = { (labels.get(i) or {}).get("expected_route") for i in ids }
        docs = { tuple((labels.get(i) or {}).get("expected_doc_ids") or []) for i in ids }
        must = { bool((labels.get(i) or {}).get("must_not_auto_respond")) for i in ids }
        if len(routes) > 1 or len(docs) > 1 or len(must) > 1:
            conflicts.append(sorted(ids, key=_ticket_id_sort))
    conflicts.sort(key=lambda g: _ticket_id_sort(g[0]))
    return conflicts


def load_ground_truth(path):
    if not path or not Path(path).exists():
        return None
    rows = _as_ticket_list(_load_json(path))
    out = {}
    for row in rows:
        if isinstance(row, dict) and row.get("ticket_id"):
            out[row["ticket_id"]] = row
    return out or None


def estimate_cost(n_tickets, n_calls):
    """Scale the official 80-ticket holdout estimate band by tickets and calls.
    Not a bill: the results file has no token usage."""
    if n_tickets <= 0:
        return None
    scale_t = n_tickets / HOLDOUT_TICKETS
    scale_c = (n_calls / HOLDOUT_CALLS) if n_calls else scale_t
    scale = max(scale_t, scale_c)
    return {
        "low": HOLDOUT_COST_LOW * scale,
        "high": HOLDOUT_COST_HIGH * scale,
        "scale_tickets": scale_t,
        "scale_calls": scale_c,
        "n_tickets": n_tickets,
        "n_calls": n_calls,
    }


def extra_lines(results, raw_tickets, labels, misses, baselines, truth, duplicates, empty,
                missing_ids, part_paths, truth_path):
    n = len(results)
    lines = ["", "## Merged run notes", "",
             f"- Part files: {', '.join(str(p) for p in part_paths)}",
             f"- Tickets in the merged file: {n}",
             "- The 'decisions written to the log this run' line in the standard report "
             "does not apply to a merge: each window wrote its own log (or skipped a row "
             "if the log was locked). Scoring uses this JSON, not the log.",
             f"- Prompt versions (from run.py): {PROMPT_VERSION}"]
    if empty:
        lines.append(f"- Empty part files: {', '.join(empty)}")
    if duplicates:
        lines.append(f"- Duplicate ticket_ids (kept the first, skipped later): {len(duplicates)}")
        for tid, first, later in duplicates[:20]:
            lines.append(f"  - {tid} first in {first}, also in {later}")
    if missing_ids:
        lines.append(f"- Tickets in the input file with no merged result: {len(missing_ids)}")
        lines.append(f"  - {_ids(missing_ids)}")
    extra_res = [r["ticket_id"] for r in results if r.get("ticket_id") not in labels
                 and labels]
    # only mention extras if we were given labelled tickets
    raw_ids = {t.get("ticket_id") for t in raw_tickets if isinstance(t, dict)}
    extra_res = [r.get("ticket_id") for r in results if r.get("ticket_id") not in raw_ids]
    if extra_res:
        lines.append(f"- Result rows not in the tickets file: {len(extra_res)} ({_ids(extra_res)})")

    # ---- PRD FCR ----
    lines += ["", "## PRD first-contact resolution (labelled dev-set check)", "",
              "A ticket counts when the system auto-answers it, the ticket is labelled "
              "for a reply (expected_route = auto_respond), the answer cites an expected "
              "article, and no safety rule is broken (must-not auto-answered, PR-04 block, "
              "banned claim, or PII in the reply). This is stricter than the brief's "
              "auto-answered / processed rate in the standard report above.",
              "This is a check on the 500 development tickets the system was tuned on. "
              "It is not an official result. The official score remains the 20 Nov holdout (T45)."]
    prd_ok = []
    for r in results:
        lab = labels.get(r.get("ticket_id")) or {}
        ok, _why = prd_fcr_ok(r, lab, use_answer_key=False)
        if ok:
            prd_ok.append(r["ticket_id"])
    lines.append(f"- PRD FCR on labelled tickets: {_pct(len(prd_ok), len(labels) or n)}")

    # 200-set with lexical mention / claim checks
    if truth:
        subset = [r for r in results if r.get("ticket_id") in truth]
        ok200 = []
        for r in subset:
            lab = labels.get(r.get("ticket_id")) or {}
            ok, why = prd_fcr_ok(r, lab, truth.get(r.get("ticket_id")), use_answer_key=True)
            if ok:
                ok200.append(r["ticket_id"])
        lines += [
            f"- PRD FCR on the {len(truth)} answer-key tickets, with lexical must_mention "
            f"and code must_not_claim (no AI / not the PR-08 judge): "
            f"{_pct(len(ok200), len(subset))}",
            "  - must_not_claim uses the same substring check as pr08_judge.must_not_claim_hits.",
            "  - must_mention is a case-insensitive substring check of the reply. Paraphrases "
            "that a judge might accept are counted as missing. Empty must_mention lists pass.",
            "  - This is not a substitute for a PR-08 judge run.",
        ]
        # 200-set current-process FCR from history, if present
        hist = _history(raw_tickets)
        sub_h = [t for t in raw_tickets
                 if isinstance(t, dict) and t.get("ticket_id") in truth
                 and isinstance(t.get("history"), dict)]
        if sub_h:
            k = sum(bool((t.get("history") or {}).get("first_contact_resolution")) for t in sub_h)
            lines.append(f"  - Current-process FCR on those same tickets (history.first_contact_resolution): {_pct1(k, len(sub_h))}")
    else:
        lines.append("- Answer-key (200-ticket) mention/claim check: skipped "
                     f"(no ground-truth file{'' if not truth_path else ' at ' + str(truth_path)}).")

    # ---- Volume already in standard report; repeat tiers clearly ----
    auto = sum(r.get("route") == "auto_respond" for r in results)
    esc = sum(r.get("route") == "escalate" for r in results)
    t1 = sum(r.get("tier") == 1 for r in results)
    t2 = sum(r.get("tier") == 2 for r in results)
    lines += ["", "## Auto-answers and escalations (merged file)", "",
              f"- Auto-answered: {_pct(auto, n)}",
              f"- Escalated: {_pct(esc, n)}  (tier 1: {t1}; tier 2: {t2})"]
    reasons = Counter((r.get("reason") or "").split(":")[0] for r in results
                      if r.get("route") == "escalate")
    for reason, c in reasons.most_common():
        lines.append(f"  - {c}  {reason}")

    # ---- Baselines ----
    lines += ["", "## Comparison with the current process (from the ticket history, not invented)", ""]
    if not baselines:
        lines.append("- No history block was found on the tickets file, so current-process "
                     "FCR / escalation / handling time could not be recomputed here. "
                     "The PRD / discovery figures already recorded from this same file are "
                     "FCR 43.8% on all 500 and enterprise FCR 37.3%; use those only if you "
                     "confirm they still match data/development_tickets.json.")
    else:
        f, fn, _ = baselines["fcr"]
        e, en, _ = baselines["escalated"]
        lines.append(f"- Current-process FCR (history.first_contact_resolution): {_pct1(f, fn)}")
        lines.append(f"- Current-process escalation rate (history.escalated): {_pct1(e, en)}")
        if baselines.get("mean_resolution_min") is not None:
            lines.append(f"- Current-process mean resolution time "
                         f"(history.resolution_time_minutes): {baselines['mean_resolution_min']:.1f} min")
        if baselines.get("repeat_contact"):
            rk, rn, _ = baselines["repeat_contact"]
            lines.append(f"- Current-process repeat contact (history.repeat_contact): {_pct1(rk, rn)}")
        lines.append("- By customer tier (same history fields):")
        for name, row in baselines["by_tier"].items():
            fk, fn_, _ = row["fcr"]
            ek, en_, _ = row["escalated"]
            mean = row["mean_resolution_min"]
            mean_s = f"; mean resolution {mean:.1f} min" if mean is not None else ""
            lines.append(f"  - {name}: FCR {_pct1(fk, fn_)}; escalated {_pct1(ek, en_)}{mean_s}")
        # System vs current FCR (PRD rule and auto rate)
        lines += [
            f"- This run, auto-answered / processed (brief's simpler FCR): {_pct(auto, n)}",
            f"- This run, PRD FCR (stricter, labelled): {_pct(len(prd_ok), len(labels) or n)}",
        ]
        # enterprise PRD / auto
        ent_raw = [t for t in raw_tickets if isinstance(t, dict) and t.get("customer_tier") == "enterprise"]
        ent_ids = {t["ticket_id"] for t in ent_raw if t.get("ticket_id")}
        ent_res = [r for r in results if r.get("ticket_id") in ent_ids]
        ent_auto = sum(r.get("route") == "auto_respond" for r in ent_res)
        ent_prd = sum(1 for r in ent_res if prd_fcr_ok(r, labels.get(r.get("ticket_id")) or {})[0])
        if ent_res:
            lines.append(f"- Enterprise this run: auto-answered {_pct(ent_auto, len(ent_res))}; "
                         f"PRD FCR {_pct(ent_prd, len(ent_res))} "
                         "(current-process enterprise FCR is in the tier list above; PRD NFR-06: "
                         "do not go below that figure).")
        lines.append("- Time-to-first-reply (8–12 hours in the PRD / interviews) is not a field "
                     "on the tickets; it is not recomputed here. The history field is "
                     "resolution_time_minutes (end-to-end handling time), shown above.")
        lines.append(f"- Tickets labelled not answerable from docs: {baselines['not_coverable']} "
                     "(the known 143 on the 500-ticket file, if this is that file).")

    # ---- Miss lists ----
    lines += ["", "## Miss lists (ticket IDs; labels used only here)", "",
              f"- Should have been auto-answered, but were escalated: "
              f"{len(misses['should_auto_escalated'])}",
              f"  - {_ids(misses['should_auto_escalated'])}",
              f"- Should have been escalated, but were auto-answered: "
              f"{len(misses['should_escalate_auto_answered'])}",
              f"  - {_ids(misses['should_escalate_auto_answered'])}",
              f"- Auto-answers that did not cite an expected article: "
              f"{len(misses['wrong_citations'])}",
              f"  - {_ids(misses['wrong_citations'])}",
              f"- Must-not tickets auto-answered (must be 0): "
              f"{len(misses['must_not_auto_answered'])}",
              f"  - {_ids(misses['must_not_auto_answered'])}"]

    # ---- Recurring issues ----
    lines += ["", "## Recurring issues (checked against what we already know)", ""]
    no_article = [r for r in results
                  if r.get("route") == "escalate"
                  and "no reviewed article covers" in (r.get("reason") or "")]
    residency_no_article = []
    for r in no_article:
        retrieved = r.get("retrieved_docs") or []
        if r.get("intent") == "data_residency" or "DOC-DATA-003" in retrieved:
            residency_no_article.append(r["ticket_id"])
    lines.append(f"- 'No article covers' escalations: {len(no_article)}; "
                 f"of those with predicted intent data_residency or DOC-DATA-003 retrieved: "
                 f"{len(residency_no_article)} ({_ids(residency_no_article)}).")
    # urgency
    scored_u = [r for r in results if (labels.get(r.get("ticket_id")) or {}).get("urgency")]
    urg_right = sum(r.get("urgency") == (labels.get(r.get("ticket_id")) or {}).get("urgency")
                    for r in scored_u)
    lines.append(f"- Urgency right: {_pct(urg_right, len(scored_u))} "
                 "(known gap; priority.py is still not called by the runner).")
    sent = [r for r in results if r.get("route") == "auto_respond"]
    extra = sum(max(len(r.get("citations") or []) - 1, 0) for r in sent)
    want_two = [r for r in sent
                if len((labels.get(r.get("ticket_id")) or {}).get("expected_doc_ids") or []) > 1]
    two_full = sum(set((labels.get(r.get("ticket_id")) or {}).get("expected_doc_ids") or [])
                   <= set(cited_ids(r)) for r in want_two)
    lines.append(f"- Second-article citing: extra (related) sources kept {extra}; "
                 f"auto-answers that cited all expected articles among those expecting 2+: "
                 f"{_pct(two_full, len(want_two))} (known unused related-source gap).")
    # 143 not-coverable behaviour
    not_cov_ids = [t.get("ticket_id") for t in raw_tickets
                   if isinstance(t, dict)
                   and (t.get("labels") or {}).get("answerable_from_docs") is False
                   and t.get("ticket_id")]
    not_cov_res = [r for r in results if r.get("ticket_id") in set(not_cov_ids)]
    not_cov_auto = [r["ticket_id"] for r in not_cov_res if r.get("route") == "auto_respond"]
    lines.append(f"- Tickets labelled not answerable from docs: {len(not_cov_ids)}; "
                 f"in this run auto-answered {len(not_cov_auto)}, "
                 f"escalated {len(not_cov_res) - len(not_cov_auto)}. "
                 "Auto-answering these is usually a miss; IDs: "
                 f"{_ids(not_cov_auto)}.")
    twins = identical_body_twins(raw_tickets, labels)
    lines.append(f"- Identical-body groups whose labels disagree (route, expected articles, "
                 f"or must-not): {len(twins)} groups. "
                 "These are a known label conflict (including residency twins); "
                 "do not retune the system to chase them.")
    for g in twins:
        lines.append(f"  - {', '.join(g)}")
    lines.append("- Generic reference replies (79 of 200 answer-key replies share the same "
                 "placeholder text, recorded earlier) are a limit of the ground truth, not "
                 "something this run measures. They are mentioned here only as context "
                 "when reading answer-key scores.")

    # ---- Calls, latency, cost ----
    call_rows = [c for r in results for c in (r.get("model_calls") or [])]
    times = timed(results)
    lines += ["", "## Calls, latency, and cost estimate", ""]
    if call_rows:
        ok = sum(1 for c in call_rows if c.get("ok"))
        mean_c = sum((c.get("latency_ms") or 0) for c in call_rows) / len(call_rows)
        by = Counter((c.get("model") or "unknown") for c in call_rows)
        lines.append(f"- AI calls: {len(call_rows)} ({ok} ok); mean {mean_c/1000:.2f} s per call")
        for m, c in by.most_common():
            lines.append(f"  - {c}  {m}")
    else:
        lines.append("- AI calls: not recorded on these results (no model_calls fields).")
    if times:
        lines.append(f"- Ticket latency: mean {sum(times)/len(times)/1000:.1f} s; "
                     f"median {percentile(times, 50)/1000:.1f} s; "
                     f"p95 {percentile(times, 95)/1000:.1f} s "
                     f"({len(times)} of {n} tickets timed)")
    cost = estimate_cost(n, len(call_rows))
    if cost:
        lines += [
            f"- Cost estimate (ESTIMATE ONLY, not a bill; the results file has no token usage): "
            f"about ${cost['low']:.2f} to ${cost['high']:.2f}.",
            f"  - Scaled from the official 80-ticket holdout estimate band of "
            f"${HOLDOUT_COST_LOW:.2f}–${HOLDOUT_COST_HIGH:.2f} "
            f"({HOLDOUT_CALLS} calls) in docs/HOLDOUT_RESULT.md, using the larger of "
            f"ticket scale ×{cost['scale_tickets']:.2f} and call scale ×{cost['scale_calls']:.2f}.",
            "  - List prices used there: Haiku 5.5 $0.10/MTok input and $0.50/MTok output "
            "(prompts up to 100k, 20 Nov). Thinking tokens are billed as output and are "
            "the main uncertainty, even at effort low. This is not a receipt.",
        ]
    return lines


def write_merged(part_paths, raw_tickets, out_path, truth_path=None):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results, duplicates, empty = merge_results(part_paths)
    out_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    labels = _labels(raw_tickets)
    raw_ids = [t.get("ticket_id") for t in raw_tickets if isinstance(t, dict) and t.get("ticket_id")]
    got = {r.get("ticket_id") for r in results}
    missing_ids = [tid for tid in raw_ids if tid not in got]

    # write_report's "logged this run / reconciles" line is about a live log session.
    # Pass 0 and explain in the extra section so we do not pretend the log was merged.
    started = finished = datetime.now()
    report = write_report(results, raw_tickets, out_path, started, finished, logged=0)

    truth = load_ground_truth(truth_path)
    misses = miss_lists(results, labels)
    baselines = current_process_baselines(raw_tickets)
    extra = extra_lines(
        results, raw_tickets, labels, misses, baselines, truth,
        duplicates, empty, missing_ids, part_paths, truth_path,
    )
    existing = Path(report).read_text(encoding="utf-8")
    header = (
        "# Metrics report (merged dev-set check)\n\n"
        "This file starts with the standard run.py report, then adds merge notes, "
        "PRD FCR, current-process baselines, miss lists, and a cost estimate. "
        "Labels are used only for scoring. This is not an official result.\n"
    )
    # The standard report already starts with "# Metrics report"; keep it and prefix a note.
    Path(report).write_text(header + existing + "\n".join(extra) + "\n", encoding="utf-8")
    return {
        "out_path": out_path,
        "report": Path(report),
        "results": results,
        "duplicates": duplicates,
        "missing_ids": missing_ids,
        "misses": misses,
    }


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Merge part result JSON files and write the metrics report."
    )
    p.add_argument("parts", nargs="+", help="part result JSON files (outputs/dev500_part1.json …)")
    p.add_argument("--tickets", required=True,
                   help="the ticket file used for the run (with labels), e.g. data/development_tickets.json")
    p.add_argument("--output", required=True, help="merged results JSON, e.g. outputs/dev500_claude.json")
    p.add_argument("--ground-truth", default="data/ground_truth_responses.json",
                   help="200-ticket answer key (optional; skipped if the file is missing)")
    args = p.parse_args(argv)
    raw = load_tickets(args.tickets)
    info = write_merged(args.parts, raw, args.output, truth_path=args.ground_truth)
    print(f"Merged {len(info['results'])} tickets -> {info['out_path']}")
    if info["duplicates"]:
        print(f"Warning: {len(info['duplicates'])} duplicate ticket_ids (kept the first).")
    if info["missing_ids"]:
        print(f"Warning: {len(info['missing_ids'])} tickets from the input file have no result.")
    print(f"Metrics report: {info['report']}")


if __name__ == "__main__":
    main()
