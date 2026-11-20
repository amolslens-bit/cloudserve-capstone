# Metrics report

- Input tickets: 50
- Tickets processed: 50
- Decisions written to the log this run: 50 (reconciles)
- Started 2026-11-19 18:23, finished 2026-11-19 18:43 (20.4 min)
- Prompt versions: PR-01 1.3, PR-05 1.2, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1

## What the system did

- Auto-answered (draft ready for agent): 45 (90%)
- Escalated: 5 (10%)
  - to tier 1: 1
  - to tier 2: 4
- AI service unavailable (escalated safely): 0
- System errors (escalated safely): 0
- Escalations with a handover package: 5 of 5
- Average time per ticket: 21.1 s

## Why tickets escalated

- 5  must-not-auto-respond intent

## Models used

- 36  openai/gpt-oss-20b
- 13  openai/gpt-oss-120b
- 1  nvidia/nemotron-3.5-lightning:free

## A10 Volume

- Tickets processed: 50
- Answered automatically: 45 (90%)
- Escalated: 5 (10%)
- Blocked by guardrails: 0 (0%)
  - (a draft was written but stopped by a draft check: no valid citation, a must-not claim, or the PR-04 reply review)

## A10 Business

- First contact resolution: 45 (90%)
  - (brief's definition: tickets closed without escalation, divided by total tickets; here = auto-answered / processed)
- Response time, mean: 21.1 s
- Response time, median: 20.5 s
  - (system processing time per ticket from latency_ms; 50 of 50 tickets timed, code fallback records with no measured time left out)
- Escalation rate: 5 (10%) (target 30% or lower)

## A10 Technical

- Intent precision and recall per class: n/a (input file has no labels)
- Retrieval hit rate: 45/45 = 100%
  - (of the tickets that reached the search step, share with at least one article kept under the MAX_SCORE cut-off)
- Latency, median (p50): 20.5 s
- Latency, 95th percentile (p95): 35.4 s (target under 3 s)

## A10 Governance

- Decisions logged: 50 of 50 processed (reconciles)
- Guardrail activations by type (the check that stopped each escalated ticket): 5
  - 5  must-not-auto-respond intent
- Reply review (PR-04) verdicts of block, including tickets stopped earlier by another check: 0
- Private data detected and masked in incoming tickets: 0 (email 0, phone 0, api_key 0)
- Private data found in auto-answered replies: 0 (must be 0)
  - (code scan of each auto-answered draft for email addresses, phone numbers and API-key-like strings)
