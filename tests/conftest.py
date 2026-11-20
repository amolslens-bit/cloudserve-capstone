"""Shared test set-up. Runs BEFORE any of our code is imported.

- Swaps the real AI (llm.py) for a fake one, so tests make no API calls,
  need no keys and cost nothing.
- Swaps the real search (retrieve.py) for a fake one, so tests don't load Chroma.
Run from C:\\capstone with:  pytest
"""
import os
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)                      # so "prompts/..." paths work


class FakeReply:
    def __init__(self, content, model="fake-model"):
        self.content = content
        self.response_metadata = {"model_name": model}


class FakeLLM:
    """Returns the replies a test queues up, in order. An Exception in the queue is raised."""
    def __init__(self):
        self.replies, self.prompts = [], []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        item = self.replies.pop(0) if self.replies else "{}"
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, FakeReply) else FakeReply(item)


fake_llm = FakeLLM()
def reset_call_log():
    """D19: no-op in tests; the real llm.py records model and latency per call."""


def pop_call_log():
    return []


def configure(mode=None):
    return "free"


sys.modules["llm"] = types.SimpleNamespace(
    llm=fake_llm, PRIMARY="fake", BACKUP="fake",
    reset_call_log=reset_call_log, pop_call_log=pop_call_log,
    configure=configure, MODE="free", PAID_SETTINGS={},
)

fake_retrieve = types.ModuleType("retrieve")
fake_retrieve.MAX_SCORE = 1.5
fake_retrieve.retrieve = lambda ticket, k=3, intent=None: []
sys.modules["retrieve"] = fake_retrieve


@pytest.fixture
def ai():
    """Use in a test to set what the fake AI replies: ai.replies = ['...']"""
    fake_llm.replies, fake_llm.prompts = [], []
    return fake_llm
