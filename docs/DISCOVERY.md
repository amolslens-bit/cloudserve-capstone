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
| E-13 | 79 of the 200 answer-key reference replies are one identical generic text with empty must_mention. | Testing | Late Discovery, So this is not factored in design.|
| E-16 | labels conflict with each other in Data | Testing Phase | This is a Data Problem and not Model problem |

**Verified against the Dataset Guide:** channel order, tier split, ~25% non-fluent, ~75% answerable (actual 71%), ~2/3 auto-respond (actual 62%): all hold.

## 2. Baseline (AS-IS, history block)

| ID | Measure | Overall | Enterprise | Business | Standard | Fluent | Non-fluent |
|---|---|---|---|---|---|---|---|
| E-12 | CSAT (1–5) | 2.97 | 3.05 | 2.91 | 2.98 | 2.95 | 3.04 |
| | Resolution time (min) | 421.7 | 483.7 | 358.8 | 442.1 | 407.7 | 466.1 |
| | First-contact resolution | 44% | 37% | 48% | 43% | 43% | 46% |
| | Repeat contact | 22% | 24% | 23% | 20% | 22% | 19% |
| | Escalated | 56% | 63% | 52% | 57% | 57% | 54% |

Insights (E-12):
- Low satisfaction overall (2.97/5) and slow fixes (~7 h).
- Enterprise, the top tier, gets the slowest and least first-time-resolved service.
- Humans escalate 56%, but labels say only 38% need it (E-06): ~18 points avoidable.
- Non-fluent customers wait ~58 min longer; other measures similar.
These AS-IS numbers are what the PRD success metrics (TO-BE) must beat.

## 3. Stakeholder interviews (source: Stakeholder Interviews PDF, read 3 Nov 2026)
| ID | Stakeholder | Need / pain point | Quote | Links to evidence |
|---|---|---|---|---|
| I-01 | Marcus (Head of Support) | FCR is the number that matters; a wrong answer is the worst failure; must be explainable for compliance review; enterprise must not get worse | "I would rather it said nothing than said something wrong." | E-12 (FCR 44%) |
| I-02 | Sofia (Tier 1) | Answers are known but docs are hard to search; escalates when not confident; wants a draft + cited page, not blind auto-send | "The documentation is fine. I cannot find things in it." | 71% answerable vs 44% FCR |
| I-03 | Daniel (Tier 2) | ~half of escalations avoidable; escalations arrive with no context; don't learn from old snippets; money, security, data location stay human | "I do not need it to be right. I need it to show its working." | E-06, E-07, E-12 |
| I-04 | Ines (Tech writer) | Keyword search can't bridge customer words to article titles; private snippets unreviewed; needs citation to tell article error from system error | "There is no path between those two phrases in a keyword search." | E-09, decision log retrieved_docs |
| I-05 | Ravi (Customer) | Wait cost depends on impact, not age; wants disclosure when AI drafted; no confident wrong answers; tier gap must not grow | "Same queue, completely different cost to me." | E-05 (urgency), E-12 |

### Disagreements settled with data
| ID | Claim | Data says | Verdict |
|---|---|---|---|
| X-01 | Sofia: non-fluent tickets have the worst satisfaction | CSAT non-fluent 3.04 vs fluent 2.95; but wait +58 min | Half right: slower, not less satisfied |
| X-02 | Daniel: ~half of escalations are avoidable | 56% escalated vs 38% needed = ~1/3 avoidable | Direction right, size overstated |
| X-03 | Ravi: enterprise gets answers in ~1 hour | Enterprise slowest (484 min) and lowest FCR (37%) | Contradicted |
| X-04 | Marcus: FCR 42% | 44% | Close; from memory, not data |

### Open questions from interviews
- Q-05: No first-response time in data; Marcus's 8–12 h (vs 2 h SLA) cannot be verified. Assumption: "Kept as an assumption; latency measured instead (NFR-01)."
- Q-06: Are billing disputes marked must_not_auto_respond? Daniel wants them human-only; check data.**Resolved : billing disputes are handled by the dispute/commitment code gate (escalate), not by the must_not label. **


## 4. Assumptions and open questions raised in discovery
- Q-01: Validation-set rule conflict (Dataset Guide: use freely; Brief: run once). **Working rule:** build on the 500, run the 80 at checkpoints/end only.
- Q-02: Guide says "eight categories" but lists 10; JSON has 10.
- Q-03: `last_reviewed_days_ago = 0` for all docs: fresh, or never filled in after update?
- Q-04: Submission deadline in docs (13 Sept) vs actual (15 Nov), to confirm in writing.Resolved:22 Nov confirmed.
- Q-07: Assumption for Q-03: treat all 29 articles as current, but log the cited article on every answer so a stale one can be traced.

## 5. Problem statement (ordinary → extraordinary)
**Ordinary (as stated by client):** CloudServe has low first-contact resolution (42–44% vs 65% benchmark) and misses its 2-hour first-response agreement (8–12 h) despite extra hires and a canned response library.

### Extraordinary framing via the 6-step framework
1. Original: "Help us answer tickets faster with a chatbot" (Marcus).
2. Levers applied: Data liquidity (71% of tickets answerable from 29 unused articles; urgency signal ignored); Network effects (each tier-2 resolution should improve answers for every later customer; today it never flows back); Algorithmic leverage (encode tier-1 pattern-matching and the escalate/answer judgment).
3. Rewrite: How do we use the answers CloudServe already has to resolve tickets at first contact, encode when it is safe to answer, and turn every escalation into knowledge that resolves the next similar ticket, and the recurring causes that create them?
4. Equation: Resolution = (Tickets + 29 articles x Routing judgment) ^ Feedback from every resolved escalation.
5. First principles: most tickets are already-solved questions, not new problems. JTBD: customers don't want a reply, they want to keep shipping; agents want a trusted, cited draft.
6. Extraordinary problem: CloudServe already holds the answer to ~71% of tickets in 29 reviewed articles, yet only 44% are resolved at first contact and 56% are escalated when only 38% need it. Articles are titled in technical language while customers write in business language, so tier-1 agents can't find them, can't trust their own drafts, and escalate without context, where tier 2 restarts discovery. What tier 2 learns never flows back into the articles, so private, unreviewed snippets replace the standard answer. And the queue is worked by age, not impact, so an outage waits behind a pagination question. Each avoidable escalation costs ~4x a resolved ticket. Each resolved escalation should feed back as reviewed knowledge, and recurring root causes should be reported so CloudServe can remove them at source.

Scope note: build the support system (brief); prevention appears as a recurring-root-cause report, not a full product change (D12).
