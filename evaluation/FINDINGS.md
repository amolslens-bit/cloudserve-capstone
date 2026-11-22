# Retrieval cut-off analysis (18 Nov, no LLM calls)
Scripts: build_index_local.py -> retrieval_scores.py -> separation.py, reach_retrieval.py, label_consistency.py, ceiling.py
- Retrieval score does not separate answerable vs not-answerable: AUC 0.47-0.48 on the 413 tickets that reach retrieval (0.5 = coin flip).
- MAX_SCORE 0.9 would catch 9/87 not-answerable but wrongly escalate 30-42 answerable (13-25 of them in the 200).
- MAX_SCORE 1.3 costs 0 answerable tickets but catches 0-1 of the 87.
- The top-1/top-2 gap does not help either: AUC 0.51-0.53.
- 58 of the 87 not-answerable tickets have an answerable twin with an IDENTICAL body. 81 have one at cosine >= 0.95.
- So no text-only check can separate them, and that includes a PR-05 "does the article answer this" prompt.
