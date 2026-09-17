# Low-Level Design — 41000 (v4)

**Story:** SLADCYBQSK-41000: Early Termination and Payout

## AC-1: The user opts into early termination

### 1.3 Impact Analysis

| # | Layer | Component/Service | Current Behavior | Impact (Low/Med/High) | Change Required |
|---|-------|-------------------|------------------|-----------------------|-----------------|
| 1 | Frontend | TerminationPage | existing | High | implement the user opts into early termination |
| 2 | Backend | ms-txn / TerminationService | existing | Medium | implement the user opts into early termination |

### 1.4 Reusability Assessment

| # | Candidate | Location (file/endpoint) | Satisfies | Reuse Level (0/1/2/4) | Decision | Gap Justification / Evidence |
|---|-----------|--------------------------|-----------|-----------------------|----------|------------------------------|
| 1 | `TerminationPage` | `web-react/src/pages/TerminationPage.tsx` | partially | 0 | NEW | graphify |
| 2 | `TxnService.find` | `ms-txn/service/TxnService.java` | partially | 2 | EXTEND | graphify |

### 1.6 UI Changes

#### Component: `TerminationPage` (`web-react/src/pages/TerminationPage.tsx`)
- **Change Type:** New
- **Screen Reference:** `screens/termination.png`

### 1.8 BPM Changes

**No BPM changes required for this AC.**

## AC-1.1: A confirmation is shown before proceeding

### 2.3 Impact Analysis

| # | Layer | Component/Service | Current Behavior | Impact (Low/Med/High) | Change Required |
|---|-------|-------------------|------------------|-----------------------|-----------------|
| 1 | Frontend | ConfirmDialog | existing | Low | implement a confirmation is shown before proceeding |

### 2.8 BPM Changes

**No BPM changes required for this AC.**

## AC-2: Consent is captured from every option holder

### 3.3 Impact Analysis

| # | Layer | Component/Service | Current Behavior | Impact (Low/Med/High) | Change Required |
|---|-------|-------------------|------------------|-----------------------|-----------------|
| 1 | Backend | ms-txn / ConsentService | existing | High | implement consent is captured from every option holder |
| 2 | Database | Txn.Consent | existing | Medium | implement consent is captured from every option holder |

### 3.4 Reusability Assessment

| # | Candidate | Location (file/endpoint) | Satisfies | Reuse Level (0/1/2/4) | Decision | Gap Justification / Evidence |
|---|-----------|--------------------------|-----------|-----------------------|----------|------------------------------|
| 1 | `ConsentRepository` | `ms-txn/repository/ConsentRepository.java` | partially | None | NEW | graphify |
| 2 | `POST /api/v1/consent` | `POST /api/v1/consent` | partially | Low | EXTEND | graphify |

### 3.8 BPM Changes

**No BPM changes required for this AC.**

## AC-3.1: The payout amount is computed from dca balances

### 4.3 Impact Analysis

| # | Layer | Component/Service | Current Behavior | Impact (Low/Med/High) | Change Required |
|---|-------|-------------------|------------------|-----------------------|-----------------|
| 1 | Backend | ms-payment / PayoutCalculator | existing | High | implement the payout amount is computed from DCA balances |
| 2 | Integration | UOB payout API | existing | High | implement the payout amount is computed from DCA balances |

### 4.4 Reusability Assessment

| # | Candidate | Location (file/endpoint) | Satisfies | Reuse Level (0/1/2/4) | Decision | Gap Justification / Evidence |
|---|-----------|--------------------------|-----------|-----------------------|----------|------------------------------|
| 1 | `PayoutCalculator` | `ms-payment/service/PayoutCalculator.java` | partially | 1 | EXTEND | graphify |
| 2 | `GET /api/v1/dca/balance` | `GET /api/v1/dca/balance` | partially | High | REUSE | graphify |

### 4.8 BPM Changes

**No BPM changes required for this AC.**

## AC-3.2: Refunds and bounce-backs are reconciled

### 5.3 Impact Analysis

| # | Layer | Component/Service | Current Behavior | Impact (Low/Med/High) | Change Required |
|---|-------|-------------------|------------------|-----------------------|-----------------|
| 1 | Backend | ms-payment / RefundReconciler | existing | Medium | implement refunds and bounce-backs are reconciled |

### 5.8 BPM Changes

**No BPM changes required for this AC.**

## AC-7.1: The status moves to terminated

### 6.3 Impact Analysis

| # | Layer | Component/Service | Current Behavior | Impact (Low/Med/High) | Change Required |
|---|-------|-------------------|------------------|-----------------------|-----------------|
| 1 | Backend | ms-txn / StatusService | existing | Low | implement the status moves to Terminated |
| 2 | BPM | Termination Process | existing | Medium | implement the status moves to Terminated |

### 6.4 Reusability Assessment

| # | Candidate | Location (file/endpoint) | Satisfies | Reuse Level (0/1/2/4) | Decision | Gap Justification / Evidence |
|---|-----------|--------------------------|-----------|-----------------------|----------|------------------------------|
| 1 | `StatusService` | `ms-txn/service/StatusService.java` | partially | 4 | REUSE | graphify |

### 6.8 BPM Changes

- **Process:** `Termination Process` (`PROC_TERM`)

| # | Step | Type | Current | New | Details |
|---|------|------|---------|-----|---------|
| 1 | Terminate | System | none | new | called after consent |

## AC-7.2: The lodgement record is closed

### 7.3 Impact Analysis

| # | Layer | Component/Service | Current Behavior | Impact (Low/Med/High) | Change Required |
|---|-------|-------------------|------------------|-----------------------|-----------------|
| 1 | Backend | ms-legalinstrument / LodgementCloser | existing | Medium | implement the lodgement record is closed |

### 7.8 BPM Changes

**No BPM changes required for this AC.**

## AC-7.3: A notification is sent to the law firm

### 8.3 Impact Analysis

| # | Layer | Component/Service | Current Behavior | Impact (Low/Med/High) | Change Required |
|---|-------|-------------------|------------------|-----------------------|-----------------|
| 1 | Backend | ms-notification / Notifier | existing | Low | implement a notification is sent to the law firm |

### 8.8 BPM Changes

**No BPM changes required for this AC.**

## AC-8: An audit entry is written for every transition

### 9.3 Impact Analysis

| # | Layer | Component/Service | Current Behavior | Impact (Low/Med/High) | Change Required |
|---|-------|-------------------|------------------|-----------------------|-----------------|
| 1 | Database | Txn.AuditTrail | existing | Low | implement an audit entry is written for every transition |
| 2 | Backend | ms-txn / AuditListener | existing | Low | implement an audit entry is written for every transition |

### 9.4 Reusability Assessment

| # | Candidate | Location (file/endpoint) | Satisfies | Reuse Level (0/1/2/4) | Decision | Gap Justification / Evidence |
|---|-----------|--------------------------|-----------|-----------------------|----------|------------------------------|
| 1 | `AuditListener` | `ms-txn/audit/AuditListener.java` | partially | Moderate | EXTEND | graphify |
| 2 | `Txn.AuditTrail` | `Txn.AuditTrail` | partially | 2 | EXTEND | graphify |

### 9.8 BPM Changes

**No BPM changes required for this AC.**

