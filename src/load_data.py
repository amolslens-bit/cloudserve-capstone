import json
from pathlib import Path

DATA = Path("data")

def load(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)

tickets = load("development_tickets.json")
articles = load("documentation.json")

if __name__ == "__main__":
    print("Tickets:", len(tickets))
    print("Articles:", len(articles))
    print("First ticket fields:", list(tickets[0].keys()))