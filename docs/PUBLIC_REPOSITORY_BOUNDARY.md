# Public Repository Boundary

```yaml
status: APPROVED
authority: INSTRUCTOR_RULING
approved_date: 2026-07-21
repository: ambijat/EcoPol-Geog-S_Asia
visibility: PUBLIC
```

## Permitted material

Self-authored project material is freely shareable under CC0 1.0. The public repository may contain governance documents, public-safe templates and schemas, validation and ledger utilities, tests, empty controlled directory structures, safe metadata, and instructor-selected classroom deliverables. No separate clearance ritual is required.

Presence in the local project, resource registry, Git history, or course ledger does not make material public-safe. Every publication set requires review.

## Prohibited material

The public repository must not contain:

- student names, email addresses, identifiers, roll numbers, attendance, marks, grades, answer scripts, submissions, or private communications;
- confidential institutional information or restricted assessment material;
- API keys, tokens, passwords, private keys, cookies, or other credentials;
- private Google Drive downloads or unapproved online captures;
- imported books, chapters, articles, datasets, images, or historical files not created for this project;
- local environment files, caches, temporary files, build artefacts, or machine-specific configuration;
- historical repository contents merely because they are locally accessible;
- unapproved drafts represented as final classroom material.

## Assessment security

Unpublished examinations, answer keys, marking schemes, question banks, draft assessments, and restricted assessment analyses remain local-only. Public assessment material requires an explicit instructor ruling that considers timing, reuse risk, student equity, and institutional policy.

## Credentials and incident handling

Credentials must be supplied through ignored local configuration or an approved secret-management system. They must never be written into examples, logs, ledger events, reports, commits, pull-request text, or release notes.

If a credential is exposed, do not merely delete the current file. Revoke or rotate it first, identify every Git location containing it, and obtain explicit authority before rewriting any published history.

## Public and local-only paths

| Project area | Public treatment |
|---|---|
| `docs/`, `templates/`, `schemas/`, `scripts/`, `tests/` | Public when reviewed and free of restricted data. |
| `course/lectures/` | Structure and approved deliverables only. Drafts and unapproved binaries remain local. |
| `course/instructor_materials/` | Local-only unless a specific item receives publication approval. |
| `course/assessments/` | Public-safe structure only; draft and restricted areas remain local. |
| `resources/` source directories | Contents local-only; `.gitkeep` may preserve controlled structure. |
| `resource_registry/` | Public only after reviewing every record for rights, personal data, private locations, and restricted provenance. |
| `reports/` | Public only when the report contains no personal data, restricted assessment detail, or machine-specific absolute paths. |
| `online_sources/` | Audit metadata only when authorised; no captured bytes by default. |
| `course_ledger/` | Public only after checking events for protected data and legacy local-path disclosure. |
| Generic triangulation schema, services, Qt view, tests, and synthetic fixtures | Public candidates after review. |
| Live triangulation topics, website-note content, source-specific claims, raw annotations, registry candidates, and draft student packages | Local-only. |

`.gitignore` prevents common accidental additions but does not approve files and does not remove already tracked content. Before every push, inspect tracked, staged, and untracked files and scan the exact proposed commit.

## Binary publication

Project-created editable decks and rendered PDFs may be public. Git LFS should manage `*.pptx`, `*.odp`, and `*.pdf` when available. Historical and imported binaries stay outside the default projection unless deliberately selected and their provenance is clear.
