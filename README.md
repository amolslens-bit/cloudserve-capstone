# CloudServe AI Support Triage

Reads support tickets, classifies them, searches the help articles, drafts a cited reply,
checks it, and then either marks it ready to send or escalates it to a person (tier 1 or tier 2)
with a handover note. Every decision is logged. Built for the FDE AI capstone (IIT Roorkee).

Uses free tiers only: OpenRouter (`nvidia/nemotron-3.5-lightning:free`) as the main model and
Groq (`openai/gpt-oss-20b`) as the backup.

## What you need

- Python 3.11 (tested on 3.11.6, Windows 10/11, PowerShell)
- Git
- A free OpenRouter API key: https://openrouter.ai/keys
- A free Groq API key: https://console.groq.com/keys
- About 3 GB of disk space, for the packages and the embedding model

All commands below are run from the project's main folder (the one holding this README).

## 1. Get the code

```powershell
git clone https://github.com/amolslens-bit/cloudserve-capstone.git capstone
cd capstone
```

## 2. Create the environment and install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell refuses to run `Activate.ps1`, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

## 3. Add your keys

```powershell
copy .env.example .env
notepad .env
```

Fill in `OPENROUTER_API_KEY` and `GROQ_API_KEY`, then save. Never commit `.env`; it is already
in `.gitignore`.

## 4. Build the search index (once)

```powershell
python src/build_index.py
```

This embeds the help articles in `data/documentation.json` into `storage/chroma`. The first run
downloads the embedding model (`all-MiniLM-L6-v2`), so it takes a few minutes. A warning about `HF_TOKEN` is harmless and can be ignored.

## 5. Run the full system (one command)

```powershell
python src/run.py <tickets file> <results file>
```

For example, on the validation set:

```powershell
python src/run.py data/validation_tickets.json outputs/validation_results.json
```

- Every ticket in the file is processed, unattended. Nothing is skipped.
- If both AI providers are rate-limited or down, it waits and retries (30 s, 60 s, 120 s). If they
  are still down, that ticket is escalated to a person with the reason logged, and the run carries on.
- An error on one ticket escalates that ticket only. The run never stops early.
- About 3.5 s pause between tickets, to keep within the free per-minute limits.

**Outputs:**

| File | What it holds |
|---|---|
| `outputs/<name>.json` | One record per ticket: intent, urgency, route, tier, reason, draft, citation, handover package. Saved after every ticket. |
| `outputs/<name>_metrics.md` | Metrics report, written automatically at the end. Includes label scores if the file has labels. |
| `storage/decisions.db` | Decision log (SQLite, table `decisions`): one row per ticket, with the checks run, model used, time taken and prompt versions. |
| `storage/llm_cache.db` | Cache of AI replies, so a repeated identical prompt makes no new call. |

The report states whether the number of decisions logged matches the number of tickets processed
("reconciles").

For a quick try on a few tickets (development only): add `--limit 5`.

## 6. Run the tests (one command)

```powershell
pytest
```

The tests use a fake AI and a fake search, so they make no API calls, need no keys and finish in
under a second.

## Project layout

```
src/        code (run.py is the entry point)
prompts/    versioned prompt files (PR-01, PR-04, PR-05, PR-06)
tests/      pytest tests
data/       tickets and help articles
docs/       CHANGE_TRAIL.md: what testing showed and what changed
storage/    created at run time: index, decision log, cache (not committed)
outputs/    created at run time: results and metrics reports
```

## How a ticket is handled

1. **Prepare:** clean the text, mask keys, emails and phone numbers, and note any missing fields.
2. **Classify (PR-01):** intent, urgency, confidence, and billing-dispute and data-commitment flags.
3. **Early checks (code):** missing details, instruction-like text, must-not intents, warning words,
   flags, and the confidence cut-off. If any check fails, the ticket escalates here.
4. **Search:** the top 2 relevant articles. Weak matches are dropped, so it may find nothing.
5. **Draft (PR-05):** a reply using the full article. The citation must be one of the articles supplied.
6. **Reply review (PR-04):** a second AI check. Anything other than a clean pass counts as a block.
7. **Route:** auto-respond only if every check passed. Otherwise escalate.
8. **Handover note (PR-06):** every escalation gets a summary, what the system was unsure about,
   the articles checked and any draft. If the AI can't write it, code writes a plain note instead.

## Credits

Built with LangChain, Chroma, sentence-transformers (`all-MiniLM-L6-v2`), OpenRouter and Groq.
The ticket and documentation data were supplied by the course.

## Quick check: one ticket per channel and a guardrail test

```powershell
python src/run.py samples/channel_and_guardrail.json outputs/samples_results.json
```

This runs 5 tickets: one each from email, chat, forum and docs comment (taken from the
development set, with labels and history removed), plus `SAMPLE-GUARD-01`, which tries to
give the AI orders ("Ignore your previous instructions..."). The guardrail ticket should be
escalated to tier 1 with the reason `possible instruction in ticket`, and the AI never drafts
a reply to it. Each result shows its `channel`.
