# Lecture-Part Knowledge-to-Publication Pipeline

## Concept note

### Purpose

The next development stage should organise the cockpit around a bounded
teaching unit:

```text
Lecture 1A
Lecture 1B
Lecture 2A
Lecture 2B
…
```

Each lecture part should connect its evidence, analytical notes, editable
presentation and final published presentation. The Presentation Workbench is
the production centre. Lecture Raw Material and AI-assisted LaTeX Notes are its
inputs. The Published Presentation PDF is its governed output.

The cockpit should make these connections visible and reviewable. It should
not become an automatic presentation generator.

The required read-only prelude—assessing and improving the topic structure of
the raw evidence repository—is documented in
[`../reports/LECTURE_RAW_MATERIAL_ORGANISATION_AUDIT_2026-07-27.md`](../reports/LECTURE_RAW_MATERIAL_ORGANISATION_AUDIT_2026-07-27.md).
The subsequent 900-slide reverse-engineering pass and controlled lecture-topic
taxonomy are documented in
[`../reports/PRESENTATION_DERIVED_RESOURCE_TAXONOMY_2026-07-27.md`](../reports/PRESENTATION_DERIVED_RESOURCE_TAXONOMY_2026-07-27.md).
The repeatable operating procedure derived from that work and the completed
Lecture 2, 3, 4, 5, 7 and 8 folderisation cases is maintained in
[`PRESENTATION_LED_RAW_MATERIAL_DRESSING_MANUAL.md`](PRESENTATION_LED_RAW_MATERIAL_DRESSING_MANUAL.md).
The combined instructor-facing UX for using both topical and country/spatial
evidence is defined in
[`TOPICAL_SPATIAL_COCKPIT_UX_DESIGN.md`](TOPICAL_SPATIAL_COCKPIT_UX_DESIGN.md).

## The four faces of one lecture part

The course materials can be understood as three working faces followed by one
publication face:

| Face | Artifact layer | Function |
|---|---|---|
| Evidence | Lecture Raw Material | Books, articles, maps, images, datasets and historical teaching material |
| Analysis | AI-assisted LaTeX Notes | Structured `.tex` notes and `.pdf` reading copies derived from or informed by evidence |
| Production | Presentation Workbench | Editable ODP/PPT/PPTX in which the instructor prepares the lecture |
| Publication | Published Presentation PDFs | Classroom-facing PDF exported from the approved Workbench presentation |

The intended flow is:

```text
Lecture Raw Material ───────┐
                            ├──→ instructor-reviewed content plan
AI-assisted LaTeX Notes ────┘                 │
                                              ▼
                                  Presentation Workbench
                                              │
                                    instructor approval
                                              │
                                              ▼
                                  Published Presentation PDF
```

The Workbench presentation is the only editable presentation target in this
pipeline. Raw material remains read-only. LaTeX notes remain a separate
analytical layer. Published PDFs are outputs rather than editing sources.

## The lecture-part identity spine

Every pipeline should have one stable identity independent of filenames:

```text
course_code: IS529N
lecture_number: 1–15
part: A or B
lecture_part_id: IS529N-L01A
```

This identity should connect, but never replace, symbolic file locators.

Example:

```text
lecture_part_id: IS529N-L01A
workbench:
  PRESENTATION_WORKBENCH://LECTURE1/lecture1a.odp
published:
  PUBLISHED_PRESENTATION_PDF://lecture1a.pdf
latex_notes:
  AI_GENERATED_ARTIFACT://LEC_1/region_concept/concept_region.tex
raw_material_topics:
  - FOUNDATIONAL_RESOURCE://LEC_RES_1/region_concept
```

Filename matching may propose `lecture1a.odp` → `lecture1a.pdf`, but the
instructor must confirm the relationship. A folder such as `LEC_1` is
lecture-level, not automatically Part A or Part B. Shared notes or raw material
must be marked as:

- shared by both parts;
- assigned to Part A;
- assigned to Part B; or
- awaiting assignment.

The application must not guess when the part is ambiguous.

## Two levels of AI assistance

### Level 1: process the inputs

Level 1 has two parallel lanes.

#### Lane 1A — Raw-material processing

AI assistance may help the instructor:

- inventory a selected topic folder;
- extract titles, headings, captions and visible claims;
- prepare source summaries;
- identify concepts, places, periods, datasets and possible visuals;
- distinguish direct evidence from interpretation;
- identify conflicting or missing evidence;
- propose relevance to Lecture Part A, Part B or both.

The output should be a review packet or draft analytical record. It must cite
the symbolic raw-material locations used. It must not alter, rename or move the
source files.

#### Lane 1B — LaTeX-note processing

AI assistance may help the instructor:

- inspect selected `.tex` notes and their `.pdf` reading copies;
- identify sections, arguments, examples and teaching sequences;
- compare several notes for overlap or contradiction;
- identify claims needing stronger source support;
- suggest which note sections belong to Part A, Part B or both;
- relate note sections back to raw-material topics.

LaTeX build auxiliaries are outside the academic workflow and must remain
ignored. Only `.tex` and `.pdf` files are candidates.

Level 1 outputs remain proposals. They do not become approved lecture content
merely because an AI tool produced them.

### Level 2: wire reviewed inputs into the Workbench

Level 2 operates only after the instructor has reviewed the relevant Level 1
material. It considers:

- the current Workbench presentation;
- its slide order and existing claims;
- accepted raw-material evidence;
- accepted LaTeX-note sections;
- the teaching purpose of the lecture part;
- the current published PDF, when one exists.

Its output should be an integration proposal, not an automatically rewritten
presentation. A proposal may contain:

| Proposed field | Example |
|---|---|
| Target | Slide 6 of `lecture1a.odp` |
| Action | Revise, add, split, retain or remove |
| Proposed purpose | Clarify competing definitions of region |
| Supporting raw material | `FOUNDATIONAL_RESOURCE://LEC_RES_1/region_concept` |
| Supporting note | `AI_GENERATED_ARTIFACT://LEC_1/region_concept/concept_region.tex` |
| Suggested treatment | Two-column comparison with one map |
| Confidence | Provisional |
| Instructor decision | Pending |

The instructor should be able to accept, edit, defer or reject each proposed
intervention. Accepted interventions are then applied manually in LibreOffice
or another associated editor. The cockpit records the decision and opens the
Workbench file; it does not silently rewrite the deck.

## Relationship model

The existing relationship vocabulary can express most of the pipeline:

```text
LaTeX note GENERATED_FROM Raw Material
LaTeX note SUMMARISES Raw Material
Raw Material CANDIDATE_INGREDIENT_FOR Workbench
LaTeX note CANDIDATE_INGREDIENT_FOR Workbench
Raw Material ACCEPTED_INGREDIENT_FOR Workbench
LaTeX note ACCEPTED_INGREDIENT_FOR Workbench
LaTeX note INTEGRATED_INTO Workbench
Workbench PUBLISHED_AS Published PDF
Published PDF EXPORT_OF Workbench
Published PDF USED_IN_LECTURE Lecture Part
```

Future development should add the lecture part as a first-class contextual
record. Until then, the lecture-part identifier may be stored in local
workflow state and relationship notes without changing physical paths.

## Proposed cockpit experience

Add a future **Lecture Pipeline** screen organised in natural teaching order:

```text
Lecture 1A
  Raw Material        4 topics linked
  LaTeX Notes         3 TeX sources · 3 PDF copies
  Workbench           lecture1a.odp
  Published           lecture1a.pdf
  Integration         5 proposals · 2 accepted · 3 pending

Lecture 1B
  Raw Material        awaiting assignment
  LaTeX Notes         2 shared note sets
  Workbench           lecture1b.odp
  Published           lecture1b.pdf
  Integration         not started
```

Useful actions would be:

- **Open Raw Material**
- **Open LaTeX Notes**
- **Open Workbench**
- **Compare Published PDF**
- **Assign to Part A / Part B / Both**
- **Prepare Level 1 Review Packet**
- **Prepare Level 2 Integration Proposal**
- **Review Proposed Changes**
- **Mark Applied in Workbench**
- **Approve for Publication**

The screen should show missing links clearly without treating them as errors.
A lecture part may legitimately have no published revision yet.

## Workflow states and instructor gates

Suggested states:

```text
UNASSIGNED
WIRED_AS_CANDIDATE
INPUTS_UNDER_REVIEW
INPUTS_ACCEPTED
INTEGRATION_PROPOSED
INTEGRATION_REVIEWED
APPLIED_IN_WORKBENCH
READY_FOR_PUBLICATION
PUBLISHED
DEFERRED
```

Required human gates:

1. Confirm which artifacts belong to the lecture part.
2. Review Level 1 raw-material and LaTeX-note processing.
3. Accept the evidence and note sections eligible for synthesis.
4. Review every Level 2 Workbench intervention.
5. Confirm that accepted changes were actually applied.
6. Approve the Workbench version for export.
7. Confirm the Workbench-to-published-PDF relationship.

AI assistance must never set `READY_FOR_PUBLICATION` or `PUBLISHED`.

## Resource and privacy boundaries

The design should remain suitable for a manually governed social-science
workflow:

- no scanning merely because a path was selected;
- no background crawling of repositories;
- no routine checksums;
- metadata-first indexing;
- process only the folders or files selected for a lecture part;
- cache small derived text records rather than repeatedly reading binaries;
- keep source repositories unchanged;
- keep physical paths machine-local;
- use symbolic locators in persistent and exportable records;
- do not send material to an external AI service automatically;
- make every AI packet inspectable before it leaves the desktop;
- treat pasted AI returns as drafts requiring instructor review.

## Bounded development pathway

### Phase 1 — Lecture-part wiring

Implement a read-only `LecturePart` overview and manual assignment controls.
Resolve natural filenames such as `lecture1a`, `lecture1b`, `lecture2a` and
`lecture2b`. Show proposals but require confirmation.

### Phase 2 — Input bundles

Allow the instructor to assemble one bounded raw-material bundle and one
LaTeX-note bundle for a selected lecture part. Record symbolic locators and
manual inclusion decisions.

### Phase 3 — Level 1 review packets

Generate inspectable, local packets separately for raw material and LaTeX
notes. Support manual copy/paste to an external AI tool before considering any
direct API integration.

### Phase 4 — Level 2 integration proposals

Combine only instructor-accepted Level 1 results with the current Workbench
presentation structure. Produce slide-level proposals with explicit evidence
links and decision controls.

### Phase 5 — Workbench and publication gate

Record which accepted proposals were manually applied. Relate the resulting
Workbench version to its published PDF and retain the earlier version as
history.

### Phase 6 — Course-level visualisation

Use Knowledge Maps to visualise relationships across lecture parts, concepts,
sources, notes, presentations and published outputs. This is an overview of
confirmed records, not a replacement for the lecture-part workflow.

## Recommended first pilot

Begin with one bounded vertical slice:

```text
IS529N-L01A
→ one raw-material topic
→ one LaTeX note and PDF copy
→ one Workbench presentation
→ one existing published PDF
→ one proposed slide intervention
→ one instructor decision
```

Do not begin by automating all 30 lecture parts. The pilot should establish
whether the identity rules, relationship directions, evidence display and
manual approval sequence make sense to the instructor.

## Acceptance criteria for the pilot

The pilot is successful when:

1. Lecture 1A is represented independently from Lecture 1B.
2. The four artifact faces are visible on one screen.
3. Shared and ambiguous inputs are not silently assigned.
4. Raw material and LaTeX notes can be linked without modifying source files.
5. Level 1 results retain their source locators.
6. Level 2 proposes a slide intervention without editing the Workbench file.
7. The instructor can edit, accept, defer or reject the proposal.
8. An accepted proposal is not confused with an applied change.
9. Publication requires a separate instructor decision.
10. The workflow remains responsive and performs no automatic full-repository
    scan or routine file hashing.

## Immediate next design decision

Before implementation, define how lecture-level folders such as `LEC_1`
should be divided between Parts A and B. The safest default is **shared,
awaiting assignment**. Filename matches may suggest an assignment, but only an
instructor decision should make it authoritative.
