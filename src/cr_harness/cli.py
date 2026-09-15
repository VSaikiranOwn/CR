"""`cr-estimate` — derive a CR estimate from a DCP harness batch workspace.

    cr-estimate <workspace>            read 01/02, write 02-design/cr/
    cr-estimate <workspace> --dry-run  print what it would do, write nothing
    cr-estimate rules                  print the mapping constants
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cr_tool import compute
from cr_tool import constants as K
from cr_tool.render import render as render_workbook
from cr_tool.spec import SpecError, parse as parse_spec
from cr_tool.verify import find_formula_errors, find_placeholders

from . import constants as H
from . import evidence as evidence_module
from .derive import derive
from .parse import load_workspace


def cmd_estimate(args) -> int:
    workspace = load_workspace(args.workspace)
    derivation = derive(workspace)

    if not derivation.spec["rows"]:
        print("ERROR: nothing to estimate.", file=sys.stderr)
        for note in derivation.notes:
            print(f"  - {note}", file=sys.stderr)
        return 1

    spec = parse_spec(derivation.spec)

    out_dir = workspace.root / H.CR_DIR
    workbook = out_dir / f"{workspace.root.name}-CR-Estimation.xlsx"

    if args.dry_run:
        _report(workspace, derivation, spec, workbook, [], [], dry_run=True)
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / H.CR_SPEC).write_text(
        json.dumps(derivation.spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    render_workbook(spec, workbook)

    errors = find_formula_errors(workbook)
    placeholders = find_placeholders(workbook)
    (out_dir / H.CR_EVIDENCE).write_text(
        evidence_module.render(workspace, derivation, spec, workbook), encoding="utf-8")

    _report(workspace, derivation, spec, workbook, errors, placeholders)
    return 2 if errors else 0


def _report(workspace, derivation, spec, workbook, errors, placeholders, dry_run=False):
    dev = compute.details_total(spec.rows)
    totals = compute.summary_totals(dev)
    rule = "-" * 66

    print()
    print(f"=== CR estimate — {workspace.root.name} ==="
          + ("  [dry run, nothing written]" if dry_run else ""))
    print(f"  Details rows : {len(spec.rows)}")
    print(f"  Stories      : {len(spec.stories)}")
    print(rule)
    for row in spec.rows:
        print(f"  {row.s_no:>2}  {row.user_story:<20} {compute.row_dev_effort(row):>3} MD")
    print(rule)
    for story in spec.stories:
        points = compute.story_points(story)
        print(f"  {story.us_id:<20} FU {points.framework_unit:>3.0f}  "
              f"reuse {points.reusability_score:>3.0f}%  TSP {points.tsp:>6.2f}")
    print(rule)
    print(f"  Development                       : {totals.development:>4} MD")
    print(f"  QA ({K.SUMMARY_QA_RATIO:.0%} of Dev)                   : {totals.qa:>4} MD")
    print(f"  Requirement & Design ({K.SUMMARY_RND_RATIO:.0%} of Dev)  : {totals.req_design:>4} MD")
    print(f"  TOTAL                             : {totals.total:>4} MD")
    print(rule)

    if not dry_run:
        print(f"  Workbook : {workbook}")
        print(f"  Spec     : {workbook.parent / H.CR_SPEC}")
        print(f"  Evidence : {workbook.parent / H.CR_EVIDENCE}")
        print(f"  Formula errors : {', '.join(errors) if errors else 'none'}")
        if placeholders:
            print(f"  Placeholders   : {len(placeholders)} -> {', '.join(placeholders)}")

    for note in derivation.notes:
        print(f"  ! {note}")
    for warning in spec.warnings:
        print(f"  ! {warning}")
    for path in workspace.missing:
        print(f"  ! missing input: {path}")
    print()


def cmd_rules(args) -> int:
    print("cr-estimate — harness mapping constants")
    print("-" * 66)
    print("WBS layer -> CR dimension:")
    for layer, dimension in H.LAYER_TO_DIMENSION.items():
        target = dimension.upper() if dimension else "(none — already in a ratio)"
        print(f"  {layer:<5} -> {target}")
    print()
    print("Task size -> complexity:")
    for size, complexity in H.SIZE_TO_COMPLEXITY.items():
        print(f"  [{size}] -> {complexity}")
    print(f"  promote one rung when {H.PROMOTE_AT_COUNT}+ tasks share the top size")
    print()
    print("Reuse ladder (lld.md x.4 accepts either spelling):")
    for word, rung in sorted(H.REUSE_WORD_TO_RUNG.items(), key=lambda kv: kv[1]):
        print(f"  {word:<9} -> {rung}")
    print(f"  API Reuse Register: " + ", ".join(
        f"{k}={v}" for k, v in H.DECISION_TO_RUNG.items()))
    print("  roll-up: mean of candidates, snapped to the nearest of {0,1,2,4}, ties low")
    print()
    print("Scope bands: " + ", ".join(f"<={c} -> {l}" for c, l in H.SCOPE_BANDS)
          + f", else {H.SCOPE_LARGE}")
    print("-" * 66)
    print("The CR framework's own arithmetic is fixed — see `cr-tool rules`.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cr-estimate",
        description="Derive a CR estimation workbook from a DCP harness batch workspace.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Estimate a batch workspace")
    run.add_argument("workspace", help=".github/workspace/<batch-id>")
    run.add_argument("--dry-run", action="store_true")
    run.set_defaults(func=cmd_estimate)

    rules = sub.add_parser("rules", help="Print the mapping constants")
    rules.set_defaults(func=cmd_rules)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Allow `cr-estimate <workspace>` as shorthand for `cr-estimate run <workspace>`.
    if argv and argv[0] not in {"run", "rules", "-h", "--help"}:
        argv.insert(0, "run")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (SpecError, FileNotFoundError, NotADirectoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
