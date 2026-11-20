"""PR-01 1.3: narrower data-commitment rule. Fake AI only, no API calls."""
from pathlib import Path

import classify
import run


def test_prompt_file_loads():
    assert classify.PROMPT.strip()
    path = Path("prompts/pr01_classify_v1.3.txt")
    assert path.is_file()
    assert classify.PROMPT == path.read_text(encoding="utf-8")


def test_prompt_has_narrowed_data_commitment_rule():
    text = classify.PROMPT
    assert 'Set "data_commitment_request" to true only if' in text
    assert "sign, guarantee, commit, or confirm in writing" in text
    assert "DPA" in text
    assert "backups are replicated" in text
    assert "existing documentation to share" in text
    assert "If unsure, set it to false" in text
    # billing_dispute and alternatives stay as they were
    assert 'Set "billing_dispute" to true if the customer asks for a refund' in text
    assert '"alternatives"' in text


def test_prompt_no_longer_says_unsure_means_true():
    # The old data-commitment wording must be gone. "If unsure, set it to true"
    # should not appear anywhere in this prompt.
    assert "If unsure, set it to true" not in classify.PROMPT
    assert "promise or confirm where their data is stored" not in classify.PROMPT


def test_version_string_is_13():
    assert "pr01_classify_v1.3.txt" in Path("src/classify.py").read_text(encoding="utf-8")
    assert run.PROMPT_VERSION.startswith("PR-01 1.3,")


def test_classify_still_works_with_fake_llm(ai):
    ai.replies = ['{"intent": "data_residency", "urgency": "low", "billing_dispute": false,'
                  ' "data_commitment_request": false, "confidence": 0.9, "alternatives": []}']
    out = classify.classify({"subject": "Data location",
                             "body": "Could you point me to something I can share?",
                             "customer_tier": "business"})
    assert out["intent"] == "data_residency"
    assert out["data_commitment_request"] is False
    assert out["model_used"] == "fake-model"
    assert "point me to something I can share" in ai.prompts[0]
    assert "If unsure, set it to false" in ai.prompts[0]
