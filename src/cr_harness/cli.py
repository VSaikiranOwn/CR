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
    workspace = load_workspace(args.workspace, hld_path=args.hld, lld_path=args.lld)
    use_wbs = None
    if args.no_wbs:
        use_wbs = False
    elif args.use_wbs:
        use_wbs = True
    derivation = derive(workspace, use_wbs=use_wbs)

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
    source = {"wbs": "wbs.md task sizes", "lld": "lld.md x.3 Impact Analysis"}[derivation.mode]
    print(f"  Complexity from : {source}")
    for name in ("requirements-summary", "hld", "lld", "wbs"):
        if name in workspace.sources:
            print(f"  {name:<15} : {workspace.sources[name]}")
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

    if dry_run:
        print()
        print("  *** DRY RUN — no files were written. ***")
        print("  To generate the workbook, run the same command without --dry-run:")
        print(f"      {_run_command(workspace)}")
    print()


def _run_command(workspace) -> str:
    """The exact command that generates the workbook, for the closing hint."""
    import os
    return (f"python .github/skills/cr-estimate/scripts/cr_estimate.py "
            f"{os.fspath(workspace.root)}")


def cmd_doctor(args) -> int:
    """Show what the parser actually found, per AC, so gaps are diagnosable."""
    workspace = load_workspace(args.workspace, hld_path=args.hld, lld_path=args.lld)
    rule = "-" * 78

    print()
    print(f"=== cr-estimate doctor — {workspace.root.name} ===")
    for name in ("requirements-summary", "hld", "lld", "wbs"):
        print(f"  {name:<21}: {workspace.sources.get(name, '(not found)')}")
    print(rule)

    tickets = workspace.requirements.tickets
    if not tickets:
        print("  requirements-summary.md yielded no tickets or ACs.")
        print("  Expected '### <TICKET-KEY> — <summary>' then '- **AC-1** — ...' bullets.")
        return 1

    lld_ids = [ac.id for ac in workspace.lld.acs]
    print(f"  ACs in requirements-summary.md : {sum(len(t.acs) for t in tickets)}")
    print(f"  AC sections found in the LLD   : {len(lld_ids)}"
          + (f"  ({', '.join(lld_ids[:12])}{' ...' if len(lld_ids) > 12 else ''})"
             if lld_ids else ""))
    print(rule)
    print(f"  {'AC':<12} {'LLD §':<7} {'impact':>7} {'reuse':>6} {'screens':>8} "
          f"{'endpts':>7} {'WBS':>5}")

    gaps = 0
    for ticket in tickets:
        for ac in ticket.acs:
            section = workspace.lld.ac(ac.id)
            tasks = workspace.wbs.tasks_for(ac.id)
            if section is None:
                print(f"  {ac.id:<12} {'MISSING':<7} {'-':>7} {'-':>6} {'-':>8} "
                      f"{'-':>7} {len(tasks):>5}")
                gaps += 1
                continue
            if not section.impact:
                gaps += 1
            print(f"  {ac.id:<12} {'ok':<7} {len(section.impact):>7} "
                  f"{len(section.reuse):>6} {len(section.screens):>8} "
                  f"{len(section.endpoints):>7} {len(tasks):>5}")

    print(rule)
    if gaps:
        print(f"  {gaps} AC(s) have no usable Impact Analysis, so their rows fall back")
        print(f"  to a minimal flag. Two possible causes:")
        print(f"    1. The LLD genuinely has no §x.3 table for that AC -- fill it in.")
        print(f"    2. The heading does not match what the parser looks for:")
        print(f"       an AC section is '## AC-1: <title>' and its table sits under")
        print(f"       '### 1.3 Impact Analysis' with a Layer and an Impact column.")
        print(f"  Check one AC that reports MISSING against a working one.")
    else:
        print("  Every AC has Impact Analysis rows. Complexity is fully derived.")
    print()
    return 0


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
    run.add_argument("--no-wbs", action="store_true",
                     help="Ignore wbs.md; take complexity from the LLD Impact Analysis.")
    run.add_argument("--use-wbs", action="store_true",
                     help="Require wbs.md task sizes (the default when a WBS exists).")
    run.add_argument("--hld", help="Use this HLD instead of the auto-resolved latest.")
    run.add_argument("--lld", help="Use this LLD instead of the auto-resolved latest.")
    run.set_defaults(func=cmd_estimate)

    doctor = sub.add_parser(
        "doctor", help="Show what was parsed from each artifact, per AC")
    doctor.add_argument("workspace", help=".github/workspace/<batch-id>")
    doctor.add_argument("--hld")
    doctor.add_argument("--lld")
    doctor.set_defaults(func=cmd_doctor)

    rules = sub.add_parser("rules", help="Print the mapping constants")
    rules.set_defaults(func=cmd_rules)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Allow `cr-estimate <workspace>` as shorthand for `cr-estimate run <workspace>`.
    if argv and argv[0] not in {"run", "rules", "doctor", "-h", "--help"}:
        argv.insert(0, "run")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (SpecError, FileNotFoundError, NotADirectoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
