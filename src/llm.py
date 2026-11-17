import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

load_dotenv()

import warnings
warnings.filterwarnings("ignore", category=Warning, module="langchain_community")

PRIMARY = "nvidia/nemotron-3.5-lightning:free"
BACKUP = "openai/gpt-oss-20b"

# Cache: every model reply is saved in storage/llm_cache.db.
# If the exact same prompt goes to the same model again, the saved reply is
# used and no AI call is made. A changed prompt means a fresh call.
# storage/ holds ticket text, so it must stay in .gitignore.
Path("storage").mkdir(exist_ok=True)
set_llm_cache(SQLiteCache(database_path="storage/llm_cache.db"))

primary = ChatOpenAI(
    model=PRIMARY,
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0,
    timeout=20,
    max_retries=1,
)
backup = ChatGroq(model=BACKUP, api_key=os.getenv("GROQ_API_KEY"),
                  temperature=0, timeout=20, max_retries=1)

# If the primary fails (limit hit, timeout, error), the backup answers instead (NFR-02)
llm = primary.with_fallbacks([backup])

if __name__ == "__main__":
    import time
    for attempt in (1, 2):
        start = time.time()
        reply = llm.invoke("Reply with exactly one word: ready")
        print(f"Run {attempt}: {reply.content} | {reply.response_metadata.get('model_name')} | {time.time() - start:.2f}s")
    print("Run 2 should be near 0s: that reply came from the cache, not the AI.")
