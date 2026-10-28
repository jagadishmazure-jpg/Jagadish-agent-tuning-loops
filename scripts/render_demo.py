"""Run the end-to-end tuning demo and print its real numbers.

Usage: python3 scripts/render_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tuning.demo import print_demo, run_demo


def main() -> int:
    print_demo(run_demo())
    return 0


if __name__ == "__main__":
    sys.exit(main())
