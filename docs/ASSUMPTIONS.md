# Assumptions register: CloudServe capstone (Amol)

Each assumption gets tested. If it fails, record it in the PRD Revision Log (Stage 5).

| # | Date | Assumption | Why it matters | How we'll test it | When | Status | If wrong |
|---|------|-----------|----------------|-------------------|------|--------|----------|
| A-01 | 2026-11-01 | `nvidia/nemotron-3.5-lightning:free` returns valid structured JSON (intent, urgency, confidence, citations) reliably | Parsing failures break routing and logging | Run 50 dev tickets; count parse failures | Week 2, day 3 | Open | Add retry with a schema reminder, or switch model (log as new decision) |
| A-02 | 2026-11-01 | The free tier rate limits allow a full unattended run of 80–120 tickets | Acceptance criterion A9 (unattended full run) | Full validation run with backoff and caching on | Week 2, day 5 | Open | Add queueing and caching; fail over to Groq |
| A-03 | 2026-11-01 | Groq works as a drop-in fallback using an OpenAI-compatible API | A11 (graceful degradation on outage) | Disable OpenRouter key and run 10 tickets | Week 2, day 4 | Open | Escalate all tickets with a logged reason |
| A-04 | 2026-11-01 | Model latency (~0.5s) keeps end-to-end p95 under 3s | Technical target, live chat | Measure p50/p95 in harness | Week 2, day 5 | Open | Cache, trim prompts, or answer simpler intents by rule |
| A-05 | 2026-11-01 | Local `all-MiniLM-L6-v2` embeddings are good enough for retrieval on 29 articles | Retrieval hit rate and citation accuracy | Compare two chunk sizes on known questions | Week 2, day 2 | Open | Tune chunking; try another free local embedding model |
