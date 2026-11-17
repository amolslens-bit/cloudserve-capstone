from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

STORE = "storage/chroma"
# Relevance cut-off (Build Spec, Retrieve): a hit with a score ABOVE this is too weak
# and is dropped, so the system gets nothing rather than something irrelevant.
# Lower score = better match. Starting value only; set from the sample run.
MAX_SCORE = 1.5

emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
db = Chroma(collection_name="kb_structure", embedding_function=emb, persist_directory=STORE)

def retrieve(ticket, k=3):
    """Return up to k different relevant articles, best match first. May return none."""
    query = f"{ticket['subject'] or ''} {ticket['body']}"
    hits = db.similarity_search_with_score(query, k=12)
    seen, results = set(), []
    for doc, score in hits:
        if score > MAX_SCORE:
            continue
        doc_id = doc.metadata["doc_id"]
        if doc_id in seen:
            continue
        seen.add(doc_id)
        results.append({"doc_id": doc_id, "title": doc.metadata["title"],
                        "text": doc.page_content, "score": round(score, 3)})
        if len(results) == k:
            break
    return results

if __name__ == "__main__":
    tests = [{"subject": "Locked out", "body": "my account got locked after wrong passwords"},
             {"subject": "", "body": "what is the best pizza topping in Naples"}]
    for test in tests:
        print("Query:", test["body"])
        for r in retrieve(test):
            print("  ", r["doc_id"], r["score"], r["title"])
        raw = db.similarity_search_with_score(test["body"], k=1)[0]
        print("   best raw score:", round(raw[1], 3), "| kept:", raw[1] <= MAX_SCORE)
