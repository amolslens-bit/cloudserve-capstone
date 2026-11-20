"""PR-08 judge harness (test harness only). FakeLLM only: no network, no keys."""
import csv
import json
from pathlib import Path

import pr08_judge as j

PASS = '{"covered_points": ["backoff"], "missing_points": [], "unsupported_claims": [], "pass": true}'
FAIL = '{"covered_points": [], "missing_points": ["backoff"], "unsupported_claims": ["refund issued"], "pass": false}'


def row(tid, model="openai/gpt-oss-120b", route="auto_respond", draft="Use backoff.", cited="DOC-API-001"):
    return {"ticket_id": tid, "route": route, "draft": draft, "cited": cited, "model_used": model}


def files(tmp_path, rows):
    res = tmp_path / "run.json"
    res.write_text(json.dumps(rows))
    key = tmp_path / "ground_truth_responses.json"
    key.write_text(json.dumps([{"ticket_id": t, "must_mention": ["backoff"],
                                "must_not_claim": ["a refund has been issued"]}
                               for t in ("DEV-1", "DEV-2", "DEV-3", "DEV-4")]))
    docs = tmp_path / "documentation.json"
    docs.write_text(json.dumps([{"doc_id": "DOC-API-001", "content": "Retry with exponential backoff."}]))
    return [str(res), "--answer-key", str(key), "--docs", str(docs)]


def test_prompt_file_is_the_stage3_text_and_inputs_are_tagged():
    t = j.PROMPT_FILE.read_text(encoding="utf-8")
    assert t.startswith("ROLE: You are a strict grader of CloudServe support answers.")
    p = j.build_prompt(t, "ANS", "ART", ["a", "b"])
    assert "<answer>\nANS\n</answer>" in p and "<article>\nART\n</article>" in p
    assert "<must_mention>\n- a\n- b\n</must_mention>" in p


def test_judge_default_is_not_the_primary_model():
    assert j.JUDGE_MODEL == "qwen/qwen3.8-27b"
    assert j.JUDGE_MODEL != "nvidia/nemotron-3.5-lightning:free"


def test_select_skips_same_model_not_auto_no_key_and_limit():
    key = {"DEV-1": {}, "DEV-2": {}, "DEV-3": {}, "DEV-4": {}}
    rows = [row("DEV-1"), row("DEV-2", model="qwen/qwen3.8-27b"), row("DEV-3", route="escalate"),
            row("DEV-9"), row("DEV-4", draft=""), row("DEV-1")]
    chosen, skipped = j.select(rows, key, "qwen/qwen3.8-27b", limit=1)
    assert [r["ticket_id"] for r in chosen] == ["DEV-1"]
    assert skipped == {"not auto-answered": 1, "no answer-key entry": 1, "same model as judge": 1,
                       "no draft or citation": 1, "over the limit": 1}


def test_must_not_claim_is_checked_by_code():
    assert j.must_not_claim_hits("Good news: A refund has been issued.", ["a refund has been issued"]) \
        == ["a refund has been issued"]
    assert j.must_not_claim_hits("Use backoff.", ["a refund has been issued"]) == []


def test_bad_judge_output_is_recorded_not_crashed(ai):
    ai.replies = ['{"pass": "yes"}', "not json", RuntimeError("429")]
    truth = {"must_mention": ["backoff"], "must_not_claim": []}
    docs = {"DOC-API-001": {"content": "x"}}
    for _ in range(3):
        g = j.grade_one(ai, "T", row("DEV-1"), truth, docs)
        assert g["status"] == "judge_failed"
    g = j.grade_one(ai, "T", row("DEV-1", cited="DOC-NONE"), truth, docs)
    assert g["status"] == "judge_failed" and "not found" in g["error"]


def test_full_run_writes_report_json_and_handcheck(ai, tmp_path):
    ai.replies = [PASS, FAIL]
    args = files(tmp_path, [row("DEV-1"), row("DEV-2", draft="A refund has been issued."),
                            row("DEV-3", model="qwen/qwen3.8-27b"), row("DEV-4", route="escalate")])
    graded, skipped = j.main(args, judge=ai, pause=0)
    assert [g["pass"] for g in graded] == [True, False]
    assert len(ai.prompts) == 2                       # one call per graded answer
    assert skipped["same model as judge"] == 1 and skipped["not auto-answered"] == 1
    md = (tmp_path / "run_pr08.md").read_text()
    assert "Judge pass (all must_mention points covered, no unsupported claims): 1/2 = 50%" in md
    assert "must_not_claim phrases found by code: 1 answers (must be 0) ['DEV-2']" in md
    assert "Judge model: qwen/qwen3.8-27b" in md
    saved = json.loads((tmp_path / "run_pr08.json").read_text())
    assert saved[1]["unsupported_claims"] == ["refund issued"]
    with open(tmp_path / "run_pr08_handcheck.csv", newline="") as f:
        assert [r["ticket_id"] for r in csv.DictReader(f)] == ["DEV-1", "DEV-2"]


def test_hand_check_agreement_and_no_overwrite(ai, tmp_path):
    args = files(tmp_path, [row("DEV-1"), row("DEV-2")])
    hand = tmp_path / "run_pr08_handcheck.csv"
    hand.write_text("ticket_id,cited,judge_pass,my_pass,notes\nDEV-1,,,yes,\nDEV-2,,,yes,\n")
    ai.replies = [PASS, FAIL]
    j.main(args + ["--hand", str(hand)], judge=ai, pause=0)
    assert "Judge agrees with Amol on pass or fail: 1/2 = 50%" in (tmp_path / "run_pr08.md").read_text()
    assert "DEV-1,,,yes," in hand.read_text()        # the filled-in hand check is untouched


def test_dry_run_makes_no_ai_calls(ai, tmp_path):
    chosen, _ = j.main(files(tmp_path, [row("DEV-1"), row("DEV-2")]) + ["--dry-run"], judge=ai, pause=0)
    assert len(chosen) == 2 and ai.prompts == []


def test_refuses_a_validation_answer_key(tmp_path):
    import pytest
    with pytest.raises(SystemExit):
        j.main([str(tmp_path / "r.json"), "--answer-key", "data/validation_answers.json"])


def test_live_path_never_imports_the_judge():
    for name in ("pipeline.py", "run.py"):
        assert "pr08" not in (Path("src") / name).read_text(encoding="utf-8")
