"""merge_runs.py: no AI. Builds tiny fake results and labelled tickets."""
import json

import merge_runs


def _ticket(tid, route="auto_respond", intent="billing_query", docs=None, must_not=False,
            urgency="low", answerable=True, tier="standard", fcr=True, escalated=False,
            resolution=10):
    return {
        "ticket_id": tid,
        "customer_tier": tier,
        "labels": {
            "intent": intent,
            "urgency": urgency,
            "expected_route": route,
            "answerable_from_docs": answerable,
            "expected_doc_ids": docs or (["DOC-A"] if route == "auto_respond" else []),
            "must_not_auto_respond": must_not,
        },
        "history": {
            "first_contact_resolution": fcr,
            "resolution_time_minutes": resolution,
            "csat_rating": 3,
            "escalated": escalated,
            "repeat_contact": False,
        },
        "subject": f"subject {tid}",
        "body": f"body {tid}",
    }


def _result(tid, route="auto_respond", cited="DOC-A", intent="billing_query",
            urgency="low", tier=None, reason="all checks passed", checks=None,
            review=None, draft="Thanks. See the article.", calls=None, latency_ms=1000,
            retrieved=None):
    return {
        "ticket_id": tid,
        "route": route,
        "tier": tier,
        "reason": reason,
        "intent": intent,
        "urgency": urgency,
        "cited": cited,
        "citations": [{"doc_id": cited, "section": "Resolution"}] if cited else [],
        "checks": checks or (["missing_fields"] if route == "auto_respond" else ["coverage_and_answer_cutoff"]),
        "review": review or ({"verdict": "pass"} if route == "auto_respond" else None),
        "draft": draft,
        "customer_reply": draft,
        "retrieved_docs": retrieved or ([] if not cited else [cited]),
        "model_used": "claude-haiku-5-5",
        "model_calls": calls if calls is not None else [
            {"model": "claude-haiku-5-5", "latency_ms": 800, "ok": True}
        ],
        "steps": ["prepare", "classify", "retrieve", "draft", "review"] if route == "auto_respond"
                 else ["prepare", "classify", "retrieve", "draft"],
        "latency_ms": latency_ms,
        "package": None if route == "auto_respond" else {"summary": "handover"},
    }


def test_merge_writes_combined_json_and_standard_report(tmp_path):
    tickets = [_ticket("DEV-0001"), _ticket("DEV-0002", route="escalate", fcr=False, escalated=True)]
    p1 = tmp_path / "part1.json"
    p2 = tmp_path / "part2.json"
    p1.write_text(json.dumps([_result("DEV-0001")]))
    p2.write_text(json.dumps([_result("DEV-0002", route="escalate", cited="",
                                     reason="no reviewed article covers the question",
                                     tier=1, latency_ms=2000)]))
    out = tmp_path / "merged.json"
    info = merge_runs.write_merged([p1, p2], tickets, out, truth_path=tmp_path / "missing_gt.json")
    rows = json.loads(out.read_text())
    assert [r["ticket_id"] for r in rows] == ["DEV-0001", "DEV-0002"]
    text = info["report"].read_text()
    assert "Tickets processed: 2" in text
    assert "to tier 1: 1" in text
    assert "Merged run notes" in text
    assert "PRD first-contact resolution" in text


def test_merge_prd_fcr_and_baselines(tmp_path):
    # 2 tickets, history FCR 1/2 = 50.0%. System auto-answers only the labelled one, with the right article.
    tickets = [
        _ticket("DEV-0001", fcr=True, escalated=False, tier="enterprise", resolution=100),
        _ticket("DEV-0002", route="escalate", fcr=False, escalated=True, tier="enterprise", resolution=200),
    ]
    p1 = tmp_path / "p1.json"
    p1.write_text(json.dumps([
        _result("DEV-0001"),
        _result("DEV-0002", route="escalate", cited="", reason="must-not-auto-respond intent: security_incident", tier=2),
    ]))
    out = tmp_path / "merged.json"
    info = merge_runs.write_merged([p1], tickets, out, truth_path=tmp_path / "nope.json")
    text = info["report"].read_text()
    assert "PRD FCR on labelled tickets: 1/2 = 50%" in text
    assert "Current-process FCR (history.first_contact_resolution): 1/2 = 50.0%" in text
    assert "enterprise: FCR 1/2 = 50.0%" in text
    assert "mean resolution 150.0 min" in text


def test_merge_miss_lists(tmp_path):
    tickets = [
        _ticket("DEV-0001", route="auto_respond"),            # should auto, but we escalate
        _ticket("DEV-0002", route="escalate", docs=[]),       # should escalate, but we auto
        _ticket("DEV-0003", route="auto_respond", docs=["DOC-A"]),  # auto, wrong citation
        _ticket("DEV-0004", route="escalate", must_not=True, docs=[]),  # must-not, we auto
    ]
    rows = [
        _result("DEV-0001", route="escalate", cited="", reason="no reviewed article covers the question", tier=1),
        _result("DEV-0002", route="auto_respond", cited="DOC-A"),
        _result("DEV-0003", route="auto_respond", cited="DOC-WRONG"),
        _result("DEV-0004", route="auto_respond", cited="DOC-A"),
    ]
    part = tmp_path / "p.json"
    part.write_text(json.dumps(rows))
    info = merge_runs.write_merged([part], tickets, tmp_path / "m.json", truth_path=tmp_path / "x.json")
    m = info["misses"]
    assert m["should_auto_escalated"] == ["DEV-0001"]
    assert m["should_escalate_auto_answered"] == ["DEV-0002", "DEV-0004"]
    assert m["wrong_citations"] == ["DEV-0003"]
    assert m["must_not_auto_answered"] == ["DEV-0004"]
    text = info["report"].read_text()
    assert "DEV-0001" in text and "DEV-0004" in text
    assert "Must-not tickets auto-answered (must be 0): 1" in text


def test_merge_lexical_must_mention_and_must_not_claim(tmp_path):
    tickets = [
        _ticket("DEV-0001", docs=["DOC-A"]),
        _ticket("DEV-0002", docs=["DOC-A"]),
    ]
    # One reply covers both mention points and avoids claims; the other misses a mention and leaks a claim.
    rows = [
        _result("DEV-0001", draft="Please send the raw body. The call is idempotent."),
        _result("DEV-0002", draft="A refund has been issued already."),
    ]
    part = tmp_path / "p.json"
    part.write_text(json.dumps(rows))
    gt = tmp_path / "gt.json"
    gt.write_text(json.dumps([
        {"ticket_id": "DEV-0001", "must_mention": ["raw body", "idempotent"],
         "must_not_claim": ["a refund has been issued"]},
        {"ticket_id": "DEV-0002", "must_mention": ["raw body"],
         "must_not_claim": ["a refund has been issued"]},
    ]))
    info = merge_runs.write_merged([part], tickets, tmp_path / "m.json", truth_path=gt)
    text = info["report"].read_text()
    # Only DEV-0001 should count on the 200-set lexical rule
    assert "on the 2 answer-key tickets" in text
    assert "1/2 = 50%" in text
    assert "not the PR-08 judge" in text.lower() or "not the PR-08 judge" in text


def test_merge_keeps_first_duplicate_and_reports_missing(tmp_path):
    tickets = [_ticket("DEV-0001"), _ticket("DEV-0002")]
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps([_result("DEV-0001", draft="first")]))
    b.write_text(json.dumps([_result("DEV-0001", draft="second")]))  # duplicate; DEV-0002 missing
    info = merge_runs.write_merged([a, b], tickets, tmp_path / "m.json", truth_path=tmp_path / "x.json")
    rows = json.loads(info["out_path"].read_text())
    assert len(rows) == 1 and rows[0]["draft"] == "first"
    assert info["duplicates"] and info["duplicates"][0][0] == "DEV-0001"
    assert info["missing_ids"] == ["DEV-0002"]
    text = info["report"].read_text()
    assert "Duplicate ticket_ids" in text and "DEV-0002" in text


def test_merge_uses_no_ai(ai, tmp_path):
    tickets = [_ticket("DEV-0001")]
    part = tmp_path / "p.json"
    part.write_text(json.dumps([_result("DEV-0001")]))
    merge_runs.write_merged([part], tickets, tmp_path / "m.json", truth_path=tmp_path / "x.json")
    assert ai.prompts == []


def test_prd_fcr_ignores_checks_that_ran_and_passed():
    # route.py lists every check that RAN, including "banned_claims", on a passing
    # auto-answer. That must not count as a banned claim (bug found on the 21 Nov merge).
    real_checks = ["missing_fields", "intent", "classify_cutoff", "warning_words",
                   "dispute_commitment_flags", "coverage_and_answer_cutoff",
                   "citation", "banned_claims", "reply_review"]
    r = _result("DEV-0001", checks=real_checks)
    lab = _ticket("DEV-0001")["labels"]
    assert merge_runs.safety_break(r, lab) == []
    assert merge_runs.prd_fcr_ok(r, lab) == (True, "ok")
    blocked = _result("DEV-0002", route="escalate", tier=1, checks=real_checks[:8],
                      reason="draft contains a must-not claim")
    assert merge_runs.prd_fcr_ok(blocked, lab)[0] is False
