"""metrics.py: no HTTP server required except the port-busy test, and no AI."""
import os
import socket

import prometheus_client
import pytest

import metrics


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    metrics.reset_for_tests()
    monkeypatch.delenv("METRICS", raising=False)
    monkeypatch.delenv("METRICS_PORT", raising=False)
    monkeypatch.delenv("METRICS_HOLD_SECONDS", raising=False)
    yield
    metrics.reset_for_tests()


def _output():
    return prometheus_client.generate_latest().decode("utf-8")


def test_counters_and_histograms_increment(monkeypatch):
    monkeypatch.setenv("METRICS", "on")
    assert metrics._init_collectors()
    raw = {"ticket_id": "T-1", "channel": "email"}
    auto = {
        "route": "auto_respond", "checks": ["missing_fields", "must_not", "citation"],
        "reason": "all checks passed", "review": {"verdict": "pass"},
        "confidence": 0.9, "latency_ms": 2500, "steps": ["prepare", "classify"],
    }
    esc = {
        "route": "escalate", "checks": ["missing_fields", "must_not"],
        "reason": "must-not-auto-respond intent: security_incident",
        "review": None, "confidence": 0.85, "latency_ms": 1200,
        "steps": ["prepare", "classify"], "channel": "chat",
    }
    block = {
        "route": "escalate", "checks": ["missing_fields", "reply_review"],
        "reason": "reply review failed or did not run",
        "review": {"verdict": "block"}, "confidence": 0.7, "latency_ms": 4000,
        "steps": ["prepare", "classify", "review"],
    }
    metrics.record_ticket(raw, auto)
    metrics.record_ticket({"channel": "chat"}, esc)
    metrics.record_ticket({"channel": "forum"}, block)
    text = _output()
    assert 'tickets_processed_total{channel="email",outcome="auto_respond"}' in text
    assert 'tickets_processed_total{channel="chat",outcome="escalate"}' in text
    assert 'guardrail_blocks_total{guardrail="must_not"}' in text
    assert 'guardrail_blocks_total{guardrail="reply_review"}' in text
    assert "response_seconds_bucket" in text
    assert "confidence_score_bucket" in text
    # Do not invent names that are not in run.py CHECK_NAMES
    assert 'guardrail="prompt_injection"' not in text


def test_metrics_off_does_not_start_or_record(monkeypatch, capsys):
    monkeypatch.setenv("METRICS", "off")
    assert metrics.start_metrics_server() is None
    out = capsys.readouterr().out
    assert "Metrics: off" in out
    metrics.record_ticket({"channel": "email"}, {"route": "auto_respond", "latency_ms": 1000,
                                                "steps": ["prepare"], "confidence": 0.5})
    text = _output()
    assert "tickets_processed_total" not in text


def test_port_busy_falls_back_to_next_port(monkeypatch, capsys):
    """If the first port cannot be bound, the next port is used and one line is printed."""
    monkeypatch.setenv("METRICS", "on")
    port = 8001
    monkeypatch.setenv("METRICS_PORT", str(port))
    # Patch the library call so this does not depend on OS port-reuse behaviour.
    assert metrics._load_prom() is not None
    tried = []

    def fake_start(chosen, **kwargs):
        tried.append(chosen)
        if chosen == port:
            raise OSError("Address already in use")
        return (None, None)

    monkeypatch.setattr(metrics._prom, "start_http_server", fake_start)
    used = metrics.start_metrics_server()
    out = capsys.readouterr().out
    assert used == port + 1
    assert tried[0] == port and port + 1 in tried
    assert f"http://localhost:{used}/metrics" in out
    assert f"({port} was busy)" in out


def test_missing_library_prints_one_line_and_continues(monkeypatch, capsys):
    monkeypatch.setenv("METRICS", "on")
    monkeypatch.setenv("METRICS_PORT", str(_free_port()))
    metrics._prom = False
    assert metrics.start_metrics_server() is None
    out = capsys.readouterr().out
    assert "prometheus_client is not installed" in out
    assert "run continues" in out
    # record must also be safe
    metrics.record_ticket({"channel": "email"}, {"route": "auto_respond"})


def test_unknown_channel_and_system_error_are_not_guardrails(monkeypatch):
    monkeypatch.setenv("METRICS", "on")
    assert metrics._init_collectors()
    metrics.record_ticket({}, {
        "route": "escalate", "checks": ["must_not"], "reason": "system error, sent to a person",
        "latency_ms": 0, "steps": ["error"], "confidence": None,
    })
    text = _output()
    assert 'channel="unknown",outcome="escalate"' in text
    assert "guardrail_blocks_total" not in text or 'guardrail="must_not"' not in text
