"""Build one Chroma collection per chunking strategy (D9)."""
import shutil
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from chunking import load_docs, fixed_size_chunks, structure_chunks

STORE = "storage/chroma"

def main():
    shutil.rmtree(STORE, ignore_errors=True)  # always rebuild from scratch
    emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    docs = load_docs()
    for name, fn in [("kb_fixed", fixed_size_chunks), ("kb_structure", structure_chunks)]:
        chunks = fn(docs)
        Chroma.from_documents(chunks, emb, collection_name=name, persist_directory=STORE)
        print(f"{name}: indexed {len(chunks)} chunks")

    # quick search test
    for name in ["kb_fixed", "kb_structure"]:
        db = Chroma(collection_name=name, embedding_function=emb, persist_directory=STORE)
        hits = db.similarity_search("my account got locked after wrong passwords", k=3)
        print(f"\n{name} top 3:", [h.metadata["doc_id"] for h in hits])

if __name__ == "__main__":
    main()