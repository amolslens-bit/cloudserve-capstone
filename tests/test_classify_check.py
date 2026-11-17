"""Code checks on PR-01's answer: anything broken is made safe."""
from classify import check, classify


def test_good_answer_kept():
    out = check('{"intent": "billing_query", "urgency": "low", "billing_dispute": false,'
                ' "data_commitment_request": false, "confidence": 0.8}')
    assert out["intent"] == "billing_query" and out["confidence"] == 0.8
    assert out["billing_dispute"] is False


def test_garbage_becomes_unclear():
    out = check("sorry, I can't help with that")
    assert out["intent"] == "unclear_request" and out["confidence"] == 0.0


def test_unknown_intent_becomes_unclear():
    out = check('{"intent": "pizza_order", "urgency": "low", "confidence": 0.99}')
    assert out["intent"] == "unclear_request" and out["confidence"] == 0.0


def test_bad_urgency_becomes_high():
    assert check('{"intent": "billing_query", "urgency": "urgent!!"}')["urgency"] == "high"


def test_missing_flags_count_as_true():
    out = check('{"intent": "billing_query", "urgency": "low", "confidence": 0.9}')
    assert out["billing_dispute"] is True and out["data_commitment_request"] is True


def test_bad_confidence_becomes_zero():
    assert check('{"intent": "billing_query", "confidence": "very sure"}')["confidence"] == 0.0


def test_classify_records_model(ai):
    ai.replies = ['{"intent": "onboarding", "urgency": "low", "billing_dispute": false,'
                  ' "data_commitment_request": false, "confidence": 0.9}']
    out = classify({"subject": "Hi", "body": "How do I start?", "customer_tier": "free"})
    assert out["intent"] == "onboarding" and out["model_used"] == "fake-model"
    assert "How do I start?" in ai.prompts[0]
