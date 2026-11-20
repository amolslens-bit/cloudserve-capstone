"""D19: opt-in Claude Haiku 5.5 hookup. All tests use mocks; no live API calls."""
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _llm_path():
    for path in (ROOT / "src" / "llm.py", ROOT / "llm.py"):
        if path.exists():
            return path
    raise FileNotFoundError("llm.py not found")


class FakeChatOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        calls["openai"].append(kwargs)

    def with_fallbacks(self, fallbacks, **kwargs):
        calls["fallbacks"].append({"fallbacks": fallbacks, "kwargs": kwargs})
        self.fallbacks = fallbacks
        return self

    def invoke(self, prompt):
        return types.SimpleNamespace(content="ok", response_metadata={"model_name": self.kwargs["model"]})


class FakeChatGroq:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        calls["groq"].append(kwargs)

    def invoke(self, prompt):
        return types.SimpleNamespace(content="ok", response_metadata={"model_name": self.kwargs["model"]})


class FakeMessage:
    def __init__(self, text, model="claude-haiku-5-5"):
        self.model = model
        self.content = [types.SimpleNamespace(type="text", text=text)]


class FakeAnthropic:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        calls["anthropic_client"].append(kwargs)
        self.messages = types.SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        calls["anthropic_create"].append(kwargs)
        return FakeMessage("ready", kwargs["model"])


calls = {"openai": [], "groq": [], "fallbacks": [], "anthropic_client": [], "anthropic_create": []}


def load_llm(env=None):
    """Import llm.py with ChatOpenAI/ChatGroq/Anthropic stubbed. No API calls."""
    calls["openai"].clear(); calls["groq"].clear(); calls["fallbacks"].clear()
    calls["anthropic_client"].clear(); calls["anthropic_create"].clear()

    stubs = {
        "langchain_openai": types.SimpleNamespace(ChatOpenAI=FakeChatOpenAI),
        "langchain_groq": types.SimpleNamespace(ChatGroq=FakeChatGroq),
        "langchain_core.globals": types.SimpleNamespace(set_llm_cache=lambda *a, **k: None),
        "langchain_community.cache": types.SimpleNamespace(SQLiteCache=lambda **k: None),
        "dotenv": types.SimpleNamespace(load_dotenv=lambda *a, **k: None),
        "anthropic": types.SimpleNamespace(Anthropic=FakeAnthropic),
    }
    saved = {name: sys.modules.get(name) for name in stubs}
    saved_env = dict(__import__("os").environ)
    for parent in ("langchain_openai", "langchain_groq", "langchain_core",
                   "langchain_community", "langchain_community.cache", "dotenv", "anthropic"):
        if parent not in sys.modules:
            sys.modules[parent] = types.ModuleType(parent)
    try:
        os = __import__("os")
        # Start from a clean mode so a previous test cannot leak paid_holdout.
        for key in ("LLM_MODE", "ANTHROPIC_API_KEY", "ANTHROPIC_EFFORT",
                    "ANTHROPIC_TEMPERATURE", "ANTHROPIC_MAX_TOKENS",
                    "PAID_HOLDOUT_FALLBACK", "PAID_MODEL"):
            os.environ.pop(key, None)
        if env:
            os.environ.update(env)
        for name, mod in stubs.items():
            sys.modules[name] = mod
        sys.modules.pop("llm_under_test", None)
        spec = importlib.util.spec_from_file_location("llm_under_test", _llm_path())
        mod = importlib.util.module_from_spec(spec)
        sys.modules["llm_under_test"] = mod
        spec.loader.exec_module(mod)
        return mod, calls
    finally:
        for name, old in saved.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
        os = __import__("os")
        for key in list(os.environ):
            if key not in saved_env:
                os.environ.pop(key, None)
        os.environ.update(saved_env)


def test_default_mode_keeps_the_free_chain():
    """D19 must not change the default: Nemotron then the three Groq models."""
    mod, c = load_llm()
    assert mod.MODE == "free"
    expected = [
        "nvidia/nemotron-3.5-lightning:free",
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
    ]
    assert mod.MODELS == expected
    assert mod.PAID_MODEL == "claude-haiku-5-5"
    assert [x["model"] for x in c["openai"]] == [expected[0]]
    assert [x["model"] for x in c["groq"]] == expected[1:]
    assert not c["anthropic_client"]
    # Default import never needs a paid key.
    for x in c["openai"] + c["groq"]:
        assert x.get("timeout") == 20
        assert x.get("max_retries") == 1
        assert x.get("temperature") == 0


def test_paid_mode_uses_claude_as_primary_with_no_free_fallback():
    """Recommended holdout setup: Claude only, so the 3 s observation stays clean."""
    mod, c = load_llm(env={"LLM_MODE": "paid_holdout", "ANTHROPIC_API_KEY": "sk-test-not-real"})
    assert mod.MODE == "paid_holdout"
    assert mod.ACTIVE_MODEL == "claude-haiku-5-5"
    assert c["anthropic_client"] and c["anthropic_client"][0]["timeout"] == 20
    assert c["anthropic_client"][0]["max_retries"] == 1
    # No Groq/OpenRouter models built unless fallback=free.
    assert c["openai"] == []
    assert c["groq"] == []
    # A mocked call should go to Claude with effort low and no temperature.
    reply = mod.llm.invoke("Reply with one word")
    assert reply.content == "ready"
    assert reply.response_metadata["model_name"] == "claude-haiku-5-5"
    kw = c["anthropic_create"][0]
    assert kw["model"] == "claude-haiku-5-5"
    assert kw["output_config"]["effort"] == "low"
    assert "temperature" not in kw
    assert kw["max_tokens"] == 8192


def test_paid_mode_effort_and_fallback_are_configurable():
    """Effort default is low; ANTHROPIC_EFFORT and PAID_HOLDOUT_FALLBACK can change it."""
    # medium, with free fallback attached
    mod, c = load_llm(env={
        "LLM_MODE": "paid_holdout",
        "ANTHROPIC_API_KEY": "sk-test-not-real",
        "ANTHROPIC_EFFORT": "medium",
        "PAID_HOLDOUT_FALLBACK": "free",
    })
    assert mod.PAID_SETTINGS["effort"] == "medium"
    assert mod.PAID_SETTINGS["fallback"] == "free"
    # Free chain was built as the fallback.
    assert [x["model"] for x in c["openai"]] == ["nvidia/nemotron-3.5-lightning:free"]
    assert len(c["groq"]) == 3
    mod.llm.invoke("hello")
    assert c["anthropic_create"][0]["output_config"]["effort"] == "medium"
    assert "temperature" not in c["anthropic_create"][0]


def test_paid_mode_temperature_stays_omitted_unless_set():
    """Haiku 5.5 docs say omit temperature. Only send it if explicitly configured."""
    mod, c = load_llm(env={
        "LLM_MODE": "paid_holdout",
        "ANTHROPIC_API_KEY": "sk-test-not-real",
        "ANTHROPIC_TEMPERATURE": "0",
    })
    mod.llm.invoke("hello")
    assert c["anthropic_create"][0]["temperature"] == 0.0


def test_paid_mode_requires_an_api_key():
    try:
        load_llm(env={"LLM_MODE": "paid_holdout"})
        raise AssertionError("expected a RuntimeError when the Anthropic key is missing")
    except RuntimeError as e:
        assert "ANTHROPIC_API_KEY" in str(e)


def test_model_calls_are_logged_per_invoke():
    """Each invoke records the model and a latency, then pop_call_log hands them over."""
    mod, c = load_llm(env={"LLM_MODE": "paid_holdout", "ANTHROPIC_API_KEY": "sk-test-not-real"})
    mod.reset_call_log()
    mod.llm.invoke("one")
    mod.llm.invoke("two")
    log = mod.pop_call_log()
    assert len(log) == 2
    assert log[0]["model"] == "claude-haiku-5-5" and log[0]["ok"] is True
    assert log[1]["model"] == "claude-haiku-5-5" and log[1]["ok"] is True
    assert "latency_ms" in log[0] and log[0]["latency_ms"] >= 0
    # pop clears the log so the next ticket starts clean
    assert mod.pop_call_log() == []


def test_free_mode_also_logs_model_calls():
    """The log is not paid-only: every mode records the model that answered."""
    mod, c = load_llm()
    mod.reset_call_log()
    mod.llm.invoke("hello")
    log = mod.pop_call_log()
    assert len(log) == 1
    assert log[0]["ok"] is True
    assert log[0]["model"] == "nvidia/nemotron-3.5-lightning:free"
