---
name: cr-estimate
description: >-
  Generate the DCP Change Request (CR) effort-estimation workbook for a batch,
  derived from the batch's own design artifacts. Reads `01-requirements/
  requirements-summary.md` and `02-design/{hld,lld,wbs}.md`, maps WBS task sizes
  to UI/MS/DB/BPM complexity and LLD §x.4 reuse levels to the Tender Story
  Points sheet, and writes `02-design/cr/` — spec, evidence trail, and the
  .xlsx. Use this AFTER `wbs-author` and BEFORE the stage-2 gate, whenever
  someone asks to "estimate the CR", "build the CR sheet", "how many man-days
  is this batch", "tender story points", or "effort estimate".
---

# cr-estimate

Produce the CR Estimation Framework (ver. 2) workbook for a batch, with every
number traced back to a design artifact.

## Role

This skill does **not** re-analyse the change. `impact-assessment` and
`reusability-assessment` already did that, and their findings are authored into
`lld.md` §x.3 / §x.4. This skill *reads* those findings, applies the fixed CR
arithmetic, and writes the sheet. If the LLD is wrong, fix the LLD and re-run —
never adjust the spreadsheet.

## Position in the pipeline

Step 6.5 of `design-agent`: after `wbs-author` writes `02-design/wbs.md`, before
the stage-2 gate. It reads only stages 01 and 02 and writes only into
`02-design/`, so the workspace contract holds.

## Boundaries

> **Produces documents only. Never modifies source.** Reads `01-requirements/`
> and `02-design/`; writes only `02-design/cr/`.

Never hand-edit the generated `.xlsx`. The workbook is rendered from
`cr-spec.json`; a re-run overwrites it and the spec stops being the record of
what was decided.

## Workflow

1. Confirm `02-design/wbs.md` exists and is confirmed. If it does not, stop and
   say the WBS must be generated first.
2. Run the skill:
   ```bash
   python3 .github/skills/cr-estimate/scripts/cr_estimate.py \
       .github/workspace/<batch-id>
   ```
   Add `--dry-run` to preview the totals without writing.
3. Read the printed report. Resolve, in this order:
   - **Formula errors** — must be `none`. Anything else is a defect, stop.
   - **Missing inputs** — a required artifact was absent; the sheet will be thin.
   - **Notes** — usually an AC with no WBS task referencing it. That is a
     traceability gap in the WBS (`Every AC-* maps to one or more WBS-*`), so
     fix `wbs.md` and re-run rather than accepting the `[TBD]` row.
   - **Warnings** — a row over 10 MD or carrying more than 3 flags.
4. Open `02-design/cr/cr-evidence.md` and walk its Review checklist. The three
   Scope Assessment columns are drafts: they are marked
   `[DRAFT: business team to confirm]` because that half of the sheet belongs to
   the business team, not to IT.
5. Ask: **"CR Review: are the effort and TSP figures correct? (yes / no)"**.
   Stop if not approved.
6. Run the stage-2 gate, which now includes `cr-complete`:
   ```bash
   python3 .github/validators/run-all.py --stage 2 --workspace .github/workspace/<batch-id>
   ```

## What drives each number

| CR field | Source |
|---|---|
| Details row (one per AC) | `requirements-summary.md` ACs |
| Business Requirement (col C) | the AC text, verbatim |
| Technical Component(s) (col D) | `wbs.md` §2.1 API Reuse Register + `lld.md` §x.6/§x.7/§x.8 |
| UI / MS / DB / BPM complexity | `wbs.md` task layer + its `[S/M/L]` |
| Reuse: Frontend / Backend / Database | `lld.md` §x.4 candidate levels, averaged |
| Reuse: Interface | `wbs.md` §2.1 decisions (REUSE=4, EXTEND=2, NEW=0) |
| Reuse: QA | proxy — reuse decision of each task carrying a TS-* slice |
| Scope: Interaction / Pages / Integration | `lld.md` §x.2 and §x.6, `hld.md` §8 |

`DOCS` tasks produce no complexity flag: documentation effort is already inside
the Requirement & Design ratio. QA likewise has no flag — it is the 40% ratio.

Print the full mapping, including the calibration thresholds, with:

```bash
python3 .github/skills/cr-estimate/scripts/cr_estimate.py rules
```

## Rules that are not negotiable

- **Effort weights are fixed** by the company template: UI/MS/BPM Simple 1.5,
  Medium 3, Complex 5; DB 0.25 / 0.5 / 1. QA = 40% of Development, Requirement
  & Design = 20%. Do not offer to change them.
- **Database names come from Confluence, never from source.** Per the harness
  data-model policy, the DB reuse level and any physical name in column D must
  come from the approved DCP Physical Data Model. If a name is not published
  there, write "not found in approved data model" and raise an Open Question —
  do not infer it from the repo.
- **Scope Assessment is the business team's column.** Draft it, mark it, never
  present it as final.
- **Every claim is cited.** If you edit `cr-spec.json` by hand, add the matching
  justification to `cr-evidence.md` — an uncited number defeats the point.

## Detail

`references/estimation-rules.md` — the complexity heuristics and column-D
conventions, for the cases the artifacts do not settle.
