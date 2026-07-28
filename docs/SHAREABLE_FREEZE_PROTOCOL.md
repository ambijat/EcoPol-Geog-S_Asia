# Shareable Freeze Protocol

```yaml
status: SHAREABLE_FREEZE
effective_date: 2026-07-28
free_sharing_ruling: INSTRUCTOR_CONFIRMED
authority_required_for_release: SEPARATE_EXPLICIT_ACTION
```

## Purpose

The project is entering controlled culmination. Work now favours correction,
clarity, preservation, verification, and a bounded handoff. New capability is
out of scope unless it is necessary to prevent data loss, correct a material
fault, protect restricted material, complete teacher incubation, or make the
project reproducibly shareable.

The state sequence is:

```text
WORKING -> FREEZE_CANDIDATE -> SHAREABLE_FREEZE -> RELEASED
```

- `FREEZE_CANDIDATE` means the project is being stabilised and audited.
- `SHAREABLE_FREEZE` means an exact, reviewed projection is ready to hand to
  another authorised person without depending on undocumented local state.
- `RELEASED` requires a separate authorised publication or distribution action.

A shareable freeze is not classroom approval, an F4 academic decision, or
semester closure.

## Free-sharing rule

Self-authored project material is freely shareable under CC0 1.0. It may be
copied, changed, taught from, or redistributed without asking permission. No
separate clearance ritual is required.

Private data, credentials, restricted assessments, and imported files created
by someone else remain outside the shareable freeze. This is a practical
boundary, not a proprietary claim over the project.

## Lecture 1A baseline

- The inherited 65-slide editable presentation is the canonical F0 pilot master
  accepted for identity and teacher incubation.
- The 15-slide v0.5 presentation is a synoptic companion: an additional overview
  layer that summarises the master. It is not a shortened, revised, or replacement
  master.
- Teacher incubation proceeds against the 65-slide master through the review
  units and decision vocabulary in
  `course/lectures/lecture_01/TEACHER_INCUBATION.md`.
- No generated deck becomes classroom-ready through technical validation alone.

## Shareable projection

The reviewed projection may include governance documents, public-safe templates
and schemas, validation utilities, tests, empty controlled structures, safe
metadata, and specifically approved deliverables.

It excludes source repositories, local databases, caches, previews, working
notes, student or assessment data, credentials, machine-specific paths, and
imported files not created for this project. The simple safety boundary in
`docs/PUBLIC_REPOSITORY_BOUNDARY.md` continues to govern.

## Freeze gate

The instructor may declare `SHAREABLE_FREEZE` only after all of the following
are evidenced:

- [x] Teacher incubation status and outstanding academic decisions are stated
  without representing them as complete.
- [x] The exact 508-file shareable candidate allowlist has been generated and
  reviewed.
- [x] Repository validation and the relevant automated tests pass.
- [x] The course ledger validates and its latest governed events are intact.
- [x] The exact projection is checked for credentials, personal or restricted
  data, private locations, absolute paths, and imported files.
- [x] Local-only binaries, databases, caches, and generated previews are absent
  from the projection.
- [x] The guide checksums, limitations, and handoff instructions are current.
- [x] The freeze is recorded in a dedicated clean commit.
- [x] The instructor's free-sharing ruling of 2026-07-28 is recorded.

Tagging, pushing, deploying, or distributing the freeze remains a separate
action and requires its own authority.

## Change control after freeze

After `SHAREABLE_FREEZE`, changes are limited to security or privacy corrections,
data-loss prevention, material factual or validation faults, authorised release
corrections, and explicitly approved academic decisions. Other ideas are placed
in a later-work record rather than added to the frozen project.

## Current determination

As of 2026-07-28, the project is `SHAREABLE_FREEZE`. The candidate allowlist is
current, all 229 automated tests and three subtests pass, repository validation
reports zero errors and zero warnings, the eleven-block ledger verifies, and the
public projection dry run passes. Self-authored project material is freely
shareable under CC0 1.0.
Lecture 1A teacher incubation remains open and must stay truthfully represented
as open; the freeze does not pretend that academic review is complete.
