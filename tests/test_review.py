"""PR-04 reply review: anything other than a clean pass counts as block."""
from review import review


def test_pass(ai):
    ai.replies = ['{"verdict": "pass", "problems": []}']
    assert review("reply", "article")["verdict"] == "pass"


def test_block(ai):
    ai.replies = ['{"verdict": "block", "problems": ["promises a refund"]}']
    assert review("reply", "article") == {"verdict": "block", "problems": ["promises a refund"]}


def test_garbage_is_block(ai):
    ai.replies = ["looks fine to me"]
    assert review("reply", "article")["verdict"] == "block"


def test_error_is_block(ai):
    ai.replies = [TimeoutError("provider timed out")]
    assert review("reply", "article")["verdict"] == "block"
