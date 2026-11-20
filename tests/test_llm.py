"""Fallback chain names and order. Loads llm.py with fakes, so no API calls."""
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


def load_llm():
    """Import llm.py as llm_under_test, with ChatOpenAI/ChatGroq stubbed."""
    calls = {"openai": [], "groq": [], "fallbacks": []}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            calls["openai"].append(kwargs)

        def with_fallbacks(self, fallbacks, **kwargs):
            calls["fallbacks"].append({"fallbacks": fallbacks, "kwargs": kwargs})
            self.fallbacks = fallbacks
            return self

    class FakeChatGroq:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            calls["groq"].append(kwargs)

    stubs = {
        "langchain_openai": types.SimpleNamespace(ChatOpenAI=FakeChatOpenAI),
        "langchain_groq": types.SimpleNamespace(ChatGroq=FakeChatGroq),
        "langchain_core.globals": types.SimpleNamespace(set_llm_cache=lambda *a, **k: None),
        "langchain_community.cache": types.SimpleNamespace(SQLiteCache=lambda **k: None),
        "dotenv": types.SimpleNamespace(load_dotenv=lambda *a, **k: None),
    }
    saved = {name: sys.modules.get(name) for name in stubs}
    # Ensure parent packages exist so "langchain_core.globals" can be imported.
    for parent in ("langchain_openai", "langchain_groq", "langchain_core",
                   "langchain_community", "langchain_community.cache", "dotenv"):
        if parent not in sys.modules:
            sys.modules[parent] = types.ModuleType(parent)
    try:
        for name, mod in stubs.items():
            sys.modules[name] = mod
        # Drop a previous load so the file is read again
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


def test_chain_order_and_names():
    mod, calls = load_llm()
    expected = [
        "nvidia/nemotron-3.5-lightning:free",
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
    ]
    assert mod.MODELS == expected
    assert mod.PRIMARY == expected[0] and mod.GROQ_BACKUPS == expected[1:]
    assert [c["model"] for c in calls["openai"]] == [expected[0]]
    assert [c["model"] for c in calls["groq"]] == expected[1:]
    # qwen hides reasoning text; the other Groq models are left as default
    qwen = [c for c in calls["groq"] if c["model"] == "qwen/qwen3.8-27b"][0]
    assert qwen.get("reasoning_format") == "hidden"
    assert all("reasoning_format" not in c for c in calls["groq"] if not c["model"].startswith("qwen/"))
    # with_fallbacks was given the three Groq models, in that order
    assert len(calls["fallbacks"]) == 1
    chain = calls["fallbacks"][0]["fallbacks"]
    assert [m.kwargs["model"] for m in chain] == expected[1:]
    # 429 is already covered by the default exceptions_to_handle=(Exception,)
    assert "exceptions_to_handle" not in calls["fallbacks"][0]["kwargs"]




def test_every_model_has_a_timeout():
    """A11: no AI call can wait forever. Each model gives up after 20 seconds
    (one retry), then the next model in the chain is tried."""
    mod, calls = load_llm()
    every_model = calls["openai"] + calls["groq"]
    assert len(every_model) == 4
    for c in every_model:
        assert c.get("timeout") == 20, c["model"]
        assert c.get("max_retries") == 1, c["model"]