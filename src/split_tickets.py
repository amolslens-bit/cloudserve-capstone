"""Split a tickets JSON file into batches.

    python src/split_tickets.py samples/dev200.json samples/dev200 50

Writes samples/dev200_01.json, samples/dev200_02.json, and so on.
The input file can be a list, or a dict with a "tickets" list.
"""
import json
import sys
from pathlib import Path


def split(input_path, output_prefix, size):
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("tickets", [])
    if not isinstance(data, list):
        raise SystemExit(f"{input_path} is not a ticket list")
    dest = Path(output_prefix)
    dest.parent.mkdir(parents=True, exist_ok=True)
    written = []
    for i, start in enumerate(range(0, len(data), size), 1):
        batch = data[start:start + size]
        path = dest.parent / f"{dest.name}_{i:02d}.json"
        path.write_text(json.dumps(batch, indent=2) + "\n", encoding="utf-8")
        written.append(path)
        print(f"Wrote {path} ({len(batch)} tickets)")
    return written


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("Usage: python src/split_tickets.py <input.json> <output_prefix> <batch_size>")
    split(sys.argv[1], sys.argv[2], int(sys.argv[3]))
