"""Append-only tuning log: every loop step, in order, forever.

Each entry is one JSON object per line with a monotonically
increasing sequence number, a step name, and a payload. The log
is append-only by API: there is no delete, no edit, no truncate.
Auditors replay the loop from this file alone.
"""

from __future__ import annotations

import json
from pathlib import Path

STEPS = (
    "sample",
    "mismatch",
    "diagnosis",
    "candidate",
    "benchmark",
    "ship",
    "block",
    "rollback",
    "segment_tuning",
)


class TuningLog:
    def __init__(self, path):
        self.path = Path(path)
        self._seq = 0
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._seq = max(
                        self._seq, json.loads(line).get("seq", 0))

    def append(self, step, payload):
        if step not in STEPS:
            raise ValueError(f"unknown tuning step: {step!r}")
        self._seq += 1
        entry = {"seq": self._seq, "step": step, "payload": payload}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
        return entry

    def read_all(self):
        if not self.path.exists():
            return []
        entries = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
        return entries
