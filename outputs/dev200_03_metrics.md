# Metrics report

- Input tickets: 50
- Tickets processed: 50
- Decisions written to the log this run: 50 (reconciles)
- Started 2026-11-18 11:03, finished 2026-11-18 11:18 (14.6 min)
- Prompt versions: PR-01 1.1, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1

## What the system did

- Auto-answered (draft ready for agent): 38 (76%)
- Escalated: 12 (24%)
  - to tier 1: 2
  - to tier 2: 10
- AI service unavailable (escalated safely): 0
- System errors (escalated safely): 0
- Escalations with a handover package: 12 of 12
- Average time per ticket: 14.1 s

## Why tickets escalated

- 4  must-not-auto-respond intent
- 4  billing dispute or data commitment flagged
- 2  warning words
- 2  no reviewed article covers the question

## Models used

- 28  openai/gpt-oss-120b
- 17  openai/gpt-oss-20b
- 3  nvidia/nemotron-3.5-lightning:free
- 2  qwen/qwen3.8-27b
