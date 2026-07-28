# Annual Release Protocol

```yaml
status: APPROVED
authority: INSTRUCTOR_RULING
approved_date: 2026-07-21
course_code: IS529N
```

## Annual lifecycle

1. Create `semester/<year>` from the latest instructor-approved stable state.
2. Develop paired Tuesday Part A and Friday Part B classroom deliverables through bounded branches where useful.
3. Review sources, provenance, factual verification, public safety, and classroom usability.
4. Record technical evolution in Git and academically consequential decisions or actual conduct in the course ledger.
5. Validate the repository throughout the course run.
6. Complete an instructor-approved semester-closure ledger event.
7. Review and merge the annual branch into `main`.
8. Create an immutable annotated annual tag and corresponding GitHub release.

## Release criteria

An annual release requires:

- instructor approval of the stable course state;
- a valid repository and test suite;
- a verified course-ledger chain and approved semester-closure event;
- completed public-safety, credential, student-data, assessment-security, imported-file, and file-size checks;
- confirmation that historical resources and local-only material are excluded;
- reviewed release notes and no unresolved high-risk factual claims in published classroom deliverables.

## Tags and versions

Use annotated tags such as:

```text
IS529N-2026-v0.1
IS529N-2026-v0.5
IS529N-2026-v1.0
IS529N-2026-v1.1
```

`v1.0` denotes the completed annual course run. Earlier versions are governed milestones; later patch versions record approved post-run corrections. Existing tags are immutable and must never be moved, overwritten, or deleted to conceal history.

## Release notes

Release notes must identify the annual scope, lecture pairs included, governance or structural changes, ledger closure reference and chain tip, validation results, public exclusions, known limitations, and any migration guidance. They must not disclose student information, credentials, restricted assessments, private locations, or unapproved material.

## Semester closure

Before closure, reconcile the delivered Tuesday and Friday sessions, post-class records, approved deferrals, assessment milestones, and final repository state. The instructor must explicitly approve the academically consequential closure event before it is appended to the ledger.

## Following year

The next annual branch begins from the latest approved `main`. Historical annual releases and tags remain unchanged. New work updates controlled derivatives and classroom deliverables; it does not rename or modify inherited original sources.

## Wikidot relationship

GitHub preserves technical history and approved public artefacts. Wikidot remains the student-facing distribution layer. Publishing to either system requires separate authorisation, and publication on Wikidot does not itself constitute a Git release or change the authoritative Semester project record.
