# Git Versioning Policy

```yaml
status: APPROVED
authority: INSTRUCTOR_RULING
approved_date: 2026-07-21
scope: IS529N_TECHNICAL_VERSION_CONTROL
```

## Role and system boundary

Git and GitHub preserve file-level technical evolution across annual IS529N course runs. A commit records that files changed; it does not establish academic approval, source authority, factual correctness, permission to publish, or actual classroom conduct.

The course ledger records academically consequential decisions and actual teaching events. The resource registry records provenance and evidentiary status. Wikidot is the student-facing distribution layer. The historical resource repository remains immutable and outside Git.

## Branches

- `main` contains the latest stable, instructor-approved course state.
- Annual development uses `semester/<year>`, beginning with `semester/2026`.
- Bounded work may use `governance/<purpose>`, `lecture/<year>-LNN`, `assessment/<year>-midsem`, `assessment/<year>-endsem`, or `website/<year>-publication`.
- Trivial formatting corrections do not require separate branches.

Annual and bounded branches enter `main` through reviewed pull requests. Active development must not be pushed directly to `main`.

## Commit discipline

Each commit must be a coherent, reviewable unit with a descriptive conventional prefix, including:

- `chore(repo):`
- `docs(governance):`
- `feat(course):`
- `feat(lecture-NN):`
- `feat(assessment):`
- `docs(session):`
- `fix(ledger):`
- `chore(release):`

Vague messages such as `update`, `changes`, `final`, and `misc` are prohibited. Staging must be explicit enough to exclude local-only, restricted, unapproved, or unrelated files.

## Review and merge policy

Pull requests must report the purpose, files changed, validation results, public-safety review, academic approval dependencies, and known exclusions. Instructor approval is required before merging an annual baseline or completed course run into `main`.

Force-pushing, rewriting published history, deleting or moving release tags, and squashing academically meaningful history without review are prohibited. Merge strategy must preserve a comprehensible annual record.

## Corrections

Technical mistakes are corrected in a new commit. Published history is not rewritten merely to make it look cleaner. Academically consequential corrections require the appropriate new ledger event; existing ledger blocks must not be altered to simplify Git history.

If sensitive material is discovered before publication, remove it from the proposed public file set. If it is discovered after publication, stop further publication, revoke exposed credentials where applicable, assess history removal separately, and document the response without exposing the sensitive value.

## Binary files

Only instructor-selected, project-created classroom decks and PDFs may enter Git. When Git LFS is available and has been deliberately enabled, selected `*.pptx`, `*.odp`, and `*.pdf` classroom artefacts should use LFS. Historical and imported files stay outside the default projection.
