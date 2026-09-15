# Worked example — the reference CR

The real ver. 2 CR, shown as the chain from input to workbook. Its spec is
`examples/sample_cr_spec.json`; building it reproduces the source workbook.

Two stories, two very different shapes:

- **SLADCYBQSK-42132 — Post Lodgment: Withdrawal.** A user-facing flow: withdraw
  lodged instruments (single and multi-select), copy a withdrawn instrument,
  sync status back from ELS, handle concurrent access.
- **SLADCYBQSK-42528 — ELS Cost API Integration.** Backend-only: fetch real-time
  fees from ELS, persist and freeze them, fall back to a config price.

---

## Tender Story Points

### SLADCYBQSK-42132

| Dimension | Size | Counted |
|---|---|---|
| User Interaction | `Medium (4-6)` | withdraw instrument, confirm withdrawal, copy instrument, confirm copy — 4 |
| Pages | `Small (1-3)` | Legal Instruments tab, Lodgement Form — 2 |
| Integration | `Small (1-3)` | Webhook status update API, Withdraw Lodgment API — 2 |

`Framework Unit = 3×4 + 1×2 + 1×8 = 22`

| Dimension | Level | Why |
|---|---|---|
| Frontend | `1 - Low` | new action links, checkbox multi-select, popups, tooltips — only the list layout is reused |
| Backend | `2 - Moderate` | two new endpoints and a new facade, but on existing orchestration patterns |
| Interface | `4 - High` | the status-update webhook already exists and is only extended |
| Database | `1 - Low` | a whole new `InstrumentWithdrawal` table plus master data |
| QA | `2 - Moderate` | new cases for withdrawal and copy, existing lodgement suite reusable |

`Reusability Score = (1+2+4+1+2) / (5×4) × 100 = 50` → band 50–74 → **65%**

```
FU (Aft. Adj.) = 22 × (1 − 0.65) = 7.70
Req & Design   = 7.70 × 0.2      = 1.54
TSP            = (7.70 + 1.54) × 1.16 = 10.72
```

### SLADCYBQSK-42528

User Interaction is `Not Applicable` — there is no new user action, only a price
shown in an existing popup. That is the distinction to get right: `Not
Applicable` removes the dimension from the calculation, it does not score zero.

`Framework Unit = 0 + 1×2 + 1×8 = 10`, reusability `(4+4+2+2+2)/20 × 100 = 70`
→ **65%** → FU adj `3.50`, R&D `0.70`, **TSP 4.87**.

---

## Details

Nine rows across the two story groups. Note the S.No restarting at 1 for the
second group, and one `Shared` row per group.

| # | Story | Covers | UI | MS | DB | MD |
|---|---|---|---|---|---|---|
| 1 | 42132 | AC1.1–AC1.3 withdraw flow (single + multi-select, confirm, toast, in-progress state) | Med | Complex | – | **8** |
| 2 | 42132 | AC1.4 ELS status sync via the webhook | – | Med | – | **3** |
| 3 | 42132 | AC1.5/AC1.5.1 copy instrument → pre-filled create page | Simple | Med | – | **5** |
| 4 | 42132 | AC1.6/AC1.7 concurrent access popup on both actions | Simple | Simple | – | **3** |
| 5 | Shared | new table, copy-lineage columns, CodeTable master data, audit, access control | – | Simple | Complex | **3** |
| 1 | Cost | TAC-1/2/5 real-time ELS fee at Prepare Lodgement | – | Complex | – | **3** |
| 2 | Cost | TAC-3/4/6 persist, freeze, invalidate, derive submit amount | – | Med | – | **3** |
| 3 | Cost | TAC-7 fallback and error handling | – | Simple | – | **2** |
| 4 | Shared | fee columns on the instrument + read view | – | Simple | Simple ×3 | **1** |

**Development = 31 MD.**

Two things worth copying from this example:

- **Row 5 is 3 MD, not 8.** A `Shared` row carrying a new table, new master data,
  audit and access control is still `MS (Simple) + DB (Complex)` = 1.5 + 1 =
  2.5 → 3. DB weights are deliberately light; schema work is cheap in this
  framework and the effort sits in the MS rows that use it.
- **Row 1 is the only 8 MD row**, because a genuinely new orchestration endpoint
  with a new external facade is `MS (Complex)` and the screen work is a real
  `UI (Medium)`. Two flags, not four.

## Summary

| Activity | Total | Original Efforts |
|---|---|---|
| Development | 31 | 38 |
| QA (40%) | 12 | 15 |
| Requirement & Design (20%) | 6 | 11 |
| **Total** | **49** | **64** |

The `Original Efforts` column is the prior estimate, carried for comparison. It
is optional — omit `summary.original_efforts` and column D stays blank.

---

## A defect this example exposes

`cr-tool validate` reports two warnings on this spec:

```
! Details references user story 'COST-CALC-P1' but it has no row on the 'Tender Story Points' sheet.
! 'Tender Story Points' lists 'SLADCYBQSK-42528' but no Details row estimates it.
```

Both are real: in the source workbook the cost-API Details rows are keyed
`COST-CALC-P1` while the TSP sheet keys the same story `SLADCYBQSK-42528`. The
two sheets do not reconcile. Using the Jira key in both places fixes it — and
this is exactly the class of slip the cross-check exists to catch.
