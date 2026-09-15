# High-Level Design — batch-42132

## 1. Overview
Adds instrument withdrawal and copy to the Seamless Lodgment module.

## 3. Affected DCP modules & services
ms-legalinstrument, web-react.

## 6. API surface (high level)
- POST /api/ext/v1/lodgement/{lodgementId}/withdraw
- POST /api/ext/v1/legal-instrument/{instrumentId}/copy

## 7. Data model changes (high level)
New table Lodgement.InstrumentWithdrawal; copy-lineage columns on Lodgement.Instrument.

## 8. Integrations
- ELS withdraw-lodgement outbound API
- ELS status-update inbound webhook

## 11. Reuse summary
Target 70% reuse.
