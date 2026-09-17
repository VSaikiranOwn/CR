"""Parsers for the DCP harness stage-01 and stage-02 markdown artifacts.

These read the templates in `.github/templates/` as they are actually filled in:
`requirements-summary.md`, `hld.md`, `lld.md`, `wbs.md`. Parsing is deliberately
tolerant -- a half-filled section yields empty structures rather than an
exception, because a thin design should still produce a sheet with `[TBD]`
markers rather than a crash.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import constants as H

# Placeholder tokens the templates ship with; never treat these as real data.
PLACEHOLDER = re.compile(r"^(<.*>|\{\{.*\}\}|TODO\(fill\)|N/A|-|—|)$", re.I)


def is_placeholder(value: str | None) -> bool:
    return value is None or bool(PLACEHOLDER.match(str(value).strip()))


def clean(value: str | None) -> str:
    """Strip markdown emphasis and code ticks from a cell value."""
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"^\*\*(.*)\*\*$", r"\1", text)
    text = text.strip("`").strip()
    return text


# ---------------------------------------------------------------------------
# generic markdown helpers
# ---------------------------------------------------------------------------

def split_sections(text: str, level: int) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) pairs at the given heading level."""
    marker = "#" * level
    pattern = re.compile(rf"^{marker} +(.*)$", re.M)
    matches = list(pattern.finditer(text))
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[match.end():end]))
    return sections


def parse_tables(text: str) -> list[list[dict[str, str]]]:
    """Extract every markdown table in `text` as a list of row dicts."""
    tables: list[list[dict[str, str]]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            current.append(line.strip())
        elif current:
            table = _rows_from_lines(current)
            if table:
                tables.append(table)
            current = []
    if current:
        table = _rows_from_lines(current)
        if table:
            tables.append(table)
    return tables


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _rows_from_lines(lines: list[str]) -> list[dict[str, str]]:
    if len(lines) < 2:
        return []
    header = _cells(lines[0])
    # second line must be the ---|--- separator
    if not all(set(c) <= set("-: ") and c for c in _cells(lines[1])):
        return []
    rows = []
    for line in lines[2:]:
        cells = _cells(line)
        if len(cells) < len(header):
            cells += [""] * (len(header) - len(cells))
        rows.append({header[i]: cells[i] for i in range(len(header))})
    return rows


def find_table(tables: list[list[dict]], *required_columns: str) -> list[dict]:
    """Return the first table whose header contains all the given fragments."""
    wanted = [c.lower() for c in required_columns]
    for table in tables:
        if not table:
            continue
        header = " | ".join(table[0]).lower()
        if all(w in header for w in wanted):
            return table
    return []


def column(row: dict, *fragments: str) -> str:
    """Fetch a cell by fuzzy header match, so column renames don't break us."""
    for key, value in row.items():
        lowered = key.lower()
        if any(f.lower() in lowered for f in fragments):
            return clean(value)
    return ""


# ---------------------------------------------------------------------------
# 01-requirements/requirements-summary.md
# ---------------------------------------------------------------------------

@dataclass
class AcceptanceCriterion:
    id: str
    text: str


@dataclass
class Ticket:
    key: str
    summary: str
    acs: list[AcceptanceCriterion] = field(default_factory=list)


@dataclass
class Requirements:
    scope: str = ""
    tickets: list[Ticket] = field(default_factory=list)
    business_rules: list[str] = field(default_factory=list)
    traceability: list[dict] = field(default_factory=list)


TICKET_HEADING = re.compile(r"^(?P<key>[A-Z][A-Z0-9]+-\d+)\s*[—\-–:]\s*(?P<summary>.+)$")
AC_BULLET = re.compile(r"^\s*[-*]\s*\*\*(?P<id>AC-[\w.]+)\*\*\s*[—\-–:]?\s*(?P<text>.+)$", re.M)


def parse_requirements(text: str) -> Requirements:
    result = Requirements()

    for heading, body in split_sections(text, 2):
        lowered = heading.lower()
        if lowered.startswith("scope"):
            result.scope = _first_prose(body)
        elif "business rule" in lowered:
            result.business_rules = [
                clean(line.lstrip("-* ").strip())
                for line in body.splitlines()
                if line.strip().startswith(("-", "*")) and not is_placeholder(line.lstrip("-* "))
            ]
        elif "traceability" in lowered:
            tables = parse_tables(body)
            result.traceability = tables[0] if tables else []
        elif "acceptance criteria" in lowered:
            for ticket_heading, ticket_body in split_sections(body, 3):
                match = TICKET_HEADING.match(ticket_heading.strip())
                if not match:
                    continue
                ticket = Ticket(key=match.group("key"),
                                summary=clean(match.group("summary")))
                for ac in AC_BULLET.finditer(ticket_body):
                    ac_text = clean(ac.group("text"))
                    if is_placeholder(ac_text):
                        continue
                    ticket.acs.append(AcceptanceCriterion(id=ac.group("id"), text=ac_text))
                if not is_placeholder(ticket.key):
                    result.tickets.append(ticket)
    return result


def _first_prose(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith((">", "#", "|")) and not is_placeholder(stripped):
            return stripped
    return ""


# ---------------------------------------------------------------------------
# 02-design/wbs.md
# ---------------------------------------------------------------------------

TASK_ID = re.compile(r"WBS-(?P<story>.+?)-(?P<layer>BE|FE|DB|BPM|DOCS)-(?P<seq>\d+)$")
TASK_LINE = re.compile(
    r"^\s*[-*]\s*\[(?P<status>[ x\-])\]\s*\*\*(?P<id>WBS-[A-Za-z0-9\-.]+)\*\*\s*(?P<rest>.*)$"
)
SIZE_TOKEN = re.compile(r"\[(?P<size>[SML])\]")
AC_REF = re.compile(r"AC-[\w.]+")


@dataclass
class WbsTask:
    id: str
    story_key: str
    layer: str
    size: str | None
    ac_ids: list[str]
    repo: str = ""
    reuse_strategy: str = ""
    source_reference: str = ""
    what: str = ""
    test_slice: str = ""

    @property
    def dimension(self) -> str | None:
        return H.LAYER_TO_DIMENSION.get(self.layer)


@dataclass
class ApiRegisterEntry:
    capability: str
    existing_api: str
    service: str
    decision: str
    gap_justification: str
    evidence: str
    wbs_ids: list[str]


@dataclass
class Wbs:
    tasks: list[WbsTask] = field(default_factory=list)
    api_register: list[ApiRegisterEntry] = field(default_factory=list)
    summary: dict[str, str] = field(default_factory=dict)

    def tasks_for(self, ac_id: str, layer: str | None = None) -> list[WbsTask]:
        return [t for t in self.tasks
                if ac_id in t.ac_ids and (layer is None or t.layer == layer)]


def parse_wbs(text: str) -> Wbs:
    result = Wbs()
    lines = text.splitlines()

    for index, line in enumerate(lines):
        match = TASK_LINE.match(line)
        if not match:
            continue
        task_id = match.group("id")
        id_match = TASK_ID.match(task_id)
        if not id_match:
            continue

        rest = match.group("rest")
        size_match = SIZE_TOKEN.search(rest)
        task = WbsTask(
            id=task_id,
            story_key=id_match.group("story"),
            layer=id_match.group("layer"),
            size=size_match.group("size") if size_match else None,
            ac_ids=sorted(set(AC_REF.findall(rest))),
        )
        _absorb_task_body(task, lines, index + 1)
        result.tasks.append(task)

    tables = parse_tables(text)
    register = find_table(tables, "capability", "decision")
    for row in register:
        capability = column(row, "capability")
        if is_placeholder(capability):
            continue
        decision = column(row, "decision").upper()
        result.api_register.append(ApiRegisterEntry(
            capability=capability,
            existing_api=column(row, "existing api", "existing"),
            service=column(row, "service", "module"),
            decision=decision if decision in H.DECISION_TO_RUNG else "",
            gap_justification=column(row, "gap"),
            evidence=column(row, "evidence"),
            wbs_ids=sorted(set(re.findall(r"WBS-[A-Za-z0-9\-.]+", " ".join(row.values())))),
        ))

    for heading, body in split_sections(text, 2):
        if "brief summary" in heading.lower():
            for line in body.splitlines():
                bullet = re.match(r"^\s*[-*]\s*\*\*(?P<k>[^:]+):\*\*\s*(?P<v>.+)$", line)
                if bullet and not is_placeholder(bullet.group("v")):
                    result.summary[bullet.group("k").strip().lower()] = clean(bullet.group("v"))
    return result


TASK_FIELDS = {
    "repo": "repo",
    "reuse strategy": "reuse_strategy",
    "source api/reference": "source_reference",
    "source api": "source_reference",
    "what": "what",
    "tdd slice (red first)": "test_slice",
    "tdd slice": "test_slice",
}


def _absorb_task_body(task: WbsTask, lines: list[str], start: int) -> None:
    """Read the indented `- **Key:** value` lines that follow a task bullet."""
    for line in lines[start:]:
        if TASK_LINE.match(line) or (line.strip().startswith("#")):
            return
        field_match = re.match(r"^\s+[-*]\s*\*\*(?P<key>[^:]+):\*\*\s*(?P<value>.*)$", line)
        if not field_match:
            if line.strip() and not line.startswith((" ", "\t")):
                return
            continue
        key = field_match.group("key").strip().lower()
        attribute = TASK_FIELDS.get(key)
        if attribute:
            value = clean(field_match.group("value"))
            if not is_placeholder(value):
                setattr(task, attribute, value)


# ---------------------------------------------------------------------------
# 02-design/lld.md
# ---------------------------------------------------------------------------

@dataclass
class ReuseCandidate:
    candidate: str
    location: str
    satisfies: str
    level: int | None
    decision: str
    evidence: str

    def dimension(self) -> str | None:
        """Which CR reuse dimension this candidate belongs to."""
        location = self.location.lower()
        if any(p in location for p in H.FRONTEND_PREFIXES):
            return "frontend"
        if H.BACKEND_PREFIX in location:
            return "backend"
        if "/api/" in location or location.startswith(("get ", "post ", "put ", "delete ")):
            return "interface"
        if re.search(r"\b\w+\.\w+\b", location) and "." in location and "/" not in location:
            return "database"
        return None


@dataclass
class ImpactRow:
    layer: str
    component: str
    impact: str
    change_required: str


@dataclass
class AcSection:
    id: str
    title: str
    impact: list[ImpactRow] = field(default_factory=list)
    reuse: list[ReuseCandidate] = field(default_factory=list)
    alternate_flows: list[str] = field(default_factory=list)
    screens: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    endpoints: list[str] = field(default_factory=list)
    bpm_steps: list[dict] = field(default_factory=list)
    bpm_process: str = ""
    no_bpm: bool = False
    participants: list[str] = field(default_factory=list)


@dataclass
class Lld:
    story_key: str = ""
    story_title: str = ""
    acs: list[AcSection] = field(default_factory=list)
    changes_summary: list[dict] = field(default_factory=list)
    reuse_percentages: list[dict] = field(default_factory=list)
    blast_radius: list[dict] = field(default_factory=list)

    def ac(self, ac_id: str) -> AcSection | None:
        return next((a for a in self.acs if a.id == ac_id), None)


AC_HEADING = re.compile(r"^(?P<id>AC-[\w.]+)\s*:\s*(?P<title>.*)$")
SCREEN_REF = re.compile(r"screens/([\w\-.]+\.(?:png|jpg|jpeg|svg))", re.I)
ENDPOINT = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[\w{}/\-.]+)")
COMPONENT_HEADING = re.compile(r"^Component:\s*`?(?P<name>[\w.]+)`?", re.I)
PARTICIPANT = re.compile(r"^\s*participant\s+(\w+)(?:\s+as\s+(.+))?$", re.M | re.I)
STORY_LINE = re.compile(r"^\*\*Story:\*\*\s*(?P<key>[A-Z][A-Z0-9]+-\d+)\s*:?\s*(?P<title>.*)$", re.M)


def parse_lld(text: str) -> Lld:
    result = Lld()

    story = STORY_LINE.search(text)
    if story and not is_placeholder(story.group("key")):
        result.story_key = story.group("key")
        result.story_title = clean(story.group("title"))

    for heading, body in split_sections(text, 3):
        lowered = heading.lower()
        tables = parse_tables(body)
        if "changes summary" in lowered and tables:
            result.changes_summary = tables[0]
        elif "code reuse summary" in lowered and tables:
            result.reuse_percentages = tables[0]
        elif "blast-radius" in lowered and tables:
            result.blast_radius = tables[0]

    for heading, body in split_sections(text, 2):
        match = AC_HEADING.match(heading.strip())
        if not match:
            continue
        section = AcSection(id=match.group("id"), title=clean(match.group("title")))
        _parse_ac_body(section, body)
        result.acs.append(section)
    return result


def _parse_ac_body(section: AcSection, body: str) -> None:
    for sub_heading, sub_body in split_sections(body, 3):
        lowered = sub_heading.lower()
        tables = parse_tables(sub_body)

        if "impact analysis" in lowered:
            for row in find_table(tables, "layer", "impact"):
                layer = column(row, "layer")
                if is_placeholder(layer):
                    continue
                section.impact.append(ImpactRow(
                    layer=layer,
                    component=column(row, "component", "service"),
                    impact=column(row, "impact"),
                    change_required=column(row, "change required", "change"),
                ))

        elif "reusability assessment" in lowered:
            for row in find_table(tables, "candidate", "decision"):
                candidate = column(row, "candidate")
                if is_placeholder(candidate):
                    continue
                section.reuse.append(ReuseCandidate(
                    candidate=candidate,
                    location=column(row, "location"),
                    satisfies=column(row, "satisfies"),
                    level=_reuse_rung(column(row, "reuse level", "level")),
                    decision=column(row, "decision").upper(),
                    evidence=column(row, "gap justification", "evidence"),
                ))

        elif "alternate flow" in lowered:
            for row in find_table(tables, "flow"):
                flow = column(row, "flow")
                if not is_placeholder(flow):
                    section.alternate_flows.append(flow)

        elif "ui change" in lowered:
            section.screens += [m.group(1) for m in SCREEN_REF.finditer(sub_body)]
            for line in sub_body.splitlines():
                comp = COMPONENT_HEADING.match(line.strip().lstrip("#").strip())
                if comp and not is_placeholder(comp.group("name")):
                    section.components.append(comp.group("name"))

        elif "microservice change" in lowered:
            section.endpoints += [f"{m.group(1)} {m.group(2)}" for m in ENDPOINT.finditer(sub_body)]
            for match in PARTICIPANT.finditer(sub_body):
                alias = clean(match.group(1))
                label = clean(match.group(2) or match.group(1))
                if not _is_internal(alias) and not _is_internal(label):
                    section.participants.append(label)

        elif "bpm change" in lowered:
            if re.search(r"no bpm changes? required", sub_body, re.I):
                section.no_bpm = True
            process = re.search(r"\*\*Process:\*\*\s*`?([^`\n·]+)`?", sub_body)
            if process and not is_placeholder(process.group(1)):
                section.bpm_process = clean(process.group(1))
            for row in find_table(tables, "step", "type"):
                if not is_placeholder(column(row, "step")):
                    section.bpm_steps.append(row)

    section.screens = sorted(set(section.screens))
    section.endpoints = sorted(set(section.endpoints))
    section.components = sorted(set(section.components))
    section.participants = sorted(set(section.participants))


def _is_internal(name: str) -> bool:
    """True for our own services/UI, which are not 'integrations with external parties'."""
    lowered = name.strip().lower()
    return (lowered in H.INTERNAL_PARTICIPANTS
            or lowered.startswith(H.INTERNAL_PARTICIPANT_PREFIXES))


def _reuse_rung(value: str) -> int | None:
    """Accept either the 0/1/2/4 rung or the None/Low/Moderate/High wording.

    lld.md declares the column as "Reuse Level (0/1/2/4)" but its own sample row
    writes the words, so real files carry both.
    """
    text = clean(value).lower()
    if is_placeholder(text):
        return None
    for token in re.split(r"[\s/|,]+", text):
        if token in H.REUSE_WORD_TO_RUNG:
            return H.REUSE_WORD_TO_RUNG[token]
    return None


# ---------------------------------------------------------------------------
# 02-design/hld.md
# ---------------------------------------------------------------------------

@dataclass
class Hld:
    overview: str = ""
    modules: str = ""
    integrations: list[str] = field(default_factory=list)
    api_surface: list[str] = field(default_factory=list)
    data_model: str = ""


KNOWN_INTEGRATIONS = ("CPF", "IRAS", "SAL", "MyInfo", "bank", "mortgage", "BPM", "ELS")


def parse_hld(text: str) -> Hld:
    result = Hld()
    for heading, body in split_sections(text, 2):
        lowered = heading.lower()
        if "overview" in lowered:
            result.overview = _first_prose(body)
        elif "affected dcp modules" in lowered:
            result.modules = _first_prose(body)
        elif "integration" in lowered:
            result.integrations = _integration_items(body)
        elif "api surface" in lowered:
            result.api_surface = [f"{m.group(1)} {m.group(2)}" for m in ENDPOINT.finditer(body)]
        elif "data model" in lowered:
            result.data_model = _first_prose(body)
    return result


def _integration_items(body: str) -> list[str]:
    items: list[str] = []
    for line in body.splitlines():
        stripped = line.strip().lstrip("-*").strip()
        if not stripped or stripped.startswith((">", "#", "<")) or is_placeholder(stripped):
            continue
        items.append(clean(stripped))
    if not items:
        return []
    # A single prose line listing touchpoints: split it into named systems.
    if len(items) == 1:
        named = [name for name in KNOWN_INTEGRATIONS
                 if re.search(rf"\b{re.escape(name)}\b", items[0], re.I)]
        if named:
            return named
    return items


# ---------------------------------------------------------------------------
# workspace loading
# ---------------------------------------------------------------------------

VERSIONED = re.compile(r"^(?P<stem>hld|lld)-v(?P<version>\d+)\.md$", re.I)


def resolve_design_doc(root: Path, stem: str) -> Path | None:
    """Find the document to use for `hld` or `lld`.

    Batches keep numbered snapshots in `02-design/versions/` alongside a working
    `02-design/<stem>.md`. The highest version number always wins.

    Deliberately NOT modification time: mtimes do not survive a copy, a fresh
    clone or an unzip, so a timestamp rule silently picks the wrong document
    depending on how the batch reached the machine. The version number is
    written by whoever authored the snapshot and travels with the file.
    Override with --hld / --lld when you need a specific one.
    """
    design = root / H.DESIGN_DIR
    plain = design / f"{stem}.md"

    newest_version: tuple[int, Path] | None = None
    versions = root / H.VERSIONS_DIR
    if versions.is_dir():
        for path in versions.iterdir():
            match = VERSIONED.match(path.name)
            if match and match.group("stem").lower() == stem:
                candidate = (int(match.group("version")), path)
                if newest_version is None or candidate[0] > newest_version[0]:
                    newest_version = candidate

    if newest_version is not None:
        return newest_version[1]
    return plain if plain.is_file() else None


@dataclass
class Workspace:
    root: Path
    requirements: Requirements
    hld: Hld
    lld: Lld
    wbs: Wbs
    missing: list[str] = field(default_factory=list)
    graphify_generated: str | None = None
    sources: dict[str, str] = field(default_factory=dict)

    @property
    def has_wbs(self) -> bool:
        return bool(self.wbs.tasks)


def load_workspace(root: str | Path, hld_path: str | Path | None = None,
                   lld_path: str | Path | None = None) -> Workspace:
    root = Path(root)
    if not root.is_dir():
        raise NotADirectoryError(f"Batch workspace not found: {root}")

    missing: list[str] = []
    sources: dict[str, str] = {}

    def read(relative: str) -> str:
        path = root / relative
        if not path.is_file():
            missing.append(relative)
            return ""
        sources[Path(relative).stem] = relative
        return path.read_text(encoding="utf-8")

    def read_design(stem: str, override: str | Path | None) -> str:
        path = Path(override) if override else resolve_design_doc(root, stem)
        if path is None or not path.is_file():
            missing.append(f"{H.DESIGN_DIR}/{stem}.md")
            return ""
        try:
            shown = path.relative_to(root).as_posix()
        except ValueError:
            shown = str(path)
        sources[stem] = shown
        return path.read_text(encoding="utf-8")

    workspace = Workspace(
        root=root,
        requirements=parse_requirements(read(H.REQUIREMENTS_SUMMARY)),
        hld=parse_hld(read_design("hld", hld_path)),
        lld=parse_lld(read_design("lld", lld_path)),
        wbs=parse_wbs(read(H.WBS) if (root / H.WBS).is_file() else ""),
        missing=missing,
        sources=sources,
    )

    graphify = root / H.GRAPHIFY_DIR
    if graphify.is_dir():
        stamps = [p.stat().st_mtime for p in graphify.rglob("*") if p.is_file()]
        if stamps:
            from datetime import datetime, timezone
            workspace.graphify_generated = datetime.fromtimestamp(
                max(stamps), tz=timezone.utc).strftime("%Y-%m-%d")
    return workspace
