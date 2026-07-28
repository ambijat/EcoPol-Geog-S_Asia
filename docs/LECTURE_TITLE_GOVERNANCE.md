# Lecture Title Governance

The human-readable title-control layer consists of `course/lecture_titles.txt` and `course/lecture_part_titles.txt`. Both are UTF-8, vertical-bar-delimited registries. Blank lines and comments beginning with `#` are ignored.

## Precedence

The cockpit applies this hierarchy:

1. `INSTRUCTOR_CONFIRMED`
2. manually edited `WORKING_DRAFT`
3. valid `TITLE_REGISTRY` file value
4. `HISTORICALLY_EXTRACTED` title-slide evidence
5. `FILENAME_INFERRED` evidence
6. `Pending instructor confirmation`

Reloading the registry creates a reviewable proposal. It does not change titles until confirmation. A proposed registry value that differs from an instructor-confirmed title is recorded as a conflict and is never applied automatically.

GUI edits are either working drafts or instructor-confirmed titles. Export writes confirmed titles atomically back to the registries while retaining all unconfirmed registry values. Existing files are first copied to `.bak` files; these backups are local-only.

All titles populated from historical evidence remain candidates until the instructor confirms them. Historical Part C evidence is classified as `SUPPLEMENTARY_PART_C`; it does not create a third Semester 2026 class session.

The canonical ledger is outside this workflow. Title reload, editing, confirmation, and export do not append or amend ledger blocks.
