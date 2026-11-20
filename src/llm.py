"""LLM chain (NFR-02).

Default (unchanged): OpenRouter Nemotron, then Groq gpt-oss-20b, gpt-oss-120b
and qwen. Every model has a 20 s timeout and one retry (T29 / A11).

Paid holdout (D19, opt-in only): Claude Haiku 5.5 (`claude-haiku-5-5`) via the
Anthropic API. Turn it on with LLM_MODE=paid_holdout or
`python src/run.py ... --paid-holdout`. Use this only for the one-time holdout
run. The free chain stays the default for every other run.

Why the official `anthropic` SDK, not langchain-anthropic: ChatAnthropic in
langchain-anthropic 1.7.12 supports `effort` / `reasoning_effort` and omits
temperature by default, but that package needs langchain-core >= 1.8.4. This
project is pinned to langchain-core 1.7.3 (req_pinned.txt / req_win.txt). The
official SDK accepts `output_config={"effort": ...}` and is wrapped so the rest
of the code still calls `llm.invoke(prompt)`.

Anthropic docs (checked 20 Nov 2026): adaptive thinking is on by default;
default effort is medium; use low for latency; omit temperature, top_p and
top_k. This pack defaults effort to low (overridable with ANTHROPIC_EFFORT)
and does not send temperature unless ANTHROPIC_TEMPERATURE is set.

Fallback in paid mode: none, by recommendation, so a latency check against the
brief's 3 s is not mixed with free-tier times. Set PAID_HOLDOUT_FALLBACK=free
to attach the free chain after Claude. If Claude fails and there is no
fallback, the existing run.py waits (30/60/120 s) and then escalates with
"AI service unavailable"; the run never stops.

Every successful or failed AI call is recorded in a per-ticket log
(model + latency_ms) so the holdout report can show which model answered
and how long each call took.
"""
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

load_dotenv()

# Models, in this order (NFR-02). Primary is OpenRouter; the rest are Groq backups.
PRIMARY = "nvidia/nemotron-3.5-lightning:free"
GROQ_BACKUPS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
]
MODELS = [PRIMARY, *GROQ_BACKUPS]
BACKUP = GROQ_BACKUPS[0]

# D19: paid holdout model. Official API id from Anthropic docs.
PAID_MODEL = "claude-haiku-5-5"
ALLOWED_EFFORTS = ("low", "medium", "high", "xhigh", "max")
# Default low: the reason for paying is a latency check against the brief's 3 s.
# The API default is medium; this is a deliberate override, and it is configurable.
DEFAULT_EFFORT = "low"

# Cache: every model reply is saved in storage/llm_cache.db.
# The cache key is the prompt plus a string that includes the model name,
# so a reply from one model is never reused for another.
# A changed prompt means a fresh call.
# storage/ holds ticket text, so it must stay in .gitignore.
Path("storage").mkdir(exist_ok=True)
set_llm_cache(SQLiteCache(database_path="storage/llm_cache.db"))

# Per-ticket call log. pipeline.process() resets it at the start of each ticket
# and stores the list on the result as model_calls.
_call_log = []


def reset_call_log():
    _call_log.clear()


def pop_call_log():
    items = list(_call_log)
    _call_log.clear()
    return items


class _LoggedLLM:
    """Wrap any invoke() model so each call records model and latency."""

    def __init__(self, inner, fallback_name):
        self._inner = inner
        self._name = fallback_name

    def invoke(self, prompt):
        t0 = time.time()
        try:
            reply = self._inner.invoke(prompt)
            meta = getattr(reply, "response_metadata", None) or {}
            model = meta.get("model_name") or meta.get("model") or self._name
            _call_log.append({
                "model": model,
                "latency_ms": int((time.time() - t0) * 1000),
                "ok": True,
            })
            return reply
        except Exception:
            _call_log.append({
                "model": self._name,
                "latency_ms": int((time.time() - t0) * 1000),
                "ok": False,
            })
            raise


class _Reply:
    def __init__(self, content, model):
        self.content = content
        self.response_metadata = {"model_name": model}


class _ClaudeLLM:
    """Thin wrapper around the official Anthropic SDK, same invoke() shape
    the rest of this project uses. Temperature is omitted unless set.
    """

    def __init__(self, model, api_key, timeout, max_retries, effort, max_tokens,
                 temperature=None):
        # Imported here so default/free-mode tests do not need the package.
        from anthropic import Anthropic
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = Anthropic(api_key=api_key, timeout=timeout, max_retries=max_retries)

    def invoke(self, prompt):
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "output_config": {"effort": self.effort},
            "messages": [{"role": "user", "content": prompt}],
        }
        # Haiku 5.5 docs: omit temperature, top_p and top_k. Only send it if
        # the operator has explicitly set ANTHROPIC_TEMPERATURE.
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        resp = self._client.messages.create(**kwargs)
        parts = []
        for block in getattr(resp, "content", None) or []:
            if getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", "") or "")
        model = getattr(resp, "model", None) or self.model
        return _Reply("".join(parts), model)

    def with_fallbacks(self, fallbacks, **kwargs):
        return _FallbackChain([self, *list(fallbacks)])


class _FallbackChain:
    """Same idea as LangChain with_fallbacks: try the next model if one fails."""

    def __init__(self, models):
        self.models = models

    def invoke(self, prompt):
        last = None
        for m in self.models:
            try:
                return m.invoke(prompt)
            except Exception as e:
                last = e
        if last is None:
            raise RuntimeError("no models in the chain")
        raise last


def _openrouter(model):
    return ChatOpenAI(
        model=model,
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        temperature=0,
        timeout=20,
        max_retries=1,
    )


def _groq(model, **extra):
    return ChatGroq(model=model, api_key=os.getenv("GROQ_API_KEY"),
                    temperature=0, timeout=20, max_retries=1, **extra)


def _build_free():
    primary = _openrouter(PRIMARY)
    # qwen3 may wrap its answer in <think> tags. langchain-groq 1.1.3 supports
    # reasoning_format='hidden', which keeps the reasoning out of the reply text.
    # Parsers also strip leftover <think> blocks (see parse.py).
    backups = []
    for name in GROQ_BACKUPS:
        extra = {"reasoning_format": "hidden"} if name.startswith("qwen/") else {}
        backups.append(_groq(name, **extra))
    return primary.with_fallbacks(backups), PRIMARY


def _effort():
    raw = (os.getenv("ANTHROPIC_EFFORT") or DEFAULT_EFFORT).strip().lower()
    if raw not in ALLOWED_EFFORTS:
        raise ValueError(
            f"ANTHROPIC_EFFORT must be one of {', '.join(ALLOWED_EFFORTS)} (got {raw!r})"
        )
    return raw


def _optional_temperature():
    raw = os.getenv("ANTHROPIC_TEMPERATURE")
    if raw is None or raw.strip() == "":
        return None
    return float(raw)


def _max_tokens():
    raw = os.getenv("ANTHROPIC_MAX_TOKENS") or "8192"
    return int(raw)


def _build_paid():
    key = os.getenv("ANTHROPIC_API_KEY") or ""
    if not key.strip() or key.strip() == "your_anthropic_key_here":
        raise RuntimeError(
            "LLM_MODE=paid_holdout needs ANTHROPIC_API_KEY in .env "
            "(add the line by hand; never commit .env)."
        )
    model = (os.getenv("PAID_MODEL") or PAID_MODEL).strip()
    claude = _ClaudeLLM(
        model=model,
        api_key=key,
        timeout=20,
        max_retries=1,
        effort=_effort(),
        max_tokens=_max_tokens(),
        temperature=_optional_temperature(),
    )
    fallback = (os.getenv("PAID_HOLDOUT_FALLBACK") or "none").strip().lower()
    if fallback in ("free", "1", "true", "yes"):
        # Optional safety net. Not the recommended default: free-tier latency
        # would mix into the 3 s observation. Per-call logs still name the model.
        free_chain, _ = _build_free()
        return claude.with_fallbacks([free_chain]), model
    if fallback not in ("none", "no", "0", "false", ""):
        raise ValueError(
            "PAID_HOLDOUT_FALLBACK must be 'none' (recommended) or 'free'"
        )
    return claude, model


class _Proxy:
    """Stable object imported as `llm` by other modules. configure() can
    swap the active chain without those modules having to re-import."""

    def invoke(self, prompt):
        return _active.invoke(prompt)


llm = _Proxy()
_active = None
MODE = "free"          # "free" or "paid_holdout"
ACTIVE_MODEL = PRIMARY  # first model in the active chain
PAID_SETTINGS = {}


def configure(mode=None):
    """Build the active chain. Called at import from LLM_MODE, and again
    from run.py if --paid-holdout is set."""
    global _active, MODE, ACTIVE_MODEL, PAID_SETTINGS
    raw = (mode or os.getenv("LLM_MODE") or "free").strip().lower()
    if raw in ("paid_holdout", "paid", "claude"):
        inner, name = _build_paid()
        MODE = "paid_holdout"
        ACTIVE_MODEL = name
        PAID_SETTINGS = {
            "model": name,
            "effort": _effort(),
            "temperature": _optional_temperature(),
            "max_tokens": _max_tokens(),
            "fallback": (os.getenv("PAID_HOLDOUT_FALLBACK") or "none").strip().lower() or "none",
        }
    elif raw in ("free", "default", ""):
        inner, name = _build_free()
        MODE = "free"
        ACTIVE_MODEL = name
        PAID_SETTINGS = {}
    else:
        raise ValueError(
            f"LLM_MODE must be 'free' (default) or 'paid_holdout' (got {raw!r})"
        )
    _active = _LoggedLLM(inner, name)
    return MODE


configure()


if __name__ == "__main__":
    import time as _time
    for attempt in (1, 2):
        start = _time.time()
        reply = llm.invoke("Reply with exactly one word: ready")
        print(f"Run {attempt}: {reply.content} | {reply.response_metadata.get('model_name')} | {_time.time() - start:.2f}s")
    print("Run 2 should be near 0s: that reply came from the cache, not the AI.")
