"""End-to-end run: clean -> classify -> early checks -> search -> draft -> review -> route -> log.
Labels are used ONLY to score at the end, never as inputs."""
import json
import random
import sys
import time
from pathlib import Path

from answer import DOCS, draft_answer, review_text, sources_line
from clarify import clarify, is_unclear_escalation
from classify import classify
from decision_log import connect, log_decision
from escalate import summarize
from impact import assess
from load_data import load
from prepare import prepare
from retrieve import retrieve
from review import review
from route import route
from llm import reset_call_log, pop_call_log

EARLY_EXIT_OK = "no reviewed article covers the question"


def process(raw_ticket):
    start = time.time()
    reset_call_log()
    # Keep the unmasked ticket for the agent handover only (NFR-04).
    original_ticket = {
        "subject": raw_ticket.get("subject") or "",
        "body": raw_ticket.get("body") or "",
    }
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
            citations = ans.get("citations") or [{"doc_id": ans["article_id"], "section": None}]
            # PR-04 sees the full primary article (as in PR-05 1.1) plus every extra cited section
            try:
                art_for_review = review_text(citations)
            except Exception:
                art_for_review = DOCS[ans["article_id"]]["content"]
            rev = review(ans["answer"], art_for_review)
            steps.append("review")
        result = route(t, cls, ans, rev and rev["verdict"] == "pass")
    else:
        result = early

    # FR-03: a suggested clarifying question, only for unclear tickets
    question = None
    if is_unclear_escalation(result, cls):
        question = clarify(t, cls)
        steps.append("clarify")

    # FR-04: business impact, for every escalation (not auto answers)
    impact = None
    if result["route"] == "escalate":
        impact = assess(t, cls)
        steps.append("impact")

    # FR-11: every escalation carries the handover package (PR-06)
    package = None
    if result["route"] == "escalate":
        # PR-06 still sees only the masked ticket (t).
        package = summarize(t, cls, arts, ans, result["reason"],
                            impact["impact"] if impact else "not assessed")
        package.update({"reason": result["reason"],
                        "alternatives_considered": cls.get("alternatives", []),
                        "articles_checked": [f"{a['doc_id']} {a['title']}" for a in arts],
                        "draft": (ans or {}).get("answer", ""),
                        "citations": (ans or {}).get("citations", [])})
        if impact:
            package.update({"impact": impact["impact"],
                            "impact_reason": impact["reason"],
                            "impact_by": impact["impact_by"]})
        if question:
            package.update({"unclear_because": question["unclear_because"],
                            "clarifying_question": question["clarifying_question"],
                            "question_by": question["question_by"]})
        # NFR-04: agents see the original ticket. Added after the summary call,
        # never passed to any model. The results JSON includes it because the
        # package is the agent-facing handover; the decision log and model cache do not.
        package["original_ticket"] = original_ticket
        steps.append("escalation_summary")

    citations = (ans or {}).get("citations")
    if citations is None:
        citations = [{"doc_id": ans["article_id"], "section": None}] if (ans or {}).get("article_id") else []
    customer_reply = ""
    if result["route"] == "auto_respond":
        try:
            customer_reply = f"{ans['answer']}\n\n{sources_line(citations)}"
        except Exception:
            customer_reply = ans["answer"]

    return {
        "ticket_id": t["ticket_id"], "channel": raw_ticket.get("channel"), "customer_tier": t["customer_tier"],
        "intent": cls["intent"], "urgency": cls["urgency"], "confidence": cls["confidence"],
        "billing_dispute": cls["billing_dispute"], "data_commitment_request": cls["data_commitment_request"],
        "retrieved_docs": [a["doc_id"] for a in arts],
        "route": result["route"], "tier": result["tier"], "reason": result["reason"],
        "checks": result["checks"], "draft": (ans or {}).get("answer", ""),
        "cited": (ans or {}).get("article_id", ""), "answer_confidence": (ans or {}).get("confidence"),
        "citations": citations, "citation_notes": (ans or {}).get("citation_notes", []),
        "customer_reply": customer_reply,
        "review": rev, "package": package,
        "unclear_because": (question or {}).get("unclear_because"),
        "clarifying_question": (question or {}).get("clarifying_question"),
        "impact": (impact or {}).get("impact"),
        "impact_reason": (impact or {}).get("reason"),
        "alternatives": cls.get("alternatives", []),
        "redactions": t.get("redactions", {}),
        "model_used": cls.get("model_used"), "steps": steps,
        "model_calls": pop_call_log(),
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
                     steps=json.dumps(r["steps"]), prompt_version="PR-01 1.3, PR-05 1.2, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1")
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
