"""Append-only tuning log tests."""

import pytest

from tuning.log import STEPS, TuningLog


def test_append_assigns_increasing_sequence_numbers(tmp_path):
    log = TuningLog(tmp_path / "log.jsonl")
    first = log.append("sample", {"n": 3})
    second = log.append("mismatch", {"n": 1})
    assert first["seq"] == 1
    assert second["seq"] == 2


def test_read_back_returns_entries_in_order(tmp_path):
    log = TuningLog(tmp_path / "log.jsonl")
    log.append("sample", {"n": 3})
    log.append("ship", {"version": 2})
    entries = log.read_all()
    assert [e["step"] for e in entries] == ["sample", "ship"]
    assert [e["seq"] for e in entries] == [1, 2]


def test_unknown_step_is_rejected(tmp_path):
    log = TuningLog(tmp_path / "log.jsonl")
    with pytest.raises(ValueError):
        log.append("teleport", {})


def test_sequence_continues_across_reopen(tmp_path):
    path = tmp_path / "log.jsonl"
    log = TuningLog(path)
    log.append("sample", {})
    reopened = TuningLog(path)
    entry = reopened.append("ship", {})
    assert entry["seq"] == 2


def test_empty_log_reads_back_empty(tmp_path):
    log = TuningLog(tmp_path / "log.jsonl")
    assert log.read_all() == []


def test_every_documented_step_is_accepted(tmp_path):
    log = TuningLog(tmp_path / "log.jsonl")
    for step in STEPS:
        log.append(step, {})
    assert len(log.read_all()) == len(STEPS)


def test_log_lines_are_valid_json(tmp_path):
    import json
    path = tmp_path / "log.jsonl"
    log = TuningLog(path)
    log.append("block", {"reasons": ["recall"]})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["payload"] == {"reasons": ["recall"]}
