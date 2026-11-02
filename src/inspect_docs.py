import json
from pathlib import Path

docs = json.loads(Path("data/documentation.json").read_text(encoding="utf-8"))
print("articles:", len(docs))
print("first id:", docs[0]["doc_id"])
print(docs[0]["content"][:300])