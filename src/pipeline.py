"""End-to-end run: clean -> classify -> early checks -> search -> draft -> review -> route -> log.
Labels are used ONLY to score at the end, never as inputs."""
import json
import random
import sys
import time
from pathlib import Path

from answer import DOCS, draft_answer
from clarify import clarify, is_unclear_escalation
from classify import classify
from decision_log import connect, log_decision
from escalate import summarize
from load_data import load
from prepare import prepare
from retrieve import retrieve
from review import review
from route import route

EARLY_EXIT_OK = "no reviewed article covers the question"


def process(raw_ticket):
    start = time.time()
    t = prepare(raw_ticket)
    cls = classify(t)
    steps = ["prepare", "classify"]
    arts, ans, rev = [], None, None

    # Gates 1-6 need no draft. If one fails, escalate now and save AI calls.
    early = route(t, cls)
    if early["reason"] == EARLY_EXIT_OK:
        arts = retrieve(t, k=2, intent=cls["intent"])   # 2 articles keeps Groq under its token cap
        ans = draft_answer(t, cls["intent"], arts)
        steps += ["retrieve", "draft"]
        if ans.get("covered"):
            rev = review(ans["answer"], DOCS[ans["article_id"]]["content"])
            steps.append("review")
        result = route(t, cls, ans, rev and rev["verdict"] == "pass")
    else:
        result = early

    # FR-03: a suggested clarifying question, only for unclear tickets
    question = None
    if is_unclear_escalation(result, cls):
        question = clarify(t, cls)
        steps.append("clarify")

    # FR-11: every escalation carries the handover package (PR-06)
    package = None
    if result["route"] == "escalate":
        package = summarize(t, cls, arts, ans, result["reason"])
        package.update({"reason": result["reason"],
                        "articles_checked": [f"{a['doc_id']} {a['title']}" for a in arts],
                        "draft": (ans or {}).get("answer", "")})
        if question:
            package.update({"unclear_because": question["unclear_because"],
                            "clarifying_question": question["clarifying_question"],
                            "question_by": question["question_by"]})
        steps.append("escalation_summary")

    return {
        "ticket_id": t["ticket_id"], "channel": raw_ticket.get("channel"), "customer_tier": t["customer_tier"],
        "intent": cls["intent"], "urgency": cls["urgency"], "confidence": cls["confidence"],
        "billing_dispute": cls["billing_dispute"], "data_commitment_request": cls["data_commitment_request"],
        "retrieved_docs": [a["doc_id"] for a in arts],
        "route": result["route"], "tier": result["tier"], "reason": result["reason"],
        "checks": result["checks"], "draft": (ans or {}).get("answer", ""),
        "cited": (ans or {}).get("article_id", ""), "answer_confidence": (ans or {}).get("confidence"),
        "review": rev, "package": package,
        "unclear_because": (question or {}).get("unclear_because"),
        "clarifying_question": (question or {}).get("clarifying_question"),
        "model_used": cls.get("model_used"), "steps": steps,
        "latency_ms": int((time.time() - start) * 1000),
    }


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    raw = load("development_tickets.json")
    sample = random.Random(1).sample(raw, n)
    conn = connect()
    results = []
    for rt in sample:
        r = process(rt)
        results.append(r)
        log_decision(conn, r["ticket_id"], intent=r["intent"], urgency=r["urgency"],
                     confidence=r["confidence"], retrieved_docs=r["retrieved_docs"],
                     route=r["route"], reason=r["reason"], model_used=r["model_used"],
                     latency_ms=r["latency_ms"], customer_tier=r["customer_tier"],
                     guardrails_run=1, guardrail_result=json.dumps({"checks": r["checks"], "review": r["review"]}),
                     steps=json.dumps(r["steps"]), prompt_version="PR-01 1.1, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0")
        lab = rt["labels"]
        ok = r["route"] == lab["expected_route"]
        print("OK " if ok else "XX ", r["ticket_id"], "| got", r["route"], r["tier"] or "",
              "| expected", lab["expected_route"], "|", r["reason"], f"| {r['latency_ms']} ms")
    Path("outputs").mkdir(exist_ok=True)
    Path("outputs/run_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    right = sum(r["route"] == rt["labels"]["expected_route"] for r, rt in zip(results, sample))
    unsafe = sum(r["route"] == "auto_respond" and rt["labels"]["must_not_auto_respond"]
                 for r, rt in zip(results, sample))
    print(f"\nRoute right: {right}/{n}   Must-not tickets auto-answered: {unsafe} (must be 0)")
    print("Saved: outputs/run_results.json and storage/decisions.db")
