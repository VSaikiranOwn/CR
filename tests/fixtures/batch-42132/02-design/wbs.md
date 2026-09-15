# WBS: batch-42132 - Post Lodgment Withdrawal

**Batch:** batch-42132
**Status:** Ready for development

## 0. Brief Summary of Expected Changes

- **Backend:** new withdraw and copy endpoints in ms-legalinstrument
- **Frontend:** withdraw + copy affordances on the Lodgment Form
- **Data:** new InstrumentWithdrawal table, copy-lineage columns
- **Integrations/BPM:** ELS withdraw API and status webhook; No BPM change

## 2.1 API Reuse Register (mandatory)

| # | Capability | Existing API/Component | Service/Module | Decision | Gap Justification | Evidence (HLD/LLD/Graphify ref) | Linked WBS IDs |
|---|------------|------------------------|----------------|----------|-------------------|----------------------------------|----------------|
| 1 | Retrieve lodgement | GET /api/ext/v1/lodgement/{id} | ms-legalinstrument | REUSE | N/A | HLD 6 | WBS-SLADCYBQSK-42132-BE-01 |
| 2 | Withdraw instruments | None | ms-legalinstrument | NEW | No existing endpoint | HLD 6 gap #1 | WBS-SLADCYBQSK-42132-BE-02 |
| 3 | Status update webhook | POST /api/ext/v1/legal-instrument/webhook/status-update | ms-legalinstrument | EXTEND | new updateType | LLD AC-2 2.4 | WBS-SLADCYBQSK-42132-BE-03 |
| 4 | Copy instrument | None | ms-legalinstrument | NEW | No existing endpoint | HLD 6 gap #2 | WBS-SLADCYBQSK-42132-BE-04 |

## 3. TODO List (ordered by sprint sequence)

### 3.1 Backend Tasks - ms-legalinstrument

- [ ] **WBS-SLADCYBQSK-42132-BE-01** - `FR-42132-01` - `AC-1` - [M]
  - **Repo:** `ms-legalinstrument/src/main/java/.../service`
  - **Reuse strategy:** `REUSE`
  - **Source API/reference:** `LodgementService#find`
  - **What:** Resolve eligible instruments for withdrawal
  - **TDD slice (RED first):** `TS-42132-BE-01`

- [ ] **WBS-SLADCYBQSK-42132-BE-02** - `FR-42132-01` - `AC-1` - [L]
  - **Repo:** `ms-legalinstrument/src/main/java/.../controller`
  - **Reuse strategy:** `NEW`
  - **Source API/reference:** none (gap in 1.4)
  - **What:** New withdraw orchestration endpoint calling ELS
  - **TDD slice (RED first):** `TS-42132-BE-02`

- [ ] **WBS-SLADCYBQSK-42132-BE-03** - `FR-42132-02` - `AC-2` - [M]
  - **Repo:** `ms-legalinstrument/src/main/java/.../webhook`
  - **Reuse strategy:** `EXTEND`
  - **Source API/reference:** `StatusUpdateHandlerRegistry`
  - **What:** Handle the Withdrawal update type
  - **TDD slice (RED first):** `TS-42132-BE-03`

- [ ] **WBS-SLADCYBQSK-42132-BE-04** - `FR-42132-03` - `AC-3` - [L]
  - **Repo:** `ms-legalinstrument/src/main/java/.../service`
  - **Reuse strategy:** `NEW`
  - **Source API/reference:** none (gap in 3.4)
  - **What:** Deep-copy the instrument aggregate into a new PREPARATION draft
  - **TDD slice (RED first):** `TS-42132-BE-04`

### 3.2 Frontend Tasks - web-react

- [ ] **WBS-SLADCYBQSK-42132-FE-01** - `FR-42132-01` - `AC-1` - [M]
  - **Repo:** `web-react/src/pages/LodgmentForm.tsx`
  - **Reuse strategy:** `EXTEND`
  - **Source API/reference:** `web-react/src/pages/LodgmentForm.tsx`
  - **What:** Withdraw action link, multi-select, confirm popup, toast
  - **TDD slice (RED first):** `TS-42132-FE-01`

- [ ] **WBS-SLADCYBQSK-42132-FE-02** - `FR-42132-03` - `AC-3` - [S]
  - **Repo:** `web-react/src/pages/LodgmentForm.tsx`
  - **Reuse strategy:** `REUSE`
  - **Source API/reference:** `web-react/src/pages/CreateInstrumentPage.tsx`
  - **What:** Copy action link and navigation to the pre-filled create page
  - **TDD slice (RED first):** `TS-42132-FE-02`

### 3.3 Coordination Tasks (DB/BPM/Docs)

- [ ] **WBS-SLADCYBQSK-42132-DB-01** - `AC-1` - [L]
  - **Repo:** DBA (manual)
  - **What:** Create Lodgement.InstrumentWithdrawal and copy-lineage columns

- [ ] **WBS-SLADCYBQSK-42132-DOCS-01** - All ACs - [S]
  - **Repo:** `.github/workspace/batch-42132/03-development/`
  - **What:** Keep tdd-log.md, mr-links.md, governance-checklist.md updated
