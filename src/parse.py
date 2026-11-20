"""Helpers for reading a model reply. Used by every prompt step."""
import json
import re

# Some qwen3 replies put reasoning in <think>...</think> before the JSON.
# The parsers look for the first { ... }, so a brace inside the think block
# would be read as the answer. Strip the block first.
THINK = re.compile(r"<think\b[^>]*>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_think(text):
    """Remove <think>...</think> blocks; leave other text as it is."""
    return THINK.sub("", text or "").strip()


def parse_json(raw):
    """Read the JSON object in a model reply, after stripping think blocks."""
    return json.loads(re.search(r"\{.*\}", strip_think(raw), re.S).group())
