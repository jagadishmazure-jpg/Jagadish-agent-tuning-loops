"""Docs and repo-hygiene tests."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_names_the_marketplace_and_status_tables():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Savorlane" in text
    assert "Built" in text
    assert "Planned" in text
    assert "Written-not-run" in text


def test_readme_quotes_real_demo_numbers():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "36" in text  # golden cases
    assert "recall 1.0" in text  # shipped recall
    assert "0.5" in text  # sushi segment recall before tuning


def test_knowledge_and_docs_files_exist():
    for rel in (
        "knowledge/design-notes.md",
        "knowledge/architecture.md",
        "knowledge/feedback-loops.md",
        "knowledge/labeling-guide.md",
        "docs/implementation-guide.md",
        "docs/interview-points.md",
        "docs/threat-model.md",
        "docs/limitations.md",
        "docs/adr-001-stub-agents.md",
        "docs/adr-002-global-config-segment-validation.md",
        "LICENSE",
        "SECURITY.md",
    ):
        assert (ROOT / rel).is_file(), rel


def test_count_tests_script_matches_pytest_collection():
    proc = subprocess.run(
        [sys.executable, "scripts/count_tests.py"],
        cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    script_total = proc.stdout.strip().split()[-1]
    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests"],
        cwd=ROOT, capture_output=True, text=True)
    assert f"{script_total} tests collected" in collected.stdout


def test_workflow_actions_are_sha_pinned():
    # Replaces the scaffold-era "no .github" check now that CI exists:
    # every third-party action must be pinned to a full commit SHA.
    import re
    workflows = list((ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows
    for wf in workflows:
        for ref in re.findall(r"uses:\s*(\S+)", wf.read_text(encoding="utf-8")):
            assert re.search(r"@[0-9a-f]{40}$", ref), f"{wf.name}: {ref}"


def test_no_venv_inside_scaffold():
    assert not (ROOT / ".venv").exists()
