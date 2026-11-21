"""Optional Prometheus metrics for a run.

This module never changes routing, answers, or result files. If
prometheus_client is missing, the port cannot be bound, or METRICS=off,
it prints one line and the run continues (A9 / A11).

Environment
- METRICS=off          disable entirely (also: 0, false, no)
- METRICS_PORT=8001    first port to try (default 8001). If that port is
                       busy, the next few ports are tried so four parallel
                       windows can share one machine (8001-8004).
- METRICS_HOLD_SECONDS seconds to keep the HTTP server up after the run
                       so Prometheus can scrape the final values.
                       Default 20 (one 15 s scrape plus a little). 0 = exit
                       immediately. Use a larger value (e.g. 180) when you
                       want to screenshot Grafana.

Metric names follow the Setup Guide sample: tickets_processed_total
[channel, outcome], response_seconds, guardrail_blocks_total[guardrail].
A Histogram confidence_score is added for the required confidence
distribution. Channel comes from the ticket's channel field. Outcome is
the route (auto_respond or escalate). Guardrail label values are the
existing check names in run.py CHECK_NAMES, plus a PR-04 block counted
as reply_review — no new names are invented.
"""
import os
import sys
import time

# Existing check names from run.py CHECK_NAMES. Do not invent new ones.
# A ticket's result["checks"] list uses these keys, in order; the last
# one on an escalation is the check that stopped it (same rule as
# run.stop_check). A PR-04 review verdict of "block" is reply_review.
CHECK_NAMES = (
    "missing_fields",
    "instruction_check",
    "must_not",
    "warning_words",
    "dispute_commitment_flags",
    "classify_cutoff",
    "coverage_and_answer_cutoff",
    "citation",
    "banned_claims",
    "reply_review",
)
NOT_A_GUARDRAIL = ("AI service unavailable", "system error", "malformed")

DEFAULT_PORT = 8001
PORT_TRIES = 8          # 8001..8008 covers four windows with a few spare
DEFAULT_HOLD_S = 20

_prom = None            # prometheus_client module, or False if missing
_started = False
_port = None
_tickets = None
_latency = None
_guardrail = None
_confidence = None


def _wanted():
    raw = (os.getenv("METRICS") or "on").strip().lower()
    return raw not in ("off", "0", "false", "no")


def _in_pytest_without_opt_in():
    """Do not bind a port during pytest unless a test sets METRICS=on."""
    if not os.getenv("PYTEST_CURRENT_TEST"):
        return False
    raw = (os.getenv("METRICS") or "").strip().lower()
    return raw not in ("on", "1", "true", "yes")


def _load_prom():
    global _prom
    if _prom is False:
        return None
    if _prom is not None:
        return _prom
    try:
        import prometheus_client
        _prom = prometheus_client
        return _prom
    except ImportError:
        _prom = False
        return None


def _init_collectors():
    """Create the four metrics once, on the default registry."""
    global _tickets, _latency, _guardrail, _confidence
    if _tickets is not None:
        return True
    prom = _load_prom()
    if prom is None:
        return False
    _tickets = prom.Counter(
        "tickets_processed_total",
        "Tickets processed",
        ["channel", "outcome"],
    )
    _latency = prom.Histogram(
        "response_seconds",
        "End to end response time",
        buckets=(0.5, 1, 2, 3, 5, 8, 10, 15, 30, 60, float("inf")),
    )
    _guardrail = prom.Counter(
        "guardrail_blocks_total",
        "Responses blocked",
        ["guardrail"],
    )
    _confidence = prom.Histogram(
        "confidence_score",
        "Classification confidence (0-1)",
        buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    )
    return True


def _first_port():
    raw = os.getenv("METRICS_PORT") or str(DEFAULT_PORT)
    try:
        port = int(raw)
    except ValueError:
        port = DEFAULT_PORT
    if port < 1 or port > 65535:
        port = DEFAULT_PORT
    return port


def start_metrics_server():
    """Open /metrics if wanted. Always safe to call. Returns the port or None."""
    global _started, _port
    if _started:
        return _port
    if not _wanted():
        print("Metrics: off (METRICS=off).")
        return None
    if _in_pytest_without_opt_in():
        return None
    prom = _load_prom()
    if prom is None:
        print("Metrics: prometheus_client is not installed; run continues without metrics.")
        return None
    if not _init_collectors():
        print("Metrics: could not create collectors; run continues without metrics.")
        return None
    first = _first_port()
    last_err = None
    for port in range(first, first + PORT_TRIES):
        try:
            prom.start_http_server(port)
            _started = True
            _port = port
            extra = f" ({first} was busy)" if port != first else ""
            print(f"Metrics: http://localhost:{port}/metrics{extra}")
            return port
        except OSError as e:
            last_err = e
            continue
        except Exception as e:
            print(f"Metrics: could not start ({type(e).__name__}); run continues without metrics.")
            return None
    print(f"Metrics: ports {first}-{first + PORT_TRIES - 1} were busy ({type(last_err).__name__ if last_err else 'error'}); "
          "run continues without metrics.")
    return None


def _channel(raw, result):
    for src in (raw, result):
        if isinstance(src, dict):
            val = src.get("channel")
            if val:
                return str(val)
    return "unknown"


def _outcome(result):
    route = (result or {}).get("route") or "unknown"
    if route in ("auto_respond", "escalate"):
        return route
    return str(route)


def _stopping_check(result):
    """Same rule as run.stop_check: last check on an escalation, unless the
    reason is a system/unavailable fallback (those are not guardrails)."""
    if not isinstance(result, dict):
        return None
    if result.get("route") != "escalate" or not result.get("checks"):
        return None
    if (result.get("reason") or "").startswith(NOT_A_GUARDRAIL):
        return None
    last = result["checks"][-1]
    if last in CHECK_NAMES:
        return last
    return None


def record_ticket(raw, result):
    """Record one finished ticket. Never raises, never changes the result."""
    try:
        if not _wanted():
            return
        if _tickets is None and not _init_collectors():
            return
        if _tickets is None:
            return
        channel = _channel(raw, result)
        outcome = _outcome(result)
        _tickets.labels(channel=channel, outcome=outcome).inc()

        if isinstance(result, dict) and result.get("steps") != ["error"]:
            ms = result.get("latency_ms")
            if isinstance(ms, (int, float)) and ms > 0:
                _latency.observe(ms / 1000.0)

        fired = set()
        stopped = _stopping_check(result)
        if stopped:
            fired.add(stopped)
        review = (result or {}).get("review") if isinstance(result, dict) else None
        if isinstance(review, dict) and review.get("verdict") == "block":
            fired.add("reply_review")
        for name in fired:
            _guardrail.labels(guardrail=name).inc()

        if isinstance(result, dict):
            conf = result.get("confidence")
            if isinstance(conf, (int, float)) and 0 <= conf <= 1:
                _confidence.observe(float(conf))
    except Exception as e:
        print(f"Metrics: could not record a ticket ({type(e).__name__}); run continues.")


def hold_metrics():
    """Keep the HTTP server up briefly so Prometheus can scrape final values."""
    if not _started:
        return
    raw = os.getenv("METRICS_HOLD_SECONDS")
    try:
        hold = DEFAULT_HOLD_S if raw is None or raw.strip() == "" else int(raw)
    except ValueError:
        hold = DEFAULT_HOLD_S
    if hold <= 0:
        return
    print(f"Metrics: holding http://localhost:{_port}/metrics for {hold} s "
          "so Prometheus can scrape (set METRICS_HOLD_SECONDS=0 to skip).")
    try:
        time.sleep(hold)
    except Exception:
        return


def reset_for_tests():
    """Drop collectors so a test can start clean. Not used in a live run."""
    global _prom, _started, _port, _tickets, _latency, _guardrail, _confidence
    if _tickets is not None:
        try:
            prom = _load_prom()
            if prom is not None:
                for metric in (_tickets, _latency, _guardrail, _confidence):
                    if metric is not None:
                        prom.REGISTRY.unregister(metric)
        except Exception:
            pass
    _started = False
    _port = None
    _tickets = _latency = _guardrail = _confidence = None
    # Drop a failed import flag so the next test can load the library again.
    if _prom is False:
        _prom = None
