# Requirements Summary — batch-42132

> Output of `requirements-consolidate`. Written to `01-requirements/requirements-summary.md`.

## Scope
Post-lodgment withdrawal and copy of legal instruments in the Seamless Lodgment module.

## Acceptance Criteria

### SLADCYBQSK-42132 — Post Lodgment: Withdrawal

- **AC-1** — Given a lodgment is Submitted, When the user withdraws one or more instruments, Then the withdrawal request is raised to ELS and the row shows a withdrawal-in-progress state.
- **AC-2** — Given ELS returns a status update, When DCP receives the webhook, Then the per-instrument withdrawal outcome is reflected in the Lodged Instruments section.
- **AC-3** — Given an instrument is Withdrawn, When the user copies it, Then the Create Instrument page opens pre-filled from the withdrawn instrument.

## Business Rules & Constraints
- BR5 — only the lodging firm may withdraw an instrument.
- BR6 — every withdrawal and copy action is audited.

## Open Questions
- None.

## Traceability

| Ticket | Figma | Confluence |
|---|---|---|
| SLADCYBQSK-42132 | figma/lodgment-form.png | confluence/withdrawal-spec.md |
