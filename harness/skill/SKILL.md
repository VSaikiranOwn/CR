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

Step 6.5 of `design-agent`: after `lld-author`, and after `wbs-author` when the
batch gets that far. It reads only stages 01 and 02 and writes only into
`02-design/`, so the workspace contract holds.

## Two modes

The skill picks automatically:

| Batch has | Mode | Complexity comes from |
|---|---|---|
| `wbs.md` with tasks | **wbs** | each task's layer + declared `[S/M/L]` |
| no `wbs.md` | **lld** | `lld.md` §x.3 Impact Analysis — layer + Low/Med/High |

Both modes read reuse levels from `lld.md` §x.4 and scope from §x.2 / §x.6 and
`hld.md` §8, so the Tender Story Points sheet is filled either way. The printed
report always names the mode and the exact files used.

Force a mode with `--no-wbs` or `--use-wbs`.

## Which HLD and LLD it reads

Batches keep numbered snapshots in `02-design/versions/`. The skill takes the
**highest** `hld-vN.md` / `lld-vN.md` whenever that folder has any, and falls
back to `02-design/hld.md` / `lld.md` otherwise. It does not look at
modification times — those do not survive a copy or a fresh clone, so they
would pick a different document depending on how the batch reached the machine.

The report names the file it used every run. If the working copy is the one you
want, pass it: `--lld 02-design/lld.md`.

## One Details row per AC group

Sub-ACs sharing a major number are folded into a single row: `AC-7.1` through
`AC-7.7` become one row labelled `AC-7.1-AC-7.7`. This matches how the reference
CRs are written; a row per sub-AC is unreadable and inflates the row count
without changing the work.

## Boundaries

> **Produces documents only. Never modifies source.** Reads `01-requirements/`
> and `02-design/`; writes only `02-design/cr/`.

Never hand-edit the generated `.xlsx`. The workbook is rendered from
`cr-spec.json`; a re-run overwrites it and the spec stops being the record of
what was decided.

## Workflow

1. Confirm `02-design/lld.md` (or a `versions/lld-vN.md`) exists and is
   confirmed. The WBS is optional — without it the skill uses the LLD Impact
   Analysis and says so.
2. Run the skill:
   ```bash
   python3 .github/skills/cr-estimate/scripts/cr_estimate.py \
       .github/workspace/<batch-id>
   ```
   Add `--dry-run` to preview the totals without writing.
3. Read the printed report. Resolve, in this order:
   - **Formula errors** — must be `none`. Anything else is a defect, stop.
   - **Missing inputs** — a required artifact was absent; the sheet will be thin.
   - **Notes** — in wbs mode, an AC with no WBS task is a traceability gap
     (`Every AC-* maps to one or more WBS-*`), so fix `wbs.md` and re-run rather
     than accepting the `[TBD]` row. In lld mode, an AC with no Impact Analysis
     rows means §x.3 was left unfilled for that AC; fill it and re-run.
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

| CR field | wbs mode | lld mode |
|---|---|---|
| Details row (one per AC group) | `requirements-summary.md` ACs | same |
| Business Requirement (col C) | the AC text, verbatim | same |
| Technical Component(s) (col D) | `wbs.md` §2.1 register + `lld.md` §x.6/§x.7/§x.8 | `lld.md` §x.3 change-required + §x.4/§x.6/§x.8 |
| UI / MS / DB / BPM complexity | task layer + `[S/M/L]` | §x.3 layer + Low/Med/High |
| Reuse: Frontend / Backend / Database | `lld.md` §x.4 levels, averaged | same |
| Reuse: Interface | `wbs.md` §2.1 decisions | §x.4 endpoint candidates |
| Reuse: QA | decision of each task with a TS-* slice | decisions across all §x.4 candidates |
| Scope: Interaction / Pages / Integration | `lld.md` §x.2 and §x.6, `hld.md` §8 | same |

In lld mode, §x.3 layers map on: `Frontend→UI`, `Backend→MS`,
`Integration→MS`, `Access Control→MS`, `Database→DB`, `BPM→BPM`.

`DOCS` tasks produce no complexity flag: documentation effort is already inside
the Requirement & Design ratio. QA likewise has no flag — it is the 40% ratio.
The sheet has no Integration column, so integration work counts as MS.

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
