"""PR-05 1.2: optional related source and section citations. FakeLLM only: no network, no keys.
The primary path must behave exactly as in 1.1."""
import json
from datetime import datetime

import answer
import pipeline
import run

T = {"subject": "Key", "body": "How do I rotate my key, and why 429?", "customer_tier": "pro"}
A = {"doc_id": "DOC-A", "title": "API keys", "text": "x", "score": 0.5}
B = {"doc_id": "DOC-B", "title": "Rate limits", "text": "y", "score": 0.8}
DOCS = {
    "DOC-A": {"doc_id": "DOC-A", "title": "API keys", "related_docs": ["DOC-B", "DOC-Z"],
              "content": "# API keys\n\n## Symptoms\n\n- Key fails\n\n## Resolution\n\n1. Create a new key.\n2. Revoke the old one.\n"},
    "DOC-B": {"doc_id": "DOC-B", "title": "Rate limits", "related_docs": ["DOC-A"],
              "content": "# Rate limits\n\n## Common causes\n\n- Too many requests per minute (429)\n\n## Notes\n\nLimits are per organisation.\n"},
    "DOC-C": {"doc_id": "DOC-C", "title": "Billing", "related_docs": [],
              "content": "# Billing\n\n## Resolution\n\nInvoices on the 1st.\n"},
    "DOC-Z": {"doc_id": "DOC-Z", "title": "Webhooks", "related_docs": ["DOC-A"],
              "content": "# Webhooks\n\n## Resolution\n\nRetry.\n"},
}
C = {"doc_id": "DOC-C", "title": "Billing", "text": "z", "score": 0.9}


def setup_module():
    answer.DOCS.update(DOCS)


def reply(also=None, section="Resolution", article="DOC-A", conf=0.9):
    return json.dumps({"covered": True, "article_id": article, "section": section,
                       "also_cited": also or [], "confidence": conf, "answer": "1. Create a new key."})


def test_v11_prompt_file_is_kept_and_v12_is_used():
    assert answer.PROMPT.startswith("ROLE: You write support answers for CloudServe")
    assert '"also_cited"' in answer.PROMPT
    assert open("prompts/pr05_answer_v1.1.txt", encoding="utf-8").read().count("also_cited") == 0


def test_primary_unchanged_when_no_related_docs(ai):
    ai.replies = [reply(article="DOC-C")]
    out = answer.draft_answer(T, "billing_query", [C, A])     # A lists no relation to C, C lists none
    assert out["covered"] is True and out["article_id"] == "DOC-C" and out["confidence"] == 0.9
    assert out["citations"] == [{"doc_id": "DOC-C", "section": "Resolution"}]
    assert "[DOC-C] Billing:\n# Billing" in ai.prompts[0]          # full article, 1.1 header
    assert "[DOC-A] API keys:\n# API keys" in ai.prompts[0]        # no supplied related article: no note


def test_related_header_only_for_supplied_related_articles(ai):
    ai.replies = [reply()]
    answer.draft_answer(T, "api_key_issue", [A, B])
    assert "[DOC-A] API keys (related: DOC-B):" in ai.prompts[0]   # DOC-Z is related but not supplied
    assert "[DOC-B] Rate limits (related: DOC-A):" in ai.prompts[0]


def test_valid_related_source_is_kept(ai):
    ai.replies = [reply([{"doc_id": "DOC-B", "section": "common causes"}])]
    out = answer.draft_answer(T, "api_key_issue", [A, B])
    assert out["citations"] == [{"doc_id": "DOC-A", "section": "Resolution"},
                                {"doc_id": "DOC-B", "section": "Common causes"}]
    assert out["citation_notes"] == []


def test_unrelated_or_unretrieved_doc_is_never_added(ai):
    # DOC-C was supplied but is not in DOC-A's related_docs; DOC-Z is related but was not retrieved
    ai.replies = [reply([{"doc_id": "DOC-C", "section": "Resolution"}]),
                  reply([{"doc_id": "DOC-Z", "section": "Resolution"}])]
    one = answer.draft_answer(T, "api_key_issue", [A, C])
    two = answer.draft_answer(T, "api_key_issue", [A, B])
    for out in (one, two):
        assert [c["doc_id"] for c in out["citations"]] == ["DOC-A"]
        assert out["covered"] is True and out["confidence"] == 0.9
    assert "not in DOC-A's related articles" in one["citation_notes"][0]
    assert "not one of the articles supplied" in two["citation_notes"][0]


def test_invalid_secondary_section_is_dropped_and_only_one_extra(ai):
    ai.replies = [reply([{"doc_id": "DOC-B", "section": "Pricing"}]),
                  reply([{"doc_id": "DOC-B", "section": "Notes"}, {"doc_id": "DOC-B", "section": "Common causes"}]),
                  reply("not a list")]
    bad = answer.draft_answer(T, "api_key_issue", [A, B])
    assert bad["citations"] == [{"doc_id": "DOC-A", "section": "Resolution"}]
    assert "is not one of its headings" in bad["citation_notes"][0]
    many = answer.draft_answer(T, "api_key_issue", [A, B])
    assert len(many["citations"]) == 2 and "only 1 extra" in many["citation_notes"][0]
    odd = answer.draft_answer(T, "api_key_issue", [A, B])
    assert odd["citations"] == [{"doc_id": "DOC-A", "section": "Resolution"}] and odd["covered"] is True


def test_invalid_primary_section_keeps_article_without_section(ai):
    ai.replies = [reply(section="Steps"), reply(section="")]
    for _ in range(2):
        out = answer.draft_answer(T, "api_key_issue", [A, B])
        assert out["covered"] is True and out["article_id"] == "DOC-A"
        assert out["citations"] == [{"doc_id": "DOC-A", "section": None}]


def test_primary_checks_are_the_same_as_v11(ai):
    ai.replies = [json.dumps({"covered": True, "article_id": "DOC-MADE-UP", "section": "Resolution",
                              "also_cited": [{"doc_id": "DOC-B", "section": "Notes"}],
                              "confidence": 0.9, "answer": "x"})]
    out = answer.draft_answer(T, "api_key_issue", [A, B])
    assert out["covered"] is False and out["citations"] == []


def test_review_sees_the_extra_section_and_reply_shows_sources():
    cits = [{"doc_id": "DOC-A", "section": "Resolution"}, {"doc_id": "DOC-B", "section": "Notes"}]
    text = answer.review_text(cits)
    assert text.startswith(DOCS["DOC-A"]["content"])               # full primary, as in 1.1
    assert "[DOC-B] Rate limits, section Notes:\n## Notes\n\nLimits are per organisation." in text
    assert "Common causes" not in text                              # only the cited section
    assert answer.review_text(cits[:1]) == DOCS["DOC-A"]["content"]  # no extra: same as 1.1
    line = answer.sources_line(cits)
    assert line == ("This reply was prepared automatically using our help articles: "
                    "DOC-A API keys (section: Resolution); DOC-B Rate limits (section: Notes).")


# ---- pipeline: a bad secondary never changes the route ----
PREP = {"ticket_id": "T-9", "subject": "Key", "body": "rotate key and 429?", "customer_tier": "pro",
        "missing_fields": []}
CLS = {"intent": "api_key_issue", "urgency": "low", "billing_dispute": False,
       "data_commitment_request": False, "confidence": 0.9, "model_used": "fake"}


def run_pipeline(monkeypatch, ai, model_reply, verdict="pass"):
    seen = []
    monkeypatch.setattr(pipeline, "prepare", lambda r: dict(PREP))
    monkeypatch.setattr(pipeline, "classify", lambda t: dict(CLS))
    monkeypatch.setattr(pipeline, "retrieve", lambda t, k=3, intent=None: [A, B][:k])
    monkeypatch.setattr(pipeline, "review",
                        lambda reply_, art: seen.append(art) or {"verdict": verdict, "problems": []})
    monkeypatch.setattr(pipeline, "summarize",
                        lambda *a, **k: {"summary": "s", "unsure_about": "u", "summary_by": "fake"})
    monkeypatch.setattr(pipeline, "assess",
                        lambda *a, **k: {"impact": "low", "reason": "r", "impact_by": "fake"})
    ai.replies = [model_reply]
    return pipeline.process({"ticket_id": "T-9"}), seen


def test_bad_secondary_never_changes_the_route(monkeypatch, ai):
    clean, _ = run_pipeline(monkeypatch, ai, reply())
    bad, _ = run_pipeline(monkeypatch, ai, reply([{"doc_id": "DOC-NOPE", "section": "x"}], section="Nope"))
    for k in ("route", "tier", "reason", "cited", "answer_confidence", "draft"):
        assert clean[k] == bad[k]
    assert clean["route"] == "auto_respond" and clean["retrieved_docs"] == ["DOC-A", "DOC-B"]
    assert bad["citations"] == [{"doc_id": "DOC-A", "section": None}] and len(bad["citation_notes"]) == 2


def test_pipeline_reply_review_and_package_carry_citations(monkeypatch, ai):
    r, seen = run_pipeline(monkeypatch, ai, reply([{"doc_id": "DOC-B", "section": "Notes"}]))
    assert r["citations"][1] == {"doc_id": "DOC-B", "section": "Notes"}
    assert "section Notes" in seen[0]
    assert r["customer_reply"].endswith("DOC-B Rate limits (section: Notes).")
    e, _ = run_pipeline(monkeypatch, ai, reply([{"doc_id": "DOC-B", "section": "Notes"}]), verdict="block")
    assert e["route"] == "escalate" and e["package"]["citations"] == e["citations"]
    assert e["customer_reply"] == ""


def test_metrics_keep_old_citation_line_and_add_new_ones(tmp_path):
    base = {"customer_tier": "pro", "intent": "api_key_issue", "urgency": "low", "confidence": 0.9,
            "billing_dispute": False, "data_commitment_request": False, "retrieved_docs": ["DOC-A", "DOC-B"],
            "route": "auto_respond", "tier": None, "reason": "all checks passed", "checks": [],
            "draft": "x", "answer_confidence": 0.9, "review": {"verdict": "pass", "problems": []},
            "package": None, "model_used": "fake", "steps": ["prepare", "classify", "retrieve", "draft", "review"],
            "latency_ms": 1000}
    results = [
        dict(base, ticket_id="P", cited="DOC-A", citations=[{"doc_id": "DOC-A", "section": "Resolution"},
                                                            {"doc_id": "DOC-B", "section": "Notes"}]),
        dict(base, ticket_id="Q", cited="DOC-A", citations=[{"doc_id": "DOC-A", "section": None}],
             citation_notes=["dropped 'DOC-C': not in DOC-A's related articles"]),
        dict(base, ticket_id="R", cited="DOC-C"),                     # a 1.1-style record
    ]
    raw = [{"ticket_id": "P", "labels": {"expected_doc_ids": ["DOC-A", "DOC-B"], "expected_route": "auto_respond",
                                         "intent": "api_key_issue", "urgency": "low", "must_not_auto_respond": False}},
           {"ticket_id": "Q", "labels": {"expected_doc_ids": ["DOC-A", "DOC-B"], "expected_route": "auto_respond",
                                         "intent": "api_key_issue", "urgency": "low", "must_not_auto_respond": False}},
           {"ticket_id": "R", "labels": {"expected_doc_ids": ["DOC-C"], "expected_route": "auto_respond",
                                         "intent": "api_key_issue", "urgency": "low", "must_not_auto_respond": False}}]
    now = datetime(2026, 11, 19, 10, 0)
    text = run.write_report(results, raw, tmp_path / "r.json", now, now, 3).read_text(encoding="utf-8")
    assert "- Auto-answers citing an expected article: 3/3 = 100% (target 85%)" in text
    assert "- Auto-answers citing ALL expected articles: 2/3 = 67%" in text
    assert "  - of those expecting 2 or more articles: 1/2 = 50%" in text
    assert "- Citations with a valid section heading: 2/3 = 67%" in text
    assert "- Extra (related) sources kept: 1; dropped by the code check: 1" in text
    assert "PR-05 1.2" in run.PROMPT_VERSION
