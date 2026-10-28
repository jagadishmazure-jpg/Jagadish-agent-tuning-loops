"""Print the real test total by actually collecting the suite."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    match = re.search(r"(\d+) tests? collected", proc.stdout)
    if match:
        print(f"TOTAL TESTS: {match.group(1)}")
        return 0
    print(proc.stdout)
    print(proc.stderr, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
