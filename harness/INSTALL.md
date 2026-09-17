# Installing `cr-estimate` into the DCP AI harness

Adds a CR estimation step to the existing four-stage harness. It is **additive**:
one new skill, one new validator, and three small edits to files you already
have. No existing skill, agent or stage changes behaviour.

---

## Quickstart (Windows / PowerShell)

Assuming the harness workspace is `C:\Microservices\Workspace\aiv2` — adjust
`$Aiv2` if yours differs.

Run these **one line at a time**. Every path is quoted, because
`$env:TEMP\cr-tool` unquoted and without a command in front of it is a
PowerShell expression, not a path, and fails with
`Unexpected token '\cr-tool' in expression or statement`.

```powershell
# 1. clone the tool OUTSIDE the harness workspace, so VS Code does not index it
git clone https://github.com/VSaikiranOwn/CR.git "$env:TEMP\cr-tool"
cd "$env:TEMP\cr-tool"
git checkout claude/cr-generation-utility-s8sfrz
```

```powershell
# 2. copy the skill and the validator in
$Aiv2 = "C:\Microservices\Workspace\aiv2"
Copy-Item -Recurse -Force ".\harness\bundle\skills\cr-estimate" "$Aiv2\.github\skills\"
Copy-Item -Force ".\harness\bundle\validators\cr_complete.py" "$Aiv2\.github\validators\"
```

```powershell
# 3. the one dependency
pip install openpyxl
```

```powershell
# 4. smoke test against a batch that already has a WBS
cd "$Aiv2"
python .github\skills\cr-estimate\scripts\cr_estimate.py .github\workspace\<batch-id> --dry-run
```

Then make the three edits in section 3 below, and you are done. Per batch after
that it is one command, or `/cr-estimate` in Copilot Chat with `design-agent`
selected.

> **If you already cloned it** (for example into `aiv2\CR`), skip step 1 — `cd`
> into that folder, run `git checkout claude/cr-generation-utility-s8sfrz` and
> `git pull`, then carry on from step 2. A clone inside `aiv2` works fine but
> shows up in VS Code search; delete or move it once the copy is done.

> **Which python?** Try `python`. If that opens the Microsoft Store, use `py`
> instead. Whatever your harness already uses for `run-all.py` is the right one.

---

## 1. The bundle

It is committed at `harness/bundle/`, so there is nothing to build. If you have
changed anything under `src/`, regenerate it first:

```bash
python tools/build_harness_bundle.py
```

## 2. Copy it in (macOS / Linux)

```bash
cp -r harness/bundle/skills/cr-estimate       <harness-repo>/.github/skills/
cp    harness/bundle/validators/cr_complete.py <harness-repo>/.github/validators/
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

## 2b. Running it, per batch

Two equivalent ways — the skill is the same code either way:

```powershell
# from the terminal
python .github\skills\cr-estimate\scripts\cr_estimate.py .github\workspace\41000
```

or in Copilot Chat with `design-agent` selected:

```
/cr-estimate    then: "batch 41000"
```

Outputs land in `.github/workspace/41000/02-design/cr/`:

| File | What it is |
|---|---|
| `41000-CR-Estimation.xlsx` | the deliverable |
| `cr-spec.json` | the reviewable input — fix numbers here, never in the .xlsx |
| `cr-evidence.md` | every flag traced to the WBS task / LLD row that set it |

Add `--dry-run` to see the totals without writing anything.

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
