# Stage 1: Discovery (working draft)

**Output of this stage → input to Stage 2 (PRD).** Every PRD requirement must cite an evidence ID below (E-xx, I-xx).

Source: `data/development_tickets.json` (500 tickets), analysed in `notebooks/01_ticket_analysis.ipynb`, 2 Nov 2026.

## 1. Data evidence

| ID | Finding | Evidence | Implication for design |
|---|---|---|---|
| E-01 | Channel mix: email 42%, chat 31%, docs comments 16%, forum 11% | value_counts | Ingest must normalise 4 channels; chat tickets have no subject |
| E-02 | Tiers: standard 51%, business 33%, enterprise 17% | value_counts | Fairness audit by tier; `applies_to` plan scope matters |
| E-03 | 24% of tickets are non-fluent English (broken grammar) | value_counts + sample tickets | Classifier must handle non-fluent text; fairness segment |
| E-04 | 22 intents, fairly even (2.6%–5.8%); smallest: rate_limit, unclear_request | value_counts | No shortcut via a few big classes; watch per-class recall on small ones |
| E-05 | Urgency: medium 45%, high 29%, low 26% | value_counts | Urgency must be predicted, not defaulted |
| E-06 | Expected route: 62% auto-respond, 38% escalate | value_counts | Automation ceiling is ~62%; escalation is normal, not failure |
| E-07 | 4 intents always escalate (must_not_auto_respond): compliance_request 26, security_incident 26, feature_request 20, unclear_request 15 = 87 (17.4%); 0 in all other intents | crosstab | **Hard rule: escalate on these intents regardless of confidence.** Classifying them is safety-critical |
| E-08 | Compliance and security tickets are often answerable from docs (17 and 14) but must still escalate | crosstab | "A doc exists" ≠ "safe to answer" |
| E-09 | 97 tickets (~19%) in normal intents have no matching article | crosstab | Retrieval needs a "no good match" signal → escalate; don't force an answer |
| E-10 | E-07 + E-09 = 184 ≈ 189 expected escalations | arithmetic | Routing ≈ (always-escalate intent) OR (no answerable doc) OR (low confidence) |
| E-11 | Same customer_id (CUST-1059) with two different names | sample rows | Data-quality question: shared accounts or bad data? Don't identify by name |

**Verified against the Dataset Guide:** channel order, tier split, ~25% non-fluent, ~75% answerable (actual 71%), ~2/3 auto-respond (actual 62%): all hold.

## 2. Baseline (history block): TO DO
CSAT, resolution time, first-contact resolution, repeat contact, overall and by tier/fluency.

## 3. Stakeholder interviews: TO DO
| ID | Stakeholder | Need / pain point | Quote | Links to evidence |
|---|---|---|---|---|

## 4. Assumptions and open questions raised in discovery
- Q-01: Validation-set rule conflict (Dataset Guide: use freely; Brief: run once). **Working rule:** build on the 500, run the 80 at checkpoints/end only.
- Q-02: Guide says "eight categories" but lists 10; JSON has 10.
- Q-03: `last_reviewed_days_ago = 0` for all docs: fresh, or never filled in?
- Q-04: Submission deadline in docs (13 Sept) vs actual (15 Nov), to confirm in writing.

## 5. Problem statement: TO DO (written last, from sections 1–3)
