"""PR-08 answer-quality judge (Stage 3 register, version 1.0). Test harness only.

It is never part of the live path: pipeline.py and run.py do not import it.
It reads a results file that run.py already wrote, and for each auto-answer
that has an entry in the answer key (data/ground_truth_responses.json) it asks
one judge model whether the answer covers the must_mention points and makes no
claim its cited article doesn't support. must_not_claim phrases are checked by
code here, not by the prompt.

Same-model check (Stage 3 review N11): the judge is ONE fixed Groq model,
by default qwen/qwen3.8-27b, called directly (not through the answer chain).
Answers whose run record says model_used == the judge model are skipped, so the
judge does not grade its own work. Note: model_used in the results is the model
that answered the classification call; the drafting call is not recorded
separately. When the whole run used a different model (for example the paid
model on the final run), every Groq judge is independent.

Usage (from C:\\capstone, optional and small: one Groq call per graded answer):
  python src/pr08_judge.py outputs/dev200_04.json --dry-run      (no AI calls)
  python src/pr08_judge.py outputs/dev200_04.json --limit 20

Writes <results>_pr08.json, <results>_pr08.md and <results>_pr08_handcheck.csv.
"""
import argparse
import csv
import json
import time
from pathlib import Path

from parse import parse_json

PROMPT_FILE = Path("prompts/pr08_judge_v1.0.txt")
PROMPT_VERSION = "PR-08 1.0"
JUDGE_MODEL = "qwen/qwen3.8-27b"
DEFAULT_LIMIT = 20
DEFAULT_PAUSE = 15          # seconds between judge calls (Groq free: 8K tokens a minute)
KEYS = ("covered_points", "missing_points", "unsupported_claims", "pass")


def make_judge(model):
    """The real judge: one Groq model, temperature 0. Imported here so tests need no keys."""
    import os
    from dotenv import load_dotenv
    from langchain_groq import ChatGroq
    from langchain_core.globals import set_llm_cache
    from langchain_community.cache import SQLiteCache
    load_dotenv()
    Path("storage").mkdir(exist_ok=True)
    set_llm_cache(SQLiteCache(database_path="storage/llm_cache.db"))   # key includes the model name
    extra = {"reasoning_format": "hidden"} if model.startswith("qwen/") else {}
    return ChatGroq(model=model, api_key=os.getenv("GROQ_API_KEY"),
                    temperature=0, timeout=60, max_retries=1, **extra)


def build_prompt(template, answer, article, must_mention):
    points = "\n".join(f"- {p}" for p in must_mention)
    return (f"{template.rstrip()}\n\n<answer>\n{answer}\n</answer>\n"
            f"<article>\n{article}\n</article>\n<must_mention>\n{points}\n</must_mention>")


def must_not_claim_hits(answer, phrases):
    low = (answer or "").lower()
    return [p for p in phrases if p.lower() in low]


def check_output(out):
    """The judge's JSON must have the 4 keys, 3 lists of text and a true/false pass."""
    if not isinstance(out, dict) or any(k not in out for k in KEYS):
        raise ValueError("missing keys")
    if not isinstance(out["pass"], bool):
        raise ValueError("pass is not true/false")
    for k in KEYS[:3]:
        if not isinstance(out[k], list) or not all(isinstance(x, str) for x in out[k]):
            raise ValueError(f"{k} is not a list of text")
    return out


def select(rows, key, judge_model, limit):
    """Pick auto-answers to grade, in file order. Returns (chosen, skipped counts)."""
    chosen, skipped = [], {"not auto-answered": 0, "no answer-key entry": 0,
                           "same model as judge": 0, "no draft or citation": 0,
                           "over the limit": 0}
    for r in rows:
        if r.get("route") != "auto_respond":
            skipped["not auto-answered"] += 1
        elif r.get("ticket_id") not in key:
            skipped["no answer-key entry"] += 1
        elif not r.get("draft") or not r.get("cited"):
            skipped["no draft or citation"] += 1
        elif r.get("model_used") == judge_model:
            skipped["same model as judge"] += 1
        elif len(chosen) >= limit:
            skipped["over the limit"] += 1
        else:
            chosen.append(r)
    return chosen, skipped


def grade_one(judge, template, row, truth, docs):
    article = docs.get(row["cited"], {}).get("content", "")
    out = {"ticket_id": row["ticket_id"], "cited": row["cited"],
           "answer_model": row.get("model_used"),
           "must_mention": truth.get("must_mention", []),
           "must_not_claim_hits": must_not_claim_hits(row["draft"], truth.get("must_not_claim", []))}
    if not article:
        return {**out, "status": "judge_failed", "error": "cited article not found"}
    try:
        reply = judge.invoke(build_prompt(template, row["draft"], article, out["must_mention"]))
        got = check_output(parse_json(reply.content))
    except Exception as e:                       # never stop the harness on one answer
        return {**out, "status": "judge_failed", "error": str(e)[:120]}
    return {**out, "status": "graded", **{k: got[k] for k in KEYS}}


def read_hand(path):
    """Amol's hand check: CSV with ticket_id and my_pass (yes/no). Blank rows are ignored."""
    mine = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            v = (r.get("my_pass") or "").strip().lower()
            if v in ("yes", "y", "true", "pass"):
                mine[r["ticket_id"]] = True
            elif v in ("no", "n", "false", "fail"):
                mine[r["ticket_id"]] = False
    return mine


def agreement(graded, mine):
    both = [g for g in graded if g["status"] == "graded" and g["ticket_id"] in mine]
    same = sum(g["pass"] == mine[g["ticket_id"]] for g in both)
    return same, len(both)


def report(results_path, judge_model, graded, skipped, hand=None):
    ok = [g for g in graded if g["status"] == "graded"]
    passed = sum(g["pass"] for g in ok)
    failed = [g for g in graded if g["status"] == "judge_failed"]
    mnc = [g for g in graded if g["must_not_claim_hits"]]
    pct = lambda a, b: f"{a}/{b} = {a / b:.0%}" if b else "n/a"
    lines = [f"# PR-08 answer-quality check: {Path(results_path).name}", "",
             f"- Prompt: {PROMPT_VERSION} ({PROMPT_FILE.as_posix()})",
             f"- Judge model: {judge_model} (one fixed model, temperature 0; answers whose model_used is the judge model were skipped)",
             "- Evaluation only: answer-key fields (must_mention, must_not_claim) are read here and nowhere in the live path.",
             "", "## Counts", "",
             f"- Answers sent to the judge: {len(graded)}",
             f"- Graded: {len(ok)}; judge failed or unusable: {len(failed)}",
             f"- Judge pass (all must_mention points covered, no unsupported claims): {pct(passed, len(ok))}",
             f"- Answers with a missing must_mention point: {sum(bool(g['missing_points']) for g in ok)}",
             f"- Answers with an unsupported claim: {sum(bool(g['unsupported_claims']) for g in ok)}",
             f"- must_not_claim phrases found by code: {len(mnc)} answers (must be 0)"
             + (f" {[g['ticket_id'] for g in mnc]}" if mnc else ""),
             "", "## Skipped", ""] + [f"- {k}: {v}" for k, v in skipped.items()]
    if hand is not None:
        same, n = hand
        lines += ["", "## Agreement with the hand check (target at least 90%)", "",
                  f"- Judge agrees with Amol on pass or fail: {pct(same, n)}"]
    lines += ["", "## Per answer", "", "| Ticket | Cited | Status | Pass | Missing points | Unsupported claims |",
              "|---|---|---|---|---|---|"]
    for g in graded:
        lines.append(f"| {g['ticket_id']} | {g['cited']} | {g['status']} | {g.get('pass', '')} | "
                     f"{'; '.join(g.get('missing_points', [])) or g.get('error', '')} | "
                     f"{'; '.join(g.get('unsupported_claims', []))} |")
    return "\n".join(lines) + "\n"


def main(argv=None, judge=None, pause=None):
    ap = argparse.ArgumentParser(description="PR-08 answer-quality judge (test harness only)")
    ap.add_argument("results", help="a results JSON written by run.py")
    ap.add_argument("--answer-key", default="data/ground_truth_responses.json")
    ap.add_argument("--docs", default="data/documentation.json")
    ap.add_argument("--judge-model", default=JUDGE_MODEL)
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    ap.add_argument("--pause", type=float, default=DEFAULT_PAUSE)
    ap.add_argument("--hand", help="CSV with ticket_id,my_pass to measure agreement")
    ap.add_argument("--dry-run", action="store_true", help="list what would be graded; no AI calls")
    a = ap.parse_args(argv)
    if any(w in a.answer_key.lower() for w in ("validation", "holdout")):
        raise SystemExit("PR-08 uses the development answer key only.")
    rows = json.loads(Path(a.results).read_text(encoding="utf-8"))
    key = {t["ticket_id"]: t for t in json.loads(Path(a.answer_key).read_text(encoding="utf-8"))}
    docs = {d["doc_id"]: d for d in json.loads(Path(a.docs).read_text(encoding="utf-8"))}
    chosen, skipped = select(rows, key, a.judge_model, a.limit)
    base = Path(a.results).with_suffix("")
    if a.dry_run:
        print(f"Would grade {len(chosen)} answers with {a.judge_model} ({len(chosen)} AI calls). Skipped: {skipped}")
        return chosen, skipped
    template = PROMPT_FILE.read_text(encoding="utf-8")
    judge = judge or make_judge(a.judge_model)
    pause = a.pause if pause is None else pause
    graded = []
    for i, r in enumerate(chosen):
        if i and pause:
            time.sleep(pause)
        graded.append(grade_one(judge, template, r, key[r["ticket_id"]], docs))
        print(f"{i + 1}/{len(chosen)} {r['ticket_id']}: {graded[-1]['status']} {graded[-1].get('pass', '')}")
    hand = agreement(graded, read_hand(a.hand)) if a.hand else None
    Path(f"{base}_pr08.json").write_text(json.dumps(graded, indent=2), encoding="utf-8")
    Path(f"{base}_pr08.md").write_text(report(a.results, a.judge_model, graded, skipped, hand), encoding="utf-8")
    hc = Path(f"{base}_pr08_handcheck.csv")
    if not hc.exists():                          # never overwrite a hand check already filled in
        with open(hc, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ticket_id", "cited", "judge_pass", "my_pass", "notes"])
            for g in graded:
                w.writerow([g["ticket_id"], g["cited"], g.get("pass", g["status"]), "", ""])
    print(f"Wrote {base}_pr08.md")
    return graded, skipped


if __name__ == "__main__":
    main()
