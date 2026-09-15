# Estimation rules

Everything the analyst (or Copilot) needs to decide, and nothing the tool decides
for you. The arithmetic is fixed; the judgement is here.

---

## 1. The two sheets you are filling

The workbook holds two independent estimates over the same change:

| Sheet | Granularity | Answers |
|---|---|---|
| **Tender Story Points** | one row **per user story** | "what does this cost commercially?" |
| **Details** | one row **per AC group** | "how many man-days of build is this?" |

They are not derived from each other. Fill both. The `Summary` sheet reports
only the Details side.

---

## 2. Tender Story Points — Scope Assessment (business view)

Three dimensions, each sized `Small (1-3)` / `Medium (4-6)` / `Large (>6)` /
`Not Applicable`, by **counting**:

| Dimension | Count | Where to look |
|---|---|---|
| **User Interaction** | distinct things a user can *do* | Figma CTAs and the ACs: entry point, save as draft, submit, cancel, withdraw, confirm popup, concurrent-user check |
| **Pages** | distinct screens / steppers | Figma frames; a module dashboard and each stepper page count separately |
| **Integration** | distinct integrations with external parties | HLD sequence diagrams: each outbound API and each inbound webhook |

Size maps to units **S=1, M=3, L=5** (`Not Applicable` = 0). The unit is
multiplied by the dimension's complexity index from `MasterData`
(user interaction **4**, pages **2**, integration **8**) and summed:

```
Framework Unit (K) = Σ (size unit × complexity index)
```

Always fill the matching `details` field. The count is the evidence for the
size; a reviewer will check it.

> **Worked**: 5 interactions (Medium→3 ×4 = 12), 2 pages (Small→1 ×2 = 2),
> 2 integrations (Small→1 ×8 = 8) → **Framework Unit 22**.

## 3. Tender Story Points — Reusability Assessment (IT view)

Five dimensions, each scored `0 - No Reusability`, `1 - Low Reusability`,
`2 - Moderate Reusability`, `4 - High Reusability`, or `Not Applicable`:

| Dimension | 0 — none | 1 — low | 2 — moderate | 4 — high |
|---|---|---|---|---|
| **Frontend** | all screens built from scratch | limited screens/components adaptable | some screens/components adaptable | most reusable as-is |
| **Backend** | logic fully redesigned | limited logic adaptable with modifications | some logic adaptable | minor tweaks on existing logic |
| **Interface** | new integration endpoints to establish | limited rework on existing endpoints | some rework on existing endpoints | most existing endpoints reusable |
| **Database** | new schema + new tables with views/audit/triggers | new table with supporting objects | add/remove columns, views, RLS changes | master data & notification template changes only |
| **QA** | all test cases from scratch | limited test cases adaptable | some test cases adaptable | most reusable or regression-run |

```
Reusability Score (V) = mean(score of applicable dimensions) ÷ 4 × 100
```

`Not Applicable` is excluded from **both** the numerator and the denominator.
`0 - No Reusability` is *not* the same thing — it counts as applicable and drags
the mean down.

The score selects a discount band, and the rest is arithmetic:

| Score | Adjustment |
|---|---|
| 0–24 | 0% |
| 25–49 | 35% |
| 50–74 | 65% |
| 75–100 | 85% |

```
Framework Unit (Aft. Adj.) = Framework Unit × (1 − Adjustment)
Req. & Design Unit         = Framework Unit (Aft. Adj.) × 0.2
TSP                        = (FU adj + Req & Design Unit) × 1.16
```

---

## 4. Details — one row per AC group

Group closely related sub-ACs into one row (AC1.1–AC1.3 together is normal).
Then flag which dimensions the row touches and at what complexity.

### Effort weights (fixed)

| Dimension | Simple | Medium | Complex |
|---|---|---|---|
| UI / MS / BPM | 1.5 | 3 | **5** |
| DB | 0.25 | 0.5 | 1 |

```
Row MD = ROUND( (UI_S+MS_S+BPM_S)×1.5 + (UI_M+MS_M+BPM_M)×3 + (UI_C+MS_C+BPM_C)×5
              + DB_S×0.25 + DB_M×0.5 + DB_C×1 , 0 )
```

Keep **1–3 flags per row** so each row lands in the **1–10 MD** band. A row over
10 MD should be split; `cr-tool` warns about both.

### Complexity heuristics

| Dim | Simple | Medium | Complex |
|---|---|---|---|
| **UI** | a label, note, flag toggle, or an error popup | a new stepper screen, popup, picker, or a conditional CTA on an existing list | a multi-step interactive flow with conditional rendering |
| **MS** | small tweak to one endpoint, a config or guard, one notification trigger, integrating an existing framework | one new straightforward endpoint, branching in an existing flow, a new template + trigger, persisting new fields | a new endpoint with non-trivial logic, cross-service orchestration, a deep-copy/aggregate operation, state reversion, a new facade to an external system |
| **DB** | a new column / flag / enum value | clean-up across a couple of tables, or a migration | a new table plus supporting objects and master data |
| **BPM** | a guard condition or notification on an existing task | a new branch or subprocess, token-copy from a waiting activity | a brand-new process, or major re-routing across processes |

When torn between two levels, **pick the lower one** and say so in column D.

### The `Shared` row

Add one `Shared` row **per story group**, and only for genuine cross-cutting
work: schema changes, CodeTable master data, audit logging, access control,
BPM coordination. If the story has none, omit it.

---

## 5. Writing column D — Technical Component(s)

This column is what reviewers actually read. It must make three things explicit:

1. **New vs existing APIs.** Label every endpoint: `NEW API:`,
   `NEW outbound:`, `EXISTING to MODIFY:`, `EXISTING to REUSE/CHECK:`.
   Include method, path, and the service or class when known.
2. **BPM entry points and subprocess behaviour**, or the literal word
   `BPM: none.` Name the process, how a subprocess is created, which state is
   copied from the waiting activity, which tasks are suppressed, and the backend
   signal used.
3. **A component breakdown prefixed by dimension and complexity**, e.g.
   `MS (Complex) - ms-legalinstrument`, matching the flags you set.

Group the prose by dimension, one dimension per block, newline-separated.

### Example

```
UI (Medium)
Lodgment Form enhancement: per-instrument Withdraw action link (Submitted/Objected),
1. Row checkboxes with a conditional multi-select Withdraw button (shown when >=2 selected)
2. Confirmation popup, success toast.
Reuses the existing Lodgment Form / Lodged Instruments layout.
MS (Complex) - ms-legalinstrument
NEW API: POST /api/ext/v1/lodgement/{lodgementId}/withdraw (WithdrawInstrumentOrchestrator)
- eligibility guards, resolve ELS instrument numbers, persist rows only after ELS success.
NEW outbound: POST {ELS}/api/v2/withdraw-lodgement via NEW ElsWithdrawFacade (SigV4, CB+retry).
EXISTING to MODIFY: lodgement/dashboard read API - expose withdrawable + withdrawalPending flags.
BPM: none.
```

---

## 6. Thin input — mark it, never block on it

Produce the sheet anyway. Where you genuinely do not know, put a bracketed
marker in column D so it is obvious and editable:

| Unknown | Write |
|---|---|
| new vs existing API | `[TBD: confirm NEW vs EXISTING] <endpoint>` |
| which service | `[TBD: service?]` |
| BPM impact | `BPM: [TBD: confirm process / subprocess impact]` |
| DB impact | `DB: [TBD: schema change?]` |
| complexity signal absent | best guess (lower of two) + `[TBD: verify complexity]` |
| a decision is pending someone | `[Highlighted: <decision> is pending <name>'s approval]` |
| whole AC undetailed | `[TBD: technical analysis pending]` + best-guess flags |

`cr-tool build` lists every cell still carrying one of these markers, so they
cannot be forgotten.

---

## 7. Summary

| Row | Formula |
|---|---|
| Development | `=Details!Q<total row>` |
| QA | `=ROUND(C3 × 40%, 0)` |
| Requirement & Design | `=ROUND(C3 × 20%, 0)` |
| Total | `=SUM(C3:C5)` |

The two percentages live in `MasterData!B11` and `MasterData!B12` so the sheet
documents itself. The optional `Original Efforts` column (D) is for showing a
prior estimate side by side; leave it out if there isn't one.
