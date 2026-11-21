"""split_tickets.py: no AI. Covers the old size mode and the new --parts mode."""
import json

import split_tickets


def _write(path, data):
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")
    return path


def test_split_by_size_writes_numbered_batches(tmp_path):
    tickets = [{"ticket_id": f"DEV-{i:04d}"} for i in range(1, 6)]
    inp = _write(tmp_path / "in.json", tickets)
    prefix = tmp_path / "batch"
    written = split_tickets.split(inp, prefix, 2)
    assert [p.name for p in written] == ["batch_01.json", "batch_02.json", "batch_03.json"]
    assert [len(json.loads(p.read_text())) for p in written] == [2, 2, 1]
    assert json.loads(written[0].read_text())[0]["ticket_id"] == "DEV-0001"


def test_split_keeps_list_shape(tmp_path):
    inp = _write(tmp_path / "in.json", [{"ticket_id": "A"}, {"ticket_id": "B"}])
    written = split_tickets.split_parts(inp, tmp_path / "part", 2)
    for p in written:
        data = json.loads(p.read_text())
        assert isinstance(data, list)


def test_split_keeps_tickets_dict_shape(tmp_path):
    payload = {"source": "dev", "tickets": [{"ticket_id": "A"}, {"ticket_id": "B"}]}
    inp = _write(tmp_path / "in.json", payload)
    written = split_tickets.split_parts(inp, tmp_path / "part", 2)
    for p in written:
        data = json.loads(p.read_text())
        assert isinstance(data, dict) and data["source"] == "dev"
        assert "tickets" in data and len(data["tickets"]) == 1


def test_split_by_parts_names_and_no_overlap(tmp_path):
    tickets = [{"ticket_id": f"T{i}"} for i in range(8)]
    inp = _write(tmp_path / "in.json", tickets)
    written = split_tickets.split_parts(inp, tmp_path / "dev500_part", 4)
    assert [p.name for p in written] == [
        "dev500_part1.json", "dev500_part2.json", "dev500_part3.json", "dev500_part4.json"
    ]
    ids = []
    for p in written:
        batch = json.loads(p.read_text())
        assert len(batch) == 2
        ids.extend(t["ticket_id"] for t in batch)
    assert ids == [f"T{i}" for i in range(8)]
    assert len(set(ids)) == 8


def test_split_by_parts_spreads_remainder(tmp_path):
    tickets = [{"ticket_id": str(i)} for i in range(10)]
    inp = _write(tmp_path / "in.json", tickets)
    written = split_tickets.split_parts(inp, tmp_path / "p", 4)
    sizes = [len(json.loads(p.read_text())) for p in written]
    assert sizes == [3, 3, 2, 2]
    assert sum(sizes) == 10


def test_split_parts_cli(tmp_path, capsys):
    tickets = [{"ticket_id": str(i)} for i in range(4)]
    inp = tmp_path / "in.json"
    _write(inp, tickets)
    split_tickets.main([str(inp), str(tmp_path / "dev500_part"), "--parts", "4"])
    assert (tmp_path / "dev500_part1.json").exists()
    out = capsys.readouterr().out
    assert "dev500_part1.json" in out and "(1 tickets)" in out
