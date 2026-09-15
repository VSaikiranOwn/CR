"""A Python mirror of every formula the workbook carries.

The workbook ships *live* formulas -- Excel recalculates them on open. These
functions exist so the CLI can print the numbers without Excel, and so the test
suite can prove the generated formulas agree with the framework's arithmetic.
Any change here must be mirrored in :mod:`cr_tool.render` and vice versa.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import constants as K


def xl_round(value: float, digits: int = 0) -> float:
    """Excel's ROUND: half away from zero (Python's round() is half to even)."""
    factor = 10 ** digits
    scaled = value * factor
    if scaled >= 0:
        rounded = math.floor(scaled + 0.5)
    else:
        rounded = -math.floor(-scaled + 0.5)
    return rounded / factor if digits else rounded


# ---------------------------------------------------------------------------
# Details sheet
# ---------------------------------------------------------------------------

def row_dev_effort_raw(row) -> float:
    """Unrounded DEV effort in MD for one Details row (mirrors column Q)."""
    ui, ms, db, bpm = row.ui, row.ms, row.db, row.bpm
    return (
        (ui[0] + ms[0] + bpm[0]) * K.WEIGHT_SIMPLE
        + (ui[1] + ms[1] + bpm[1]) * K.WEIGHT_MEDIUM
        + (ui[2] + ms[2] + bpm[2]) * K.WEIGHT_COMPLEX
        + db[0] * K.WEIGHT_DB_SIMPLE
        + db[1] * K.WEIGHT_DB_MEDIUM
        + db[2] * K.WEIGHT_DB_COMPLEX
    )


def row_dev_effort(row) -> int:
    return int(xl_round(row_dev_effort_raw(row)))


def details_total(rows) -> int:
    return sum(row_dev_effort(row) for row in rows)


# ---------------------------------------------------------------------------
# Summary sheet
# ---------------------------------------------------------------------------

@dataclass
class SummaryTotals:
    development: int
    qa: int
    req_design: int

    @property
    def total(self) -> int:
        return self.development + self.qa + self.req_design


def summary_totals(development: int) -> SummaryTotals:
    return SummaryTotals(
        development=development,
        qa=int(xl_round(development * K.SUMMARY_QA_RATIO)),
        req_design=int(xl_round(development * K.SUMMARY_RND_RATIO)),
    )


# ---------------------------------------------------------------------------
# Tender Story Points sheet
# ---------------------------------------------------------------------------

@dataclass
class StoryPoints:
    framework_unit: float
    reusability_score: float
    adjustment_pct: float
    framework_unit_adjusted: float
    req_design_unit: float
    tsp: float


def framework_unit(story) -> float:
    """Column K: sum of (size unit x complexity index) over the scope dimensions."""
    total = 0.0
    for dimension in K.SCOPE_DIMENSIONS:
        units = K.SCOPE_SIZE_UNITS[story.scope[dimension].size]
        total += units * K.SCOPE_INDEX[dimension]
    return total


def reusability_score(story) -> float:
    """Column V: mean reusability across applicable dimensions, as a percentage."""
    scores = [
        K.REUSE_LEVEL_SCORES[story.reusability[dimension].level]
        for dimension in K.REUSE_DIMENSIONS
    ]
    applicable = [s for s in scores if s is not None]
    if not applicable:
        return 0.0
    return sum(applicable) / (len(applicable) * K.REUSE_MAX_SCORE) * 100


def adjustment_pct(score: float) -> float:
    """Column W: the reusability discount band the score falls into."""
    for ceiling, adjustment in K.ADJUSTMENT_BANDS[:-1]:
        if score <= ceiling:
            return adjustment
    return K.ADJUSTMENT_BANDS[-1][1]


def story_points(story) -> StoryPoints:
    unit = framework_unit(story)
    score = reusability_score(story)
    adjustment = adjustment_pct(score)
    adjusted = unit * (1 - adjustment)
    req_design = adjusted * K.REQ_DESIGN_UNIT_RATIO
    return StoryPoints(
        framework_unit=unit,
        reusability_score=score,
        adjustment_pct=adjustment,
        framework_unit_adjusted=adjusted,
        req_design_unit=req_design,
        tsp=(adjusted + req_design) * K.TSP_FACTOR,
    )
