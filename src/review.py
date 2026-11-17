"""PR-04 reply review (FR-06, FR-15). Anything other than a clean 'pass' counts as block."""
import json
import re
from pathlib import Path

from llm import llm

PROMPT = Path("prompts/pr04_review_v1.0.txt").read_text(encoding="utf-8")


def review(reply, article_text):
    prompt = PROMPT.replace("{article}", article_text).replace("{reply}", reply)
    try:
        out = json.loads(re.search(r"\{.*\}", llm.invoke(prompt).content, re.S).group())
    except Exception as e:
        return {"verdict": "block", "problems": [f"review failed: {str(e)[:80]}"]}
    if out.get("verdict") != "pass":
        return {"verdict": "block", "problems": out.get("problems") or ["blocked"]}
    return {"verdict": "pass", "problems": []}


if __name__ == "__main__":
    art = "Data is stored in the region you select when creating a project."
    print(review("Your data is stored in the region you chose when you created the project.", art))
    print(review("Don't worry, your data will never leave the EU.", art))
