"""PR-05 answer drafting (FR-07, FR-08). Code checks the citation; labels only score the test."""
import json
import random
import re
from pathlib import Path

from classify import classify
from llm import llm
from load_data import load
from prepare import prepare
from retrieve import retrieve

DOCS = {d["doc_id"]: d for d in load("documentation.json")}
PROMPT = Path("prompts/pr05_answer_v1.1.txt").read_text(encoding="utf-8")
NOT_COVERED = {"covered": False, "article_id": "", "confidence": 0.0, "answer": ""}


def draft_answer(ticket, intent, articles):
    # give the AI the FULL article, not just the one section search matched
    art_text = "\n\n".join(f"[{a['doc_id']}] {DOCS[a['doc_id']]['title']}:\n{DOCS[a['doc_id']]['content']}"
                           for a in articles)
    prompt = (PROMPT.replace("{subject}", ticket["subject"] or "")
                    .replace("{body}", ticket["body"])
                    .replace("{tier}", ticket["customer_tier"] or "")
                    .replace("{intent}", intent)
                    .replace("{articles}", art_text))
    raw = ""
    try:
        raw = llm.invoke(prompt).content
        out = json.loads(re.search(r"\{.*\}", raw, re.S).group())
    except Exception as e:
        return dict(NOT_COVERED, why=f"error or bad JSON: {str(e)[:80]} | raw: {raw[:120]}")
    # FR-08: the cited article must be one we actually supplied
    if out.get("covered") is not True or out.get("article_id") not in {a["doc_id"] for a in articles}:
        return dict(NOT_COVERED, why=f"model said covered={out.get('covered')}, cited {out.get('article_id')!r}")
    try:
        out["confidence"] = float(out.get("confidence", 0))
    except (TypeError, ValueError):
        out["confidence"] = 0.0
    return out


if __name__ == "__main__":
    raw = load("development_tickets.json")
    # small test: 5 tickets meant to be auto-answered (labels used only to pick and score)
    pool = [t for t in raw if t["labels"]["expected_route"] == "auto_respond"]
    for t in random.Random(7).sample(pool, 5):
        clean = prepare(t)
        c = classify(clean)
        arts = retrieve(clean)
        a = draft_answer(clean, c["intent"], arts)
        ok = a["article_id"] in t["labels"]["expected_doc_ids"]
        print("OK " if ok else "XX ", t["ticket_id"], "| cited", a["article_id"] or "-",
              "| expected", t["labels"]["expected_doc_ids"], "| conf", a["confidence"])
        print("     searched:", [x["doc_id"] for x in arts])
        print("    ", (a["answer"] or "(not covered) " + a.get("why", ""))[:200].replace("\n", " "))
