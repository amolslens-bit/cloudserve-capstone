# Metrics report

- Input tickets: 1
- Tickets processed: 1
- Decisions written to the log this run: 1 (reconciles)
- Started 2026-11-20 13:01, finished 2026-11-20 13:01 (0.1 min)
- Prompt versions: PR-01 1.3, PR-05 1.2, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1

## What the system did

- Auto-answered (draft ready for agent): 1 (100%)
- Escalated: 0 (0%)
  - to tier 1: 0
  - to tier 2: 0
- AI service unavailable (escalated safely): 0
- System errors (escalated safely): 0
- Escalations with a handover package: 0 of 0
- Average time per ticket: 6.7 s

## Why tickets escalated


## Models used

- 1  claude-haiku-5-5

## Model calls (each AI call)

- 3  claude-haiku-5-5 (3 ok; mean 2.16 s)

## A10 Volume

- Tickets processed: 1
- Answered automatically: 1 (100%)
- Escalated: 0 (0%)
- Blocked by guardrails: 0 (0%)
  - (a draft was written but stopped by a draft check: no valid citation, a must-not claim, or the PR-04 reply review)

## A10 Business

- First contact resolution: 1 (100%)
  - (brief's definition: tickets closed without escalation, divided by total tickets; here = auto-answered / processed)
- Response time, mean: 6.7 s
- Response time, median: 6.7 s
  - (system processing time per ticket from latency_ms; 1 of 1 tickets timed, code fallback records with no measured time left out)
- Escalation rate: 0 (0%) (target 30% or lower)

## A10 Technical

- Intent precision and recall per class: n/a (input file has no labels)
- Retrieval hit rate: 1/1 = 100%
  - (of the tickets that reached the search step, share with at least one article kept under the MAX_SCORE cut-off)
- Latency, median (p50): 6.7 s
- Latency, 95th percentile (p95): 6.7 s (target under 3 s)

## A10 Governance

- Decisions logged: 1 of 1 processed (reconciles)
- Guardrail activations by type (the check that stopped each escalated ticket): 0
- Reply review (PR-04) verdicts of block, including tickets stopped earlier by another check: 0
- Private data detected and masked in incoming tickets: 0 (email 0, phone 0, api_key 0)
- Private data found in auto-answered replies: 0 (must be 0)
  - (code scan of each auto-answered draft for email addresses, phone numbers and API-key-like strings)
