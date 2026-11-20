# Metrics report

- Input tickets: 50
- Tickets processed: 50
- Decisions written to the log this run: 50 (reconciles)
- Started 2026-11-18 21:59, finished 2026-11-18 22:17 (17.8 min)
- Prompt versions: PR-01 1.2, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1

## What the system did

- Auto-answered (draft ready for agent): 40 (80%)
- Escalated: 10 (20%)
  - to tier 1: 2
  - to tier 2: 8
- AI service unavailable (escalated safely): 0
- System errors (escalated safely): 0
- Escalations with a handover package: 10 of 10
- Average time per ticket: 17.9 s

## Why tickets escalated

- 4  must-not-auto-respond intent
- 4  billing dispute or data commitment flagged
- 1  reply review failed or did not run
- 1  no reviewed article covers the question

## Models used

- 24  openai/gpt-oss-120b
- 13  openai/gpt-oss-20b
- 13  qwen/qwen3.8-27b

## A10 Volume

- Tickets processed: 50
- Answered automatically: 40 (80%)
- Escalated: 10 (20%)
- Blocked by guardrails: 1 (2%)
  - (a draft was written but stopped by a draft check: no valid citation, a must-not claim, or the PR-04 reply review)

## A10 Business

- First contact resolution: 40 (80%)
  - (brief's definition: tickets closed without escalation, divided by total tickets; here = auto-answered / processed)
- Response time, mean: 17.9 s
- Response time, median: 15.3 s
  - (system processing time per ticket from latency_ms; 50 of 50 tickets timed, code fallback records with no measured time left out)
- Escalation rate: 10 (20%) (target 30% or lower)

## A10 Technical

- Intent precision and recall per class: n/a (input file has no labels)
- Retrieval hit rate: 42/42 = 100%
  - (of the tickets that reached the search step, share with at least one article kept under the MAX_SCORE cut-off)
- Latency, median (p50): 15.3 s
- Latency, 95th percentile (p95): 39.3 s (target under 3 s)

## A10 Governance

- Decisions logged: 50 of 50 processed (reconciles)
- Guardrail activations by type (the check that stopped each escalated ticket): 10
  - 4  must-not-auto-respond intent
  - 4  billing dispute or data commitment
  - 1  reply review (PR-04) blocked the draft or did not run
  - 1  no article covers it, or answer confidence too low
- Reply review (PR-04) verdicts of block, including tickets stopped earlier by another check: 1
- Private data detected and masked in incoming tickets: 0 (email 0, phone 0, api_key 0)
- Private data found in auto-answered replies: 0 (must be 0)
  - (code scan of each auto-answered draft for email addresses, phone numbers and API-key-like strings)
