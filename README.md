# CR Estimation Framework utility (ver. 2)

Turn a CR input pack — Figma screens, Jira user stories, the HLD and (when it
exists) the LLD — into the company's **CR Estimation Framework** workbook,
driven from GitHub Copilot.

```
inputs/                                       output/
  figma/   *.png *.jpg *.pdf   ─┐
  stories/ *.md                 ├─► Copilot ─► <KEY>_cr_spec.json ─► cr-tool build ─► <KEY>-CR-Estimation.xlsx
  hld/     *.md                 │   analyses      (you review it)      (deterministic)
  lld/     *.md                ─┘
```

**Copilot makes the judgement calls. `cr-tool` owns the Excel.** The spec JSON in
the middle is the reviewable artefact: if a number looks wrong, you fix the spec
and rebuild, you never touch the workbook.

**Two modes. Pick one — you do not need both.**

| | Mode A — standalone | Mode B — inside the DCP AI harness |
|---|---|---|
| **Use when** | there is no HLD/LLD/WBS; you have loose docs and Figma exports | the batch already has `02-design/` |
| **You supply** | a folder of Figma PNG/PDF, stories, HLD, LLD | nothing — it reads the batch |
| **Copilot's job** | read it all and write the spec | none; the mapping is deterministic |
| **Run it with** | `cr-tool build <spec>` | `/cr-estimate`, or one `cr_estimate.py` command |
| **Read** | [QUICKSTART.md](QUICKSTART.md) | **[harness/INSTALL.md](harness/INSTALL.md)** |

If you already run the four-stage harness, **Mode B is the one you want** — it
derives the estimate from your own signed-off design instead of re-reading
documents, and writes an evidence trail alongside the workbook. — where to clone, where your CR
files go, and how to drive it from Copilot, step by step.

---

## Install

```bash
pip install -e .
# optional, only to rasterise Figma PDFs into readable PNG pages:
pip install -e ".[pdf]"
```

## Use it

```bash
# 1. scaffold a workspace
cr-tool init workspaces/SLADCYBQSK-42132 --key SLADCYBQSK-42132

# 2. drop your files into inputs/figma, inputs/stories, inputs/hld, inputs/lld

# 3. in VS Code Copilot Chat, run the prompt:
#      /generate-cr
#    it inventories the pack, analyses it, and writes the spec JSON

# 4. build (Copilot does this for you, or run it yourself)
cr-tool build workspaces/SLADCYBQSK-42132/output/SLADCYBQSK-42132_cr_spec.json
```

### All commands

| Command | Does |
|---|---|
| `cr-tool init <dir> --key <KEY>` | Scaffold `inputs/` + `output/` and a starter spec |
| `cr-tool inventory <dir> [--json <path>] [--split-pdf]` | Classify the input pack and report what is missing |
| `cr-tool validate <spec>` | Check a spec and print the totals, without writing Excel |
| `cr-tool build <spec> [-o <xlsx>]` | Generate the workbook, verify it, print the report |
| `cr-tool rules` | Print every fixed constant |
| `cr-tool schema` | Print the spec JSON schema |

`build` derives the output name from the spec (`<KEY>_cr_spec.json` →
`<KEY>-CR-Estimation.xlsx`) unless you pass `-o`.

---

## What gets generated

Five sheets, every calculation left as a **live Excel formula** so the sheet
stays auditable and editable after delivery.

| Sheet | Filled from | Contents |
|---|---|---|
| `Readme (Definitions)` | template | The scoring legend. Untouched. |
| `MasterData` | template | Complexity indices, adjustment bands, ratios. Untouched apart from the two Summary ratios. |
| `Tender Story Points` | `spec.stories` | One row per user story: scope sizes, reusability levels, and the Framework Unit → Reusability Score → Adjustment → TSP chain. |
| `Details` | `spec.rows` | One row per AC group: the UI/MS/DB/BPM × Simple/Medium/Complex matrix and the DEV effort formula, plus a Total row. |
| `Summary` | derived | Development (linked to the Details total), QA, Requirement & Design, Total, and an optional `Original Efforts` comparison column. |

Dropdown validations, merged headers, frozen panes, column widths and fonts all
come from the template untouched — and the dropdowns are extended automatically
if you have more stories than the template band.

## The fixed arithmetic

Nothing below is configurable. `cr-tool rules` prints it, and
`tests/test_compute.py` pins every number to the reference workbook.

**Details — DEV effort per flagged component (MD)**

| Dimension | Simple | Medium | Complex |
|---|---|---|---|
| UI / MS / BPM | 1.5 | 3 | **5** |
| DB | 0.25 | 0.5 | 1 |

`Row MD = ROUND(sum, 0)`. MS Simple shares the 1.5 weight with UI and BPM Simple
— that is what the reference workbook does, and it is deliberate.

**Summary** — QA = `ROUND(Dev × 40%, 0)`, Requirement & Design =
`ROUND(Dev × 20%, 0)`. Both percentages live in `MasterData!B11:B12`, so the
workbook documents its own ratios.

**Tender Story Points**

```
Framework Unit           = Σ (size unit × complexity index)      S=1 M=3 L=5, NA=0
                           indices: user interaction 4, pages 2, integration 8
Reusability Score        = mean(applicable dimension scores) ÷ 4 × 100
Adjustment %             = 0–24 → 0% | 25–49 → 35% | 50–74 → 65% | 75–100 → 85%
Framework Unit (Aft.Adj) = Framework Unit × (1 − Adjustment %)
Req. & Design Unit       = Framework Unit (Aft. Adj.) × 0.2
TSP                      = (FU adj + Req & Design Unit) × 1.16
```

`Not Applicable` is excluded from both sides of the reusability mean;
`0 - No Reusability` is not — it counts and drags the mean down.

---

## Repository layout

```
QUICKSTART.md                   start here: setup and the per-CR workflow
.github/
  copilot-instructions.md       repo-wide rules Copilot loads automatically
  prompts/generate-cr.prompt.md the /generate-cr workflow
  prompts/review-cr.prompt.md   the /review-cr checklist
docs/
  estimation-rules.md           how to size, score and flag — the judgement half
  worked-example.md             the reference CR, end to end
schema/cr_spec.schema.json      the spec contract
examples/
  starter_cr_spec.json          copy this per CR
  sample_cr_spec.json           the reference CR as a spec (regression fixture)
templates/
  cr_framework_template.xlsx    the blank framework — never edit by hand
src/cr_tool/                    constants, spec, compute, render, verify, cli
harness/                        drop-in for the DCP AI harness (skill + validator)
src/cr_harness/                 parses batch artifacts, derives the spec + evidence
tools/build_template.py         re-derive the template from a filled workbook
tools/build_harness_bundle.py   assemble the harness drop-in
tests/                          81 tests pinning the arithmetic and the output
```

## Verified against the reference

`examples/sample_cr_spec.json` is the real ver. 2 CR, extracted from the source
workbook. Building it reproduces that workbook cell for cell:

| | Reference workbook | Generated |
|---|---|---|
| Details rows | 9, Total row 12 | 9, Total row 12 |
| Development | 31 MD | 31 MD |
| TSP — SLADCYBQSK-42132 | FU 22, reuse 50%, adj 65%, **TSP 10.72** | identical |
| TSP — SLADCYBQSK-42528 | FU 10, reuse 70%, adj 65%, **TSP 4.87** | identical |

The only intentional differences: Summary QA and Requirement & Design are now
live formulas (40% / 20%) rather than the typed-in `9` and `7`, and `MasterData`
gains rows 11–12 holding those two ratios.

## Updating the template

If the company issues a new version of the framework workbook:

```bash
python tools/build_template.py <new_filled_workbook.xlsx> templates/cr_framework_template.xlsx
python -m pytest
```

The tests will tell you immediately if a weight, a band or a formula moved.
