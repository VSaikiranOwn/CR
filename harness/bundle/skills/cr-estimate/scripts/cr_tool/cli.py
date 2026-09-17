"""Command line entry point: ``cr-tool`` / ``python -m cr_tool``."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import __version__, constants as K
from . import compute, inventory, verify
from .render import TEMPLATE_PATH, render
from .spec import Spec, SpecError, load

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STARTER_SPEC = REPO_ROOT / "examples" / "starter_cr_spec.json"


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

def _rule(width: int = 68) -> str:
    return "-" * width


def print_report(spec: Spec, output: Path, errors: list[str], placeholders: list[str]) -> None:
    dev_total = compute.details_total(spec.rows)
    totals = compute.summary_totals(dev_total)

    print()
    print("=== CR Estimation Framework (ver. 2) ===")
    print(f"  Workbook : {output}")
    print(f"  Details  : {len(spec.rows)} row(s)")
    print(f"  Stories  : {len(spec.stories)} on '{K.SHEET_TSP}'")
    print(_rule())
    print(f"  {'#':>2}  {'User Story':<22} {'Group':<22} {'MD':>4}")
    for row in spec.rows:
        print(f"  {row.s_no:>2}  {row.user_story:<22} {(row.group or ''):<22} "
              f"{compute.row_dev_effort(row):>4}")
    print(_rule())

    if spec.stories:
        print(f"  {'US #':<22} {'FU':>5} {'Reuse%':>7} {'Adj':>6} {'FU adj':>7} "
              f"{'R&D':>6} {'TSP':>7}")
        tsp_total = 0.0
        for story in spec.stories:
            points = compute.story_points(story)
            tsp_total += points.tsp
            print(f"  {story.us_id:<22} {points.framework_unit:>5.0f} "
                  f"{points.reusability_score:>6.0f}% {points.adjustment_pct:>5.0%} "
                  f"{points.framework_unit_adjusted:>7.2f} {points.req_design_unit:>6.2f} "
                  f"{points.tsp:>7.2f}")
        print(f"  {'TOTAL TSP':<22} {'':>5} {'':>7} {'':>6} {'':>7} {'':>6} {tsp_total:>7.2f}")
        print(_rule())

    qa_pct = int(K.SUMMARY_QA_RATIO * 100)
    rnd_pct = int(K.SUMMARY_RND_RATIO * 100)
    print(f"  Development                      : {totals.development:>4} MD")
    print(f"  QA ({qa_pct}% of Dev)                  : {totals.qa:>4} MD")
    print(f"  Requirement & Design ({rnd_pct}% of Dev) : {totals.req_design:>4} MD")
    print(f"  SUMMARY TOTAL                    : {totals.total:>4} MD")
    if spec.original_efforts:
        original = spec.original_efforts
        original_total = sum(original.get(k, 0) for k in ("development", "qa", "req_design"))
        print(f"  (Original efforts column         : {original_total:>4.0f} MD)")
    print(_rule())

    print(f"  Formula errors : {', '.join(errors) if errors else 'none'}")
    if placeholders:
        print(f"  Placeholders   : {len(placeholders)} cell(s) still marked "
              f"[TBD]/[Assumption] -> {', '.join(placeholders)}")
    for warning in spec.warnings:
        print(f"  ! {warning}")
    print()


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_build(args) -> int:
    spec = load(args.spec)
    output = Path(args.output) if args.output else _derive_output(Path(args.spec))
    render(spec, output, template=args.template)

    errors = verify.find_formula_errors(output)
    placeholders = verify.find_placeholders(output)
    print_report(spec, output, errors, placeholders)
    return 2 if errors else 0


def _derive_output(spec_path: Path) -> Path:
    name = spec_path.name
    key = name[: -len("_cr_spec.json")] if name.endswith("_cr_spec.json") else spec_path.stem
    return spec_path.parent / f"{key}-CR-Estimation.xlsx"


def cmd_validate(args) -> int:
    spec = load(args.spec)
    dev_total = compute.details_total(spec.rows)
    totals = compute.summary_totals(dev_total)
    print(f"OK: {len(spec.rows)} Details row(s), {len(spec.stories)} story row(s).")
    print(f"    Development {totals.development} MD | QA {totals.qa} MD | "
          f"R&D {totals.req_design} MD | Total {totals.total} MD")
    for warning in spec.warnings:
        print(f"  ! {warning}")
    return 0


def cmd_inventory(args) -> int:
    manifest = inventory.scan(args.input_dir, split_pdfs=args.split_pdf)
    print(inventory.render_text(manifest))
    if args.json:
        path = inventory.write_manifest(manifest, args.json)
        print(f"\nManifest written to {path}")
    return 0


def cmd_init(args) -> int:
    target = Path(args.directory)
    for sub in ("inputs/figma", "inputs/stories", "inputs/hld", "inputs/lld", "output"):
        (target / sub).mkdir(parents=True, exist_ok=True)

    spec_path = target / "output" / f"{args.key}_cr_spec.json"
    if spec_path.exists() and not args.force:
        print(f"{spec_path} already exists (use --force to overwrite).")
    else:
        shutil.copyfile(STARTER_SPEC, spec_path)
        print(f"Starter spec written to {spec_path}")

    print(f"Workspace ready at {target}")
    print("  1. Drop Figma PNG/JPG/PDF into inputs/figma/")
    print("  2. Drop Jira user story .md into inputs/stories/")
    print("  3. Drop HLD .md into inputs/hld/ and LLD .md into inputs/lld/")
    print(f"  4. In Copilot Chat run:  /generate-cr  (fills {spec_path.name})")
    print(f"  5. Then:  cr-tool build {spec_path}")
    return 0


def cmd_rules(args) -> int:
    print("CR Estimation Framework ver. 2 -- fixed constants")
    print(_rule())
    print("Details DEV effort (MD) per flagged component:")
    print(f"  UI / MS / BPM   Simple {K.WEIGHT_SIMPLE}   Medium {K.WEIGHT_MEDIUM}   "
          f"Complex {K.WEIGHT_COMPLEX}")
    print(f"  DB              Simple {K.WEIGHT_DB_SIMPLE}  Medium {K.WEIGHT_DB_MEDIUM}   "
          f"Complex {K.WEIGHT_DB_COMPLEX}")
    print(f"  Row effort = ROUND(sum of the above, 0); guideline band "
          f"{K.ROW_MD_SOFT_MIN}-{K.ROW_MD_SOFT_MAX} MD per row")
    print()
    print("Summary:")
    print(f"  Development          = Details Total")
    print(f"  QA                   = ROUND(Dev x {K.SUMMARY_QA_RATIO:.0%}, 0)")
    print(f"  Requirement & Design = ROUND(Dev x {K.SUMMARY_RND_RATIO:.0%}, 0)")
    print()
    print("Tender Story Points:")
    print(f"  Framework Unit  = SUM(size unit x complexity index)   "
          f"size: S=1 M=3 L=5, NA=0")
    print(f"                    index: user interaction {K.SCOPE_INDEX['user_interaction']}, "
          f"pages {K.SCOPE_INDEX['pages']}, integration {K.SCOPE_INDEX['integration']}")
    print(f"  Reusability %   = mean(level scores of applicable dimensions) / "
          f"{K.REUSE_MAX_SCORE} x 100")
    print(f"  Adjustment %    = 0-24:0%  25-49:35%  50-74:65%  75-100:85%")
    print(f"  FU (Aft. Adj.)  = Framework Unit x (1 - Adjustment %)")
    print(f"  Req & Design    = FU (Aft. Adj.) x {K.REQ_DESIGN_UNIT_RATIO}")
    print(f"  TSP             = (FU adj + Req & Design) x {K.TSP_FACTOR}")
    print(_rule())
    print(f"Template: {TEMPLATE_PATH}")
    return 0


def cmd_schema(args) -> int:
    path = REPO_ROOT / "schema" / "cr_spec.schema.json"
    print(path.read_text(encoding="utf-8"))
    return 0


# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cr-tool",
        description="Generate the company CR Estimation Framework workbook from a spec.",
    )
    parser.add_argument("--version", action="version", version=f"cr-tool {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Scaffold a CR workspace (inputs/ + starter spec)")
    p_init.add_argument("directory")
    p_init.add_argument("--key", default="CR", help="CR / epic key used in file names")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_inv = sub.add_parser("inventory", help="List and classify the input pack")
    p_inv.add_argument("input_dir")
    p_inv.add_argument("--json", help="Also write the manifest to this path")
    p_inv.add_argument("--split-pdf", action="store_true",
                       help="Rasterise Figma PDFs to PNG pages (needs pymupdf)")
    p_inv.set_defaults(func=cmd_inventory)

    p_val = sub.add_parser("validate", help="Check a spec without writing a workbook")
    p_val.add_argument("spec")
    p_val.set_defaults(func=cmd_validate)

    p_build = sub.add_parser("build", help="Generate the workbook from a spec")
    p_build.add_argument("spec")
    p_build.add_argument("-o", "--output", help="Output .xlsx (derived from the spec name if omitted)")
    p_build.add_argument("--template", help="Override the bundled template")
    p_build.set_defaults(func=cmd_build)

    p_rules = sub.add_parser("rules", help="Print the fixed framework constants")
    p_rules.set_defaults(func=cmd_rules)

    p_schema = sub.add_parser("schema", help="Print the spec JSON schema")
    p_schema.set_defaults(func=cmd_schema)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except SpecError as exc:
        print(f"SPEC ERROR: {exc}", file=sys.stderr)
        return 1
    except (FileNotFoundError, NotADirectoryError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
