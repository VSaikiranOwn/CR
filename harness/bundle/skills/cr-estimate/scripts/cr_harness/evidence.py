"""Render the evidence trail that accompanies a generated CR."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from cr_tool import compute
from cr_tool import constants as K

from . import constants as H
from .derive import Derivation
from .parse import Workspace


def render(workspace: Workspace, derivation: Derivation, spec, workbook: Path) -> str:
    lines: list[str] = [
        f"# CR Evidence — {workspace.root.name}",
        "",
        "> Output of `cr-estimate`. Written to `02-design/cr/cr-evidence.md`.",
        "> Every complexity flag and reuse level below is traced to the artifact row that",
        "> produced it. Reviewers should check this file, not the spreadsheet.",
        "",
        f"**Generated:** {date.today().isoformat()}  ",
        f"**Workbook:** `{workbook.name}`  ",
        f"**Graphify evidence dated:** {workspace.graphify_generated or 'not present'}  ",
        "",
        "---",
        "",
        "## Totals",
        "",
    ]

    dev = compute.details_total(spec.rows)
    totals = compute.summary_totals(dev)
    lines += [
        "| Activity | MD |",
        "|---|---|",
        f"| Development | {totals.development} |",
        f"| QA ({K.SUMMARY_QA_RATIO:.0%} of Dev) | {totals.qa} |",
        f"| Requirement & Design ({K.SUMMARY_RND_RATIO:.0%} of Dev) | {totals.req_design} |",
        f"| **Total** | **{totals.total}** |",
        "",
    ]

    if spec.stories:
        lines += ["### Tender Story Points", "",
                  "| US # | Framework Unit | Reuse % | Adjustment | FU (adj) | R&D | TSP |",
                  "|---|---|---|---|---|---|---|"]
        for story in spec.stories:
            points = compute.story_points(story)
            lines.append(
                f"| {story.us_id} | {points.framework_unit:.0f} | "
                f"{points.reusability_score:.0f}% | {points.adjustment_pct:.0%} | "
                f"{points.framework_unit_adjusted:.2f} | {points.req_design_unit:.2f} | "
                f"{points.tsp:.2f} |")
        lines.append("")

    lines += ["---", "", "## Per-row effort", "",
              "| # | User Story | Business Requirement | MD |", "|---|---|---|---|"]
    for row in spec.rows:
        requirement = row.business_requirement.replace("|", "\\|")
        if len(requirement) > 90:
            requirement = requirement[:87] + "..."
        lines.append(f"| {row.s_no} | {row.user_story} | {requirement} | "
                     f"{compute.row_dev_effort(row)} |")
    lines += ["", "---", "", "## Evidence trail", ""]

    by_scope: dict[str, list] = {}
    for item in derivation.evidence:
        by_scope.setdefault(item.scope, []).append(item)

    for scope, items in by_scope.items():
        lines += [f"### {scope}", "",
                  "| Decision | Value | Derived from |", "|---|---|---|"]
        for item in items:
            source = item.source.replace("|", "\\|")
            lines.append(f"| {item.field} | `{item.value}` | {source} |")
        lines.append("")

    lines += ["---", "", "## Review checklist", ""]
    checks = [
        "Scope Assessment counts confirmed by the business team "
        f"(all three columns are marked `{H.DRAFT_SCOPE}`).",
        "Database reuse and physical names checked against the approved DCP "
        "Confluence Physical Data Model — never inferred from source.",
        "QA reuse level is a proxy derived from each task's reuse decision; "
        "confirm with the QA lead.",
        "Any `[TBD: verify]` marker in the workbook resolved.",
    ]
    lines += [f"- [ ] {check}" for check in checks]

    if derivation.notes:
        lines += ["", "## Notes raised during derivation", ""]
        lines += [f"- {note}" for note in derivation.notes]

    if workspace.missing:
        lines += ["", "## Missing inputs", ""]
        lines += [f"- `{path}` not found in the batch workspace." for path in workspace.missing]

    if spec.warnings:
        lines += ["", "## Validation warnings", ""]
        lines += [f"- {warning}" for warning in spec.warnings]

    return "\n".join(lines) + "\n"
