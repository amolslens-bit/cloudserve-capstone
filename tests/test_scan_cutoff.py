"""Tests for the pure parts of src/scan_cutoff.py. No Chroma, no AI.
scan_cutoff only imports retrieve inside main(), so conftest's fake retrieve is never touched."""
import scan_cutoff as sc


def row(best, best_exp, answerable):
    return {"best_score": best, "best_expected_score": best_exp, "answerable": answerable}


ROWS = [
    row(0.50, 0.50, True),    # answerable, expected article is the top hit
    row(0.70, 0.90, True),    # answerable, expected article second
    row(1.00, None, True),    # answerable, expected article not retrieved
    row(0.80, None, False),   # not answerable, close-looking hit
    row(1.20, None, False),   # not answerable, weak hit
    row(None, None, False),   # not answerable, nothing found at all
]


def by_cut(table):
    return {t["cutoff"]: t for t in table}


def test_candidate_cutoffs_include_current_and_range():
    c = sc.candidate_cutoffs(1.5)
    assert c[0] == 0.6 and c[-1] == 1.6 and len(c) == 21
    assert sc.candidate_cutoffs(1.234).count(1.234) == 1
    assert sc.candidate_cutoffs(1.5).count(1.5) == 1


def test_threshold_table_counts():
    t = by_cut(sc.threshold_table(ROWS, [0.6, 0.85, 1.5]))
    assert t[0.6]["answerable_kept"] == 1
    assert t[0.6]["answerable_with_expected_kept"] == 1
    assert t[0.6]["unanswerable_kept"] == 0 and t[0.6]["unanswerable_blocked"] == 3
    assert t[0.85]["answerable_kept"] == 2
    assert t[0.85]["answerable_with_expected_kept"] == 1     # second one's expected article is at 0.90
    assert t[0.85]["unanswerable_kept"] == 1
    assert t[1.5]["answerable_kept"] == 3
    assert t[1.5]["answerable_with_expected"] == 2
    assert t[1.5]["answerable_with_expected_kept"] == 2
    assert t[1.5]["unanswerable_kept"] == 2                   # None (no hit) is never kept


def test_boundary_score_equal_to_cutoff_is_kept():
    t = by_cut(sc.threshold_table([row(0.8, 0.8, True), row(0.8, None, False)], [0.8]))
    assert t[0.8]["answerable_kept"] == 1 and t[0.8]["unanswerable_kept"] == 1


def test_rates_and_youden():
    t = by_cut(sc.threshold_table(ROWS, [0.6, 1.5]))
    assert t[0.6]["recall_expected"] == 0.5 and t[0.6]["false_keep_rate"] == 0.0
    assert abs(t[1.5]["youden"] - (1.0 - 2 / 3)) < 1e-9


def test_best_youden_picks_balance():
    table = sc.threshold_table(ROWS, [0.6, 0.95, 1.5])
    # 0.6: 0.5-0 = 0.5 ; 0.95: 1.0-1/3 = 0.67 ; 1.5: 1.0-2/3 = 0.33
    assert sc.best_youden(table)["cutoff"] == 0.95


def test_best_at_recall_is_strictest_that_reaches_target():
    table = sc.threshold_table(ROWS, [0.6, 0.95, 1.0, 1.5])
    best = sc.best_at_recall(table, target=0.95)
    assert best["cutoff"] == 0.95 and best["unanswerable_blocked"] == 2


def test_best_at_recall_none_when_unreachable():
    table = sc.threshold_table(ROWS, [0.6])
    assert sc.best_at_recall(table, target=0.95) is None
    assert sc.best_youden([]) is None


def test_summarize():
    s = sc.summarize([0.4, None, 1.0, 0.6, 0.8, 0.2, 0.5, 0.7, 0.9, 0.3, 0.1])
    assert s["n"] == 10 and s["min"] == 0.1 and s["max"] == 1.0
    assert abs(s["median"] - 0.55) < 1e-9 and s["p90"] == 0.9
    assert sc.summarize([None])["median"] is None


def test_scan_row_distinct_docs_and_expected():
    ticket = {"ticket_id": "DEV-X", "labels": {"expected_doc_ids": ["DOC-B"],
              "answerable_from_docs": True, "expected_route": "auto_respond"}}
    hits = [("DOC-A", 0.5), ("DOC-A", 0.55), ("DOC-B", 0.9), ("DOC-C", 1.1)]
    r = sc.scan_row(ticket, hits, k=2, intent_used="webhook_issue", intent_source="label")
    assert r["best_score"] == 0.5 and r["second_score"] == 0.9
    assert r["top_doc_id"] == "DOC-A" and r["second_doc_id"] == "DOC-B"
    assert r["top_in_expected"] is False and r["best_expected_score"] == 0.9
    r1 = sc.scan_row(ticket, hits, k=1, intent_used=None, intent_source="label")
    assert r1["best_expected_score"] is None              # expected doc only 2nd, k=1 never takes it
    empty = sc.scan_row(ticket, [], k=2, intent_used=None, intent_source="label")
    assert empty["best_score"] is None and empty["top_doc_id"] == ""


def test_report_lines_mark_current():
    text = "\n".join(sc.report_lines(ROWS, [0.6, 1.5], 1.5, 2, "label"))
    assert "1.50 (current)" in text and "Best balance" in text


def test_report_lines_no_recommendation_without_both_groups():
    only_answerable = [r for r in ROWS if r["answerable"]]
    text = "\n".join(sc.report_lines(only_answerable, [0.6, 1.5], 1.5, 2, "label"))
    assert "No recommendation" in text and "Best balance" not in text
