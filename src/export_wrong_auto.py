"""List every ticket the system AUTO-ANSWERED that the labels say was wrong,
side by side with the original ticket and the answer-key reply, so a person can
cross-check them. Read-only: makes no AI calls and changes nothing.

Run (from C:\\capstone):
  python src\\export_wrong_auto.py
Output: outputs\\wrong_auto_review.csv (opens in Excel) and a short summary.
"""
import argparse, csv, json
from pathlib import Path


def load_list(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("tickets") or data.get("results") or list(data.values())
    return data if isinstance(data, list) else []


def why_wrong(r, lab):
    """Reasons an auto-answer disagrees with the labels (empty list = looks right)."""
    out = []
    if lab.get("must_not_auto_respond"):
        out.append("must-not ticket auto-answered")
    if lab.get("answerable_from_docs") is False:
        out.append("docs cannot answer it")
    if lab.get("expected_route") == "escalate":
        out.append("label says escalate")
    exp = set(lab.get("expected_doc_ids") or [])
    if exp and r.get("cited") not in exp:
        out.append("cited a different article than expected")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results", default="outputs/dev500_claude.json")
    p.add_argument("--tickets", default="data/development_tickets.json")
    p.add_argument("--ground-truth", default="data/ground_truth_responses.json")
    p.add_argument("--out", default="outputs/wrong_auto_review.csv")
    a = p.parse_args()

    tickets = {t["ticket_id"]: t for t in load_list(a.tickets) if isinstance(t, dict)}
    results = [r for r in load_list(a.results) if isinstance(r, dict)]
    truth = {}
    if Path(a.ground_truth).exists():
        truth = {g["ticket_id"]: g for g in load_list(a.ground_truth)
                 if isinstance(g, dict) and g.get("ticket_id")}
    # every text field in the answer key except the id and the phrase lists
    gt_fields = sorted({k for g in truth.values() for k, v in g.items()
                        if isinstance(v, str) and k != "ticket_id"})

    auto = [r for r in results if r.get("route") == "auto_respond"]
    rows, counts = [], {}
    for r in auto:
        t = tickets.get(r.get("ticket_id"), {})
        lab = t.get("labels", {})
        reasons = why_wrong(r, lab)
        if not reasons:
            continue
        for x in reasons:
            counts[x] = counts.get(x, 0) + 1
        hist = t.get("history", {})
        g = truth.get(r["ticket_id"], {})
        row = {
            "ticket_id": r["ticket_id"],
            "why_flagged": "; ".join(reasons),
            "subject": t.get("subject", ""),
            "ticket_body": t.get("body", ""),
            "tier": t.get("customer_tier", ""),
            "label_intent": lab.get("intent", ""),
            "our_intent": r.get("intent", ""),
            "label_route": lab.get("expected_route", ""),
            "answerable_from_docs": lab.get("answerable_from_docs", ""),
            "expected_docs": ", ".join(lab.get("expected_doc_ids") or []),
            "our_cited": r.get("cited", ""),
            "our_answer_confidence": r.get("answer_confidence", ""),
            "our_reply": r.get("draft", ""),
            "in_answer_key": "yes" if g else "no",
        }
        for k in gt_fields:
            row["key_" + k] = g.get(k, "")
        row["key_must_mention"] = "; ".join(g.get("must_mention") or []) if g else ""
        row["history_escalated"] = hist.get("escalated", "")
        row["history_csat"] = hist.get("csat_rating", "")
        row["your_check"] = ""
        row["your_notes"] = ""
        rows.append(row)

    rows.sort(key=lambda x: x["ticket_id"])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys()) if rows else ["ticket_id"]
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    print(f"Results file: {a.results}")
    print(f"Tickets in results: {len(results)}")
    print(f"Auto-answered: {len(auto)}")
    print(f"Auto-answered but flagged by the labels: {len(rows)}")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {v:4d}  {k}")
    print("(one ticket can have more than one reason)")
    print(f"Answer key file: {a.ground_truth if truth else 'not found, key_ columns left out'}")
    print(f"Wrote {a.out}")


if __name__ == "__main__":
    main()
