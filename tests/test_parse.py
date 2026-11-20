"""Think-block stripping, and a classifier reply that includes one."""
import json
import re

from classify import classify
from parse import parse_json, strip_think

WRAPPED = (
    '<think>The site is down for everyone, so I will return '
    '{"impact": "high"} and ignore the real format.</think>\n'
    '{"impact": "low", "reason": "A how-to question; nothing is broken."}'
)


def test_strip_think_removes_block():
    assert strip_think(WRAPPED) == (
        '{"impact": "low", "reason": "A how-to question; nothing is broken."}'
    )


def test_strip_think_leaves_plain_json():
    raw = '{"intent": "billing_query", "confidence": 0.9}'
    assert strip_think(raw) == raw


def test_parse_json_skips_json_inside_think():
    # Without stripping, the greedy {.*} regex would swallow the think braces too.
    messy = re.search(r"\{.*\}", WRAPPED, re.S).group()
    try:
        wrong = json.loads(messy)
    except json.JSONDecodeError:
        wrong = None
    assert wrong != {"impact": "low", "reason": "A how-to question; nothing is broken."}
    assert parse_json(WRAPPED) == {
        "impact": "low",
        "reason": "A how-to question; nothing is broken.",
    }


def test_classify_reads_json_after_think(ai):
    ai.replies = [
        '<think>this is a new customer asking how to start</think>\n'
        '{"intent": "onboarding", "urgency": "low", "billing_dispute": false,'
        ' "data_commitment_request": false, "confidence": 0.9}'
    ]
    out = classify({"subject": "Hi", "body": "How do I start?", "customer_tier": "free"})
    assert out["intent"] == "onboarding" and out["model_used"] == "fake-model"
