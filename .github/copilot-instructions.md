# CR Estimation Framework — repository instructions

This repository is a **utility**, not an application. Its job is to turn a CR
input pack (Figma screens, Jira user stories, HLD, LLD) into the company's
fixed **CR Estimation Framework (ver. 2)** Excel workbook.

## The one rule that matters

**Never hand-build the workbook, and never edit the .xlsx directly.**
The workbook has five sheets whose formulas, dropdowns, styling and MasterData
references must stay byte-identical to the company template. The only supported
path is:

```
input pack  →  (you analyse)  →  <KEY>_cr_spec.json  →  cr-tool build  →  .xlsx
```

You write the **spec JSON**. `cr-tool` owns the Excel.

## Division of labour

| Who | Does what |
|---|---|
| **You (Copilot)** | Read the Figma / stories / HLD / LLD. Decide the scope sizes, reusability levels, and UI/MS/DB/BPM complexity flags. Write the prose for Business Requirement and Technical Component(s). Emit the spec JSON. |
| **`cr-tool`** | Validates the spec, fills the template, writes live Excel formulas, checks for formula errors, prints the totals. It makes **no** judgement calls. |

## Commands

```bash
cr-tool init <workspace> --key <KEY>   # scaffold inputs/ + a starter spec
cr-tool inventory <workspace>/inputs   # list and classify what you were given
cr-tool validate <spec.json>           # check the spec without writing Excel
cr-tool build <spec.json>              # generate the workbook + report
cr-tool rules                          # print the fixed constants
cr-tool schema                         # print the spec JSON schema
```

## Fixed constants — never change these, never offer to

Details DEV effort per flagged component, in man-days:

| Dimension | Simple | Medium | Complex |
|---|---|---|---|
| UI / MS / BPM | 1.5 | 3 | **5** |
| DB | 0.25 | 0.5 | 1 |

- Row effort = `ROUND(sum, 0)`. Keep **1–3 flags per row**, landing in **1–10 MD**.
- Summary: QA = **40%** of Development, Requirement & Design = **20%** of Development.
- Tender Story Points: scope size S=1 / M=3 / L=5; complexity index user
  interaction 4, pages 2, integration 8; reusability adjustment bands
  0–24→0%, 25–49→35%, 50–74→65%, 75–100→85%; TSP factor 1.16.

MS Simple deliberately shares the 1.5 weight with UI Simple and BPM Simple —
there is no separate MS Simple weight. This matches the reference workbook.

## When asked to produce a CR estimate

Use the `/generate-cr` prompt in `.github/prompts/`. Do not improvise a
different workflow. The full estimation method — how to size scope, how to score
reusability, how to assign complexity, and how to write column D — is in
[`docs/estimation-rules.md`](../docs/estimation-rules.md). Read it first.

## Code conventions

- Python 3.10+, standard library plus `openpyxl`. No new runtime dependencies.
- Every formula written into the workbook must have a matching Python mirror in
  `src/cr_tool/compute.py`, and a test asserting both agree with the reference
  numbers in `tests/test_compute.py`.
- Constants live in `src/cr_tool/constants.py` only. No magic numbers elsewhere.
