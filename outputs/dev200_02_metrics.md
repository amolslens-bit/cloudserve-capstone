# Metrics report

- Input tickets: 50
- Tickets processed: 50
- Decisions written to the log this run: 50 (reconciles)
- Started 2026-11-18 10:38, finished 2026-11-18 10:57 (19.1 min)
- Prompt versions: PR-01 1.1, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1

## What the system did

- Auto-answered (draft ready for agent): 40 (80%)
- Escalated: 10 (20%)
  - to tier 1: 1
  - to tier 2: 9
- AI service unavailable (escalated safely): 0
- System errors (escalated safely): 0
- Escalations with a handover package: 10 of 10
- Average time per ticket: 19.5 s

## Why tickets escalated

- 4  must-not-auto-respond intent
- 3  billing dispute or data commitment flagged
- 2  warning words
- 1  reply review failed or did not run

## Models used

- 28  openai/gpt-oss-20b
- 19  nvidia/nemotron-3.5-lightning:free
- 3  openai/gpt-oss-120b
