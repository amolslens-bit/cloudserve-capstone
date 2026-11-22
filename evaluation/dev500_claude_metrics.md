# Metrics report (merged dev-set check)

This file starts with the standard run.py report, then adds merge notes, PRD FCR, current-process baselines, miss lists, and a cost estimate. Labels are used only for scoring. This is not an official result.
# Metrics report

- Input tickets: 500
- Tickets processed: 500
- Decisions written to the log this run: 0 (DOES NOT reconcile)
- Started 2026-11-21 11:38, finished 2026-11-21 11:38 (0.0 min)
- Prompt versions: PR-01 1.3, PR-05 1.2, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1

## What the system did

- Auto-answered (draft ready for agent): 270 (54%)
- Escalated: 230 (46%)
  - to tier 1: 154
  - to tier 2: 76
- AI service unavailable (escalated safely): 0
- System errors (escalated safely): 0
- Escalations with a handover package: 230 of 230
- Average time per ticket: 5.9 s

## Why tickets escalated

- 77  must-not-auto-respond intent
- 64  no reviewed article covers the question
- 38  reply review failed or did not run
- 27  answer confidence 0.6 below cut-off (draft attached)
- 12  warning words
- 6  low classification confidence 0.45
- 2  billing dispute or data commitment flagged
- 2  low classification confidence 0.55
- 2  low classification confidence 0.5

## Models used

- 500  claude-haiku-5-5

## Model calls (each AI call)

- 1719  claude-haiku-5-5 (1719 ok; mean 1.70 s)

## A10 Volume

- Tickets processed: 500
- Answered automatically: 270 (54%)
- Escalated: 230 (46%)
- Blocked by guardrails: 38 (8%)
  - (a draft was written but stopped by a draft check: no valid citation, a must-not claim, or the PR-04 reply review)

## A10 Business

- First contact resolution: 270 (54%)
  - (brief's definition: tickets closed without escalation, divided by total tickets; here = auto-answered / processed)
- First contact resolution, correct answers only: 205/500 = 41%
  - (auto-answered AND the label says it should be auto-answered, divided by labelled tickets)
- Response time, mean: 5.9 s
- Response time, median: 5.5 s
  - (system processing time per ticket from latency_ms; 500 of 500 tickets timed, code fallback records with no measured time left out)
- Escalation rate: 230 (46%) (target 30% or lower)

## A10 Technical

Intent precision and recall per class (500 labelled tickets):

| Intent | Precision | Recall | Labelled tickets |
|---|---|---|---|
| account_access | 75% | 95% | 22 |
| api_key_issue | 61% | 61% | 18 |
| api_usage_question | 100% | 92% | 24 |
| authentication_failure | 100% | 65% | 20 |
| billing_query | 100% | 100% | 24 |
| compliance_request | 100% | 35% | 26 |
| configuration_help | 71% | 100% | 17 |
| data_export | 63% | 100% | 29 |
| data_residency | 100% | 100% | 29 |
| database_issue | 100% | 92% | 26 |
| deployment_failure | 100% | 100% | 27 |
| feature_request | 100% | 100% | 20 |
| integration_help | 100% | 43% | 21 |
| onboarding | 100% | 82% | 22 |
| performance_degradation | 79% | 100% | 23 |
| quota_or_overage | 100% | 96% | 23 |
| rate_limit | 93% | 100% | 13 |
| rollback_request | 97% | 100% | 28 |
| security_incident | 79% | 100% | 26 |
| sso_configuration | 100% | 100% | 26 |
| unclear_request | 100% | 100% | 15 |
| webhook_issue | 100% | 100% | 21 |

- Average precision across classes: 92% (target 85%)
- Average recall across classes: 89%
  - (precision = of the tickets we put in a class, share that were really that class; recall = of the tickets really in a class, share we found)
- Retrieval hit rate: 399/399 = 100%
  - (of the tickets that reached the search step, share with at least one article kept under the MAX_SCORE cut-off)
- Retrieval hit rate, right article: 299/312 = 96%
  - (of searched tickets whose label lists expected articles, share where one of them was among the articles retrieved)
- Latency, median (p50): 5.5 s
- Latency, 95th percentile (p95): 9.8 s (target under 3 s)

## A10 Governance

- Decisions logged: 0 of 500 processed (DOES NOT reconcile)
- Guardrail activations by type (the check that stopped each escalated ticket): 230
  - 91  no article covers it, or answer confidence too low
  - 77  must-not-auto-respond intent
  - 38  reply review (PR-04) blocked the draft or did not run
  - 12  warning words (breach, lawyer, audit ...)
  - 10  low classification confidence
  - 2  billing dispute or data commitment
- Reply review (PR-04) verdicts of block, including tickets stopped earlier by another check: 40
- Private data detected and masked in incoming tickets: 0 (email 0, phone 0, api_key 0)
- Private data found in auto-answered replies: 0 (must be 0)
  - (code scan of each auto-answered draft for email addresses, phone numbers and API-key-like strings)

## Scores against labels (labels used only here)

- Intent right: 447/500 = 89% (target 85%)
- Urgency right: 240/500 = 48% (target 80%)
- Route right: 329/500 = 66% (target 85%)
- Must-not tickets auto-answered: 0 of 87 (must be 0) []
- Auto-answered of those that should be: 205/311 = 66%
- Auto-answers citing an expected article: 200/270 = 74% (target 85%)
- Auto-answers citing ALL expected articles: 146/213 = 69%
  - of those expecting 2 or more articles: 0/54 = 0%
- Citations with a valid section heading: 271/271 = 100%
  - (code checks every section against the article's ## headings; an invalid primary section keeps the article with no section)
- Extra (related) sources kept: 1; dropped by the code check: 0

## Merged run notes

- Part files: outputs\dev500_part1.json, outputs\dev500_part2.json, outputs\dev500_part3.json, outputs\dev500_part4.json
- Tickets in the merged file: 500
- The 'decisions written to the log this run' line in the standard report does not apply to a merge: each window wrote its own log (or skipped a row if the log was locked). Scoring uses this JSON, not the log.
- Prompt versions (from run.py): PR-01 1.3, PR-05 1.2, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1

## PRD first-contact resolution (labelled dev-set check)

A ticket counts when the system auto-answers it, the ticket is labelled for a reply (expected_route = auto_respond), the answer cites an expected article, and no safety rule is broken (must-not auto-answered, PR-04 block, banned claim, or PII in the reply). This is stricter than the brief's auto-answered / processed rate in the standard report above.
This is a check on the 500 development tickets the system was tuned on. It is not an official result. The official score remains the 20 Nov holdout (T45).
- PRD FCR on labelled tickets: 192/500 = 38%
- PRD FCR on the 200 answer-key tickets, with lexical must_mention and code must_not_claim (no AI / not the PR-08 judge): 91/200 = 46%
  - must_not_claim uses the same substring check as pr08_judge.must_not_claim_hits.
  - must_mention is a case-insensitive substring check of the reply. Paraphrases that a judge might accept are counted as missing. Empty must_mention lists pass.
  - This is not a substitute for a PR-08 judge run.
  - Current-process FCR on those same tickets (history.first_contact_resolution): 118/200 = 59.0%

## Auto-answers and escalations (merged file)

- Auto-answered: 270/500 = 54%
- Escalated: 230/500 = 46%  (tier 1: 154; tier 2: 76)
  - 77  must-not-auto-respond intent
  - 64  no reviewed article covers the question
  - 38  reply review failed or did not run
  - 27  answer confidence 0.6 below cut-off (draft attached)
  - 12  warning words
  - 6  low classification confidence 0.45
  - 2  billing dispute or data commitment flagged
  - 2  low classification confidence 0.55
  - 2  low classification confidence 0.5

## Comparison with the current process (from the ticket history, not invented)

- Current-process FCR (history.first_contact_resolution): 219/500 = 43.8%
- Current-process escalation rate (history.escalated): 281/500 = 56.2%
- Current-process mean resolution time (history.resolution_time_minutes): 421.7 min
- Current-process repeat contact (history.repeat_contact): 108/500 = 21.6%
- By customer tier (same history fields):
  - business: FCR 79/164 = 48.2%; escalated 85/164 = 51.8%; mean resolution 358.8 min
  - enterprise: FCR 31/83 = 37.3%; escalated 52/83 = 62.7%; mean resolution 483.7 min
  - standard: FCR 109/253 = 43.1%; escalated 144/253 = 56.9%; mean resolution 442.1 min
- This run, auto-answered / processed (brief's simpler FCR): 270/500 = 54%
- This run, PRD FCR (stricter, labelled): 192/500 = 38%
- Enterprise this run: auto-answered 41/83 = 49%; PRD FCR 28/83 = 34% (current-process enterprise FCR is in the tier list above; PRD NFR-06: do not go below that figure).
- Time-to-first-reply (8–12 hours in the PRD / interviews) is not a field on the tickets; it is not recomputed here. The history field is resolution_time_minutes (end-to-end handling time), shown above.
- Tickets labelled not answerable from docs: 143 (the known 143 on the 500-ticket file, if this is that file).

## Miss lists (ticket IDs; labels used only here)

- Should have been auto-answered, but were escalated: 106
  - DEV-0012, DEV-0016, DEV-0023, DEV-0029, DEV-0036, DEV-0037, DEV-0048, DEV-0054, DEV-0058, DEV-0059, DEV-0060, DEV-0062, DEV-0071, DEV-0072, DEV-0074, DEV-0079, DEV-0088, DEV-0093, DEV-0096, DEV-0103, DEV-0104, DEV-0113, DEV-0129, DEV-0130, DEV-0135, DEV-0143, DEV-0159, DEV-0161, DEV-0173, DEV-0185, DEV-0192, DEV-0194, DEV-0195, DEV-0206, DEV-0208, DEV-0209, DEV-0213, DEV-0215, DEV-0219, DEV-0222, DEV-0228, DEV-0247, DEV-0252, DEV-0255, DEV-0258, DEV-0269, DEV-0276, DEV-0278, DEV-0279, DEV-0285, DEV-0289, DEV-0292, DEV-0295, DEV-0299, DEV-0309, DEV-0310, DEV-0311, DEV-0312, DEV-0314, DEV-0316, DEV-0317, DEV-0319, DEV-0321, DEV-0326, DEV-0329, DEV-0331, DEV-0334, DEV-0337, DEV-0340, DEV-0341, DEV-0343, DEV-0346, DEV-0357, DEV-0360, DEV-0362, DEV-0364, DEV-0365, DEV-0366, DEV-0369, DEV-0375, DEV-0379, DEV-0385, DEV-0387, DEV-0389, DEV-0408, DEV-0409, DEV-0420, DEV-0424, DEV-0429, DEV-0431, DEV-0435, DEV-0440, DEV-0446, DEV-0450, DEV-0453, DEV-0464, DEV-0467, DEV-0469, DEV-0474, DEV-0479, DEV-0483, DEV-0485, DEV-0487, DEV-0490, DEV-0491, DEV-0492
- Should have been escalated, but were auto-answered: 65
  - DEV-0002, DEV-0030, DEV-0031, DEV-0039, DEV-0040, DEV-0042, DEV-0051, DEV-0057, DEV-0064, DEV-0067, DEV-0070, DEV-0073, DEV-0082, DEV-0086, DEV-0087, DEV-0095, DEV-0101, DEV-0119, DEV-0128, DEV-0136, DEV-0138, DEV-0147, DEV-0149, DEV-0160, DEV-0170, DEV-0180, DEV-0186, DEV-0220, DEV-0225, DEV-0226, DEV-0232, DEV-0236, DEV-0241, DEV-0266, DEV-0267, DEV-0272, DEV-0274, DEV-0280, DEV-0283, DEV-0284, DEV-0286, DEV-0287, DEV-0291, DEV-0325, DEV-0330, DEV-0339, DEV-0342, DEV-0347, DEV-0349, DEV-0353, DEV-0374, DEV-0384, DEV-0399, DEV-0400, DEV-0406, DEV-0407, DEV-0439, DEV-0442, DEV-0444, DEV-0458, DEV-0460, DEV-0461, DEV-0476, DEV-0480, DEV-0497
- Auto-answers that did not cite an expected article: 13
  - DEV-0001, DEV-0008, DEV-0075, DEV-0090, DEV-0198, DEV-0223, DEV-0233, DEV-0256, DEV-0262, DEV-0281, DEV-0350, DEV-0416, DEV-0451
- Must-not tickets auto-answered (must be 0): 0
  - (none)

## Recurring issues (checked against what we already know)

- 'No article covers' escalations: 64; of those with predicted intent data_residency or DOC-DATA-003 retrieved: 17 (DEV-0058, DEV-0059, DEV-0061, DEV-0110, DEV-0118, DEV-0123, DEV-0135, DEV-0154, DEV-0208, DEV-0275, DEV-0289, DEV-0292, DEV-0309, DEV-0317, DEV-0389, DEV-0432, DEV-0492).
- Urgency right: 240/500 = 48% (known gap; priority.py is still not called by the runner).
- Second-article citing: extra (related) sources kept 1; auto-answers that cited all expected articles among those expecting 2+: 0/54 = 0% (known unused related-source gap).
- Tickets labelled not answerable from docs: 143; in this run auto-answered 57, escalated 86. Auto-answering these is usually a miss; IDs: DEV-0002, DEV-0030, DEV-0031, DEV-0039, DEV-0040, DEV-0042, DEV-0051, DEV-0057, DEV-0064, DEV-0067, DEV-0070, DEV-0073, DEV-0082, DEV-0086, DEV-0087, DEV-0101, DEV-0119, DEV-0128, DEV-0136, DEV-0138, DEV-0147, DEV-0149, DEV-0160, DEV-0170, DEV-0180, DEV-0220, DEV-0226, DEV-0232, DEV-0236, DEV-0241, DEV-0266, DEV-0272, DEV-0280, DEV-0283, DEV-0284, DEV-0287, DEV-0291, DEV-0325, DEV-0339, DEV-0342, DEV-0347, DEV-0353, DEV-0374, DEV-0384, DEV-0399, DEV-0400, DEV-0406, DEV-0407, DEV-0439, DEV-0442, DEV-0444, DEV-0458, DEV-0460, DEV-0461, DEV-0476, DEV-0480, DEV-0497.
- Identical-body groups whose labels disagree (route, expected articles, or must-not): 55 groups. These are a known label conflict (including residency twins); do not retune the system to chase them.
  - DEV-0015, DEV-0210, DEV-0254, DEV-0370
  - DEV-0026, DEV-0055
  - DEV-0027, DEV-0066, DEV-0201, DEV-0430
  - DEV-0033, DEV-0069, DEV-0220
  - DEV-0034, DEV-0242, DEV-0407
  - DEV-0035, DEV-0327
  - DEV-0040, DEV-0163, DEV-0315, DEV-0386, DEV-0473
  - DEV-0041, DEV-0112, DEV-0454
  - DEV-0042, DEV-0127, DEV-0339, DEV-0345, DEV-0423
  - DEV-0046, DEV-0200
  - DEV-0051, DEV-0119, DEV-0145
  - DEV-0058, DEV-0123
  - DEV-0059, DEV-0118, DEV-0433, DEV-0492
  - DEV-0061, DEV-0292, DEV-0389
  - DEV-0064, DEV-0138, DEV-0172
  - DEV-0065, DEV-0087, DEV-0447
  - DEV-0068, DEV-0137
  - DEV-0073, DEV-0151
  - DEV-0076, DEV-0103
  - DEV-0078, DEV-0189
  - DEV-0086, DEV-0130
  - DEV-0092, DEV-0203
  - DEV-0096, DEV-0424
  - DEV-0102, DEV-0146, DEV-0231
  - DEV-0105, DEV-0307
  - DEV-0108, DEV-0272, DEV-0375
  - DEV-0109, DEV-0191, DEV-0248, DEV-0498
  - DEV-0115, DEV-0337, DEV-0354
  - DEV-0124, DEV-0223, DEV-0325
  - DEV-0128, DEV-0143, DEV-0277
  - DEV-0141, DEV-0235
  - DEV-0147, DEV-0297, DEV-0404, DEV-0412
  - DEV-0155, DEV-0305, DEV-0417, DEV-0450
  - DEV-0156, DEV-0399
  - DEV-0166, DEV-0177, DEV-0434
  - DEV-0167, DEV-0264, DEV-0368, DEV-0482
  - DEV-0176, DEV-0281
  - DEV-0181, DEV-0314
  - DEV-0182, DEV-0217, DEV-0320, DEV-0384
  - DEV-0186, DEV-0495
  - DEV-0199, DEV-0455, DEV-0457
  - DEV-0204, DEV-0286
  - DEV-0240, DEV-0391, DEV-0470
  - DEV-0251, DEV-0462
  - DEV-0261, DEV-0291, DEV-0406
  - DEV-0270, DEV-0294
  - DEV-0280, DEV-0353, DEV-0442, DEV-0449
  - DEV-0287, DEV-0367
  - DEV-0312, DEV-0335
  - DEV-0318, DEV-0347
  - DEV-0319, DEV-0369
  - DEV-0322, DEV-0349
  - DEV-0382, DEV-0414
  - DEV-0387, DEV-0476
  - DEV-0416, DEV-0480
- Generic reference replies (79 of 200 answer-key replies share the same placeholder text, recorded earlier) are a limit of the ground truth, not something this run measures. They are mentioned here only as context when reading answer-key scores.

## Calls, latency, and cost estimate

- AI calls: 1719 (1719 ok); mean 1.70 s per call
  - 1719  claude-haiku-5-5
- Ticket latency: mean 5.9 s; median 5.5 s; p95 9.8 s (500 of 500 tickets timed)
- Cost estimate (ESTIMATE ONLY, not a bill; the results file has no token usage): about $0.65 to $2.58.
  - Scaled from the official 80-ticket holdout estimate band of $0.10–$0.40 (266 calls) in docs/HOLDOUT_RESULT.md, using the larger of ticket scale ×6.25 and call scale ×6.46.
  - List prices used there: Haiku 5.5 $0.10/MTok input and $0.50/MTok output (prompts up to 100k, 20 Nov). Thinking tokens are billed as output and are the main uncertainty, even at effort low. This is not a receipt.
