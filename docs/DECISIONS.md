Decision record: CloudServe capstone (Amol)
#	Date	Decision	Why	Alternatives considered
D1	2026-11-01	Use Python 3.11, installed alongside 3.14	3.14 is too new for parts of the stack; the guide's CI uses 3.11	Stay on 3.14 (risk of build failures)
D2	2026-11-01	Protect `.env`, `storage/`, `.venv/` in `.gitignore` before creating any key	The submission is scanned for credentials; a key stays in history forever once committed	none
D3	2026-11-01	Replace the university requirements.txt with current pinned versions (LangChain 1.x, LangGraph 1.x, Chroma 1.x)	The supplied file is unsatisfiable: openai 1.0.0 vs langchain-openai 0.0.7, pydantic 2.0.0 vs fastapi 0.104, and langsmith clash between langchain 0.1.0 and langchain-openai 0.0.7. Current versions match today's documentation	Patch the old 0.1-era pins so the guide's examples work as written
D4	2026-11-01	Drop psycopg2-binary, jupyter, black, flake8 from runtime deps	SQLite is used for the decision log; fewer packages means fewer failures on the grader's machine	Keep the full original list
D5	2026-11-01	Use VS Code integrated terminal with venv activated	One workbench; fewer environment mistakes	Separate PowerShell window
| D6 | 2026-11-01 | Add .gitattributes with * text=auto eol=lf | Graders and CI run on Linux, so this keeps line endings consistent | Leave Git's default conversion |