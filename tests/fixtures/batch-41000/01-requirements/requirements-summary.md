# Requirements Summary — 41000

## Scope
Early termination, consent and payout for the Seamless Lodgment module.

## Acceptance Criteria

### SLADCYBQSK-41000 — Early Termination and Payout

- **AC-1** — Given the transaction is active, When the user opts into early termination, Then the system records the outcome.
- **AC-1.1** — Given the transaction is active, When a confirmation is shown before proceeding, Then the system records the outcome.
- **AC-2** — Given the transaction is active, When consent is captured from every option holder, Then the system records the outcome.
- **AC-3.1** — Given the transaction is active, When the payout amount is computed from DCA balances, Then the system records the outcome.
- **AC-3.2** — Given the transaction is active, When refunds and bounce-backs are reconciled, Then the system records the outcome.
- **AC-7.1** — Given the transaction is active, When the status moves to Terminated, Then the system records the outcome.
- **AC-7.2** — Given the transaction is active, When the lodgement record is closed, Then the system records the outcome.
- **AC-7.3** — Given the transaction is active, When a notification is sent to the law firm, Then the system records the outcome.
- **AC-8** — Given the transaction is active, When an audit entry is written for every transition, Then the system records the outcome.
