# Metrics report

- Input tickets: 50
- Tickets processed: 50
- Decisions written to the log this run: 50 (reconciles)
- Started 2026-11-17 18:23, finished 2026-11-17 18:44 (21.0 min)
- Prompt versions: PR-01 1.1, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1

## What the system did

- Auto-answered (draft ready for agent): 38 (76%)
- Escalated: 12 (24%)
  - to tier 1: 4
  - to tier 2: 8
- AI service unavailable (escalated safely): 0
- System errors (escalated safely): 0
- Escalations with a handover package: 12 of 12
- Average time per ticket: 21.8 s

## Why tickets escalated

- 4  reply review failed or did not run
- 4  must-not-auto-respond intent
- 3  billing dispute or data commitment flagged
- 1  warning words

## Models used

- 44  openai/gpt-oss-20b
- 5  openai/gpt-oss-120b
- 1  nvidia/nemotron-3.5-lightning:free
