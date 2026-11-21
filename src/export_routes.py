"""Write a small CSV of how every ticket was routed (no ticket text, no replies).
Read-only, no AI calls. Run from C:\\capstone:
  python src\\export_routes.py
Output: outputs\\routes_slim.csv
"""
import csv, json, sys
from pathlib import Path

src = Path(sys.argv[1] if len(sys.argv) > 1 else "outputs/dev500_claude.json")
out = Path(sys.argv[2] if len(sys.argv) > 2 else "outputs/routes_slim.csv")
data = json.loads(src.read_text(encoding="utf-8"))
if isinstance(data, dict):
    data = data.get("tickets") or data.get("results") or []
cols = ["ticket_id", "route", "tier", "reason", "intent", "urgency", "confidence",
        "cited", "answer_confidence", "review_verdict", "billing_dispute",
        "data_commitment_request", "retrieved_docs"]
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for r in data:
        rv = r.get("review") if isinstance(r.get("review"), dict) else {}
        w.writerow([r.get("ticket_id"), r.get("route"), r.get("tier"), r.get("reason"),
                    r.get("intent"), r.get("urgency"), r.get("confidence"), r.get("cited"),
                    r.get("answer_confidence"), rv.get("verdict"), r.get("billing_dispute"),
                    r.get("data_commitment_request"), ";".join(r.get("retrieved_docs") or [])])
print(f"Wrote {out} with {len(data)} rows")
