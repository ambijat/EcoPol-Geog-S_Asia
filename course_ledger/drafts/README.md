# Draft Ledger Events

This directory is the required location for unapproved academic-event proposals.

Draft files:

- are outside the canonical `ledger.jsonl` chain;
- have no block number, previous-block hash, or content hash;
- carry `approval_status: DRAFT` and `approved_by: null`;
- may be revised during instructor review;
- confer no academic or governance authority;
- must not be appended until the instructor gives explicit approval.

After approval, the event metadata must record `approval_status: APPROVED` and identify the instructor as approving authority. Only then may the approved event be supplied to the ledger utility, which assigns its canonical block number and hashes.

Existing canonical draft-status blocks are immutable legacy evidence. They remain in place and are not examples for future practice.
