"""A10 metrics report: every figure the Build Specification asks for, worked out by code.
Uses made-up result records only: no AI calls, no keys, no cost."""
import json
from datetime import datetime

import run

BASE = {"ticket_id": "T-1", "customer_tier": "pro", "intent": "billing_query", "urgency": "low",
        "confidence": 0.9, "billing_dispute": False, "data_commitment_request": False,
        "retrieved_docs": ["DOC-1"], "route": "auto_respond", "tier": None,
        "reason": "all checks passed", "checks": ["missing_fields", "reply_review"],
        "draft": "Go to Settings.", "cited": "DOC-1", "answer_confidence": 0.9,
        "review": {"verdict": "pass", "problems": []}, "package": None, "model_used": "fake",
        "steps": ["prepare", "classify", "retrieve", "draft", "review"], "latency_ms": 1000}


def rec(tid, **changes):
    return dict(BASE, ticket_id=tid, **changes)


# 4 tickets: 1 auto-answer, 1 blocked by the reply review, 1 stopped early by warning words,
# 1 searched but no article found
RESULTS = [
    rec("A", latency_ms=1000),
    rec("B", route="escalate", tier=1, reason="reply review failed or did not run",
        checks=["missing_fields", "citation", "banned_claims", "reply_review"],
        review={"verdict": "block", "problems": ["unsupported claim"]}, latency_ms=2000),
    rec("C", route="escalate", tier=2, reason="warning words: hacked", intent="security_incident",
        checks=["missing_fields", "instruction_check", "must_not", "warning_words"],
        retrieved_docs=[], draft="", review=None, steps=["prepare", "classify"], latency_ms=3000),
    rec("D", route="escalate", tier=1, reason="no reviewed article covers the question",
        checks=["missing_fields", "coverage_and_answer_cutoff"], retrieved_docs=[], draft="",
        review=None, steps=["prepare", "classify", "retrieve", "draft"], latency_ms=4000),
]


def report_text(tmp_path, results, raw, logged=None):
    out = tmp_path / "results.json"
    now = datetime(2026, 11, 18, 10, 0)
    path = run.write_report(results, raw, out, now, now, len(results) if logged is None else logged)
    return path.read_text(encoding="utf-8")


def test_percentile_p50_p95():
    v = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert run.percentile(v, 50) == 5.5
    assert abs(run.percentile(v, 95) - 9.55) < 1e-9
    assert run.percentile([7], 95) == 7
    assert run.percentile([], 50) is None


def test_precision_recall_tiny_example():
    # predicted, labelled
    pairs = [("billing", "billing"), ("billing", "auth"), ("auth", "auth"), ("auth", "auth")]
    s = run.intent_scores(pairs)
    assert s["billing"] == (0.5, 1.0, 1)        # 1 of 2 'billing' guesses right; found the 1 real one
    assert s["auth"][0] == 1.0                  # both 'auth' guesses right
    assert abs(s["auth"][1] - 2 / 3) < 1e-9     # found 2 of the 3 real auth tickets


def test_blocked_only_counts_stopped_drafts():
    assert [r["ticket_id"] for r in RESULTS if run.is_blocked(r)] == ["B"]
    # a system error is never counted as a guardrail, whatever checks it carries
    err = rec("E", route="escalate", reason="AI service unavailable, sent to a person")
    assert run.stop_check(err) is None and not run.is_blocked(err)


def test_fallback_records_left_out_of_timing():
    fallback = run.escalation("X", 1, "system error, sent to a person: ValueError")
    assert run.timed(RESULTS + [fallback]) == [1000, 2000, 3000, 4000]


def test_private_data_scan():
    assert run.private_data_in_reply("Go to Settings > API Keys.") == {}
    assert run.private_data_in_reply("Your invoice of 2026-11-18 10:00 is ready.") == {}
    found = run.private_data_in_reply("Mail jo@acme.com or call +91 98765 43210, key sk_live_abcdef123456789")
    assert found == {"email address": 1, "phone number": 1, "API key or secret": 1}


def test_report_with_labels(tmp_path):
    raw = [{"ticket_id": t, "labels": lab} for t, lab in [
        ("A", {"intent": "billing_query", "expected_route": "auto_respond", "expected_doc_ids": ["DOC-1"]}),
        ("B", {"intent": "billing_query", "expected_route": "auto_respond", "expected_doc_ids": ["DOC-9"]}),
        ("C", {"intent": "security_incident", "expected_route": "escalate", "expected_doc_ids": []}),
        ("D", {"intent": "api_key_issue", "expected_route": "auto_respond", "expected_doc_ids": ["DOC-2"]}),
    ]]
    text = report_text(tmp_path, RESULTS, raw)
    # Volume
    assert "- Tickets processed: 4" in text
    assert "- Answered automatically: 1 (25%)" in text
    assert "- Escalated: 3 (75%)" in text
    assert "- Blocked by guardrails: 1 (25%)" in text
    # Business
    assert "- First contact resolution: 1 (25%)" in text
    assert "- First contact resolution, correct answers only: 1/4 = 25%" in text
    assert "- Response time, mean: 2.5 s" in text
    assert "- Response time, median: 2.5 s" in text
    assert "- Escalation rate: 3 (75%)" in text
    # Technical: D was labelled api_key_issue but we said billing_query
    assert "| billing_query | 67% | 100% | 2 |" in text
    assert "| api_key_issue | n/a | 0% | 1 |" in text
    assert "| security_incident | 100% | 100% | 1 |" in text
    assert "- Retrieval hit rate: 2/3 = 67%" in text            # A, B kept an article; D none
    assert "- Retrieval hit rate, right article: 1/3 = 33%" in text  # only A had the expected doc
    assert "- Latency, median (p50): 2.5 s" in text
    assert "- Latency, 95th percentile (p95): 3.9 s" in text
    # Governance
    assert "- Decisions logged: 4 of 4 processed (reconciles)" in text
    assert "activations by type (the check that stopped each escalated ticket): 3" in text
    assert "1  warning words" in text and "1  reply review" in text and "1  no article covers it" in text
    assert "including tickets stopped earlier by another check: 1" in text
    assert "masked in incoming tickets: not recorded" in text
    assert "- Private data found in auto-answered replies: 0 (must be 0)" in text
    # Existing sections are still there
    assert "## What the system did" in text and "## Scores against labels" in text


def test_report_without_labels_still_works(tmp_path):
    raw = [{"ticket_id": t} for t in "ABCD"]
    text = report_text(tmp_path, RESULTS, raw, logged=3)
    assert "- Blocked by guardrails: 1 (25%)" in text
    assert "precision and recall per class: n/a (input file has no labels)" in text
    assert "correct answers only" not in text and "right article" not in text
    assert "- Retrieval hit rate: 2/3 = 67%" in text
    assert "- Decisions logged: 3 of 4 processed (DOES NOT reconcile)" in text
    assert "## Scores against labels" not in text


def test_report_empty_run(tmp_path):
    text = report_text(tmp_path, [], [])
    assert "- Tickets processed: 0" in text and "- Response time, median: n/a" in text
    assert "- Retrieval hit rate: n/a" in text


def test_redaction_counts_used_when_records_carry_them(tmp_path):
    results = [rec("A", redactions={"email": 2, "phone": 1}), rec("B", redactions={"email": 1})]
    text = report_text(tmp_path, results, [])
    assert "masked in incoming tickets: 4 (email 3, phone 1)" in text


def test_leak_in_auto_answer_is_reported(tmp_path):
    text = report_text(tmp_path, [rec("A", draft="Write to jo@acme.com")], [])
    assert "- Private data found in auto-answered replies: 1 (must be 0)" in text
