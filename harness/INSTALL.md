# Installing `cr-estimate` into the DCP AI harness

Adds a CR estimation step to the existing four-stage harness. It is **additive**:
one new skill, one new validator, and three small edits to files you already
have. No existing skill, agent or stage changes behaviour.

## 1. Build the bundle

```bash
python tools/build_harness_bundle.py          # writes dist/harness/
```

## 2. Copy it in

```bash
cp -r dist/harness/skills/cr-estimate   <harness-repo>/.github/skills/
cp    dist/harness/validators/cr_complete.py <harness-repo>/.github/validators/
```

Resulting layout:

```
.github/
  skills/cr-estimate/
    SKILL.md
    scripts/cr_estimate.py          entry point — no pip install needed
    scripts/cr_tool/                renders the workbook (fixed CR arithmetic)
    scripts/cr_harness/             reads the batch artifacts (the mapping)
    assets/cr_framework_template.xlsx
    references/estimation-rules.md
  validators/cr_complete.py
```

Only dependency is `openpyxl`, which the harness already needs for nothing else —
if it is not present: `pip install openpyxl`.

Smoke test against any batch that has a WBS:

```bash
python3 .github/skills/cr-estimate/scripts/cr_estimate.py \
        .github/workspace/<batch-id> --dry-run
```

## 3. Three edits to existing files

### `.github/agents/design.agent.md`

Add `cr-estimate` to **Owned skills**:

```diff
-- `graphify-analyse`, `impact-assessment`, `reusability-assessment`, `ddd-modelling`, `hld-author`, `lld-author`, `wbs-author`.
+- `graphify-analyse`, `impact-assessment`, `reusability-assessment`, `ddd-modelling`, `hld-author`, `lld-author`, `wbs-author`, `cr-estimate`.
```

Insert a new step between the current 6 (`wbs-author`) and 7 (stage-2 gate):

```diff
 6. Generate `wbs.md` via `wbs-author`, including functional requirement breakdown and `FR-* -> AC-* -> WBS-* -> TS-*` traceability matrix (rolls up each AC's `x.9`).
+7. Generate the CR estimate via `cr-estimate` — reads `01-requirements/` + `02-design/`, writes `02-design/cr/` (spec, evidence trail, workbook). Then ask: **"CR Review: are the effort and TSP figures correct? (yes / no)"**. Stop if not approved.
-7. Run stage-2 gate: `python3 .github/validators/run-all.py --stage 2 --workspace .github/workspace/<batch-id>`.
-8. If gate passes, hand off with WBS counts, first unblocked task, and open blockers.
+8. Run stage-2 gate: `python3 .github/validators/run-all.py --stage 2 --workspace .github/workspace/<batch-id>`.
+9. If gate passes, hand off with WBS counts, first unblocked task, and open blockers.
```

And in the **Handoff** summary list, add:

```diff
 - Any open items that block sprint start
+- CR estimate: Development / QA / R&D / Total MD and the TSP per story
```

### `.github/docs/design.md`

Skills table — add a row under `design`:

```
| design | cr-estimate | cr-complete | Derive the CR estimation workbook from `02-design/` -> `02-design/cr/` | "estimate the CR", "effort estimate", "tender story points" | new | P1 |
```

Validators table — add:

```
| cr-complete | stage + skill | 2 | cr-estimate |
```

Agents table — the `design-agent` row is **already missing `wbs-author`**; fix
both while you are there:

```diff
-| design-agent | 02 | graphify-analyse, impact-assessment, reusability-assessment, ddd-modelling, hld-author, lld-author | documents only; never modifies source |
+| design-agent | 02 | graphify-analyse, impact-assessment, reusability-assessment, ddd-modelling, hld-author, lld-author, wbs-author, cr-estimate | documents only; never modifies source |
```

### `.github/copilot-instructions.md`

```diff
-- **02 design:** `/graphify-analyse` · `/impact-assessment` · `/reusability-assessment` · `/ddd-modelling` · `/hld-author` · `/lld-author` · `/wbs-author`
+- **02 design:** `/graphify-analyse` · `/impact-assessment` · `/reusability-assessment` · `/ddd-modelling` · `/hld-author` · `/lld-author` · `/wbs-author` · `/cr-estimate`
```

And in the stage table:

```diff
-| 02 | design-agent | `hld.md`, `lld.md` (per-AC impact + reusability inside each AC), `wbs.md` (FR -> task -> test-slice mapping) | design-complete |
+| 02 | design-agent | `hld.md`, `lld.md` (per-AC impact + reusability inside each AC), `wbs.md` (FR -> task -> test-slice mapping), `cr/` (CR estimate + evidence) | design-complete, cr-complete |
```

## 4. Register the validator

`cr_complete.py` runs standalone:

```bash
python3 .github/validators/cr_complete.py --workspace .github/workspace/<batch-id>
```

It follows the harness convention — `--workspace`, one finding per line,
non-zero exit on failure, `PASS <name>` on success. **How `run-all.py`
discovers validators is the one thing not yet wired**, because that file has not
been shared. If it auto-discovers `.github/validators/*.py`, this is already
done. If it keeps an explicit stage->validator registry, add `cr_complete` to
stage 2.

`cr-complete` is deliberately lenient about timing: if the batch has no
`wbs.md`, it passes with a note, so stage 2 still gates cleanly on batches that
have not reached design sign-off.

## 5. Calibrate before trusting the numbers

The mapping thresholds in `scripts/cr_harness/constants.py` are **judgement,
not fact**. Two in particular:

| Knob | Default | What it does |
|---|---|---|
| `PROMOTE_AT_COUNT` | 3 | tasks at the top size before a layer is promoted a rung |
| `snap_to_rung` ties | round down | which way a borderline reuse mean falls |

Run the skill on a batch whose CR sheet was produced by hand, compare, and
adjust. `cr-estimate rules` prints every constant, and `cr-evidence.md` shows
which rows drove each number, so a disagreement is traceable to a specific rule.

Known divergence from the one reference CR available: the Framework Unit
reproduced exactly (22), but the per-dimension reuse levels differed from the
human assessment in both directions — the mean-based roll-up is generous when
few candidates are listed. Expect to tune this.

## 6. Uninstall

Delete `.github/skills/cr-estimate/` and `.github/validators/cr_complete.py`,
and revert the three edits. Nothing else references them.
