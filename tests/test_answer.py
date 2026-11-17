"""PR-05 drafting (FR-07, FR-08): the citation must be an article we supplied."""
import answer

T = {"subject": "Locked", "body": "Account locked", "customer_tier": "pro"}
ARTS = [{"doc_id": "DOC-T-1", "title": "Locked accounts", "text": "part", "score": 0.9}]


def setup_module():
    answer.DOCS["DOC-T-1"] = {"doc_id": "DOC-T-1", "title": "Locked accounts",
                              "content": "FULL ARTICLE: wait 15 minutes, then reset."}


def test_full_article_sent(ai):
    ai.replies = ['{"covered": true, "article_id": "DOC-T-1", "confidence": 0.9, "answer": "Wait 15 min."}']
    out = answer.draft_answer(T, "account_access", ARTS)
    assert out["covered"] is True and out["article_id"] == "DOC-T-1"
    assert "FULL ARTICLE" in ai.prompts[0]


def test_citation_not_supplied_is_not_covered(ai):
    ai.replies = ['{"covered": true, "article_id": "DOC-MADE-UP", "confidence": 0.9, "answer": "x"}']
    assert answer.draft_answer(T, "account_access", ARTS)["covered"] is False


def test_bad_json_is_not_covered(ai):
    ai.replies = ["I think you should reset it"]
    assert answer.draft_answer(T, "account_access", ARTS)["covered"] is False
