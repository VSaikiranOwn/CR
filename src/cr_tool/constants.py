"""Fixed constants of the CR Estimation Framework (ver. 2).

Nothing in this module is configurable per CR. The weights, the sheet layout
and the dropdown vocabularies are properties of the company template; changing
them would produce a workbook that no longer reconciles with previous CRs.
"""
from __future__ import annotations

TEMPLATE_NAME = "cr_framework_template.xlsx"

SHEET_README = "Readme (Definitions)"
SHEET_MASTERDATA = "MasterData"
SHEET_TSP = "Tender Story Points"
SHEET_DETAILS = "Details"
SHEET_SUMMARY = "Summary"

# --------------------------------------------------------------------------
# Details sheet
# --------------------------------------------------------------------------
DETAILS_FIRST_DATA_ROW = 3
# The row the template's own Total sits on. Used only as a style donor -- the
# generated Total row follows the data.
DETAILS_TEMPLATE_TOTAL_ROW = 12

DETAILS_COL = {
    "s_no": 1,               # A
    "user_story": 2,         # B
    "business_requirement": 3,   # C
    "technical_component": 4,    # D
    "ui": 5,                 # E,F,G  Simple / Medium / Complex
    "ms": 8,                 # H,I,J
    "db": 11,                # K,L,M
    "bpm": 14,               # N,O,P
    "dev_efforts": 17,       # Q
}
DETAILS_LAST_COL = 17
DETAILS_DIMENSIONS = ("ui", "ms", "db", "bpm")
COMPLEXITIES = ("simple", "medium", "complex")

# Effort weights, in man-days per flagged component.
# UI, MS and BPM share one set; DB is deliberately lighter.
# These reproduce the ver_2 workbook formula exactly -- do not "tidy" them.
WEIGHT_SIMPLE = 1.5
WEIGHT_MEDIUM = 3
WEIGHT_COMPLEX = 5
WEIGHT_DB_SIMPLE = 0.25
WEIGHT_DB_MEDIUM = 0.5
WEIGHT_DB_COMPLEX = 1

# Sanity band for a single Details row, in MD. Outside this, the row is
# probably doing too much (or too little) and should be split or merged.
ROW_MD_SOFT_MIN = 1
ROW_MD_SOFT_MAX = 10

# --------------------------------------------------------------------------
# Tender Story Points sheet
# --------------------------------------------------------------------------
TSP_FIRST_DATA_ROW = 3

TSP_COL = {
    "s_no": 1,            # A
    "epic": 2,            # B
    "us_id": 3,           # C
    "us_summary": 4,      # D
    "user_interaction": 5,        # E
    "user_interaction_details": 6,   # F
    "pages": 7,           # G
    "pages_details": 8,   # H
    "integration": 9,     # I
    "integration_details": 10,   # J
    "framework_unit": 11,     # K  (formula)
    "frontend": 12,       # L
    "frontend_details": 13,   # M
    "backend": 14,        # N
    "backend_details": 15,    # O
    "interface": 16,      # P
    "interface_details": 17,  # Q
    "database": 18,       # R
    "database_details": 19,   # S
    "qa": 20,             # T
    "qa_details": 21,     # U
    "reusability_score": 22,  # V  (array formula)
    "adjustment_pct": 23,     # W  (formula)
    "framework_unit_adj": 24, # X  (formula)
    "req_design_unit": 25,    # Y  (formula)
    "tsp": 26,                # Z  (formula)
}
TSP_LAST_COL = 26

SCOPE_DIMENSIONS = ("user_interaction", "pages", "integration")
REUSE_DIMENSIONS = ("frontend", "backend", "interface", "database", "qa")

NOT_APPLICABLE = "Not Applicable"

# Exact strings the sheet's dropdown validation accepts.
SCOPE_SIZES = (NOT_APPLICABLE, "Small (1-3)", "Medium (4-6)", "Large (>6)")
SCOPE_SIZE_UNITS = {NOT_APPLICABLE: 0, "Small (1-3)": 1, "Medium (4-6)": 3, "Large (>6)": 5}

REUSE_LEVELS = (
    NOT_APPLICABLE,
    "0 - No Reusability",
    "1 - Low Reusability",
    "2 - Moderate Reusability",
    "4 - High Reusability",
)
REUSE_LEVEL_SCORES = {
    NOT_APPLICABLE: None,
    "0 - No Reusability": 0,
    "1 - Low Reusability": 1,
    "2 - Moderate Reusability": 2,
    "4 - High Reusability": 4,
}
REUSE_MAX_SCORE = 4

# Shorthand the spec may use instead of the full dropdown strings.
SCOPE_SIZE_ALIASES = {
    "na": NOT_APPLICABLE, "n/a": NOT_APPLICABLE, "none": NOT_APPLICABLE,
    "notapplicable": NOT_APPLICABLE, "not applicable": NOT_APPLICABLE,
    "s": "Small (1-3)", "small": "Small (1-3)", "1": "Small (1-3)",
    "m": "Medium (4-6)", "medium": "Medium (4-6)", "3": "Medium (4-6)",
    "l": "Large (>6)", "large": "Large (>6)", "5": "Large (>6)",
}
REUSE_LEVEL_ALIASES = {
    "na": NOT_APPLICABLE, "n/a": NOT_APPLICABLE, "none": NOT_APPLICABLE,
    "notapplicable": NOT_APPLICABLE, "not applicable": NOT_APPLICABLE,
    "0": "0 - No Reusability", "no": "0 - No Reusability",
    "1": "1 - Low Reusability", "low": "1 - Low Reusability",
    "2": "2 - Moderate Reusability", "moderate": "2 - Moderate Reusability",
    "4": "4 - High Reusability", "high": "4 - High Reusability",
}

# --------------------------------------------------------------------------
# MasterData -- cells the generated formulas point at
# --------------------------------------------------------------------------
MD_UI_INDEX = "MasterData!$B$2"
MD_PAGES_INDEX = "MasterData!$B$3"
MD_INTEGRATION_INDEX = "MasterData!$B$4"
MD_ADJ_BAND_0 = "MasterData!$B$5"
MD_ADJ_BAND_25 = "MasterData!$B$6"
MD_ADJ_BAND_50 = "MasterData!$B$7"
MD_ADJ_BAND_75 = "MasterData!$B$8"
MD_REQ_DESIGN_UNIT = "MasterData!$B$9"
MD_TSP_FACTOR = "MasterData!$B$10"
MD_SUMMARY_QA_RATIO = "MasterData!$B$11"
MD_SUMMARY_RND_RATIO = "MasterData!$B$12"

# Values written into those MasterData cells by the template build step.
SUMMARY_QA_RATIO = 0.4
SUMMARY_RND_RATIO = 0.2
REQ_DESIGN_UNIT_RATIO = 0.2
TSP_FACTOR = 1.16
SCOPE_INDEX = {"user_interaction": 4, "pages": 2, "integration": 8}
ADJUSTMENT_BANDS = ((24, 0.0), (49, 0.35), (74, 0.65), (100, 0.85))

# --------------------------------------------------------------------------
# Summary sheet
# --------------------------------------------------------------------------
SUMMARY_ROW_DEV = 3
SUMMARY_ROW_QA = 4
SUMMARY_ROW_RND = 5
SUMMARY_ROW_TOTAL = 6
SUMMARY_COL_TOTAL = 3   # C
SUMMARY_COL_ORIGINAL = 4   # D

# --------------------------------------------------------------------------
# Row-height heuristics (Excel does not auto-fit wrapped text via openpyxl)
# --------------------------------------------------------------------------
LINE_HEIGHT_PT = 13.0
MIN_ROW_HEIGHT = 30.0
MAX_ROW_HEIGHT = 409.0
