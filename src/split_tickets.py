"""Split a tickets JSON file into batches.

Two modes (the old size mode is unchanged):

    python src/split_tickets.py samples/dev200.json samples/dev200 50

Writes samples/dev200_01.json, samples/dev200_02.json, and so on.

    python src/split_tickets.py data/development_tickets.json samples/dev500_part --parts 4

Writes samples/dev500_part1.json ... samples/dev500_part4.json (no extra underscore
or zero-padding, so the names match the APPLY commands).

The input file can be a list, or a dict with a "tickets" list. Each part keeps
that same JSON shape. Tickets are kept in the original order and are not
duplicated across parts.
"""
import argparse
import json
import sys
from pathlib import Path


def _load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data, data
    if isinstance(data, dict):
        tickets = data.get("tickets", [])
        if not isinstance(tickets, list):
            raise SystemExit(f"{path} has a 'tickets' field that is not a list")
        return data, tickets
    raise SystemExit(f"{path} is not a ticket list")


def _dump(original, tickets):
    """Keep a top-level list, or a dict that already had a tickets list."""
    if isinstance(original, dict) and "tickets" in original:
        out = dict(original)
        out["tickets"] = tickets
        return out
    return tickets


def _write(path, original, tickets):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_dump(original, tickets), indent=2) + "\n", encoding="utf-8")
    return path


def split(input_path, output_prefix, size):
    """Existing size mode: prefix_01.json, prefix_02.json, ... each of `size` tickets
    (the last batch may be shorter)."""
    size = int(size)
    if size < 1:
        raise SystemExit("batch size must be at least 1")
    original, data = _load(input_path)
    dest = Path(output_prefix)
    written = []
    for i, start in enumerate(range(0, len(data), size), 1):
        batch = data[start:start + size]
        path = dest.parent / f"{dest.name}_{i:02d}.json"
        written.append(_write(path, original, batch))
        print(f"Wrote {path} ({len(batch)} tickets)")
    return written


def _part_sizes(n_tickets, n_parts):
    """Spread remainder so parts differ by at most one ticket."""
    if n_parts < 1:
        raise SystemExit("--parts must be at least 1")
    if n_tickets == 0:
        return [0] * n_parts
    base, extra = divmod(n_tickets, n_parts)
    if base == 0:
        # More parts than tickets: some parts would be empty. Refuse, so a typo
        # cannot silently write empty run files.
        raise SystemExit(
            f"cannot split {n_tickets} tickets into {n_parts} non-empty parts"
        )
    return [base + 1] * extra + [base] * (n_parts - extra)


def split_parts(input_path, output_prefix, n_parts):
    """Split into n_parts files named {prefix}1.json ... {prefix}N.json."""
    original, data = _load(input_path)
    dest = Path(output_prefix)
    sizes = _part_sizes(len(data), int(n_parts))
    written = []
    start = 0
    for i, size in enumerate(sizes, 1):
        batch = data[start:start + size]
        start += size
        path = dest.parent / f"{dest.name}{i}.json"
        written.append(_write(path, original, batch))
        print(f"Wrote {path} ({len(batch)} tickets)")
    return written


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Split a tickets JSON file into batches, keeping the original JSON shape."
    )
    p.add_argument("input", help="path to the tickets JSON file")
    p.add_argument("output_prefix", help="output prefix, e.g. samples/dev500_part")
    p.add_argument("batch_size", nargs="?", type=int,
                   help="tickets per file (writes prefix_01.json, prefix_02.json, ...)")
    p.add_argument("--parts", type=int,
                   help="number of parts (writes prefix1.json ... prefixN.json)")
    args = p.parse_args(argv)
    if args.parts and args.batch_size is not None:
        sys.exit("Use either a batch size or --parts, not both.")
    if args.parts:
        split_parts(args.input, args.output_prefix, args.parts)
    elif args.batch_size is not None:
        split(args.input, args.output_prefix, args.batch_size)
    else:
        sys.exit(
            "Usage:\n"
            "  python src/split_tickets.py <input.json> <output_prefix> <batch_size>\n"
            "  python src/split_tickets.py <input.json> <output_prefix> --parts N"
        )


if __name__ == "__main__":
    main()
