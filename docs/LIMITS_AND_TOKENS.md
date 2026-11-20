# LLM provider limits and token estimates

Written on 19 Nov 2026 (Asia/Calcutta) for the CloudServe capstone. This file records the official free-tier limits we work under, the speeds and model use we have actually measured, and a rough estimate of tokens per ticket.

It is written in plain English. Every measured figure comes from the result files named below, or from official provider pages checked on 19 Nov 2026. Estimates are labelled as estimates. This file does not contain API keys, and it never should. The holdout file was not opened and is not used here.

## 1. The model chain

The system tries models in this order. The first is on OpenRouter. The other three are Groq backups, used only if the one before it fails (for example a timeout, an error, or a rate limit).

| Order | Provider | Model id | Role |
| --- | --- | --- | --- |
| 1 | OpenRouter | `nvidia/nemotron-3.5-lightning:free` | Primary |
| 2 | Groq | `openai/gpt-oss-20b` | First backup |
| 3 | Groq | `openai/gpt-oss-120b` | Second backup |
| 4 | Groq | `qwen/qwen3.8-27b` | Last backup |

These ids and this order are what `src/llm.py` is set to on 19 Nov 2026.

Each model is called with temperature 0, a 20 second timeout, and at most one retry (`max_retries=1`). If a model fails, the next one is tried. For the Qwen model, `reasoning_format` is set to `hidden`, so any chain-of-thought text is kept out of the reply the rest of the code reads.

`src/run.py` then adds a safety net around the whole ticket:

- If no model answers (`model_used` is `none`), the run waits 30 seconds, then 60, then 120, and tries the ticket again after each wait.
- If it still has no model, the ticket is escalated with the reason "AI service unavailable, sent to a person".
- If 3 tickets in a row have no model, the provider is treated as down. Later tickets in that run are escalated without those extra waits.
- Any unexpected error on one ticket is escalated as a "system error". The run continues with the next ticket.
- There is a 3.5 second pause between tickets, to stay under per-minute request limits. That pause is between tickets, not between the several model calls inside one ticket.
- Replies are cached locally in `storage/llm_cache.db`. A later ticket with the same prompt can be answered from this cache without a new provider call. `storage/` stays in `.gitignore`.

`model_used` on a result record is taken from the **classify** step only. Later steps on the same ticket (draft, review, and so on) may have used a backup model if the first one failed mid-ticket. We do not record that. The "Models used" counts in the metrics report are this classify-step field.

## 2. Official free-tier limits

Checked on **19 Nov 2026**. Exact source URLs are at the end of this file. Limits can change, so re-check those pages before the final run.

### OpenRouter, free model variants (ids ending in `:free`)

From OpenRouter's limits page:

| Credits purchased (all time) | Requests per minute | Requests per day |
| --- | --- | --- |
| Less than 10 | 20 | 50 |
| At least 10 | 20 | 1,000 |

This project is set up to stay on free tiers and not buy OpenRouter credits, so the **50 requests per day** row is the one that applies.

Other official points from the same page, and from OpenRouter's pricing FAQ, checked on the same day:

- The limits apply to model ids that end in `:free`. The daily counter to watch is `free_model_daily_requests` on `GET /api/v1/key`.
- Making extra accounts or API keys does not raise the limit.
- The pricing FAQ states that failed attempts count toward the daily cap, and that the daily number rises to 1,000 once the account has bought at least $10 of credits. The limits page describes the same threshold as "at least 10" credits purchased, and says the higher ceiling starts one credit below that (currently 9 credits).
- The limits page does not publish a token cap for free models. Only request caps are listed there.
- I could not confirm, from those official pages, the exact clock time at which the free-model daily counter resets. Related counters on the same docs are described as a UTC day, and key-management limits reset at 00:00 UTC, but that is not the same as a stated reset time for free-model requests.

A small helper, `src/check_limits.py`, can print how many free OpenRouter requests are left today. It does not print the key.

### Groq, for the three backup models

From Groq's rate-limits page, checked on 19 Nov 2026, these figures are published for the three models we use:

| Model id | Requests per minute (RPM) | Requests per day (RPD) | Tokens per minute (TPM) | Tokens per day (TPD) |
| --- | --- | --- | --- | --- |
| `openai/gpt-oss-20b` | 30 | 1,000 | 8,000 | 200,000 |
| `openai/gpt-oss-120b` | 30 | 1,000 | 8,000 | 200,000 |
| `qwen/qwen3.8-27b` | 30 | 1,000 | 8,000 | 200,000 |

The same Groq page also says:

- This table is a high-level summary, and there may be exceptions.
- The exact limits for an account are on the limits page in that account's console. We cannot open this project's Groq console from here, so the figures above are the published table, not a confirmed readout of this account.
- The page also says "the limits shown below are the base limits for the Developer plan." Because of that wording, these numbers should be treated as what the public table showed on 19 Nov 2026, not as a separately confirmed "Free plan" label.
- Limits apply at the organisation level, not per API key. Extra keys do not add a second allowance.
- Cached tokens do not count toward the limits.
- You can hit whichever cap you reach first (requests or tokens, per minute or per day).

The draft step sends two full knowledge-base articles, not just the matched section. A comment in `src/pipeline.py` says this is to stay under Groq's token cap.

## 3. Measured usage from our runs

Two result files were on the box and were recomputed for this write-up. Batches 1 to 3 and the `dev_other50` run were not on the box, so they are not included. No new model calls were made.

| Run | Tickets | Prompt versions | File | Wall-clock time |
| --- | --- | --- | --- | --- |
| Batch 4 (dev200_04) | 50 | PR-01 1.2, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1 | `analysis/results/dev200_04.json` | Start and finish were not stored in the results file. The metrics report for this run was not on the box. |
| T11 residency check | 29 | PR-01 1.3, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1 | `analysis/results/t11_residency29.json` | Started 19 Nov 2026, 09:32, finished 09:53 (20.8 min), Asia/Calcutta, from Amol's metrics report. That duration matches the sum of measured ticket times plus the 3.5 s pauses. |

Latency is the ticket's `latency_ms` field: end-to-end time inside `process()`, including retrieval, in milliseconds. The median (p50) and 95th percentile (p95) use the same method as the A10 report: a straight line between the two nearest values (linear interpolation). Records with no measured time (code fallbacks) would be left out; **neither of these runs had any**, so all tickets are included. The 3.5 second pause between tickets is not inside `latency_ms`.

### Models used (classify step)

| Run | `nvidia/nemotron-3.5-lightning:free` | `openai/gpt-oss-20b` | `openai/gpt-oss-120b` | `qwen/qwen3.8-27b` | `none` |
| --- | --- | --- | --- | --- | --- |
| Batch 4 | 0 | 13 | 24 | 13 | 0 |
| T11 | 23 | 4 | 2 | 0 | 0 |

Batch 4 ran entirely on the Groq backups. OpenRouter's daily free limit had already been used up that day, so Nemotron was not available. Every ticket still got a model: 0 "AI service unavailable", and 0 system errors.

On the T11 run, OpenRouter quota was available again: Nemotron classified 23 of 29 tickets.

### Latency, whole run

Times are in seconds, rounded to one decimal place, which is how the metrics reports print them.

| Run | Tickets timed | Mean | Median (p50) | p95 | Fastest | Slowest | Brief's target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Batch 4 | 50 of 50 | 17.9 s | 15.3 s | 39.3 s | 2.1 s | 83.0 s | p95 under 3 s |
| T11 | 29 of 29 | 39.6 s | 48.3 s | 83.5 s | 0.018 s | 90.3 s | p95 under 3 s |

Neither run meets the brief's p95 target of under 3 seconds, measured end to end including retrieval.

### Latency by model

Same method, grouped by `model_used` (the classify model). Small groups (2 or 4 tickets) are shown for completeness; a p95 on so few tickets is not a stable figure.

**Batch 4**

| Model | Tickets | Mean | p50 | p95 | Fastest | Slowest |
| --- | --- | --- | --- | --- | --- | --- |
| `openai/gpt-oss-20b` | 13 | 18.7 s | 19.2 s | 33.9 s | 2.1 s | 36.9 s |
| `openai/gpt-oss-120b` | 24 | 17.1 s | 14.1 s | 29.6 s | 3.0 s | 61.0 s |
| `qwen/qwen3.8-27b` | 13 | 18.8 s | 10.8 s | 57.9 s | 2.9 s | 83.0 s |

**T11**

| Model | Tickets | Mean | p50 | p95 | Fastest | Slowest |
| --- | --- | --- | --- | --- | --- | --- |
| `nvidia/nemotron-3.5-lightning:free` | 23 | 46.4 s | 50.7 s | 84.1 s | 0.018 s | 90.3 s |
| `openai/gpt-oss-20b` | 4 | 12.5 s | 13.3 s | 20.5 s | 2.7 s | 20.8 s |
| `openai/gpt-oss-120b` | 2 | 16.4 s | 16.4 s | 18.4 s | 14.3 s | 18.6 s |

On the T11 run, five tickets finished in 18 to 25 milliseconds (DEV-0123, DEV-0309, DEV-0359, DEV-0389, DEV-0433). That is far too fast for a live model call. They were almost certainly answered from the local LLM cache. The official p50 and p95 above include them, because the A10 report includes every ticket with a measured time. If those five are left out, the remaining 24 tickets have a mean of 47.9 s, a median of 50.7 s, and a p95 of 84.0 s. The 18 live Nemotron tickets (the 23 minus those five) have a mean of 59.3 s, a median of 55.3 s, and a p95 of 85.3 s. So the cache hits pull the T11 average down, but they do not hide the p95 problem.

Nemotron, when it is actually called, is slower in these runs than the Groq backups. That is why T11's p95 (83.5 s), with most tickets on Nemotron, is worse than batch 4's p95 (39.3 s), which ran only on Groq.

### Steps and model calls per ticket

These steps always run: `prepare` (no model) and `classify` (one model call). If the ticket is not stopped by an early rule, the system then runs `retrieve` (no model; this is the knowledge-base search), `draft` (one model call), and, if a draft was written, `review` (one model call). Escalated tickets also get `impact` and `escalation_summary` (one model call each). A ticket escalated because it is unclear also gets `clarify` (one model call). There were no `clarify` steps in these two runs.

So a typical auto-answer uses **3 model calls** (classify, draft, review). An escalation uses 3 to 5, depending on whether a draft and a review were also produced.

| Run | Auto-answered (always 3 calls) | Escalated | Mean calls per ticket | Total model-call steps |
| --- | --- | --- | --- | --- |
| Batch 4 | 40 of 50 | 10 (8 with 3 calls, 1 with 4, 1 with 5) | 3.06 | 153 |
| T11 | 24 of 29 | 5 (3 with 4 calls, 2 with 5) | 3.24 | 94 |

Step patterns:

| Steps that include a model call | Batch 4 | T11 |
| --- | --- | --- |
| classify, draft, review | 40 | 24 |
| classify, impact, escalation_summary | 8 | 0 |
| classify, draft, impact, escalation_summary | 1 | 3 |
| classify, draft, review, impact, escalation_summary | 1 | 2 |

## 4. Token estimates

These are **estimates**, not measured tokenizer counts. Providers did not return token counts in the result files we have.

**Method.** For each ticket in the two runs, the prompt files were filled with that ticket's subject, body and tier, and with the articles actually retrieved or cited. The character count of each filled prompt was divided by 4. That is a common rough rule for English text, not a real tokenizer. Output sizes are a lower bound: they use the draft text and the short JSON fields we stored, not the raw model reply, and they do not include any hidden reasoning tokens the provider may also count.

Prompt files used: `prompts/pr01_classify_v1.3.txt` (and v1.2 for the batch 4 reconstruct), `pr05_answer_v1.1.txt`, `pr04_review_v1.0.txt`, `pr03_impact_v1.1.txt`, `pr06_escalation_v1.0.txt`, and `pr02_clarify_v1.0.txt`. Ticket text came from the development samples, not the holdout. Article text came from the knowledge-base file `documentation.json` (29 articles; body text from about 860 to 1,336 characters each).

### Estimated size of each kind of call

Figures below are mean estimated input tokens (characters ÷ 4) from the T11 run, which uses the current PR-01 1.3 classify prompt. Batch 4 is similar except that its classify prompt (v1.2) is a little shorter.

| Call | When it runs | Template file | Estimated input tokens (mean) | Visible output (lower bound, mean) |
| --- | --- | --- | --- | --- |
| Classify (PR-01) | Every ticket | v1.3: 6,798 characters (~1,700 tokens as a template) | about 1,740 | about 30 |
| Draft (PR-05) | When the early rules do not already escalate | 2,591 characters (~650 tokens as a template), plus two full articles | about 1,250 | about 110 |
| Review (PR-04) | When a draft was written | 1,996 characters (~500 tokens as a template), plus one article and the draft | about 880 | about 10 |
| Impact (PR-03) | Every escalation | 1,973 characters (~490 tokens as a template) | about 530 | not measured as raw text |
| Escalation summary (PR-06) | Every escalation | 2,183 characters (~550 tokens as a template) | about 590 | not measured as raw text |
| Clarify (PR-02) | Only unclear escalations | 1,846 characters (~460 tokens as a template) | not seen in these two runs | not seen |

The draft call is large because it includes two full articles (together about 2,200 characters of article body, plus titles). The classify call is large because the PR-01 1.3 instruction file itself is long. Ticket subject and body are short (typically about 160 to 170 characters in these samples).

### Estimated tokens per ticket and per 50 tickets

Input tokens only, characters ÷ 4, plus a smaller visible-output lower bound where we have it.

| | Mean input tokens per ticket | Mean model calls | Estimated input tokens for 50 tickets | Estimated calls for 50 tickets |
| --- | --- | --- | --- | --- |
| Batch 4 mix (40 auto-answers, 10 escalations) | about 3,570 | 3.06 | about 178,000 (this actual 50-ticket run) | 153 (measured step count) |
| Batch 4 auto-answer only | about 3,700 | 3.00 | about 185,000 | 150 |
| T11 mix, projected to 50 | about 3,980 | 3.24 | about 199,000 | about 162 |
| T11 auto-answer only | about 3,870 | 3.00 | about 194,000 | 150 |

Adding the visible classify, draft and review outputs we can see (a lower bound) adds only about 130 tokens per ticket in batch 4, and about 140 in T11. The real number may be higher if a provider also counts hidden reasoning tokens. We did not measure those.

### How many tickets fit in a day's free limits

These conversions use the official request and token caps from section 2, and the estimates above. They are planning figures, not a guarantee.

**OpenRouter, 50 requests a day (no purchased credits), 20 requests a minute.**

- A typical auto-answer needs 3 live requests. 50 ÷ 3 = **16 auto-answer tickets** in a day, if every call goes to Nemotron and succeeds.
- Escalations can need 4 or 5 calls, so the day would hold fewer tickets.
- A 50-ticket batch at the rates we measured needs about 150 to 160 model calls. That is about three days of OpenRouter free quota, or more if failed attempts also count (the pricing FAQ says they do).
- That matches what we saw: batch 4 could not use Nemotron at all, because the daily free limit was already exhausted, and the 50 tickets were served by Groq instead.
- The 20-requests-per-minute cap is less tight than the daily cap for our pacing. One ticket's 3 to 5 calls, then a 3.5 second pause, stays well under 20 in a minute, unless many retries pile up.

**Groq, per model: 1,000 requests a day and 200,000 tokens a day; 30 requests and 8,000 tokens a minute.**

- If only the request cap mattered, 1,000 ÷ 3 ≈ **330 auto-answer tickets** per model per day.
- If the token cap matters, and a ticket uses about 3,700 to 4,000 input tokens plus some output, then 200,000 tokens would cover on the order of **about 45 to 50 tickets per model per day**. That is only an estimate, and it would be lower if hidden reasoning tokens are counted. On this estimate the **daily token cap binds first**.
- The 8,000 tokens-per-minute cap: one ticket at about 4,000 tokens is under it. Two tickets squeezed into the same minute would be close. The 3.5 second pause, plus the time each ticket already takes, usually spaces them out. The choice to send only two articles is meant to keep a single draft call inside this cap.
- The three Groq models have separate published caps. In batch 4 the 50 tickets were spread across all three (13, 24 and 13 at the classify step) and the run finished with no "AI service unavailable" records. So **a 50-ticket day on the Groq backups is possible**. We have measured that. We have not measured a larger Groq-only day, so we should not claim a higher number as fact.

We did not receive provider request or token counters in the result files, so we cannot say exactly how many OpenRouter or Groq requests the T11 run consumed. Five of those 29 tickets were almost certainly cache hits and would not have counted against a provider cap.

## 5. Implications

1. **The brief's latency target is not met on these free tiers.** The target is a p95 under 3 seconds, measured end to end, including retrieval. Batch 4, all on Groq, had a p95 of 39.3 seconds. T11, mostly on Nemotron, had a p95 of 83.5 seconds. Even the faster Groq tickets in these files are usually well above 3 seconds.

2. **The planned final (holdout) run may use Amol's paid Claude or Grok credits as a latency observation.** That would be a one-time exception to the free-tier rule, for speed, and only after the rest of the work is frozen. The model choice must be decided and written down in `docs/DECISIONS.md` **before** the holdout is run. The holdout is run once, near the end. It must not be opened or used for tuning before that. The speed difference should be recorded in the write-up as an observation, next to the free-tier figures in this file.

3. **A 50-ticket batch does not fit in one day of OpenRouter free quota.** Plan on Groq backups once the 50 requests are gone, or split a large run across days. Check remaining OpenRouter free requests with `src/check_limits.py` before starting. Failed OpenRouter attempts may still count toward the 50.

4. **Keep the laptop awake for the whole run.** Results are saved after every ticket, but a sleep or shutdown still interrupts the batch. The T11 run of 29 tickets took 20.8 minutes (Asia/Calcutta). A 50-ticket run at batch 4's average of 17.9 seconds, plus the 3.5 second pauses, would be on the order of 18 minutes of processing, and longer if Nemotron is serving most tickets.

5. **Re-check the official pages before the final run.** The figures in section 2 are what those pages showed on 19 Nov 2026. Providers can change free-tier caps.

## 6. What this file could not confirm

- The exact free-model daily reset time on OpenRouter (see section 2).
- The exact Groq caps on this project's account (the public table has caveats, and we cannot see the console).
- Token counts from a real tokenizer, or hidden reasoning tokens.
- How many provider requests each run actually made. We only have classify-step `model_used`, the step list, and local latency.
- Whether later steps of a ticket sometimes used a different model from classify.
- Latency and model mix for batches 1 to 3 and `dev_other50` (those result files were not on the box).
- Start and finish clock times for batch 4 (the metrics report was not on the box).
- Whether a paid Claude or Grok model will meet the 3 second p95 target. That is the point of the planned observation, and it has not been run yet.

## Sources

Official pages, checked 19 Nov 2026:

- OpenRouter limits: https://openrouter.ai/docs/api_reference/limits
- OpenRouter pricing FAQ (free-model caps, failed attempts, $10 credit threshold): https://openrouter.ai/pricing
- Groq rate limits: https://console.groq.com/docs/rate-limits

Measured result files (working copies):

- `/workspace/capstone/analysis/results/dev200_04.json` (batch 4)
- `/workspace/capstone/analysis/results/t11_residency29.json` (T11 residency check)

Code and prompts used to describe the chain, the retries, and the token estimates: `src/llm.py`, `src/run.py`, `src/pipeline.py`, `src/classify.py`, `src/answer.py`, `src/review.py`, `src/impact.py`, `src/escalate.py`, `src/clarify.py`, and the prompt files listed in section 4. The knowledge-base sizes came from `documentation.json`. The brief's p95 target of under 3 seconds, measured end to end including retrieval, is the target already used in the A10 metrics report.
