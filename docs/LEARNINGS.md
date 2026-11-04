# Learnings log

| Date | Learning | Where it came from |
|---|---|---|
| 2026-11-02 | `CREATE TABLE IF NOT EXISTS` won't change an existing table; schema changes need a migration | Decision log rerun gave 2 rows |
| 2026-11-02 | An unsaved file in VS Code is empty on disk; ● on the tab means unsaved | inspect_docs.py printed nothing |
| 2026-11-02 | Category is better as a metadata filter than as a chunking unit | Chunking discussion |
| 2026-11-02 | Top-k results can all come from one article, so count unique doc_ids | First Chroma search test |
| 2026-11-02 | Build-before-discovery is a risk; setup only until evidence exists | Own concern, confirmed |
| 2026-11-04 | Never delete or reuse IDs. Mark items resolved and give new items the next number, so traceability doesn't break. | Own concern, confirmed |