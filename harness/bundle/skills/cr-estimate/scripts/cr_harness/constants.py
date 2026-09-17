"""Mapping constants for the DCP harness -> CR framework bridge.

Everything here is a *calibration knob*: the values encode judgement about how
WBS task sizes and LLD reuse levels translate into the CR sheet, and they should
be tuned against a batch whose CR sheet was produced by hand. They are kept in
one place, and `cr-estimate rules` prints them, so a reviewer can see exactly
what produced a number.

The CR framework's own arithmetic (effort weights, ratios, TSP chain) is NOT
here -- that lives in cr_tool.constants and is fixed by the company template.
"""
from __future__ import annotations

# --------------------------------------------------------------------------
# WBS layer -> CR sheet dimension
# --------------------------------------------------------------------------
# DOCS carries no CR dimension: documentation effort is already inside the
# Requirement & Design ratio (20% of Dev). Counting it again would double it.
# QA likewise has no WBS layer -- test slices live inside BE/FE tasks and QA
# effort is the 40% ratio.
LAYER_TO_DIMENSION = {
    "FE": "ui",
    "BE": "ms",
    "DB": "db",
    "BPM": "bpm",
    "DOCS": None,
}
WBS_LAYERS = tuple(LAYER_TO_DIMENSION)

# --------------------------------------------------------------------------
# WBS task size -> CR complexity
# --------------------------------------------------------------------------
SIZE_ORDER = ("S", "M", "L")
SIZE_TO_COMPLEXITY = {"S": "simple", "M": "medium", "L": "complex"}

# A layer with this many tasks at its top size on one AC is promoted one rung
# (S->M, M->L, L stays). Rationale: five medium backend tasks on a single AC is
# not a medium change. CALIBRATE THIS against a known-good CR sheet.
PROMOTE_AT_COUNT = 3

# --------------------------------------------------------------------------
# LLD-only mode: complexity from section x.3 Impact Analysis
# --------------------------------------------------------------------------
# When there is no wbs.md, the per-AC Impact Analysis table is the best
# available signal: it already states a layer and a Low/Med/High impact per
# touched component, which is the same shape as a task size.
IMPACT_TO_COMPLEXITY = {
    "low": "simple",
    "medium": "medium", "med": "medium", "moderate": "medium",
    "high": "complex",
}

# lld.md x.3 / Changes Summary layer names -> CR sheet dimension.
# Integration and Access Control are backend work; the sheet has no column of
# their own for them.
LLD_LAYER_TO_DIMENSION = {
    "frontend": "ui", "fe": "ui", "ui": "ui",
    "backend": "ms", "be": "ms", "microservice": "ms", "service": "ms",
    "integration": "ms", "access control": "ms", "security": "ms",
    "database": "db", "db": "db", "data": "db",
    "bpm": "bpm", "workflow": "bpm",
}

# --------------------------------------------------------------------------
# Reuse levels -- the CR ladder, which lld.md section x.4 already uses
# --------------------------------------------------------------------------
REUSE_RUNGS = (0, 1, 2, 4)

# lld.md x.4 declares the column as "Reuse Level (0/1/2/4)" but its own sample
# row writes High/Moderate/Low/None. Both appear in real files; both are the
# same ladder, so accept either.
REUSE_WORD_TO_RUNG = {
    "none": 0, "no": 0, "0": 0,
    "low": 1, "1": 1,
    "moderate": 2, "medium": 2, "2": 2,
    "high": 4, "4": 4,
}

# WBS section 2.1 API Reuse Register decision -> Interface reuse rung.
# Mirrors the Readme ladder: NEW endpoints to establish = 0, most existing
# endpoints reusable = 4.
DECISION_TO_RUNG = {"REUSE": 4, "EXTEND": 2, "NEW": 0}

# QA reuse is a proxy: a test slice hanging off a REUSE task usually adds a
# method to an existing test class; one hanging off a NEW task usually means a
# new class. Same mapping, different evidence -- flagged as derived.
QA_DECISION_TO_RUNG = dict(DECISION_TO_RUNG)

# --------------------------------------------------------------------------
# Location prefix -> reuse dimension (lld.md x.4 "Location" column)
# --------------------------------------------------------------------------
FRONTEND_PREFIXES = ("web-react", "src/components", "src/pages")
BACKEND_PREFIX = "ms-"

# --------------------------------------------------------------------------
# Scope Assessment banding (counts -> the sheet's dropdown sizes)
# --------------------------------------------------------------------------
SCOPE_BANDS = ((3, "Small (1-3)"), (6, "Medium (4-6)"))
SCOPE_LARGE = "Large (>6)"

# Sequence-diagram participants that are internal, so not integrations.
# The Scope Assessment counts integrations with EXTERNAL parties only, so the
# services under change (ms-*) and our own frontend never count.
INTERNAL_PARTICIPANTS = {
    "user", "actor", "fe", "web-react", "ui", "frontend", "browser", "svc",
    "db", "postgresql", "postgres", "database", "gw", "api gateway", "gateway",
    "service", "app",
}
INTERNAL_PARTICIPANT_PREFIXES = ("ms-", "web-")

# --------------------------------------------------------------------------
# WBS reuse decision -> the CR's column D endpoint label
# --------------------------------------------------------------------------
DECISION_TO_LABEL = {
    "REUSE": "EXISTING to REUSE/CHECK",
    "EXTEND": "EXISTING to MODIFY",
    "NEW": "NEW API",
}

# --------------------------------------------------------------------------
# Harness workspace layout
# --------------------------------------------------------------------------
REQUIREMENTS_SUMMARY = "01-requirements/requirements-summary.md"
DESIGN_DIR = "02-design"
VERSIONS_DIR = "02-design/versions"
HLD = "02-design/hld.md"
LLD = "02-design/lld.md"
WBS = "02-design/wbs.md"
GRAPHIFY_DIR = "02-design/graphify"
CR_DIR = "02-design/cr"
CR_SPEC = "cr-spec.json"
CR_EVIDENCE = "cr-evidence.md"

TBD = "[TBD: verify]"
DRAFT_SCOPE = "[DRAFT: business team to confirm]"
