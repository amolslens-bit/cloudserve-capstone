import re
from load_data import load

# Only these fields may reach the AI. labels, history and language_fluency never do.
ALLOWED = ["ticket_id", "channel", "subject", "body", "received_at",
           "customer_id", "customer_tier", "customer_region"]
REQUIRED = ["body", "customer_id", "customer_tier", "customer_region"]

def redact(text):
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[EMAIL]", text)
    text = re.sub(r"\+?\d[\d\s-]{8,}\d", "[PHONE]", text)
    text = re.sub(r"\b(sk|pk|key|api)[-_][A-Za-z0-9_-]{12,}\b", "[KEY]", text)
    return text

def prepare(ticket):
    clean = {k: ticket.get(k) for k in ALLOWED}
    clean["missing_fields"] = [k for k in REQUIRED if not ticket.get(k)]
    clean["subject"] = redact(clean["subject"] or "")
    clean["body"] = redact(clean["body"] or "")
    return clean

if __name__ == "__main__":
    tickets = [prepare(t) for t in load("development_tickets.json")]
    print("Prepared:", len(tickets))
    print("Fields:", list(tickets[0].keys()))
    print("With missing fields:", sum(1 for t in tickets if t["missing_fields"]))