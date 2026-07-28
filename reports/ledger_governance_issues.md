# Ledger Governance Issues

```yaml
inspection_mode: READ_ONLY
inspection_date: 2026-07-21
canonical_blocks_inspected: 9
status: OPEN_ISSUES_NOT_CORRECTED
```

This report records inconsistencies without changing any canonical block.

## Principal unresolved issue: block 4

Block 4 is a `PEDAGOGICAL_DECISION` titled **“Sanitised resource-avatar lifecycle adopted.”** It has:

- `approval_status: REVIEWED`
- `approved_by: null`
- `fidelity_status: F1 — Structurally faithful`

The title uses “adopted” despite the absence of an approving actor, and it uses terminology the instructor has now declined to adopt formally. Block 4 remains immutable historical evidence. No substantive correction to block 4 was authorised in this task.

## Other status and boundary issues

| Block | Observation | Governance issue | Current treatment |
|---:|---|---|---|
| 1 | `COURSE_CHARTER`, `DRAFT`, `approved_by: null` | A draft charter is present in the canonical chain without instructor approval. | Preserve; future review required. |
| 2 | `RESOURCE_AUDIT`, `REVIEWED`, `approved_by: null` | `REVIEWED` does not identify a reviewer. | Preserve; status semantics require later ruling. |
| 3 | `PEDAGOGICAL_DECISION`, `REVIEWED`, `approved_by: null` | A decision-like block lacks an approving or reviewing actor. | Preserve; later governance review required. |
| 4 | `PEDAGOGICAL_DECISION`, `REVIEWED`, `approved_by: null` | “Adopted” wording and non-adopted terminology conflict with approval metadata. | Preserve unchanged. |
| 5 | `PEDAGOGICAL_DECISION`, `REVIEWED`, `approved_by: null` | A decision-like block lacks an approving or reviewing actor. | Preserve; later governance review required. |
| 6 | `VERSION_CONTROL_EVENT`, `REVIEWED`, `approved_by: null` | Routine Git initialisation is now outside the normal academic-ledger boundary. | Preserve as legacy evidence. |
| 7 | `WORKFLOW_EVENT`, `DRAFT`, `approved_by: null` | Ledger activation is a routine technical event and a draft was appended canonically. | Preserve as legacy evidence. |
| 8 | `RESOURCE_AUDIT`, `DRAFT`, `approved_by: null` | Draft event was appended and exceeded its bounded authority. | Preserved and contextually corrected by approved block 9. |
| 9 | `GOVERNANCE_CORRECTION`, `APPROVED`, `approved_by: Instructor`, `F4` | No inconsistency observed; it is approved but deliberately not sealed. | Canonical corrective record. |

## System-level observations

- No existing block carries `approval_status: SEALED` or fidelity `F5`.
- The historical meanings of `DRAFT`, `REVIEWED`, `APPROVED`, and `SEALED` were not consistently enforced before block 9.
- Future unapproved proposals must remain in `course_ledger/drafts/`.
- Routine technical changes belong in Git, not the academic ledger.
- Later corrections must use new instructor-approved blocks rather than rewriting historical records.
