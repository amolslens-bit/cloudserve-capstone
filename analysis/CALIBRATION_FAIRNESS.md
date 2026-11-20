# Confidence calibration and fairness audit

Computed on 19 Nov 2026 (Asia/Calcutta) from **existing run results only**. No new model calls were made. The holdout file (`pack/HOLDOUT_validation_tickets.json`) was **not opened** and is not used here. Labels from the 500-ticket development file are used only for scoring, never as system inputs.

This write-up is in plain English. Every figure is a count from the files listed below. Where a sample is small, the count is shown so you can see how thin the evidence is.

## Files used

| Run | Tickets | Prompt versions | File used | Where the prompt versions come from |
| --- | --- | --- | --- | --- |
| Batch 4 (dev200_04) | 50 | PR-01 1.2, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1 | /workspace/capstone/analysis/results/dev200_04.json | metrics report for this run (not stored in the results JSON) |
| T11 residency check (29 tickets) | 29 | PR-01 1.3, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1 | /workspace/capstone/analysis/results/t11_residency29.json | metrics report for this run (Started 2026-11-19 09:32, finished 09:53 Asia/Calcutta) |

Labels file (scoring only): `/workspace/capstone/pack/01M6JM77KEQZAB08BHDKG7QACH.json` (500 development tickets).

Working copies used by the script live in `analysis/results/`. They were copied from the original attachments: batch 4 from `.../attachments/e9f7aaeb8d6412d61442db3c8b3f786a11ce42f62541686939e87edd1d510e2f.txt`, and the T11 run from `.../attachments/61f11a2d2c74d20db3055cc71279a5ca29a01549f418877a3552cdb3f291c004.txt`.

### Search for other result files

Folders searched: `/workspace/capstone/analysis/results`, `/workspace/capstone/outputs`, `/workspace/capstone/build/outputs`, `/workspace/capstone/review`, `/workspace/capstone/analysis`.

Batches 1–3 of dev200 and the `dev_other50` run were looked for under `analysis/results/`, `outputs/`, `build/outputs/`, `review/`, and `analysis/`, and in the known attachment copies. **No result files for those runs were on the box**, so they are not in this report. If you still have them on your PC, copy them into `analysis/results/` and add a row to `RUNS` in `calib_fair.py`, then rerun the script.

No other run-result files were found in the searched folders.

## How overlapping tickets were combined

Each run is scored on its own, in the sections below.

For a **combined view**, if the same ticket appears in more than one run, the **latest** run is kept (the T11 residency run is later than batch 4, and uses PR-01 1.3). That is a convenience view only. It mixes two prompt versions and two model mixes, so the per-run tables are the cleaner evidence for each setup.

These ticket ids appear in more than one run: DEV-0433, DEV-0464, DEV-0483, DEV-0489.
In the combined view, the later run is kept for each of them (T11 residency check (29 tickets)).

- DEV-0433: Batch 4 (dev200_04) routed **escalate** (billing dispute or data commitment flagged); T11 residency check (29 tickets) routed **auto_respond** (all checks passed); label is **auto_respond**.
- DEV-0464: Batch 4 (dev200_04) routed **escalate** (billing dispute or data commitment flagged); T11 residency check (29 tickets) routed **auto_respond** (all checks passed); label is **auto_respond**.
- DEV-0483: Batch 4 (dev200_04) routed **escalate** (billing dispute or data commitment flagged); T11 residency check (29 tickets) routed **escalate** (reply review failed or did not run); label is **auto_respond**.
- DEV-0489: Batch 4 (dev200_04) routed **escalate** (billing dispute or data commitment flagged); T11 residency check (29 tickets) routed **auto_respond** (all checks passed); label is **auto_respond**.

Combined unique tickets: **75** (from 50 + 29 records, minus 4 overlap).

This is not a random sample of all 500 development tickets. Batch 4 is the last 50 tickets of a 200-ticket slice. The T11 run is all 29 data-residency tickets. Together they over-represent residency questions.

## Headline numbers

### Combined view (latest run per ticket)

- Unique tickets scored: **75**
- Intent accuracy: **73/75 (97.3%)**
- Route accuracy: **61/75 (81.3%)**
- Auto-answered: **64/75 (85.3%)**
- Escalated: **11/75 (14.7%)**
- Wrong auto-answers: **8** (of which **7** are known T11 residency label conflicts)
- Should have been auto-answered, but were escalated: **6**
- Auto-answered tickets marked must-not-auto-respond: **0** (must be 0; none were)
- Citation accuracy on auto-answered tickets: **53/64 (82.8%)**
- Models in the combined view: 24 openai/gpt-oss-120b, 23 nvidia/nemotron-3.5-lightning:free, 17 openai/gpt-oss-20b, 11 qwen/qwen3.8-27b

After setting aside the 8 known T11 label-conflict tickets (n = 67): intent **65/67 (97.0%)**, route **60/67 (89.6%)**, auto-answered **57/67 (85.1%)**, wrong auto-answers **1**, citation on auto-answered tickets **53/57 (93.0%)**.

## Per-run results

### Batch 4 (dev200_04)

- Prompt versions: PR-01 1.2, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1
- File used: `/workspace/capstone/analysis/results/dev200_04.json`
- Tickets: 50
- Intent accuracy: 48/50 (96.0%)
- Route accuracy: 43/50 (86.0%)
- Auto-answered: 40/50 (80.0%)
- Escalated: 10/50 (20.0%)
- Wrong auto-answers (auto-answered, but the label says escalate): 1
- Should have been auto-answered, but were escalated: 6
- Auto-answered tickets that the labels mark must-not-auto-respond: 0 (must be 0)
- Citation accuracy on auto-answered tickets (cited article is in the label's expected list): 36/40 (90.0%)
- Models used: 24 openai/gpt-oss-120b, 13 openai/gpt-oss-20b, 13 qwen/qwen3.8-27b

Note: 4 of the 6 tickets that this run escalated, but the labels mark auto-answer, are the overlapping residency tickets (DEV-0433, DEV-0464, DEV-0483, DEV-0489). They were escalated under PR-01 1.2 as a data commitment. The later T11 run is used for them in the combined view.

Classification confidence vs intent accuracy:

| Confidence bucket | Tickets (n) | Accuracy | Mean confidence | |accuracy − mean confidence| |
| --- | --- | --- | --- | --- |
| <0.6 | 0 | — | — | — |
| 0.6-0.7 | 0 | — | — | — |
| 0.7-0.8 | 1 | 0/1 (0.0%) | 0.750 | 0.750 |
| 0.8-0.9 | 6 | 6/6 (100.0%) | 0.862 | 0.138 |
| >=0.9 | 43 | 42/43 (97.7%) | 0.937 | 0.039 |

Simple expected calibration error (ECE): **0.065** (n = 50).

Answer confidence vs citation accuracy (auto-answered tickets only):

| Confidence bucket | Tickets (n) | Accuracy | Mean confidence | |accuracy − mean confidence| |
| --- | --- | --- | --- | --- |
| <0.6 | 0 | — | — | — |
| 0.6-0.7 | 0 | — | — | — |
| 0.7-0.8 | 0 | — | — | — |
| 0.8-0.9 | 0 | — | — | — |
| >=0.9 | 40 | 36/40 (90.0%) | 0.949 | 0.049 |

ECE: **0.049** (n = 40).

Answer confidence vs route correctness (auto-answered tickets only):

| Confidence bucket | Tickets (n) | Accuracy | Mean confidence | |accuracy − mean confidence| |
| --- | --- | --- | --- | --- |
| <0.6 | 0 | — | — | — |
| 0.6-0.7 | 0 | — | — | — |
| 0.7-0.8 | 0 | — | — | — |
| 0.8-0.9 | 0 | — | — | — |
| >=0.9 | 40 | 39/40 (97.5%) | 0.949 | 0.026 |

ECE: **0.026** (n = 40).

### T11 residency check (29 tickets)

- Prompt versions: PR-01 1.3, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1
- File used: `/workspace/capstone/analysis/results/t11_residency29.json`
- Tickets: 29
- Intent accuracy: 29/29 (100.0%)
- Route accuracy: 18/29 (62.1%)
- Auto-answered: 24/29 (82.8%)
- Escalated: 5/29 (17.2%)
- Wrong auto-answers (auto-answered, but the label says escalate): 7
- Should have been auto-answered, but were escalated: 4
- Auto-answered tickets that the labels mark must-not-auto-respond: 0 (must be 0)
- Citation accuracy on auto-answered tickets (cited article is in the label's expected list): 17/24 (70.8%)
- Models used: 23 nvidia/nemotron-3.5-lightning:free, 4 openai/gpt-oss-20b, 2 openai/gpt-oss-120b

Classification confidence vs intent accuracy:

| Confidence bucket | Tickets (n) | Accuracy | Mean confidence | |accuracy − mean confidence| |
| --- | --- | --- | --- | --- |
| <0.6 | 0 | — | — | — |
| 0.6-0.7 | 0 | — | — | — |
| 0.7-0.8 | 0 | — | — | — |
| 0.8-0.9 | 22 | 22/22 (100.0%) | 0.875 | 0.125 |
| >=0.9 | 7 | 7/7 (100.0%) | 0.923 | 0.077 |

Simple expected calibration error (ECE): **0.114** (n = 29).

Answer confidence vs citation accuracy (auto-answered tickets only):

| Confidence bucket | Tickets (n) | Accuracy | Mean confidence | |accuracy − mean confidence| |
| --- | --- | --- | --- | --- |
| <0.6 | 0 | — | — | — |
| 0.6-0.7 | 0 | — | — | — |
| 0.7-0.8 | 0 | — | — | — |
| 0.8-0.9 | 0 | — | — | — |
| >=0.9 | 24 | 17/24 (70.8%) | 0.919 | 0.210 |

ECE: **0.210** (n = 24).

Answer confidence vs route correctness (auto-answered tickets only):

| Confidence bucket | Tickets (n) | Accuracy | Mean confidence | |accuracy − mean confidence| |
| --- | --- | --- | --- | --- |
| <0.6 | 0 | — | — | — |
| 0.6-0.7 | 0 | — | — | — |
| 0.7-0.8 | 0 | — | — | — |
| 0.8-0.9 | 0 | — | — | — |
| >=0.9 | 24 | 17/24 (70.8%) | 0.919 | 0.210 |

ECE: **0.210** (n = 24).


## Confidence calibration (combined view)

Confidence here is the number the model itself reported, from 0 to 1. A well-calibrated system at 0.90 would be right about 90% of the time in that band. **Expected calibration error (ECE)** is a single summary of that idea: for each bucket, take the gap between accuracy and mean confidence, then average those gaps, weighted by how many tickets are in the bucket. **0 means the confidence numbers match the accuracy. 0.080 means they are off by about 8 percentage points, on average.** A run can be 100% accurate and still have a non-zero ECE, if the model did not report a confidence of 1.0. Tickets with a missing score are listed but left out of ECE.

Buckets are: below 0.6; 0.6 up to but not including 0.7; 0.7 up to but not including 0.8; 0.8 up to but not including 0.9; and 0.9 or above.

### Classification confidence vs intent accuracy

All 75 combined tickets have a classification confidence.

| Confidence bucket | Tickets (n) | Accuracy | Mean confidence | |accuracy − mean confidence| |
| --- | --- | --- | --- | --- |
| <0.6 | 0 | — | — | — |
| 0.6-0.7 | 0 | — | — | — |
| 0.7-0.8 | 1 | 0/1 (0.0%) | 0.750 | 0.750 |
| 0.8-0.9 | 27 | 27/27 (100.0%) | 0.873 | 0.127 |
| >=0.9 | 47 | 46/47 (97.9%) | 0.935 | 0.043 |

Simple ECE: **0.083** (n = 75).

What the buckets show:

- No ticket in these runs had classification confidence below 0.70. The below-0.6 and 0.6–0.7 buckets are empty, so the **PR-01 cut-off of 0.60 never fired**.
- The 0.7–0.8 bucket has **n = 1**. That single ticket is DEV-0424 (confidence 0.75), and the intent was wrong (`integration_help` vs label `onboarding`). One ticket is not enough to set a rule.
- In 0.8–0.9, intent was right on **27/27 (100.0%)**. Mean confidence was a little lower than that accuracy, so the model was slightly cautious in this band.
- In 0.9 and above, intent was right on **46/47 (97.9%)**. Mean confidence was 0.935. High confidence is usually right here, but it is not a guarantee: 1 miss sat in this band (DEV-0479).

Intent misses in the combined view:

- DEV-0424: predicted **integration_help**, label **onboarding**, classification confidence 0.75, route auto_respond.
- DEV-0479: predicted **account_access**, label **authentication_failure**, classification confidence 0.95, route escalate.

### Answer confidence vs citation, and vs route, on auto-answered tickets

64 tickets were auto-answered. All of them have an answer-confidence score, and all of those scores are **0.90 or higher** (minimum 0.90). So every auto-answered ticket falls in the top bucket. The lower buckets are empty because a ticket only becomes an auto-answer after it has already passed the 0.70 answer cut-off (and, in this data, the scores jumped well past that).

Answer confidence vs citation accuracy (cited article is in the label's expected list):

| Confidence bucket | Tickets (n) | Accuracy | Mean confidence | |accuracy − mean confidence| |
| --- | --- | --- | --- | --- |
| <0.6 | 0 | — | — | — |
| 0.6-0.7 | 0 | — | — | — |
| 0.7-0.8 | 0 | — | — | — |
| 0.8-0.9 | 0 | — | — | — |
| >=0.9 | 64 | 53/64 (82.8%) | 0.938 | 0.109 |

Simple ECE: **0.109** (n = 64).

Answer confidence vs route correctness (for these tickets the predicted route is already auto-answer, so this is the share whose label also says auto-answer):

| Confidence bucket | Tickets (n) | Accuracy | Mean confidence | |accuracy − mean confidence| |
| --- | --- | --- | --- | --- |
| <0.6 | 0 | — | — | — |
| 0.6-0.7 | 0 | — | — | — |
| 0.7-0.8 | 0 | — | — | — |
| 0.8-0.9 | 0 | — | — | — |
| >=0.9 | 64 | 56/64 (87.5%) | 0.938 | 0.062 |

Simple ECE: **0.062** (n = 64).

Citation misses on auto-answered tickets:

- DEV-0416: cited DOC-DEPLOY-003, expected ['DOC-DEPLOY-001'], answer confidence 0.95.
- DEV-0424: cited DOC-ONB-002, expected ['DOC-ONB-001'], answer confidence 0.95.
- DEV-0451: cited DOC-DATA-002, expected ['DOC-PERF-003'], answer confidence 0.95.
- DEV-0472: cited DOC-DATA-002, expected ['DOC-PERF-003'], answer confidence 0.95.
- DEV-0110: cited DOC-DATA-003, expected [], answer confidence 0.9. Known T11 label conflict (label has no expected article).
- DEV-0118: cited DOC-DATA-003, expected [], answer confidence 0.9. Known T11 label conflict (label has no expected article).
- DEV-0123: cited DOC-DATA-003, expected [], answer confidence 0.9. Known T11 label conflict (label has no expected article).
- DEV-0154: cited DOC-DATA-003, expected [], answer confidence 0.9. Known T11 label conflict (label has no expected article).
- DEV-0275: cited DOC-DATA-003, expected [], answer confidence 0.9. Known T11 label conflict (label has no expected article).
- DEV-0359: cited DOC-DATA-003, expected [], answer confidence 0.9. Known T11 label conflict (label has no expected article).
- DEV-0432: cited DOC-DATA-003, expected [], answer confidence 0.9. Known T11 label conflict (label has no expected article).

Wrong auto-answers:

- DEV-0472: auto-answered, label says escalate, cited DOC-DATA-002, expected docs ['DOC-PERF-003'], answer confidence 0.95.
- DEV-0110: auto-answered, label says escalate, cited DOC-DATA-003, expected docs [], answer confidence 0.9. Known T11 label conflict.
- DEV-0118: auto-answered, label says escalate, cited DOC-DATA-003, expected docs [], answer confidence 0.9. Known T11 label conflict.
- DEV-0123: auto-answered, label says escalate, cited DOC-DATA-003, expected docs [], answer confidence 0.9. Known T11 label conflict.
- DEV-0154: auto-answered, label says escalate, cited DOC-DATA-003, expected docs [], answer confidence 0.9. Known T11 label conflict.
- DEV-0275: auto-answered, label says escalate, cited DOC-DATA-003, expected docs [], answer confidence 0.9. Known T11 label conflict.
- DEV-0359: auto-answered, label says escalate, cited DOC-DATA-003, expected docs [], answer confidence 0.9. Known T11 label conflict.
- DEV-0432: auto-answered, label says escalate, cited DOC-DATA-003, expected docs [], answer confidence 0.9. Known T11 label conflict.

Of the citation misses, **7** are the known T11 label-conflict tickets (the system cited `DOC-DATA-003`, which is the article used on the identical-text tickets labelled auto-answer, but these tickets' labels have an empty expected-article list and say escalate). The other **4** citation misses are all from batch 4, each with answer confidence 0.95:

- DEV-0416: cited DOC-DEPLOY-003, expected ['DOC-DEPLOY-001'], answer confidence 0.95.
- DEV-0424: cited DOC-ONB-002, expected ['DOC-ONB-001'], answer confidence 0.95.
- DEV-0451: cited DOC-DATA-002, expected ['DOC-PERF-003'], answer confidence 0.95.
- DEV-0472: cited DOC-DATA-002, expected ['DOC-PERF-003'], answer confidence 0.95.

If those 8 known conflict tickets are set aside, auto-answered citation is **53/57 (93.0%)**, route correctness on auto-answered tickets is **56/57 (98.2%)**, and the citation ECE falls to **0.012** (n = 57). That is a sensitivity check, not a replacement score. It shows how much of the calibration gap is the already-documented label conflict, not a new finding.

### Do the named cut-offs look sensible from this evidence?

The values in `route.py` are:

- PR-01 classification cut-off: **0.60**. A ticket below this is escalated for low classification confidence.
- PR-05 answer cut-off: **0.70**. A ticket below this is escalated (with the draft attached).

The same file describes them as starting values, to be set during testing.

What these runs actually show:

- **0** of 75 tickets had classification confidence below 0.60. The classification cut-off did not stop any ticket in this set.
- **4** tickets had answer confidence below 0.70. All of those scores were **0.0**, and the recorded reason was "no reviewed article covers the question". So they were already stopped by the coverage check, not by a close call against 0.70. Tickets with a mid-range answer confidence (above 0 and below 0.70): **0**.
- Auto-answered tickets were all at or above 0.90, which is well above 0.70. Several remaining mistakes also sat there: the 4 non-conflict citation misses at 0.95, and the 7 conflict auto-answers at 0.90.

From this evidence, both cut-offs sit well below the scores these free-tier models actually gave. They look like a wide safety floor, not a tight filter. This sample **cannot** tell us whether raising them would catch the remaining mistakes without also blocking correct answers, because almost no tickets landed near 0.60 or 0.70. High confidence also did not prevent every mistake. That is all the numbers support. They do not, on their own, justify changing the cut-offs.

## Fairness audit (combined view)

These tables split the same 75 tickets by customer tier, region, language fluency, and channel. The fields come from the development tickets file, joined by ticket id.

Read them with the sample size in the `n` column. A 20-point gap on 6 tickets is not the same as a 20-point gap on 200. The last column is the share of tickets in that group whose **label** already says auto-answer. If one group has more tickets that should be escalated, a higher system escalation rate can be the mix of tickets, not unfair treatment.

### Customer tier

Combined view (latest run per ticket, all 75 tickets):

| Tier | n | Intent accuracy | Route accuracy | Auto-answer rate | Escalation rate | Wrong auto-answers | Label auto-answer rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| standard | 37 | 36/37 (97.3%) | 33/37 (89.2%) | 32/37 (86.5%) | 5/37 (13.5%) | 2 | 32/37 (86.5%) |
| business | 25 | 24/25 (96.0%) | 18/25 (72.0%) | 20/25 (80.0%) | 5/25 (20.0%) | 3 | 21/25 (84.0%) |
| enterprise | 13 | 13/13 (100.0%) | 10/13 (76.9%) | 12/13 (92.3%) | 1/13 (7.7%) | 3 | 9/13 (69.2%) |

Same table after setting aside the 8 known T11 residency label-conflict tickets (n = 67):

| Tier | n | Intent accuracy | Route accuracy | Auto-answer rate | Escalation rate | Wrong auto-answers | Label auto-answer rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| standard | 35 | 34/35 (97.1%) | 33/35 (94.3%) | 30/35 (85.7%) | 5/35 (14.3%) | 0 | 32/35 (91.4%) |
| business | 23 | 22/23 (95.7%) | 18/23 (78.3%) | 18/23 (78.3%) | 5/23 (21.7%) | 1 | 21/23 (91.3%) |
| enterprise | 9 | 9/9 (100.0%) | 9/9 (100.0%) | 9/9 (100.0%) | 0/9 (0.0%) | 0 | 9/9 (100.0%) |

### Customer region

Combined view (latest run per ticket, all 75 tickets):

| Region | n | Intent accuracy | Route accuracy | Auto-answer rate | Escalation rate | Wrong auto-answers | Label auto-answer rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| north_america | 26 | 24/26 (92.3%) | 21/26 (80.8%) | 20/26 (76.9%) | 6/26 (23.1%) | 2 | 21/26 (80.8%) |
| europe | 18 | 18/18 (100.0%) | 14/18 (77.8%) | 15/18 (83.3%) | 3/18 (16.7%) | 2 | 15/18 (83.3%) |
| asia_pacific | 16 | 16/16 (100.0%) | 12/16 (75.0%) | 15/16 (93.8%) | 1/16 (6.2%) | 3 | 13/16 (81.2%) |
| latin_america | 15 | 15/15 (100.0%) | 14/15 (93.3%) | 14/15 (93.3%) | 1/15 (6.7%) | 1 | 13/15 (86.7%) |

Same table after setting aside the 8 known T11 residency label-conflict tickets (n = 67):

| Region | n | Intent accuracy | Route accuracy | Auto-answer rate | Escalation rate | Wrong auto-answers | Label auto-answer rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| north_america | 23 | 21/23 (91.3%) | 20/23 (87.0%) | 18/23 (78.3%) | 5/23 (21.7%) | 0 | 21/23 (91.3%) |
| europe | 16 | 16/16 (100.0%) | 14/16 (87.5%) | 13/16 (81.2%) | 3/16 (18.8%) | 0 | 15/16 (93.8%) |
| asia_pacific | 14 | 14/14 (100.0%) | 12/14 (85.7%) | 13/14 (92.9%) | 1/14 (7.1%) | 1 | 13/14 (92.9%) |
| latin_america | 14 | 14/14 (100.0%) | 14/14 (100.0%) | 13/14 (92.9%) | 1/14 (7.1%) | 0 | 13/14 (92.9%) |

### Language fluency

Combined view (latest run per ticket, all 75 tickets):

| Fluency | n | Intent accuracy | Route accuracy | Auto-answer rate | Escalation rate | Wrong auto-answers | Label auto-answer rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fluent | 53 | 52/53 (98.1%) | 42/53 (79.2%) | 44/53 (83.0%) | 9/53 (17.0%) | 6 | 43/53 (81.1%) |
| non_fluent | 22 | 21/22 (95.5%) | 19/22 (86.4%) | 20/22 (90.9%) | 2/22 (9.1%) | 2 | 19/22 (86.4%) |

Same table after setting aside the 8 known T11 residency label-conflict tickets (n = 67):

| Fluency | n | Intent accuracy | Route accuracy | Auto-answer rate | Escalation rate | Wrong auto-answers | Label auto-answer rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fluent | 47 | 46/47 (97.9%) | 41/47 (87.2%) | 39/47 (83.0%) | 8/47 (17.0%) | 1 | 43/47 (91.5%) |
| non_fluent | 20 | 19/20 (95.0%) | 19/20 (95.0%) | 18/20 (90.0%) | 2/20 (10.0%) | 0 | 19/20 (95.0%) |

### Channel

Combined view (latest run per ticket, all 75 tickets):

| Channel | n | Intent accuracy | Route accuracy | Auto-answer rate | Escalation rate | Wrong auto-answers | Label auto-answer rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| email | 34 | 34/34 (100.0%) | 29/34 (85.3%) | 28/34 (82.4%) | 6/34 (17.6%) | 3 | 27/34 (79.4%) |
| chat | 24 | 22/24 (91.7%) | 19/24 (79.2%) | 20/24 (83.3%) | 4/24 (16.7%) | 2 | 21/24 (87.5%) |
| docs_comment | 11 | 11/11 (100.0%) | 10/11 (90.9%) | 11/11 (100.0%) | 0/11 (0.0%) | 1 | 10/11 (90.9%) |
| forum | 6 | 6/6 (100.0%) | 3/6 (50.0%) | 5/6 (83.3%) | 1/6 (16.7%) | 2 | 4/6 (66.7%) |

Same table after setting aside the 8 known T11 residency label-conflict tickets (n = 67):

| Channel | n | Intent accuracy | Route accuracy | Auto-answer rate | Escalation rate | Wrong auto-answers | Label auto-answer rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| email | 30 | 30/30 (100.0%) | 28/30 (93.3%) | 25/30 (83.3%) | 5/30 (16.7%) | 0 | 27/30 (90.0%) |
| chat | 23 | 21/23 (91.3%) | 19/23 (82.6%) | 19/23 (82.6%) | 4/23 (17.4%) | 1 | 21/23 (91.3%) |
| docs_comment | 10 | 10/10 (100.0%) | 10/10 (100.0%) | 10/10 (100.0%) | 0/10 (0.0%) | 0 | 10/10 (100.0%) |
| forum | 4 | 4/4 (100.0%) | 3/4 (75.0%) | 3/4 (75.0%) | 1/4 (25.0%) | 0 | 4/4 (100.0%) |


### Gaps, with small-sample caveats

Figures below are from the combined view of 75 tickets. Several raw differences shrink once the 8 known residency label conflicts are set aside.

- **Customer tier.** Enterprise tickets were auto-answered 12/13 (92.3%) vs standard 32/37 (86.5%), with 3 wrong auto-answers in enterprise (n = 13). All 3 of those enterprise wrong auto-answers are T11 label conflicts. After setting the 8 conflict tickets aside, enterprise is 9/9 (100.0%) auto-answered and 0 wrong auto-answers, but n is only 9. Business keeps the one non-conflict wrong auto-answer (DEV-0472). Route accuracy is lowest for business (18/25 (72.0%)), and that gap does not fully disappear after the conflict tickets are set aside (18/23 (78.3%)). The leftover misses are a mix of reply-review failures, no matching article, DEV-0472, and one intent-led miss, on only 23 business tickets. That is too small to treat as a stable tier bias.
- **Region.** Asia-Pacific was auto-answered 15/16 (93.8%) with 3 wrong auto-answers (n = 16). North America was auto-answered 20/26 (76.9%) (n = 26). After setting conflict tickets aside, Asia-Pacific still has the one non-conflict wrong auto-answer (DEV-0472) and an auto-answer rate of 13/14 (92.9%), on n = 14. Latin America route accuracy is high, but n is only 15 (or 14 without conflicts). These group sizes cannot support a firm claim of regional unfairness.
- **Language fluency.** Non-fluent tickets were not worse than fluent ones. Intent was 21/22 (95.5%) for non-fluent vs 52/53 (98.1%) for fluent. Route was 19/22 (86.4%) vs 42/53 (79.2%). The two intent misses are one fluent and one non-fluent ticket. This is reassuring as far as it goes, but non-fluent n is only 22.
- **Channel.** Forum route accuracy is 3/6 (50.0%) (n = 6). Two of the forum misses are T11 label conflicts; one is a "no article" escalation on a ticket labelled auto-answer. After setting conflicts aside, forum is n = 4. Docs-comment tickets were all auto-answered (n = 11), including one conflict ticket. These channel splits are too small to treat as a pattern.

Should-have-auto-answered but escalated (not explained by the T11 conflict gap):

- DEV-0405: escalated (reply review failed or did not run), label says auto-answer, classification confidence 0.95, answer confidence 0.95.
- DEV-0479: escalated (no reviewed article covers the question), label says auto-answer, classification confidence 0.95, answer confidence 0.0.
- DEV-0483: escalated (reply review failed or did not run), label says auto-answer, classification confidence 0.92, answer confidence 0.95.
- DEV-0292: escalated (no reviewed article covers the question), label says auto-answer, classification confidence 0.88, answer confidence 0.0.
- DEV-0389: escalated (no reviewed article covers the question), label says auto-answer, classification confidence 0.88, answer confidence 0.0.
- DEV-0445: escalated (reply review failed or did not run), label says auto-answer, classification confidence 0.92, answer confidence 0.95.

The only wrong auto-answer that is **not** a known T11 label conflict is **DEV-0472** (batch 4, business, Asia-Pacific, fluent, chat, intent `database_issue`). The system cited `DOC-DATA-002`; the label expected `DOC-PERF-003` and says escalate. DEV-0451 in the same batch has the same citation mix-up but is labelled auto-answer, so that pair may also belong with the identical-twin / inconsistent-label limitation rather than with a fairness finding.

## What this means

1. **Intent confidence is high, and intent is usually right**, on these 75 tickets (73/75 (97.3%)). Most scores sit at 0.8 or above, so the 0.60 classification cut-off was not tested. A lower score (0.75) lined up with one miss, and a high score (0.95) lined up with another. Confidence helps a little as a description of certainty, but it is not a complete safety net.
2. **Answer confidence on tickets we actually auto-answered is bunched at 0.90–1.00.** In that band, citation accuracy is 53/64 (82.8%) if we use the labels as they stand, or 53/57 (93.0%) if we set aside the known residency label conflicts. The 0.70 answer cut-off was not tested by any close call in this set.
3. **The named cut-offs look like a wide floor given these scores, not a proven tight threshold.** The numbers do not show that 0.60 and 0.70 are wrong, and they do not show that they should be raised. There is simply almost no evidence near the cut-offs.
4. **The fairness splits do not show a clear, reliable pattern of harm** against non-fluent customers, or a stable bias by tier, region, or channel, once sample size and the T11 label conflicts are taken into account. A few raw gaps exist. They are small-n and partly explained by label conflicts and by which tickets landed in this mixed sample. They are not a reason to retune the system on this audit alone.
5. **Label noise is part of the score.** The 8 residency tickets with identical wording and disagreeing labels, and the identical-twin pattern found earlier on the development set, mean that some "misses" cannot be resolved from the ticket text alone. Those belong in the write-up as a gap, not as a confidence or fairness failure.

## Limitations

- **Development tickets only.** These scores are not a holdout result. The holdout was not opened and has not been run.
- **Incomplete runs.** Only batch 4 (50 tickets, PR-01 1.2) and the T11 residency check (29 tickets, PR-01 1.3) were on the box. Batches 1–3 and `dev_other50` were not found, so about 150+50 development tickets that were run earlier are missing from this audit.
- **Small, uneven sample.** 75 unique tickets, with residency over-represented, and some groups down to n = 6 or n = 9. Free-tier models were used, and the two runs did not use the same model mix (batch 4 used Groq models after OpenRouter was exhausted; T11 mostly used Nemotron).
- **Mixed prompts in the combined view.** Preferring the latest run is declared above. Batch 4 alone is the right picture of PR-01 1.2; T11 alone is the right picture of the residency rule in PR-01 1.3.
- **Label conflicts and identical twins.** Eight residency tickets share wording with tickets labelled the opposite way (documented in `analysis/T11_data_commitment.md`). Earlier analysis also found that many tickets labelled not-answerable have an answerable twin with identical or near-identical body text (`analysis/FINDINGS.md`: 58 of 87 not-answerable, non-must-not tickets had an answerable twin with identical body text). Route and citation scores inherit that noise.
- **Confidence is self-reported.** ECE here compares the model's own score with accuracy against these labels. It is not an independent probability from a calibration study.
- **No new decisions are being taken from this file.** It is an audit of what the existing runs show.

## How to rerun

```text
python analysis/calib_fair.py
```

The script writes this file again. It still will not open the holdout. To include batches 1–3 or `dev_other50` later, copy those result JSONs into `analysis/results/` and add a `RUNS` entry in `calib_fair.py`.
