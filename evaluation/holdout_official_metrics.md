# Metrics report

- Input tickets: 80
- Tickets processed: 80
- Decisions written to the log this run: 80 (reconciles)
- Started 2026-11-20 13:38, finished 2026-11-20 13:50 (12.5 min)
- Prompt versions: PR-01 1.3, PR-05 1.2, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1

## What the system did

- Auto-answered (draft ready for agent): 45 (56%)
- Escalated: 35 (44%)
  - to tier 1: 23
  - to tier 2: 12
- AI service unavailable (escalated safely): 0
- System errors (escalated safely): 0
- Escalations with a handover package: 35 of 35
- Average time per ticket: 5.9 s

## Why tickets escalated

- 18  must-not-auto-respond intent
- 13  no reviewed article covers the question
- 3  answer confidence 0.6 below cut-off (draft attached)
- 1  low classification confidence 0.55

## Models used

- 80  claude-haiku-5-5

## Model calls (each AI call)

- 266  claude-haiku-5-5 (266 ok; mean 1.78 s)

## A10 Volume

- Tickets processed: 80
- Answered automatically: 45 (56%)
- Escalated: 35 (44%)
- Blocked by guardrails: 0 (0%)
  - (a draft was written but stopped by a draft check: no valid citation, a must-not claim, or the PR-04 reply review)

## A10 Business

- First contact resolution: 45 (56%)
  - (brief's definition: tickets closed without escalation, divided by total tickets; here = auto-answered / processed)
- First contact resolution, correct answers only: 34/80 = 42%
  - (auto-answered AND the label says it should be auto-answered, divided by labelled tickets)
- Response time, mean: 5.9 s
- Response time, median: 5.9 s
  - (system processing time per ticket from latency_ms; 80 of 80 tickets timed, code fallback records with no measured time left out)
- Escalation rate: 35 (44%) (target 30% or lower)

## A10 Technical

Intent precision and recall per class (80 labelled tickets):

| Intent | Precision | Recall | Labelled tickets |
|---|---|---|---|
| account_access | 67% | 50% | 4 |
| api_key_issue | 67% | 33% | 6 |
| api_usage_question | 100% | 75% | 4 |
| authentication_failure | 100% | 67% | 3 |
| billing_query | 100% | 100% | 10 |
| compliance_request | 100% | 100% | 1 |
| configuration_help | 60% | 100% | 3 |
| data_export | 50% | 100% | 1 |
| data_residency | 100% | 100% | 6 |
| database_issue | 100% | 100% | 1 |
| deployment_failure | 100% | 100% | 5 |
| feature_request | 100% | 100% | 3 |
| integration_help | 100% | 33% | 3 |
| onboarding | 100% | 100% | 4 |
| performance_degradation | 100% | 100% | 3 |
| quota_or_overage | 100% | 100% | 2 |
| rate_limit | 100% | 100% | 1 |
| rollback_request | 100% | 100% | 6 |
| security_incident | 50% | 100% | 4 |
| sso_configuration | 100% | 100% | 1 |
| unclear_request | 100% | 100% | 6 |
| webhook_issue | 75% | 100% | 3 |

- Average precision across classes: 89% (target 85%)
- Average recall across classes: 89%
  - (precision = of the tickets we put in a class, share that were really that class; recall = of the tickets really in a class, share we found)
- Retrieval hit rate: 61/61 = 100%
  - (of the tickets that reached the search step, share with at least one article kept under the MAX_SCORE cut-off)
- Retrieval hit rate, right article: 43/44 = 98%
  - (of searched tickets whose label lists expected articles, share where one of them was among the articles retrieved)
- Latency, median (p50): 5.9 s
- Latency, 95th percentile (p95): 7.8 s (target under 3 s)

## A10 Governance

- Decisions logged: 80 of 80 processed (reconciles)
- Guardrail activations by type (the check that stopped each escalated ticket): 35
  - 18  must-not-auto-respond intent
  - 16  no article covers it, or answer confidence too low
  - 1  low classification confidence
- Reply review (PR-04) verdicts of block, including tickets stopped earlier by another check: 0
- Private data detected and masked in incoming tickets: 0 (email 0, phone 0, api_key 0)
- Private data found in auto-answered replies: 0 (must be 0)
  - (code scan of each auto-answered draft for email addresses, phone numbers and API-key-like strings)

## Scores against labels (labels used only here)

- Intent right: 70/80 = 88% (target 85%)
- Urgency right: 31/80 = 39% (target 80%)
- Route right: 55/80 = 69% (target 85%)
- Must-not tickets auto-answered: 0 of 14 (must be 0) []
- Auto-answered of those that should be: 34/48 = 71%
- Auto-answers citing an expected article: 34/45 = 76% (target 85%)
- Auto-answers citing ALL expected articles: 21/35 = 60%
  - of those expecting 2 or more articles: 0/13 = 0%
- Citations with a valid section heading: 45/45 = 100%
  - (code checks every section against the article's ## headings; an invalid primary section keeps the article with no section)
- Extra (related) sources kept: 0; dropped by the code check: 0
