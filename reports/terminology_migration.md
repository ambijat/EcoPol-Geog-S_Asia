# Terminology Migration

```yaml
authority: INSTRUCTOR_RULING
date: 2026-07-21
scope: MUTABLE_SUBORDINATE_PROJECT_FILES_ONLY
```

The term `avatar` is not adopted as formal IS529N terminology. This migration leaves historical evidence unchanged.

## Files changed

| File | Old term | Replacement |
|---|---|---|
| `README.md` | `working derivative and sanitised avatar` | `controlled working derivative`; `sanitised working derivative` only when actual sanitisation occurred |
| `docs/RESOURCE_GOVERNANCE.md` | `Sanitised avatars and other working derivatives` | `Controlled working derivatives`; conditional `sanitised working derivative` |
| `templates/resource_map.md` | `Source/Avatar path` | `Source/Derivative path` |
| `templates/factual_verification.md` | `avatar_id` | `working_derivative_id` |
| `docs/IDENTIFIER_CONVENTION.md` | `IS529N-AVT-0001` | `IS529N-DER-0001` |

## Controlled replacements

- Use `original source` for immutable source material.
- Use `registered source` only after canonical registration.
- Use `controlled working derivative` for ordinary project-owned derivatives.
- Use `sanitised working derivative` only when sanitisation actually occurred.
- Use `classroom deliverable` for instructor-facing or student-facing teaching outputs.

## Files deliberately left unchanged

| Preserved file or class | Reason |
|---|---|
| `SEMESTER2026_Course_Governance_Preamble.md` | Explicitly protected by instructor ruling; wording is historical governance evidence. |
| `course_ledger/ledger.jsonl` blocks 2, 4, and 8 | Canonical blocks are immutable historical evidence. |
| `course_ledger/retrospective_events_2026-07-20.json` | Source evidence for already appended retrospective blocks. |
| `course_ledger/events/2026-07-20-hosted-references-page-registered.json` | Source event associated with appended block 8. |
| `online_sources/references-ma_audit.md` | Historical audit record whose original terminology is evidentially relevant. |
| `docs/HOSTED_SOURCE_GOVERNANCE_DRAFT.md` | Preserved remediation draft showing the wording removed from the preamble. |
| Previously generated census/reconstruction reports | Point-in-time reports are retained rather than silently rewritten. |

Future mutable documentation and classroom-production files must use the controlled terminology defined in `docs/HOSTED_SOURCE_GOVERNANCE.md`.
