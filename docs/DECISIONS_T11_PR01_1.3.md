# Snippet to paste into docs/DECISIONS.md (PR-01 1.3 / T11)

Add the next decision number in the # column (the number below is a placeholder).
Evidence is from the 500 development tickets only. The holdout set was not opened.
Labels were used only to score and to write this note, never as an input to the system.

## Decision entry (table row)

| # | Date | Decision | Why | Alternatives considered |
|---|------|----------|-----|------------------------|
| Dxx | 2026-11-19 | Tighten PR-01's `data_commitment_request` flag in version 1.3: set it true only when the customer asks CloudServe itself to sign, guarantee, commit, or confirm in writing where data is stored (a DPA, a contract, or a written residency guarantee). Plain questions about where data is stored, which region to pick, or backup replication, and requests for existing documentation to share, are false. If unsure, set it to false. | T11 / all 500 dev tickets: 29 data-residency tickets, 3 wordings, 21 labelled auto-answer and 8 labelled escalate. None are must-not-auto-respond. The old "if unsure, set it to true" rule matched the labels on only 8/29. The narrower rule matches 21/29, including all 6 backup-replication questions (always labelled auto-answer). | Keep the cautious 1.2 rule (8/29). Flag every residency ticket (would still miss the 21 auto-answer labels). |

## GAP / known limit: 8 label conflicts on identical text

No wording rule can get all 29 of these tickets right, because the same body text is labelled both ways.

Examples (same text, different labels; tier, channel and region do not explain the difference):

- DEV-0433 is labelled auto-answer, DEV-0061 is labelled escalate.
- DEV-0483 is labelled auto-answer, DEV-0110 is labelled escalate.

The 8 escalate labels (DEV-0061, DEV-0118, DEV-0123, DEV-0275, DEV-0432, DEV-0110, DEV-0154, DEV-0359) are all marked `answerable_from_docs=false` with no expected article, while the auto-answer twins of the same text are marked answerable and point at DOC-DATA-003. Under PR-01 1.3 those 8 will be treated as ordinary questions and can be auto-answered, which disagrees with their labels. They are not must-not-auto-respond tickets. This is a data-label gap, recorded here as a known limit, in the same way as the identical-twin tickets.

## One-line hand edit in src/pipeline.py

`run.py` now has `PROMPT_VERSION = "PR-01 1.3, ..."`. If you still use `python src/pipeline.py` for a small test, the version string in `__main__` is hardcoded and also needs this one-line change (search for the old line and replace it):

Old:

`steps=json.dumps(r["steps"]), prompt_version="PR-01 1.2, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1")`

New:

`steps=json.dumps(r["steps"]), prompt_version="PR-01 1.3, PR-05 1.1, PR-04 1.0, PR-06 1.0, PR-02 1.0, PR-03 1.1")`

Do not replace the whole of `pipeline.py`; only that version string changes. `run.py` already picks the version up from `PROMPT_VERSION`, so normal batch runs do not need this edit.
