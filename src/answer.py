"""PR-05 answer drafting (FR-07, FR-08). Code checks the citations; labels only score the test.

Version 1.2 keeps the 1.1 primary path: the same articles (full text), the same
covered / article_id / confidence checks, and `article_id` stays the primary
article. It adds a `citations` list, each {"doc_id", "section"}, primary first:
- the primary's section must be a real ## heading of that article, otherwise
  the citation keeps the article id with no section (never a failure);
- at most ONE extra source, and only an article that was supplied for this
  ticket AND is listed in the primary article's related_docs, with a real
  heading of that article. Anything else is dropped and noted in
  `citation_notes`; it never changes covered, confidence or the route.
"""
import random
import re
from pathlib import Path

from classify import classify
from llm import llm
from parse import parse_json
from load_data import load
from prepare import prepare
from retrieve import retrieve

DOCS = {d["doc_id"]: d for d in load("documentation.json")}
PROMPT = Path("prompts/pr05_answer_v1.2.txt").read_text(encoding="utf-8")
NOT_COVERED = {"covered": False, "article_id": "", "confidence": 0.0, "answer": "",
               "citations": [], "citation_notes": []}
MAX_EXTRA = 1
HEADING = re.compile(r"^##\s+(.+?)\s*$", re.M)


def headings(doc_id):
    return HEADING.findall(DOCS.get(doc_id, {}).get("content", ""))


def real_heading(doc_id, section):
    """The heading exactly as written in the article, or None if it isn't one of them."""
    want = str(section or "").strip().lstrip("#").strip().lower()
    for h in headings(doc_id):
        if h.lower() == want:
            return h
    return None


def section_text(doc_id, heading):
    """The text of one ## section, heading included."""
    content = DOCS.get(doc_id, {}).get("content", "")
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$", content, re.M)
    if not m:
        return ""
    nxt = HEADING.search(content, m.end())
    return content[m.start(): nxt.start() if nxt else len(content)].strip()


def related(doc_id):
    return list(DOCS.get(doc_id, {}).get("related_docs") or [])


def header(a, supplied):
    """1.1 header, plus a 'related' note only when another supplied article is related."""
    rel = [d for d in related(a["doc_id"]) if d in supplied and d != a["doc_id"]]
    note = f" (related: {', '.join(rel)})" if rel else ""
    return f"[{a['doc_id']}] {DOCS[a['doc_id']]['title']}{note}"


def check_citations(out, supplied):
    """Build the citations list from the model output. Never raises."""
    primary = out["article_id"]
    notes = []
    sec = real_heading(primary, out.get("section"))
    if out.get("section") and not sec:
        notes.append(f"primary section {str(out.get('section'))[:40]!r} is not a heading of {primary}; kept the article only")
    citations = [{"doc_id": primary, "section": sec}]
    extra = out.get("also_cited") or []
    if not isinstance(extra, list):
        notes.append("also_cited was not a list; ignored")
        extra = []
    for item in extra:
        doc = item.get("doc_id") if isinstance(item, dict) else None
        if len(citations) > MAX_EXTRA:
            notes.append(f"dropped {doc!r}: only {MAX_EXTRA} extra source allowed")
        elif not doc or doc == primary:
            notes.append(f"dropped {doc!r}: empty or same as the primary")
        elif doc not in supplied:
            notes.append(f"dropped {doc!r}: not one of the articles supplied for this ticket")
        elif doc not in related(primary):
            notes.append(f"dropped {doc!r}: not in {primary}'s related articles")
        elif not real_heading(doc, item.get("section")):
            notes.append(f"dropped {doc!r}: section {str(item.get('section'))[:40]!r} is not one of its headings")
        else:
            citations.append({"doc_id": doc, "section": real_heading(doc, item.get("section"))})
    return citations, notes


def review_text(citations):
    """What PR-04 reads: the full primary article (as in 1.1), plus each extra cited section."""
    parts = [DOCS[citations[0]["doc_id"]]["content"]]
    for c in citations[1:]:
        parts.append(f"[{c['doc_id']}] {DOCS[c['doc_id']]['title']}, section {c['section']}:\n"
                     f"{section_text(c['doc_id'], c['section'])}")
    return "\n\n".join(parts)


def sources_line(citations):
    """FR-09 fixed disclosure line naming every source as doc id plus section."""
    names = [f"{c['doc_id']} {DOCS.get(c['doc_id'], {}).get('title', '')}".strip()
             + (f" (section: {c['section']})" if c.get("section") else "") for c in citations]
    word = "article" if len(names) == 1 else "articles"
    return f"This reply was prepared automatically using our help {word}: " + "; ".join(names) + "."


def draft_answer(ticket, intent, articles):
    # give the AI the FULL article, not just the one section search matched
    supplied = {a["doc_id"] for a in articles}
    art_text = "\n\n".join(f"{header(a, supplied)}:\n{DOCS[a['doc_id']]['content']}" for a in articles)
    prompt = (PROMPT.replace("{subject}", ticket["subject"] or "")
                    .replace("{body}", ticket["body"])
                    .replace("{tier}", ticket["customer_tier"] or "")
                    .replace("{intent}", intent)
                    .replace("{articles}", art_text))
    raw = ""
    try:
        raw = llm.invoke(prompt).content
        out = parse_json(raw)
    except Exception as e:
        return dict(NOT_COVERED, why=f"error or bad JSON: {str(e)[:80]} | raw: {raw[:120]}")
    # FR-08: the cited article must be one we actually supplied
    if out.get("covered") is not True or out.get("article_id") not in supplied:
        return dict(NOT_COVERED, why=f"model said covered={out.get('covered')}, cited {out.get('article_id')!r}")
    try:
        out["confidence"] = float(out.get("confidence", 0))
    except (TypeError, ValueError):
        out["confidence"] = 0.0
    try:
        out["citations"], out["citation_notes"] = check_citations(out, supplied)
    except Exception as e:                    # a citation problem never fails the answer
        out["citations"] = [{"doc_id": out["article_id"], "section": None}]
        out["citation_notes"] = [f"citation check error: {type(e).__name__}"]
    return out


if __name__ == "__main__":
    raw = load("development_tickets.json")
    # small test: 5 tickets meant to be auto-answered (labels used only to pick and score)
    pool = [t for t in raw if t["labels"]["expected_route"] == "auto_respond"]
    for t in random.Random(7).sample(pool, 5):
        clean = prepare(t)
        c = classify(clean)
        arts = retrieve(clean)
        a = draft_answer(clean, c["intent"], arts)
        ok = a["article_id"] in t["labels"]["expected_doc_ids"]
        print("OK " if ok else "XX ", t["ticket_id"], "| cited", a.get("citations") or "-",
              "| expected", t["labels"]["expected_doc_ids"], "| conf", a["confidence"])
        print("     searched:", [x["doc_id"] for x in arts], "| notes:", a.get("citation_notes"))
        print("    ", (a["answer"] or "(not covered) " + a.get("why", ""))[:200].replace("\n", " "))
