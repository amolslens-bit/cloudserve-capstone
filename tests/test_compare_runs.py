"""Non-regression comparison for PR-05 1.2. Made-up records only: no AI calls."""
import json

import compare_runs as c

R = {"intent": "api_key_issue", "billing_dispute": False, "data_commitment_request": False,
     "route": "auto_respond", "cited": "DOC-A", "review": {"verdict": "pass"}, "model_used": "m"}
LAB = {"expected_route": "auto_respond", "expected_doc_ids": ["DOC-A"], "must_not_auto_respond": False}


def rec(**k):
    return dict(R, **k)


def test_same_and_better_and_worse_by_label():
    assert c.verdict(rec(), rec(), LAB)[0] == "same"
    assert c.verdict(rec(), rec(route="escalate", review={"verdict": "block"}), LAB)[0] == "WORSE"
    esc = LAB | {"expected_route": "escalate", "expected_doc_ids": []}
    assert c.verdict(rec(), rec(route="escalate", review=None), esc)[0] == "better"
    assert c.verdict(rec(), rec(cited="DOC-B"), LAB) == ("WORSE", "cited DOC-A -> DOC-B")


def test_pr04_and_pr08_drops_are_worse():
    assert c.verdict(rec(), rec(review={"verdict": "block"}, route="auto_respond"), None)[0] == "WORSE"
    assert c.verdict(rec(), rec(), LAB, True, False) == ("WORSE", "PR-08 pass -> fail")
    assert c.verdict(rec(), rec(), LAB, False, True)[0] == "better"


def test_no_labels_means_changed_not_judged():
    assert c.verdict(rec(), rec(cited="DOC-B"), None)[0] == "CHANGED"


def test_upstream_change_is_listed_not_counted_but_unsafe_is_always_worse():
    assert c.verdict(rec(), rec(data_commitment_request=True, route="escalate"), LAB)[0] == "upstream"
    mn = LAB | {"must_not_auto_respond": True}
    assert c.verdict(rec(route="escalate"), rec(intent="other"), mn)[0] == "WORSE"


def test_main_exit_code_and_missing(tmp_path, capsys):
    old = [rec(ticket_id="T1"), rec(ticket_id="T2"), rec(ticket_id="T3")]
    new = [rec(ticket_id="T1"), rec(ticket_id="T2", cited="DOC-B")]
    (tmp_path / "o.json").write_text(json.dumps(old))
    (tmp_path / "n.json").write_text(json.dumps(new))
    labels = [{"ticket_id": t, "labels": LAB} for t in ("T1", "T2", "T3")]
    (tmp_path / "dev.json").write_text(json.dumps(labels))
    code = c.main([str(tmp_path / "o.json"), str(tmp_path / "n.json"), "--labels", str(tmp_path / "dev.json")])
    out = capsys.readouterr().out
    assert code == 1 and "WORSE: ['T2']" in out and "['T3']" in out
    (tmp_path / "n.json").write_text(json.dumps(old))
    assert c.main([str(tmp_path / "o.json"), str(tmp_path / "n.json")]) == 0
