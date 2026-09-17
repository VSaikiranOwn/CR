#!/usr/bin/env python3
"""Entry point for the cr-estimate skill.

Bundled so the skill runs with no pip install:
    python3 .github/skills/cr-estimate/scripts/cr_estimate.py <workspace>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cr_harness.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
