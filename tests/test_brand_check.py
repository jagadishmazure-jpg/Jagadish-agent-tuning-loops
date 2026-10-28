"""Brand guard tests: the check passes, and it can catch."""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import brand_check

ROOT = Path(__file__).resolve().parents[1]


def test_brand_check_passes_on_this_repo():
    assert brand_check.scan_paths(ROOT) == {}


def test_brand_check_detects_a_planted_hash(monkeypatch, tmp_path):
    # Never write a real company name into a test: plant a hash for
    # an invented word instead, and confirm the scanner finds it.
    monkeypatch.setattr(
        brand_check, "BLOCKLIST_HASHES",
        {hashlib.sha256(b"testword").hexdigest()})
    target = tmp_path / "note.md"
    target.write_text("this note mentions testword once\n", encoding="utf-8")
    found = brand_check.find_violations(target)
    assert len(found) == 1


def test_brand_check_ignores_clean_text(tmp_path):
    target = tmp_path / "note.md"
    target.write_text("savorlane marketplace tuning loops\n", encoding="utf-8")
    assert brand_check.find_violations(target) == []
