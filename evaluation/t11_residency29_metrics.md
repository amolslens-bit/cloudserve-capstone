# Metrics report

- Input tickets: 29
- Tickets processed: 29
- Decisions written to the log this run: 29 (reconciles)
- Started 2026-11-19 09:32, finished 2026-11-19 09:53 (20.8 min)
- Prompt versions: PR-01 1.3, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1

## What the system did

- Auto-answered (draft ready for agent): 24 (83%)
- Escalated: 5 (17%)
  - to tier 1: 5
  - to tier 2: 0
- AI service unavailable (escalated safely): 0
- System errors (escalated safely): 0
- Escalations with a handover package: 5 of 5
- Average time per ticket: 39.6 s

## Why tickets escalated

- 3  no reviewed article covers the question
- 2  reply review failed or did not run

## Models used

- 23  nvidia/nemotron-3.5-lightning:free
- 4  openai/gpt-oss-20b
- 2  openai/gpt-oss-120b

## A10 Volume

- Tickets processed: 29
- Answered automatically: 24 (83%)
- Escalated: 5 (17%)
- Blocked by guardrails: 2 (7%)
  - (a draft was written but stopped by a draft check: no valid citation, a must-not claim, or the PR-04 reply review)

## A10 Business

- First contact resolution: 24 (83%)
  - (brief's definition: tickets closed without escalation, divided by total tickets; here = auto-answered / processed)
- Response time, mean: 39.6 s
- Response time, median: 48.3 s
  - (system processing time per ticket from latency_ms; 29 of 29 tickets timed, code fallback records with no measured time left out)
- Escalation rate: 5 (17%) (target 30% or lower)

## A10 Technical

- Intent precision and recall per class: n/a (input file has no labels)
- Retrieval hit rate: 29/29 = 100%
  - (of the tickets that reached the search step, share with at least one article kept under the MAX_SCORE cut-off)
- Latency, median (p50): 48.3 s
- Latency, 95th percentile (p95): 83.5 s (target under 3 s)

## A10 Governance

- Decisions logged: 29 of 29 processed (reconciles)
- Guardrail activations by type (the check that stopped each escalated ticket): 5
  - 3  no article covers it, or answer confidence too low
  - 2  reply review (PR-04) blocked the draft or did not run
- Reply review (PR-04) verdicts of block, including tickets stopped earlier by another check: 2
- Private data detected and masked in incoming tickets: 0 (email 0, phone 0, api_key 0)
- Private data found in auto-answered replies: 0 (must be 0)
  - (code scan of each auto-answered draft for email addresses, phone numbers and API-key-like strings)
