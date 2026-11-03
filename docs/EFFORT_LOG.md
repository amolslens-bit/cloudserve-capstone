# Effort log

Times are approximate, reconstructed from session timestamps (IST). **Amol: adjust to your actual time.**

## Day 1: Setup (Sun 1 Nov and Mon 2 Nov 2026)

| Date | Session (IST) | Activity | Role | Output | Effort (h) |
|---|---|---|---|---|---|
| 1 Nov | | Read university docs (README, Brief, Build Spec, Setup Guide); flagged inconsistencies (deadline, validation-set rules, 100 vs 120 hidden tickets) | Analyst | Notes, open questions | _fill_ |
| 1 Nov | | Installed Python 3.11 alongside 3.14; created venv; learned VS Code + terminal | Engineer | `.venv` working | _fill_ |
| 1 Nov | | Found university requirements.txt unsatisfiable; chose modern versions; installed and verified pinned deps | Architect / Engineer | `requirements.txt` (D3, D4) | _fill_ |
| 1 Nov | | Git basics; repo init, `.gitignore`, `.gitattributes`, first commits | DevOps | Repo (D2, D5, D6) | _fill_ |
| 1 Nov | | Compared free LLMs; set up OpenRouter + Groq keys; tested both (200 "ready") | Architect | `.env`, `check_keys.py` (D7, D8) | _fill_ |
| 1 Nov | | Started decision record and assumptions file | Governance | `DECISIONS.md`, `ASSUMPTIONS.md` | _fill_ |
| 2 Nov | ~09:00–09:50 | Studied documentation.json and Dataset Guide; chunking concepts; chose fixed vs structure-based comparison; confirmed D4 (kept Jupyter) | Architect | D4, D9 | ~0.8 |
| 2 Nov | ~09:50–11:20 | Built and ran chunker (109 vs 145 chunks) and Chroma index (2 collections) | Engineer | `chunking.py`, `build_index.py` | ~1.5 |
| 2 Nov | ~11:20–12:15 | Repo tidy-up; wrote end-to-end delivery approach for peer review | Delivery lead | `Delivery_Approach.docx` | ~0.9 |
| 2 Nov | ~12:15–12:40 | Designed decision log from an auditor's view; SQLite table; learnings log; commit + GitHub push | Engineer / Governance | `decision_log.py` (D10), `LEARNINGS.md`, GitHub repo | ~0.4 |
| | | | | **Day 1 total** | _sum_ |

**Status at end of Day 1:** setup complete and pushed. Next: Stage 1 Discovery.
**Blockers or risks:** started 2 weeks late; deadline in the docs (13 Sept) still to be confirmed in writing; interview notes and Stage 1 workbook not yet reviewed.
