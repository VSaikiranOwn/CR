"""Turn parsed harness artifacts into a CR spec, with an evidence trail.

Every value this module produces is accompanied by an `Evidence` record naming
the artifact and the rows it came from. That is what makes the CR defensible in
review: a reviewer can trace any complexity flag or reuse level back to a WBS
task id or an LLD table row, rather than taking the number on trust.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from cr_tool import constants as K

from . import constants as H
from .parse import AcSection, Ticket, Workspace


@dataclass
class Evidence:
    scope: str           # "US-123 / AC-1" or "US-123"
    field: str           # what was decided
    value: str           # what it was decided to be
    source: str          # where it came from
    derived: bool = False   # true when inferred rather than read directly


@dataclass
class Derivation:
    spec: dict
    evidence: list[Evidence] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    mode: str = "wbs"           # "wbs" or "lld"


@dataclass
class AcGroup:
    """One Details row: an AC, or a run of sub-ACs sharing a major number."""
    label: str
    acs: list

    @property
    def ids(self) -> list[str]:
        return [ac.id for ac in self.acs]

    def requirement_text(self) -> str:
        if len(self.acs) == 1:
            return f"{self.acs[0].id} - {self.acs[0].text}"
        joined = " ".join(f"({ac.id}) {ac.text}" for ac in self.acs)
        return f"{self.label} - {joined}"


AC_MAJOR = re.compile(r"AC-(\d+)")


def group_acs(acs: list) -> list[AcGroup]:
    """Fold AC-7.1 .. AC-7.7 into one row, the way the reference CRs are written.

    A sheet with one row per sub-AC is unreadable and inflates the row count
    without changing the work; the template groups closely related ACs.
    """
    groups: list[AcGroup] = []
    for ac in acs:
        match = AC_MAJOR.match(ac.id)
        major = match.group(1) if match else ac.id
        if groups and groups[-1].acs and _major_of(groups[-1].acs[0]) == major:
            groups[-1].acs.append(ac)
        else:
            groups.append(AcGroup(label=ac.id, acs=[ac]))
    for group in groups:
        if len(group.acs) > 1:
            group.label = f"{group.acs[0].id}-{group.acs[-1].id}"
    return groups


def _major_of(ac) -> str:
    match = AC_MAJOR.match(ac.id)
    return match.group(1) if match else ac.id


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _promote(size: str) -> str:
    index = H.SIZE_ORDER.index(size)
    return H.SIZE_ORDER[min(index + 1, len(H.SIZE_ORDER) - 1)]


def _max_size(sizes: list[str]) -> str:
    return max(sizes, key=H.SIZE_ORDER.index)


def snap_to_rung(mean: float) -> int:
    """Snap an averaged reuse score onto the sheet's 0/1/2/4 ladder.

    Ties go to the lower rung: a borderline case should read as less reusable,
    which produces a higher (safer) estimate.
    """
    return min(H.REUSE_RUNGS, key=lambda rung: (abs(rung - mean), rung))


def band_scope(count: int) -> str:
    if count <= 0:
        return K.NOT_APPLICABLE
    for ceiling, label in H.SCOPE_BANDS:
        if count <= ceiling:
            return label
    return H.SCOPE_LARGE


def rung_to_level(rung: int) -> str:
    for level in K.REUSE_LEVELS:
        if level.startswith(f"{rung} "):
            return level
    return K.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# Details sheet -- complexity flags from WBS task sizes
# ---------------------------------------------------------------------------

def complexity_flags(tasks, evidence: list[Evidence], scope: str) -> dict[str, list[int]]:
    """One complexity flag per CR dimension, from the WBS tasks on this AC.

    Rule (calibration knobs in constants): the highest declared [S/M/L] in a
    layer sets the level; if that top size appears PROMOTE_AT_COUNT times or
    more, the layer is promoted one rung, because many medium tasks on one AC is
    not a medium change.
    """
    flags = {dimension: [0, 0, 0] for dimension in K.DETAILS_DIMENSIONS}

    by_layer: dict[str, list] = {}
    for task in tasks:
        if task.dimension is None:      # DOCS -- already inside the R&D ratio
            continue
        by_layer.setdefault(task.layer, []).append(task)

    for layer, layer_tasks in sorted(by_layer.items()):
        dimension = H.LAYER_TO_DIMENSION[layer]
        sizes = [task.size or "M" for task in layer_tasks]
        unsized = [task.id for task in layer_tasks if not task.size]

        base = _max_size(sizes)
        promoted = False
        if sizes.count(base) >= H.PROMOTE_AT_COUNT:
            base = _promote(base)
            promoted = True

        complexity = H.SIZE_TO_COMPLEXITY[base]
        flags[dimension][K.COMPLEXITIES.index(complexity)] = 1

        detail = ", ".join(f"{t.id}[{t.size or '?'}]" for t in layer_tasks)
        reason = f"{len(layer_tasks)} {layer} task(s): {detail}"
        if promoted:
            reason += f" -> promoted to {base} ({sizes.count(_max_size(sizes))}+ at top size)"
        if unsized:
            reason += f" [assumed M for unsized: {', '.join(unsized)}]"

        evidence.append(Evidence(
            scope=scope,
            field=f"{dimension.upper()} complexity",
            value=complexity,
            source=f"wbs.md 3.x -- {reason}",
            derived=True,
        ))

    return flags


def impact_complexity_flags(impact_rows, evidence: list[Evidence],
                            scope: str) -> dict[str, list[int]]:
    """Complexity from lld.md x.3 Impact Analysis, when there is no WBS.

    The Impact Analysis already names a layer and a Low/Med/High impact per
    touched component -- the same shape as a WBS task size, so the same rule
    applies: the highest impact in a layer sets the level, promoted one rung
    when several components share that top impact.
    """
    flags = {dimension: [0, 0, 0] for dimension in K.DETAILS_DIMENSIONS}

    by_dimension: dict[str, list] = {}
    for row in impact_rows:
        dimension = H.LLD_LAYER_TO_DIMENSION.get(row.layer.strip().lower())
        complexity = H.IMPACT_TO_COMPLEXITY.get(row.impact.strip().lower())
        if dimension is None or complexity is None:
            continue
        by_dimension.setdefault(dimension, []).append((complexity, row))

    for dimension, entries in sorted(by_dimension.items()):
        levels = [complexity for complexity, _ in entries]
        base = max(levels, key=K.COMPLEXITIES.index)
        promoted = False
        if (levels.count(base) >= H.PROMOTE_AT_COUNT
                and base != K.COMPLEXITIES[-1]):
            base = K.COMPLEXITIES[K.COMPLEXITIES.index(base) + 1]
            promoted = True

        flags[dimension][K.COMPLEXITIES.index(base)] = 1
        detail = ", ".join(f"{row.component}[{row.impact}]" for _, row in entries)
        reason = f"{len(entries)} impact row(s): {detail}"
        if promoted:
            reason += f" -> promoted to {base}"
        evidence.append(Evidence(
            scope=scope, field=f"{dimension.upper()} complexity", value=base,
            source=f"lld.md x.3 Impact Analysis -- {reason}", derived=True))

    return flags


# ---------------------------------------------------------------------------
# Details sheet -- column D
# ---------------------------------------------------------------------------

def technical_component(ac: AcSection | None, tasks, workspace: Workspace) -> str:
    """Build the Technical Component(s) prose, grouped by dimension."""
    blocks: list[str] = []
    task_ids = {task.id for task in tasks}

    def complexity_label(layer: str) -> str:
        layer_tasks = [t for t in tasks if t.layer == layer]
        if not layer_tasks:
            return ""
        sizes = [t.size or "M" for t in layer_tasks]
        base = _max_size(sizes)
        if sizes.count(base) >= H.PROMOTE_AT_COUNT:
            base = _promote(base)
        return H.SIZE_TO_COMPLEXITY[base].capitalize()

    # ---- UI
    fe_tasks = [t for t in tasks if t.layer == "FE"]
    if fe_tasks:
        lines = [f"UI ({complexity_label('FE')})"]
        if ac and ac.components:
            lines.append("Components: " + ", ".join(ac.components))
        if ac and ac.screens:
            lines.append("Screens: " + ", ".join(ac.screens))
        for task in fe_tasks:
            strategy = task.reuse_strategy.upper()
            prefix = H.DECISION_TO_LABEL.get(strategy, strategy or "")
            what = task.what or task.id
            lines.append(f"{prefix}: {what}" if prefix else f"- {what}")
        blocks.append("\n".join(lines))

    # ---- MS
    be_tasks = [t for t in tasks if t.layer == "BE"]
    if be_tasks:
        services = sorted({t.repo.split("/")[0] for t in be_tasks if t.repo})
        header = f"MS ({complexity_label('BE')})"
        if services:
            header += " - " + ", ".join(services)
        lines = [header]
        for entry in workspace.wbs.api_register:
            if task_ids & set(entry.wbs_ids):
                label = H.DECISION_TO_LABEL.get(entry.decision, entry.decision or "API")
                # A NEW capability has no existing API; the register writes "None".
                existing = entry.existing_api.strip()
                target = entry.capability if existing.lower() in ("", "none", "n/a") else existing
                note = f" ({entry.service})" if entry.service else ""
                gap = (f" - {entry.gap_justification}"
                       if entry.gap_justification.lower() not in ("", "n/a", "none") else "")
                lines.append(f"{label}: {target}{note}{gap}")
        if ac and ac.endpoints and len(lines) == 1:
            lines += [f"{H.TBD} endpoint: {e}" for e in ac.endpoints]
        blocks.append("\n".join(lines))

    # ---- DB
    db_tasks = [t for t in tasks if t.layer == "DB"]
    if db_tasks:
        lines = [f"DB ({complexity_label('DB')}) - executed manually by DBA"]
        lines += [f"- {task.what or task.id}" for task in db_tasks]
        lines.append("Physical names per the approved DCP Confluence Physical Data Model.")
        blocks.append("\n".join(lines))

    # ---- BPM
    bpm_tasks = [t for t in tasks if t.layer == "BPM"]
    if bpm_tasks:
        header = f"BPM ({complexity_label('BPM')}) - IBM BPM (manual handoff)"
        lines = [header]
        if ac and ac.bpm_process:
            lines.append(f"Process: {ac.bpm_process}")
        lines += [f"- {task.what or task.id}" for task in bpm_tasks]
        blocks.append("\n".join(lines))
    elif ac and ac.no_bpm:
        blocks.append("BPM: none.")
    else:
        blocks.append(f"BPM: {H.TBD} confirm process / subprocess impact.")

    if not blocks:
        return f"{H.TBD} no WBS tasks reference this AC -- technical analysis pending."
    return "\n".join(blocks)


def technical_component_from_lld(sections, flags: dict[str, list[int]]) -> str:
    """Column D from the LLD alone: impact rows, screens, endpoints, BPM."""
    def label(dimension: str) -> str:
        counts = flags.get(dimension, [0, 0, 0])
        for index, count in enumerate(counts):
            if count:
                return K.COMPLEXITIES[index].capitalize()
        return ""

    def impacts(*dimensions: str) -> list:
        out = []
        for section in sections:
            for row in section.impact:
                if H.LLD_LAYER_TO_DIMENSION.get(row.layer.strip().lower()) in dimensions:
                    out.append(row)
        return out

    blocks: list[str] = []

    if sum(flags.get("ui", [0, 0, 0])):
        lines = [f"UI ({label('ui')})"]
        components = sorted({c for s in sections for c in s.components})
        screens = sorted({s2 for s in sections for s2 in s.screens})
        if components:
            lines.append("Components: " + ", ".join(components))
        if screens:
            lines.append("Screens: " + ", ".join(screens))
        for row in impacts("ui"):
            if row.change_required:
                lines.append(f"- {row.component}: {row.change_required}")
        blocks.append("\n".join(lines))

    if sum(flags.get("ms", [0, 0, 0])):
        services = sorted({row.component.split("/")[0].strip()
                           for row in impacts("ms") if row.component})
        header = f"MS ({label('ms')})"
        if services:
            header += " - " + ", ".join(services[:4])
        lines = [header]
        # Endpoint labels come from the x.4 reuse decisions, which state
        # REUSE / EXTEND / NEW per candidate.
        for section in sections:
            for candidate in section.reuse:
                if candidate.dimension() != "interface":
                    continue
                marker = H.DECISION_TO_LABEL.get(candidate.decision, candidate.decision)
                if marker:
                    lines.append(f"{marker}: {candidate.location or candidate.candidate}")
        endpoints = sorted({e for s in sections for e in s.endpoints})
        if endpoints and len(lines) == 1:
            lines += [f"{H.TBD} NEW vs EXISTING: {e}" for e in endpoints]
        for row in impacts("ms"):
            if row.change_required:
                lines.append(f"- {row.component}: {row.change_required}")
        blocks.append("\n".join(lines))

    if sum(flags.get("db", [0, 0, 0])):
        lines = [f"DB ({label('db')}) - executed manually by DBA"]
        for row in impacts("db"):
            lines.append(f"- {row.component}: {row.change_required or 'change required'}")
        lines.append("Physical names per the approved DCP Confluence Physical Data Model.")
        blocks.append("\n".join(lines))

    if sum(flags.get("bpm", [0, 0, 0])):
        lines = [f"BPM ({label('bpm')}) - IBM BPM (manual handoff)"]
        processes = sorted({s.bpm_process for s in sections if s.bpm_process})
        if processes:
            lines.append("Process: " + ", ".join(processes))
        for row in impacts("bpm"):
            lines.append(f"- {row.component}: {row.change_required or 'change required'}")
        blocks.append("\n".join(lines))
    elif any(s.no_bpm for s in sections):
        blocks.append("BPM: none.")
    else:
        blocks.append(f"BPM: {H.TBD} confirm process impact.")

    if not blocks:
        return (f"{H.TBD} the LLD Impact Analysis lists no usable rows for this AC "
                f"- technical analysis pending.")
    return "\n".join(blocks)


# ---------------------------------------------------------------------------
# Tender Story Points -- reusability roll-up
# ---------------------------------------------------------------------------

def reuse_levels(ticket: Ticket, workspace: Workspace,
                 evidence: list[Evidence]) -> dict[str, dict]:
    """One reuse level per TSP dimension, averaged over the LLD's candidates."""
    ac_ids = {ac.id for ac in ticket.acs}
    sections = [ac for ac in workspace.lld.acs if ac.id in ac_ids] or workspace.lld.acs

    buckets: dict[str, list[int]] = {
        "frontend": [], "backend": [], "database": [], "interface": []}
    citations: dict[str, list[str]] = {k: [] for k in buckets}

    for section in sections:
        for candidate in section.reuse:
            dimension = candidate.dimension()
            if dimension in buckets and candidate.level is not None:
                buckets[dimension].append(candidate.level)
                citations[dimension].append(
                    f"{section.id} {candidate.candidate} ({candidate.location})={candidate.level}")

    # Interface: prefer the WBS API Reuse Register, which is mandatory and states
    # a decision for every capability considered. Without a WBS, fall back to the
    # endpoint-shaped candidates in x.4.
    story_tasks = {t.id for t in workspace.wbs.tasks if t.story_key in ticket.key
                   or ticket.key in t.story_key}
    register_rungs, register_cites = [], []
    for entry in workspace.wbs.api_register:
        if entry.decision and (not entry.wbs_ids or story_tasks & set(entry.wbs_ids)):
            register_rungs.append(H.DECISION_TO_RUNG[entry.decision])
            register_cites.append(f"{entry.capability}={entry.decision}")
    if register_rungs:
        buckets["interface"] = register_rungs
        citations["interface"] = register_cites

    # QA is a proxy. With a WBS: the reuse decision of each task carrying a test
    # slice. Without one: the reuse decisions across all x.4 candidates, on the
    # same logic -- mostly NEW work needs mostly new tests.
    qa_rungs, qa_cites = [], []
    for task in workspace.wbs.tasks:
        if task.id in story_tasks and task.test_slice:
            decision = task.reuse_strategy.upper()
            if decision in H.QA_DECISION_TO_RUNG:
                qa_rungs.append(H.QA_DECISION_TO_RUNG[decision])
                qa_cites.append(f"{task.id}={decision}")
    if not qa_rungs:
        for section in sections:
            for candidate in section.reuse:
                if candidate.decision in H.QA_DECISION_TO_RUNG:
                    qa_rungs.append(H.QA_DECISION_TO_RUNG[candidate.decision])
                    qa_cites.append(f"{section.id} {candidate.candidate}={candidate.decision}")
    buckets["qa"] = qa_rungs
    citations["qa"] = qa_cites

    result: dict[str, dict] = {}
    for dimension in K.REUSE_DIMENSIONS:
        rungs = buckets.get(dimension, [])
        if not rungs:
            result[dimension] = {
                "level": K.NOT_APPLICABLE,
                "details": f"{H.TBD} no reuse candidates found for this dimension.",
            }
            evidence.append(Evidence(
                scope=ticket.key, field=f"Reuse / {dimension}", value=K.NOT_APPLICABLE,
                source="lld.md x.4 / wbs.md 2.1 -- no rows matched", derived=True))
            continue

        mean = sum(rungs) / len(rungs)
        rung = snap_to_rung(mean)
        cites = citations[dimension]
        result[dimension] = {
            "level": rung_to_level(rung),
            "details": f"mean {mean:.2f} of {len(rungs)} candidate(s) -> {rung}. "
                       + "; ".join(cites[:6]) + (" ..." if len(cites) > 6 else ""),
        }
        evidence.append(Evidence(
            scope=ticket.key, field=f"Reuse / {dimension}", value=rung_to_level(rung),
            source=f"mean({rungs}) = {mean:.2f} -> rung {rung}; {'; '.join(cites[:4])}",
            derived=True))
    return result


# ---------------------------------------------------------------------------
# Tender Story Points -- scope assessment
# ---------------------------------------------------------------------------

def scope_assessment(ticket: Ticket, workspace: Workspace,
                     evidence: list[Evidence]) -> dict[str, dict]:
    ac_ids = {ac.id for ac in ticket.acs}
    sections = [ac for ac in workspace.lld.acs if ac.id in ac_ids] or workspace.lld.acs

    interactions: list[str] = []
    for section in sections:
        if section.components or section.screens:
            interactions.append(f"{section.id}: {section.title or 'main flow'}")
        interactions += [f"{section.id}: {flow}" for flow in section.alternate_flows]

    screens = sorted({screen for section in sections for screen in section.screens})

    integrations = list(workspace.hld.integrations)
    for section in sections:
        for participant in section.participants:
            # A sequence-diagram participant usually restates an integration the
            # HLD already lists ("ELS" vs "ELS withdraw-lodgement outbound API").
            # Counting both would inflate the Framework Unit.
            if any(participant.lower() in existing.lower() for existing in integrations):
                continue
            integrations.append(participant)
    integrations = sorted(set(integrations))

    counts = {
        "user_interaction": (interactions, "lld.md x.2 Alternate Flows + x.6 UI Changes"),
        "pages": (screens, "lld.md x.6 Screen Reference"),
        "integration": (integrations, "hld.md 8 Integrations + x.7 sequence participants"),
    }

    result: dict[str, dict] = {}
    for dimension, (items, source) in counts.items():
        size = band_scope(len(items))
        listing = "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1))
        result[dimension] = {
            "size": size,
            "details": (listing + f"\n{H.DRAFT_SCOPE}") if items else H.DRAFT_SCOPE,
        }
        evidence.append(Evidence(
            scope=ticket.key, field=f"Scope / {dimension}", value=f"{size} ({len(items)})",
            source=f"{source} -- {len(items)} item(s)", derived=True))
    return result


# ---------------------------------------------------------------------------
# top level
# ---------------------------------------------------------------------------

def derive(workspace: Workspace, use_wbs: bool | None = None) -> Derivation:
    """Build the CR spec from a batch.

    `use_wbs=None` picks automatically: the WBS when the batch has one, the LLD
    Impact Analysis when it does not.
    """
    evidence: list[Evidence] = []
    notes: list[str] = []

    if use_wbs is None:
        use_wbs = workspace.has_wbs
    mode = "wbs" if use_wbs else "lld"
    if use_wbs and not workspace.has_wbs:
        notes.append("--use-wbs was requested but wbs.md has no tasks; "
                     "falling back to the LLD Impact Analysis.")
        use_wbs, mode = False, "lld"
    if not use_wbs:
        notes.append("Complexity derived from lld.md x.3 Impact Analysis "
                     "(Low/Med/High per layer), not from WBS task sizes.")

    tickets = workspace.requirements.tickets
    if not tickets:
        notes.append("requirements-summary.md lists no tickets with acceptance criteria; "
                     "no Details rows can be produced.")
        return Derivation(spec={"rows": [], "stories": []}, evidence=evidence,
                          notes=notes, mode=mode)

    stories, rows = [], []

    for ticket in tickets:
        stories.append({
            "epic": workspace.requirements.scope[:80] or "",
            "us_id": ticket.key,
            "us_summary": ticket.summary,
            "scope": scope_assessment(ticket, workspace, evidence),
            "reusability": reuse_levels(ticket, workspace, evidence),
        })

        story_tasks = [t for t in workspace.wbs.tasks
                       if t.story_key in ticket.key or ticket.key in t.story_key]

        for group in group_acs(ticket.acs):
            scope_label = f"{ticket.key} / {group.label}"
            sections = [s for s in (workspace.lld.ac(i) for i in group.ids) if s]

            if use_wbs:
                tasks = [t for t in story_tasks if set(t.ac_ids) & set(group.ids)]
                if not tasks:
                    notes.append(f"{scope_label}: no WBS task references this AC.")
                flags = complexity_flags(tasks, evidence, scope_label)
                column_d = technical_component(sections[0] if sections else None,
                                               tasks, workspace)
            else:
                impact_rows = [row for section in sections for row in section.impact]
                if not impact_rows:
                    notes.append(f"{scope_label}: the LLD has no Impact Analysis rows "
                                 f"for this AC.")
                flags = impact_complexity_flags(impact_rows, evidence, scope_label)
                column_d = technical_component_from_lld(sections, flags)

            if not any(sum(v) for v in flags.values()):
                flags["ms"] = [1, 0, 0]     # keep the row non-zero and visible
                column_d = f"{H.TBD} complexity unresolved.\n" + column_d

            rows.append({
                "user_story": ticket.key,
                "business_requirement": group.requirement_text(),
                "technical_component": column_d,
                **flags,
            })

        if use_wbs:
            orphans = [t for t in story_tasks if not t.ac_ids and t.dimension]
            if orphans:
                shared_flags = complexity_flags(orphans, evidence, f"{ticket.key} / Shared")
                rows.append({
                    "user_story": "Shared",
                    "group": ticket.key,
                    "business_requirement": "Cross-cutting tasks not tied to a single AC "
                                            "(data model, access control, audit, coordination).",
                    "technical_component": technical_component(None, orphans, workspace),
                    **shared_flags,
                })

    return Derivation(
        spec={
            "meta": {
                "batch": workspace.root.name,
                "source": f"Derived from {', '.join(sorted(workspace.sources.values()))} "
                          f"by cr-estimate ({mode} mode).",
                "mode": mode,
                "graphify_generated": workspace.graphify_generated,
            },
            "stories": stories,
            "rows": rows,
        },
        evidence=evidence,
        notes=notes,
        mode=mode,
    )
