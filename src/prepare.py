import re
from load_data import load

# Only these fields may reach the AI. labels, history and language_fluency never do.
ALLOWED = ["ticket_id", "channel", "subject", "body", "received_at",
           "customer_id", "customer_tier", "customer_region"]
REQUIRED = ["body", "customer_id", "customer_tier", "customer_region"]

# What gets masked, in this order. Same patterns as before.
PATTERNS = [
    ("email", r"[\w.+-]+@[\w-]+\.[\w.]+", "[EMAIL]"),
    ("phone", r"\+?\d[\d\s-]{8,}\d", "[PHONE]"),
    ("api_key", r"\b(sk|pk|key|api)[-_][A-Za-z0-9_-]{12,}\b", "[KEY]"),
]


def redact(text, counts=None):
    """Mask private data. If a counts dict is given, add how many of each were masked."""
    for name, pattern, mask in PATTERNS:
        text, n = re.subn(pattern, mask, text)
        if counts is not None:
            counts[name] = counts.get(name, 0) + n
    return text


def prepare(ticket):
    clean = {k: ticket.get(k) for k in ALLOWED}
    clean["missing_fields"] = [k for k in REQUIRED if not ticket.get(k)]
    counts = {name: 0 for name, _, _ in PATTERNS}
    clean["subject"] = redact(clean["subject"] or "", counts)
    clean["body"] = redact(clean["body"] or "", counts)
    # Counts only (never the masked values), for the metrics report (A10 governance).
    clean["redactions"] = counts
    return clean


if __name__ == "__main__":
    tickets = [prepare(t) for t in load("development_tickets.json")]
    print("Prepared:", len(tickets))
    print("Fields:", list(tickets[0].keys()))
    print("With missing fields:", sum(1 for t in tickets if t["missing_fields"]))
    print("Tickets with private data masked:", sum(1 for t in tickets if sum(t["redactions"].values())))
