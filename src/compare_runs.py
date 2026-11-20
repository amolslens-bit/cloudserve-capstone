"""Non-regression check for a prompt change (PR-05 1.2): old vs new results for the same tickets.

    python src/compare_runs.py OLD.json NEW.json [--labels data/development_tickets.json]
                               [--pr08-old OLD_pr08.json] [--pr08-new NEW_pr08.json]

No AI calls. Labels (if given) are used only to judge better or worse, never as inputs.
For each ticket it prints the route, the primary citation, the PR-04 verdict and (if given)
the PR-08 pass for old -> new, and a verdict:
  same      nothing that matters changed
  better    the change matches the label (or PR-08 fail -> pass)
  CHANGED   something changed and there is no label to judge it; read it by hand
  WORSE     the change goes against the label, or PR-04 / PR-08 went from pass to fail,
            or a must-not ticket was auto-answered
  upstream  the classification (intent or flags) differs, so the change did not start in PR-05;
            listed but not counted, except that an unsafe auto-answer is always WORSE
Exit code 1 if any ticket is WORSE: then 1.2 is fixed or not shipped.
"""
import argparse
import json
from pathlib import Path


def load(path):
    return {r["ticket_id"]: r for r in json.loads(Path(path).read_text(encoding="utf-8"))}


def pr08(path):
    if not path:
        return {}
    return {g["ticket_id"]: g.get("pass") for g in json.loads(Path(path).read_text(encoding="utf-8"))
            if g.get("status") == "graded"}


def verdict(o, n, lab, p_old=None, p_new=None):
    """Return (verdict, why) for one ticket."""
    if lab and lab.get("must_not_auto_respond") and n["route"] == "auto_respond":
        return "WORSE", "must-not ticket auto-answered"
    upstream = any(o.get(k) != n.get(k) for k in ("intent", "billing_dispute", "data_commitment_request"))
    if upstream:
        return "upstream", "classification differs (intent or flags), not caused by PR-05"
    rev = lambda r: (r.get("review") or {}).get("verdict")
    worse, better, changed = [], [], []
    exp_route = (lab or {}).get("expected_route")
    exp_docs = (lab or {}).get("expected_doc_ids") or []
    if o["route"] != n["route"]:
        txt = f"route {o['route']} -> {n['route']}"
        if not lab:
            changed.append(txt)
        elif n["route"] == exp_route:
            better.append(txt)
        else:
            worse.append(txt)
    if o["route"] == n["route"] == "auto_respond" and o.get("cited") != n.get("cited"):
        txt = f"cited {o.get('cited')} -> {n.get('cited')}"
        if not lab:
            changed.append(txt)
        elif o.get("cited") in exp_docs and n.get("cited") not in exp_docs:
            worse.append(txt)
        elif n.get("cited") in exp_docs and o.get("cited") not in exp_docs:
            better.append(txt)
        else:
            changed.append(txt)
    if rev(o) == "pass" and rev(n) not in (None, "pass"):
        worse.append("PR-04 pass -> block")
    if rev(o) == "block" and rev(n) == "pass":
        better.append("PR-04 block -> pass")
    if p_old is True and p_new is False:
        worse.append("PR-08 pass -> fail")
    if p_old is False and p_new is True:
        better.append("PR-08 fail -> pass")
    if worse:
        return "WORSE", "; ".join(worse + better + changed)
    if changed:
        return "CHANGED", "; ".join(changed + better)
    if better:
        return "better", "; ".join(better)
    return "same", ""


def compare(old, new, labels=None, p_old=None, p_new=None):
    labels, p_old, p_new = labels or {}, p_old or {}, p_new or {}
    rows = []
    for tid in [t for t in old if t in new]:
        o, n = old[tid], new[tid]
        v, why = verdict(o, n, labels.get(tid), p_old.get(tid), p_new.get(tid))
        rows.append({"ticket_id": tid, "verdict": v, "why": why,
                     "route": (o["route"], n["route"]), "cited": (o.get("cited"), n.get("cited")),
                     "pr04": ((o.get("review") or {}).get("verdict"), (n.get("review") or {}).get("verdict")),
                     "pr08": (p_old.get(tid), p_new.get(tid)),
                     "model": (o.get("model_used"), n.get("model_used")),
                     "citations_new": n.get("citations")})
    missing = sorted(set(old) ^ set(new))
    return rows, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description="Old vs new results: flag any ticket that got worse")
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--labels", help="development tickets file (labels used only to judge)")
    ap.add_argument("--pr08-old")
    ap.add_argument("--pr08-new")
    a = ap.parse_args(argv)
    labels = None
    if a.labels:
        if any(w in a.labels.lower() for w in ("validation", "holdout")):
            raise SystemExit("Use the development tickets only.")
        labels = {t["ticket_id"]: t.get("labels") for t in json.loads(Path(a.labels).read_text(encoding="utf-8"))}
    rows, missing = compare(load(a.old), load(a.new), labels, pr08(a.pr08_old), pr08(a.pr08_new))
    show = lambda v: "-" if v in (None, "") else str(v)
    arrow = lambda p: f"{show(p[0])} -> {show(p[1])}" if p[0] != p[1] else show(p[0])
    print(f"{'ticket':10} {'verdict':9} {'route':28} {'primary cited':32} {'PR-04':16} {'PR-08':14} why")
    for r in rows:
        print(f"{r['ticket_id']:10} {r['verdict']:9} {arrow(r['route']):28} {arrow(r['cited']):32} "
              f"{arrow(r['pr04']):16} {arrow(r['pr08']):14} {r['why']}"
              + (f" [model {r['model'][0]} -> {r['model'][1]}]" if r['model'][0] != r['model'][1] else ""))
    count = lambda v: sum(r["verdict"] == v for r in rows)
    print(f"\nCompared {len(rows)} tickets: same {count('same')}, better {count('better')}, "
          f"CHANGED {count('CHANGED')}, upstream {count('upstream')}, WORSE {count('WORSE')}")
    if missing:
        print(f"In only one of the two files (not compared): {missing}")
    worse = [r["ticket_id"] for r in rows if r["verdict"] == "WORSE"]
    if worse:
        print(f"WORSE: {worse}. Fix PR-05 1.2 or don't ship it.")
        return 1
    print("No ticket got worse." + (" Read the CHANGED tickets by hand." if count("CHANGED") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
