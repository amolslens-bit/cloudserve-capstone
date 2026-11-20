# Metrics report

- Input tickets: 50
- Tickets processed: 50
- Decisions written to the log this run: 50 (reconciles)
- Started 2026-11-18 15:30, finished 2026-11-18 15:47 (16.1 min)
- Prompt versions: PR-01 1.1, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1

## What the system did

- Auto-answered (draft ready for agent): 39 (78%)
- Escalated: 11 (22%)
  - to tier 1: 4
  - to tier 2: 7
- AI service unavailable (escalated safely): 0
- System errors (escalated safely): 0
- Escalations with a handover package: 11 of 11
- Average time per ticket: 15.9 s

## Why tickets escalated

- 6  must-not-auto-respond intent
- 3  reply review failed or did not run
- 2  billing dispute or data commitment flagged

## Models used

- 32  openai/gpt-oss-120b
- 14  openai/gpt-oss-20b
- 4  nvidia/nemotron-3.5-lightning:free
