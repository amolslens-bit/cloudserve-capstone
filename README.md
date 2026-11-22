# CloudServe AI Support Triage

Reads support tickets, classifies them, searches the help articles, drafts a cited reply,
checks it, and then either marks it ready to send or escalates it to a person (tier 1 or tier 2)
with a handover note. Every decision is logged. Built for the FDE AI capstone (IIT Roorkee).

It runs on free models only, no paid key needed:

* OpenRouter (`nvidia/nemotron-3.5-lightning:free`) as the main model,
  with Groq models (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`) as backups.

(The author also used a paid model, Claude Haiku 5.5, once for the official holdout run. You do not
need it; see "Results" below.)

The answer prompt in use is **PR-05 1.2** (final). Versions 1.3, 1.4 and 1.5 were tried and not shipped;
see `docs/DECISIONS.md` and `docs/CHANGE_TRAIL.md`.

## What you need

* Python 3.11 (tested on 3.11.6, Windows 10/11, PowerShell)
* Git
* A free OpenRouter API key: https://openrouter.ai/keys
* A free Groq API key: https://console.groq.com/keys
* About 3 GB of disk space, for the packages and the embedding model

All commands below are run from the project's main folder (the one holding this README).

## 1. Get the code

```powershell
git clone https://github.com/amolslens-bit/cloudserve-capstone.git capstone_test
cd capstone_test
```

## 2. Create the environment and install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell refuses to run `Activate.ps1`, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.
On macOS or Linux, use `source .venv/bin/activate` instead.

## 3. Add your keys

```powershell
copy .env.example .env
notepad .env
```

Fill in `OPENROUTER_API_KEY` and `GROQ_API_KEY`, and leave `ANTHROPIC_API_KEY` empty.
Save. **Never commit `.env`**; it is already in `.gitignore`.

## 4. Build the search index (once)

```powershell
python src/build_index.py
```

This embeds the help articles in `data/documentation.json` into `storage/chroma`. The first run
downloads the embedding model (`all-MiniLM-L6-v2`), so it takes a few minutes. A warning about
`HF_TOKEN` is harmless and can be ignored.

## 5. Run the tests (one command)

```powershell
pytest
```

Expected: **175 passed**. The tests use a fake AI and a fake search, so they make no API calls
and need no keys.


## 6. Optional: monitoring with Prometheus and Grafana

Skip this section if you don't need dashboards.

`run.py` serves live metrics at `http://localhost:8001/metrics` only while it runs (set `METRICS=off`
to turn this off). Prometheus must be collecting during the run, so start it first. What it collects
is kept, so Grafana can still show a finished run.

**6a. Download the tools (once).** Prometheus and Grafana are not committed. From the project folder:

```powershell
New-Item -ItemType Directory -Force monitoring\tools | Out-Null
cd monitoring\tools
curl.exe -L -o prometheus-3.16.0.windows-amd64.zip "https://github.com/prometheus/prometheus/releases/download/v3.16.0/prometheus-3.16.0.windows-amd64.zip"
curl.exe -L -o grafana_13.3.1_42849527790_windows_amd64.tar.gz "https://dl.grafana.com/grafana/release/13.3.1/grafana_13.3.1_42849527790_windows_amd64.tar.gz"
Expand-Archive -Path .\prometheus-3.16.0.windows-amd64.zip -DestinationPath .
tar -xf .\grafana_13.3.1_42849527790_windows_amd64.tar.gz
cd ..\..
```

**6b. Point Grafana at the dashboard (once).** From the project folder:

```powershell
$g = Get-ChildItem -Directory monitoring\tools | Where-Object { $_.Name -like "grafana*" } | Select-Object -First 1
$provDs = Join-Path $g.FullName "conf\provisioning\datasources"
$provDb = Join-Path $g.FullName "conf\provisioning\dashboards"
New-Item -ItemType Directory -Force $provDs, $provDb | Out-Null
Copy-Item monitoring\grafana\datasource.yml (Join-Path $provDs "cloudserve.yml") -Force
$dashDir = (Resolve-Path monitoring\grafana).Path
@"
apiVersion: 1
providers:
  - name: CloudServe
    orgId: 1
    folder: CloudServe
    type: file
    options:
      path: $dashDir
"@ | Set-Content -Encoding utf8 (Join-Path $provDb "cloudserve.yml")
```

**6c. Start everything.** Open three PowerShell windows. In each one, go to the project folder and
activate the environment first (`cd <path to capstone_test>` then `.venv\Scripts\Activate.ps1`;
the prompt should start with `(.venv)`). Keep all three open, and start them in this order:

```powershell
# Window 1: Prometheus (http://localhost:9090)
cd monitoring\tools\prometheus-3.16.0.windows-amd64
.\prometheus.exe --config.file=..\..\prometheus.yml --storage.tsdb.path=..\prom-data
```

```powershell
# Window 2: Grafana (http://localhost:3000, first login admin/admin)
cd monitoring\tools\grafana-13.3.1
.\bin\grafana.exe server
```

```powershell
# Window 3: the run, kept open 3 minutes after it finishes
$env:METRICS_HOLD_SECONDS = "180"
python src\run.py samples\channel_and_guardrail.json outputs\metrics_demo.json
```

In Prometheus, Status > Targets should show 8001 as up. The "CloudServe support triage" dashboard
loads from `monitoring\grafana\`.



## 7. Run the full system (one command)

```powershell
python src/run.py <tickets file> <results file>
```

Examples:

```powershell
# quick try on 5 tickets
python src/run.py data/development_tickets.json outputs/try5.json --limit 5

# the validation set
python src/run.py data/validation_tickets.json outputs/validation_results.json
```

* Every ticket in the file is processed, unattended. Nothing is skipped.
* If the free providers are rate-limited or down, it waits and retries (30 s, 60 s, 120 s).
  If they are still down, that ticket is escalated with the reason logged, and the run carries on.
* An error on one ticket escalates that ticket only. The run never stops early.
* On free models a full run is slow (about 30 minutes for 80 tickets) because of free-tier rate limits.
* Within 180 Seconds holdout of Grafana you can see the Board updating near real time when you run a full system .

**Outputs:**

| File | What it holds |
|-|-|
| `outputs/<name>.json` | One record per ticket: intent, urgency, route, tier, reason, draft, citation, handover package. Saved after every ticket. Confidential: escalation packages hold the original ticket text. |
| `outputs/<name>_metrics.md` | Metrics report, written at the end. Includes label scores if the file has labels. |
| `storage/decisions.db` | Decision log (SQLite): one row per ticket, with the checks run, model used, time taken and prompt versions. |
| `storage/llm_cache.db` | Cache of AI replies, so a repeated identical prompt makes no new call. |

## Quick check: one ticket per channel and a guardrail test

```powershell
python src/run.py samples/channel_and_guardrail.json outputs/samples_results.json
```

Runs 5 tickets: one each from email, chat, forum and docs comment, plus `SAMPLE-GUARD-01`, which
tries to give the AI orders ("Ignore your previous instructions..."). That ticket should be
escalated to tier 1 with the reason `possible instruction in ticket`, and the AI never drafts a reply.


## Continuous integration

`.github/workflows/ci.yml` runs `pytest` on every push and pull request (GitHub Actions).

## Project layout

```
src/         code (run.py is the entry point)
prompts/     versioned prompt files (PR-01 1.3, PR-04, PR-05 1.2, PR-06, PR-08 judge)
tests/       pytest tests (fake AI and fake search)
evaluation/  harness, results and analysis
data/        tickets and help articles
samples/     ticket subsets used for checks (confidential)
docs/        DECISIONS.md, CHANGE_TRAIL.md, architecture notes and diagrams
monitoring/  Prometheus config and Grafana dashboard (tools themselves are not committed)
storage/     created at run time: index, decision log, cache (not committed)
outputs/     created at run time: results and metrics reports (not committed)
```

## How a ticket is handled

1. **Prepare:** clean the text, mask keys, emails and phone numbers, and note any missing fields.
2. **Classify (PR-01):** intent, urgency, confidence, and billing-dispute and data-commitment flags.
3. **Early checks (code):** missing details, instruction-like text, must-not intents, warning words,
   flags, and the confidence cut-off (0.60). If any check fails, the ticket escalates here.
4. **Search:** the top 2 relevant articles. Weak matches are dropped, so it may find nothing.
5. **Draft (PR-05 1.2):** a reply from the full article, naming the section, with a sources line.
   The citation must be one of the articles supplied. Answer confidence below 0.70 escalates.
6. **Reply review (PR-04):** a second AI check. Anything other than a clean pass counts as a block.
7. **Route:** auto-respond only if every check passed. Otherwise escalate.
8. **Handover note (PR-06):** every escalation gets a summary, what the system was unsure about,
   the articles checked and any draft. If the AI can't write it, code writes a plain note instead.

## Results

The official result is the holdout run on 20 Nov 2026, 13:38 IST (80 validation tickets, Claude
Haiku 5.5 via `--paid-holdout`, PR-05 1.2): 56% auto-answered, 0 of 14 must-not tickets
auto-answered, intent 88%, precision 89%, p95 7.8 s.

A demo re-run of the same 80 tickets on the free models (21 Nov 2026) auto-answered 72%, with
intent 88%, precision 90% and p95 43.3 s. It auto-answered one must-not ticket (VAL-0003, a very
vague "it is not working" ticket the free model classified as a performance problem). This is a
known limitation; see `docs/DECISIONS.md`. Any later run is a demo, not a score.

## Credits and attribution

Built with LangChain, Chroma, sentence-transformers (`all-MiniLM-L6-v2`), OpenRouter, Groq and
Anthropic (holdout run only). Prometheus and Grafana are used for monitoring. The ticket and
documentation data were supplied by the course.

AI assistance: much of the code, tests and prompt drafts were generated with an AI assistant
(Grok Bot), then reviewed, run and tested by the author, who made all design decisions
(recorded in `docs/DECISIONS.md`).
