---
mode: agent
description: Analyse a CR input pack (Figma, user stories, HLD, LLD) and generate the CR Estimation Framework workbook.
---

# Generate a CR estimation workbook

You are producing a **Change Request effort estimate** in the company's fixed
ver. 2 framework. You do the analysis; `cr-tool` writes the Excel.

Read `docs/estimation-rules.md` before you decide anything. It holds the sizing
counts, the reusability ladder, the complexity heuristics and the column D
conventions. Do not improvise around it.

Ask me for the workspace path if I have not given you one.

---

## Step 1 — See what you were given

```bash
cr-tool inventory <workspace>/inputs --json <workspace>/output/manifest.json
```

Read every file it lists:

- **Figma** (`.png` / `.jpg` / `.pdf`) — attach the images to your context and
  look at them. Count screens, count the distinct actions a user can take, note
  every popup, toast, disabled state and error dialog. These drive the TSP
  **Pages** and **User Interaction** sizes and the **UI** complexity flags.
  If the Figma arrived as PDF, run the command again with `--split-pdf` to get
  per-page PNGs you can actually read.
- **User stories** (`.md` from Jira) — the AC numbering is your row structure.
  Extract every AC and its acceptance detail verbatim before you group anything.
- **HLD** (`.md`) — service boundaries, outbound APIs, webhooks, BPM processes,
  schema impact. Drives TSP **Integration** and **Interface**, and the MS/DB/BPM
  flags.
- **LLD** (`.md`, often absent) — endpoint signatures, class names, table and
  column names. Use it to make column D specific. Its absence is normal and is
  not a reason to stop.

Report the `gaps` the inventory prints back to me before continuing.

## Step 2 — Plan out loud, before writing any JSON

Show me a short plan and wait for nothing — just make it visible:

1. **One TSP row per user story.** For each: the counted interactions, pages and
   integrations with the evidence behind each count, and the five reusability
   levels with a one-line justification each.
2. **One Details row per AC group.** List the groups (e.g. `AC1.1–AC1.3`,
   `AC1.4`, `AC1.5/AC1.5.1`) and, for each, which of UI / MS / DB / BPM it
   touches and at what complexity.
3. **A `Shared` row per story group** if — and only if — there is genuine
   cross-cutting work: schema change, master data, audit, access control, BPM
   coordination.

Sanity-check yourself here: 1–3 flags per row, each row landing in 1–10 MD.

## Step 3 — Write the spec

Write `<workspace>/output/<KEY>_cr_spec.json` against `schema/cr_spec.schema.json`
(`cr-tool schema` prints it). Use `examples/sample_cr_spec.json` as the model for
tone, density and structure — it is the real reference CR.

Rules you must not break:

- Column C (`business_requirement`) is **prose describing the ACs**, opening with
  the AC references and a short label, e.g.
  `AC1.1-AC1.3 (Withdraw flow) - On the Lodgment Form, ...`
- Column D (`technical_component`) is **newline-separated, grouped by
  dimension**, labels every endpoint `NEW API:` / `NEW outbound:` /
  `EXISTING to MODIFY:` / `EXISTING to REUSE/CHECK:`, and states BPM impact
  explicitly — `BPM: none.` if there is none.
- The dimension prefix in column D must match the flags you set. If you write
  `MS (Complex)`, then `"ms": [0,0,1]`.
- Where you do not know something, write the bracketed marker from
  `docs/estimation-rules.md` §6. Never invent an endpoint, a table or a service
  name to fill a gap, and never silently drop an AC because it was thin.
- Every `details` field on the TSP sheet gets filled. The count is the evidence.

## Step 4 — Validate, then build

```bash
cr-tool validate <workspace>/output/<KEY>_cr_spec.json
cr-tool build    <workspace>/output/<KEY>_cr_spec.json
```

Act on everything the tool prints:

- **Formula errors** — must be `none`. If not, stop and fix the spec.
- **Warnings** — a row over 10 MD, a row with more than 3 flags, or a story on
  one sheet with no counterpart on the other. Resolve each one or explain to me
  why it is intentional. Do not hand me a workbook with unexplained warnings.
- **Placeholders** — list every `[TBD]` / `[Assumption]` cell back to me by
  coordinate so I know exactly what to review.

## Step 5 — Report

Give me, in the chat:

- Development / QA / Requirement & Design / Total MD, and the TSP per story.
- The row-by-row MD breakdown.
- Every assumption you made, and every placeholder cell with its coordinate.
- Anything in the input pack you could not reconcile.

Then tell me the workbook path. Do not open, edit or reformat the `.xlsx`
yourself — it is already correct, and editing it outside `cr-tool` breaks the
template contract.
