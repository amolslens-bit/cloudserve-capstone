"""Two chunking strategies for the CloudServe knowledge base (decision D9)."""
import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


def load_docs(path="data/documentation.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def base_metadata(doc):
    # Chroma metadata must be simple values, so the list becomes a comma string
    return {
        "doc_id": doc["doc_id"],
        "title": doc["title"],
        "category": doc["category"],
        "applies_to": doc["applies_to"],
        "related_docs": ",".join(doc.get("related_docs", [])),
    }


def fixed_size_chunks(docs, size=500, overlap=50):
    """Baseline: cut every article into ~500-character pieces."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)
    chunks = []
    for doc in docs:
        for i, text in enumerate(splitter.split_text(doc["content"])):
            meta = base_metadata(doc) | {"strategy": "fixed", "chunk": i}
            chunks.append(Document(page_content=text, metadata=meta))
    return chunks


def structure_chunks(docs):
    """Split each article on its ## section headings."""
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "section")], strip_headers=False
    )
    chunks = []
    for doc in docs:
        for i, part in enumerate(splitter.split_text(doc["content"])):
            section = part.metadata.get("section", "Overview")
            # put the title in each chunk so it still makes sense on its own
            text = f"{doc['title']}\n{part.page_content}"
            meta = base_metadata(doc) | {"strategy": "structure", "section": section, "chunk": i}
            chunks.append(Document(page_content=text, metadata=meta))
    return chunks


if __name__ == "__main__":
    docs = load_docs()
    for name, fn in [("fixed", fixed_size_chunks), ("structure", structure_chunks)]:
        chunks = fn(docs)
        avg = sum(len(c.page_content) for c in chunks) // len(chunks)
        print(f"{name}: {len(chunks)} chunks, avg {avg} chars")
    sample = structure_chunks(docs)[2]
    print("\nSample structure chunk:")
    print(sample.metadata)
    print(sample.page_content)