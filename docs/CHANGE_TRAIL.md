# Change trail: from testing finding to PRD v2 to code

Working list for PRD v2 (Stage 5). Each row shows what testing found, the evidence,
what changes in the PRD, and what changed in the code. When PRD v2 is written, each
"PRD v2 change" becomes one line in the PRD Revision Log, and each design choice gets
a DECISIONS.md entry (next free D-number) with the why and the alternatives.

Status: **Done** = code changed and tested. **Proposed** = waiting for Amol's yes.
**Open** = Amol to decide. **To do** = agreed, not built yet.

## A. Findings from building and testing (16 and 17 Nov 2026)

| # | Date | What testing showed | Evidence | PRD v2 change | Code change | Status |
|---|------|---------------------|----------|---------------|-------------|--------|
| T1 | 16 Nov | The answer step (PR-05) said "not covered" on 4 of 5 tickets even though search had found the right article, because it was only given the one matching section | 5-ticket test: 1/5 before, 5/5 after sending the whole article | FR-07 / FR-08: the answer is drafted from the whole reviewed article, not a matching fragment | `answer.py` sends the full article text; PR-05 change history updated | Done |
| T2 | 16 Nov | When both models failed, classification crashed the run | Traceback on ticket 7 of the classify test | None: NFR-02 already says "send the ticket to a person"; the code now meets it | `classify.py` catches the error and returns a safe "unclear" result that goes to tier 1 | Done |
| T3 | 16 Nov | OpenRouter's free models allow only 50 requests a day for an account that has never bought credits (20 a minute). That is far below what a run needs | OpenRouter key check: used 52, limit 50, credits never bought | NFR-07 / NFR-02 / A-04: A-04 ("free tiers are fast and reliable enough") failed for OpenRouter alone; the model chain relies on Groq for volume | Caching (T4); longer fallback chain (T5) | Partly done |
| T4 | 17 Nov | Re-running the same prompt wasted the daily allowance | Build Spec section 7: "Caching is encouraged". Test: 2nd identical call took 0.00 s, no AI call | Design note under NFR-07: model replies are cached; a changed prompt always makes a fresh call | `llm.py`: SQLite cache in `storage/llm_cache.db` (kept out of Git) | Done |
| T5 | 16 Nov | One Groq backup model may not cover a whole run | Groq docs: gpt-oss-20b, gpt-oss-120b, qwen3.8-27b each list 1K requests a day | NFR-02, D7/D8: name the full chain and the "Model used" line in the prompt register | `llm.py`: add the extra Groq models as further fallbacks | Open: confirm limits on Groq console first |
| T6 | 17 Nov | The graded run is one command on a file we never see (80 to 120 tickets), with no restarts and no skipped tickets. The old runner stopped after 3 failures | Build Spec A9, section 04 | NFR-02: when both models fail, wait and retry, then escalate with the reason "AI service unavailable"; the run never stops. Add the one-command rule | `run.py`: input and output paths, retries 30/60/120 s, never stops, logs every ticket | Done, tested on 5 tickets |
| T7 | 17 Nov | The metrics report must appear without manual work | Build Spec A10 | NFR-03 / NFR-05 verification: the run writes the report and checks the log matches the ticket count | `run.py` writes `<output>_metrics.md` | Done, tested |
| T8 | 17 Nov | NFR-03 says to measure on all 500 dev tickets, but the free tier can't run 500 quickly, and the brief never asks for 500 in one go | Build Spec section 04 (hidden set of 120); OpenRouter limit (T3) | NFR-03 and Section 8 measurement: say which tickets are scored and why | `run.py --limit` for development; caching helps re-runs | **Open**: conflicts with the 11 Nov decision to read FCR from one run of all 500 |
| T9 | 16 Nov | Sending several full articles to the answer step uses many tokens, and Groq has a per-minute token cap | Groq 8K tokens a minute | Design note: the answer step reads the top 2 articles | `pipeline.py` uses `retrieve(t, k=2)` | Done; check: 17 Nov output listed 3 retrieved docs |
| T10 | 16 Nov | A feature request (DEV-0392) was classified "unclear" and went to tier 1, not tier 2 | 6-ticket pipeline run | None: FR-05 and the 13 Nov rule already say tier 2 | PR-01 v1.2: clearer feature-request example | To do |
| T11 | 16 Nov | A data-residency question (DEV-0292) was flagged as a data commitment because of the "if unsure, mark true" rule | 6-ticket pipeline run | FR-06: keep as deliberate caution, or tighten the flag | PR-01 flag wording, if tightened | **Open** |
| T12 | 16 Nov | An SSO question (DEV-0033) was judged not covered and escalated | 6-ticket pipeline run | Possibly none (escalating is correct when unsure) | None yet | To check |
| T13 | 17 Nov | A compliance request (DEV-0003, "auditor ... access records") was classified as data export; only the reply review stopped it | 5-ticket `run.py` test. "audit" appears in 33 of 500 dev tickets, all labelled must-not-auto-respond (20 compliance, 13 security) | FR-05: the warning-word list is built from the dev tickets and named | `route.py`: add "audit" to `WARNING_WORDS` | Proposed |
| T14 | 16 Nov | The starter warning-word list barely matches real tickets | Only "breach" matched (10 tickets, all must-not) | Same as T13 | Same as T13 | Proposed |
| T15 | 17 Nov | Two tickets disagree with their labels, and the system looks right | DEV-0001: cited DOC-DEPLOY-003 "Build failures caused by dependency resolution"; label expects DOC-DEPLOY-001 (health checks). DEV-0002: "key returns 401", DOC-AUTH-004 lists exactly that symptom; label says not answerable | None: this is what A-07 predicts. Add them to the hand-review list | None | Logged for report / LEARNINGS.md |
| T16 | 17 Nov | Each ticket takes far longer than 3 seconds | 5-ticket test: average 28.9 s per ticket (free models, 3 to 4 AI calls) | NFR-01: drop or relax the 3 s target (the PRD review flagged this as S6) and keep timing every ticket | None | **Open** |
| T17 | 16-17 Nov | Urgency accuracy is low | 6/10 (classify test), 3/5 (17 Nov) | None yet: target stays 80% until the sample run | PR-01 tuning after the sample run | To do |
| T18 | 16 Nov | The two cut-offs are starting guesses | CLASSIFY 0.60, ANSWER 0.70 | Stage 5: record the values chosen from data | `route.py` after the sample run | To do |

## B. Already agreed before testing (13 to 16 Nov), to apply in the same PRD v2 pass

| # | Item | Where |
|---|------|-------|
| P1 | Missing body, customer ID, tier or region: never auto-answered, tier 1 with the package (D17) | FR-01, FR-07, FR-12. Code: `prepare.py` + `route.py` gate 1 (done) |
| P2 | A customer's reply to a clarifying question is a new message on the same ticket | FR-03 |
| P3 | Each ticket is processed once on arrival; unanswered tickets don't re-enter the AI | FR-11 |
| P4 | FR-04 queue order: impact, then urgency, then waiting time, moving up after a waiting limit | FR-04. Code: not built |
| P5 | Feature requests always go to tier 2 (D15 update) | FR-05, FR-11. Code: `route.py` (done) |
| P6 | Code masks keys, emails and phones before any AI call | NFR-04. Code: `prepare.py` (done) |
| P7 | Groq backup model named as openai/gpt-oss-20b | NFR-02 (may change with T5) |
| P8 | Stage 3 leftovers: what redaction masks and what agents see; PR-08 model; the 11 D14 flag disagreements; PR-03 and PR-05 1.1 versions; the empty Known weakness row; the garbled FR-11 sentence; PR-07 naming Nori 1; FR-08 "every" vs NFR-03 85% | Stage 3 / PRD |
