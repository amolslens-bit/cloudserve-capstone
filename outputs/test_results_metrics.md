# Metrics report

- Input tickets: 5
- Tickets processed: 5
- Decisions written to the log this run: 5 (reconciles)
- Started 2026-11-17 08:57, finished 2026-11-17 08:58 (0.5 min)
- Prompt versions: PR-01 1.1, PR-05 1.1, PR-04 1.0, PR-06 1.0

## What the system did

- Auto-answered (draft ready for agent): 3 (60%)
- Escalated: 2 (40%)
  - to tier 1: 0
  - to tier 2: 2
- AI service unavailable (escalated safely): 0
- System errors (escalated safely): 0
- Escalations with a handover package: 2 of 2
- Average time per ticket: 3.1 s

## Why tickets escalated

- 1  warning words
- 1  must-not-auto-respond intent

## Models used

- 5  nvidia/nemotron-3.5-lightning:free

## Scores against labels (labels used only here)

- Intent right: 4/5 = 80% (target 85%)
- Urgency right: 3/5 = 60% (target 80%)
- Route right: 4/5 = 80% (target 85%)
- Must-not tickets auto-answered: 0 of 2 (must be 0) []
- Auto-answered of those that should be: 2/2 = 100%
- Auto-answers citing an expected article: 1/3 = 33% (target 85%)
