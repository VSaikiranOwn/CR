"""Load, normalise and validate a CR spec.

The spec is the only thing that changes between CRs. Copilot writes it from the
Figma screens / user stories / HLD / LLD; this module turns whatever it wrote
into a strict, normalised structure and refuses anything the template could not
represent.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import constants as K


class SpecError(ValueError):
    """The spec is malformed in a way that would produce an invalid workbook."""


@dataclass
class ScopeEntry:
    size: str
    details: str = ""


@dataclass
class ReuseEntry:
    level: str
    details: str = ""


@dataclass
class Story:
    epic: str
    us_id: str
    us_summary: str
    scope: dict[str, ScopeEntry]
    reusability: dict[str, ReuseEntry]


@dataclass
class DetailRow:
    user_story: str
    business_requirement: str
    technical_component: str
    ui: list[int]
    ms: list[int]
    db: list[int]
    bpm: list[int]
    group: str | None = None
    s_no: int | None = None

    def counts(self, dimension: str) -> list[int]:
        return getattr(self, dimension)


@dataclass
class Spec:
    rows: list[DetailRow]
    stories: list[Story] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    original_efforts: dict[str, float] | None = None
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _normalise_choice(raw: Any, canonical: tuple[str, ...], aliases: dict[str, str],
                      what: str, where: str) -> str:
    if raw is None:
        return K.NOT_APPLICABLE
    text = str(raw).strip()
    if text in canonical:
        return text
    key = text.lower()
    if key in aliases:
        return aliases[key]
    # Tolerate the template's own "Resuability" typo and stray double spaces.
    key = key.replace("resuability", "reusability").replace("  ", " ")
    if key in aliases:
        return aliases[key]
    for option in canonical:
        if option.lower() == key:
            return option
    raise SpecError(
        f"{where}: {what} {text!r} is not a valid option. "
        f"Use one of {list(canonical)} (or a shorthand such as 'S'/'M'/'L', '0'/'1'/'2'/'4', 'NA')."
    )


def _normalise_counts(raw: Any, dimension: str, where: str) -> list[int]:
    if raw is None:
        return [0, 0, 0]
    if isinstance(raw, dict):
        raw = [raw.get(level, 0) or 0 for level in K.COMPLEXITIES]
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        raise SpecError(
            f"{where}: '{dimension}' must be a 3-element list "
            f"[simple, medium, complex], got {raw!r}."
        )
    counts = []
    for value, level in zip(raw, K.COMPLEXITIES):
        if value in (None, "", False):
            value = 0
        if isinstance(value, bool):
            value = int(value)
        if not isinstance(value, (int, float)) or value != int(value) or value < 0:
            raise SpecError(
                f"{where}: '{dimension}.{level}' must be a non-negative whole number, got {value!r}."
            )
        counts.append(int(value))
    return counts


def _require_text(mapping: dict, key: str, where: str, *, allow_empty: bool = False) -> str:
    value = mapping.get(key)
    if value is None:
        value = ""
    text = str(value).strip()
    if not text and not allow_empty:
        raise SpecError(f"{where}: '{key}' is required and must not be empty.")
    return text


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

def _parse_story(raw: dict, index: int) -> Story:
    where = f"stories[{index}]"
    if not isinstance(raw, dict):
        raise SpecError(f"{where}: expected an object, got {type(raw).__name__}.")

    scope_raw = raw.get("scope") or {}
    reuse_raw = raw.get("reusability") or raw.get("reuse") or {}

    scope: dict[str, ScopeEntry] = {}
    for dimension in K.SCOPE_DIMENSIONS:
        entry = scope_raw.get(dimension) or {}
        if isinstance(entry, str):
            entry = {"size": entry}
        size = _normalise_choice(entry.get("size"), K.SCOPE_SIZES, K.SCOPE_SIZE_ALIASES,
                                 f"scope.{dimension}", where)
        scope[dimension] = ScopeEntry(size=size, details=str(entry.get("details") or "").strip())

    reusability: dict[str, ReuseEntry] = {}
    for dimension in K.REUSE_DIMENSIONS:
        entry = reuse_raw.get(dimension) or {}
        if isinstance(entry, (str, int)):
            entry = {"level": entry}
        level = _normalise_choice(entry.get("level"), K.REUSE_LEVELS, K.REUSE_LEVEL_ALIASES,
                                  f"reusability.{dimension}", where)
        reusability[dimension] = ReuseEntry(level=level, details=str(entry.get("details") or "").strip())

    return Story(
        epic=_require_text(raw, "epic", where, allow_empty=True),
        us_id=_require_text(raw, "us_id", where),
        us_summary=_require_text(raw, "us_summary", where, allow_empty=True),
        scope=scope,
        reusability=reusability,
    )


def _parse_row(raw: dict, index: int) -> DetailRow:
    where = f"rows[{index}]"
    if not isinstance(raw, dict):
        raise SpecError(f"{where}: expected an object, got {type(raw).__name__}.")

    row = DetailRow(
        user_story=_require_text(raw, "user_story", where),
        business_requirement=_require_text(raw, "business_requirement", where),
        technical_component=_require_text(raw, "technical_component", where),
        ui=_normalise_counts(raw.get("ui"), "ui", where),
        ms=_normalise_counts(raw.get("ms"), "ms", where),
        db=_normalise_counts(raw.get("db"), "db", where),
        bpm=_normalise_counts(raw.get("bpm"), "bpm", where),
        group=(str(raw["group"]).strip() if raw.get("group") else None),
    )
    if raw.get("s_no") is not None:
        row.s_no = int(raw["s_no"])
    if not any(sum(row.counts(d)) for d in K.DETAILS_DIMENSIONS):
        raise SpecError(
            f"{where}: no component flags set. Every Details row must flag at least one "
            f"UI / MS / DB / BPM complexity, otherwise its effort is 0 MD."
        )
    return row


def assign_groups(rows: list[DetailRow]) -> None:
    """Fill in ``group`` and restart ``s_no`` at 1 for each user-story group.

    The ver_2 workbook numbers Details rows per story group, not continuously,
    and a trailing ``Shared`` row belongs to the group above it.
    """
    current = None
    for row in rows:
        if row.group:
            current = row.group
        elif row.user_story.strip().lower() != "shared":
            current = row.user_story
        elif current is None:
            current = row.user_story
        row.group = current

    counter: dict[str, int] = {}
    for row in rows:
        key = row.group or ""
        counter[key] = counter.get(key, 0) + 1
        if row.s_no is None:
            row.s_no = counter[key]


def _parse_original_efforts(raw: Any) -> dict[str, float] | None:
    if not raw:
        return None
    if not isinstance(raw, dict):
        raise SpecError("summary.original_efforts must be an object.")
    keys = {"development": "development", "dev": "development",
            "qa": "qa",
            "req_design": "req_design", "rnd": "req_design",
            "requirement_and_design": "req_design"}
    out: dict[str, float] = {}
    for key, value in raw.items():
        canonical = keys.get(str(key).lower())
        if canonical is None:
            raise SpecError(
                f"summary.original_efforts: unknown key {key!r}; "
                f"expected 'development', 'qa' and/or 'req_design'."
            )
        out[canonical] = float(value)
    return out


def parse(data: dict) -> Spec:
    """Turn a raw spec dict into a validated :class:`Spec`."""
    if not isinstance(data, dict):
        raise SpecError("Spec must be a JSON object.")

    raw_rows = data.get("rows")
    if not raw_rows:
        raise SpecError("Spec has no 'rows'. At least one Details row is required.")
    if not isinstance(raw_rows, list):
        raise SpecError("'rows' must be a list.")

    rows = [_parse_row(row, i) for i, row in enumerate(raw_rows)]
    assign_groups(rows)

    raw_stories = data.get("stories") or []
    if not isinstance(raw_stories, list):
        raise SpecError("'stories' must be a list.")
    stories = [_parse_story(story, i) for i, story in enumerate(raw_stories)]

    summary_cfg = data.get("summary") or {}
    if not isinstance(summary_cfg, dict):
        raise SpecError("'summary' must be an object.")
    for legacy in ("qa_ratio", "rnd_ratio"):
        if legacy in summary_cfg:
            raise SpecError(
                f"summary.{legacy} is not supported: QA (40%) and Requirement & Design (20%) "
                f"are fixed for this framework and live in the MasterData sheet."
            )

    spec = Spec(
        rows=rows,
        stories=stories,
        meta=data.get("meta") or {},
        original_efforts=_parse_original_efforts(summary_cfg.get("original_efforts")),
    )
    spec.warnings = collect_warnings(spec)
    return spec


def collect_warnings(spec: Spec) -> list[str]:
    """Non-fatal findings worth showing the estimator before they ship the sheet."""
    from .compute import row_dev_effort

    warnings: list[str] = []

    for index, row in enumerate(spec.rows):
        effort = row_dev_effort(row)
        if effort > K.ROW_MD_SOFT_MAX:
            warnings.append(
                f"rows[{index}] ({row.user_story}) is {effort} MD, above the "
                f"{K.ROW_MD_SOFT_MAX} MD guideline -- consider splitting it."
            )
        flags = sum(sum(row.counts(d)) for d in K.DETAILS_DIMENSIONS)
        if flags > 3:
            warnings.append(
                f"rows[{index}] ({row.user_story}) carries {flags} component flags; "
                f"the template convention is 1-3 per row."
            )

    if spec.stories:
        story_ids = {s.us_id for s in spec.stories}
        detail_ids = {r.user_story for r in spec.rows if r.user_story.strip().lower() != "shared"}
        for missing in sorted(detail_ids - story_ids):
            warnings.append(
                f"Details references user story {missing!r} but it has no row on the "
                f"'{K.SHEET_TSP}' sheet."
            )
        for unused in sorted(story_ids - detail_ids):
            warnings.append(
                f"'{K.SHEET_TSP}' lists {unused!r} but no Details row estimates it."
            )
    else:
        warnings.append(
            f"No 'stories' in the spec, so the '{K.SHEET_TSP}' sheet will be left blank."
        )

    return warnings


def load(path: str | Path) -> Spec:
    """Read a spec JSON file and validate it."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SpecError(f"Spec file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SpecError(f"{path}: invalid JSON -- {exc}") from None
    return parse(strip_help_keys(raw))


def strip_help_keys(value):
    """Drop the "//" comment keys the starter spec ships with, at any depth."""
    if isinstance(value, dict):
        return {k: strip_help_keys(v) for k, v in value.items()
                if not str(k).startswith("//")}
    if isinstance(value, list):
        return [strip_help_keys(v) for v in value]
    return value
