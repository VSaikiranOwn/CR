#!/usr/bin/env python3
"""`cr-complete` — stage-2 validator for the CR estimate.

Declared on the `cr-estimate` skill. Checks that the CR artifacts exist, are
internally consistent, and carry no unresolved markers. Exits non-zero with one
finding per line, matching the harness validator convention.

    python3 .github/validators/cr_complete.py --workspace .github/workspace/<batch-id>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CR_DIR = "02-design/cr"
WBS = "02-design/wbs.md"
SPEC = "cr-spec.json"
EVIDENCE = "cr-evidence.md"

# The CR is advisory until a human confirms the business-owned columns, so a
# draft marker is a warning, not a failure.
DRAFT_MARKER = "[DRAFT:"
TBD_MARKER = "[TBD"


def check(workspace: Path) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    cr_dir = workspace / CR_DIR
    if not cr_dir.is_dir():
        # No WBS means design is not far enough along for a CR to be expected.
        if not (workspace / WBS).is_file():
            return [], ["cr-complete: no wbs.md yet, CR estimate not expected."]
        return [f"cr-complete: {CR_DIR}/ is missing — run the cr-estimate skill."], []

    spec_path = cr_dir / SPEC
    if not spec_path.is_file():
        failures.append(f"cr-complete: {CR_DIR}/{SPEC} is missing.")
        return failures, warnings

    if not (cr_dir / EVIDENCE).is_file():
        failures.append(f"cr-complete: {CR_DIR}/{EVIDENCE} is missing — "
                        f"a CR without its evidence trail is not reviewable.")

    workbooks = sorted(cr_dir.glob("*-CR-Estimation.xlsx"))
    if not workbooks:
        failures.append(f"cr-complete: no *-CR-Estimation.xlsx in {CR_DIR}/.")

    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"cr-complete: {SPEC} is not valid JSON — {exc}")
        return failures, warnings

    rows = spec.get("rows") or []
    stories = spec.get("stories") or []
    if not rows:
        failures.append("cr-complete: the spec has no Details rows.")
    if not stories:
        warnings.append("cr-complete: no stories — the Tender Story Points sheet is blank.")

    # Every row must flag at least one dimension, or its effort is zero.
    for index, row in enumerate(rows):
        flags = sum(sum(row.get(d) or [0, 0, 0]) for d in ("ui", "ms", "db", "bpm"))
        if flags == 0:
            failures.append(f"cr-complete: rows[{index}] ({row.get('user_story')}) "
                            f"has no complexity flag, so it contributes 0 MD.")

    # Details and Tender Story Points must agree on which stories exist.
    story_ids = {s.get("us_id") for s in stories}
    row_ids = {r.get("user_story") for r in rows if r.get("user_story") != "Shared"}
    for orphan in sorted(row_ids - story_ids):
        failures.append(f"cr-complete: Details estimates {orphan!r} but it has no "
                        f"Tender Story Points row.")
    for unused in sorted(story_ids - row_ids):
        failures.append(f"cr-complete: Tender Story Points lists {unused!r} but no "
                        f"Details row estimates it.")

    blob = json.dumps(spec)
    if TBD_MARKER in blob:
        count = blob.count(TBD_MARKER)
        warnings.append(f"cr-complete: {count} unresolved {TBD_MARKER}...] marker(s) "
                        f"in the spec — resolve before sending the CR out.")
    if DRAFT_MARKER in blob:
        warnings.append("cr-complete: Scope Assessment is still marked "
                        "[DRAFT: business team to confirm].")

    return failures, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the CR estimate for a batch.")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()

    failures, warnings = check(Path(args.workspace))
    for warning in warnings:
        print(f"WARN  {warning}")
    for failure in failures:
        print(f"FAIL  {failure}")
    if not failures:
        print("PASS  cr-complete")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
