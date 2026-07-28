# Presentation-Led Raw Material Dressing Manual

## Status and purpose

This is the standard operating reference for arranging IS529N Lecture Raw
Material in accordance with the structure of the published presentations.
Use it whenever a new lecture resource folder is created, an inherited folder
is cleaned up, or new readings, datasets, maps, images or reports are added.

The procedure is **presentation-led, evidence-based and instructor-governed**.
Published presentations reveal the teaching sequence; they do not prove that
every old file belongs to a topic. The aim is to make material easy to find
without rewriting sources, hiding uncertainty or creating artificial matches.

“Dressing” means:

- recovering the lecture and topic structure from the published presentation;
- assigning each source a clear academic role;
- replacing generic containers with meaningful topic folders;
- isolating uncertain, duplicate, derived and workflow material for review;
- recording every proposed and completed move; and
- verifying that no physical file was lost.

It does **not** mean editing source content, automatically registering files,
deleting suspected duplicates, or generating a presentation.

## Governing principles

1. **The published presentation supplies the teaching taxonomy.**
2. **The source's content supplies its placement.** A filename alone is never
   sufficient evidence for a move.
3. **Every physical file has one primary home.** Additional relevance is
   represented as a relationship, not by making another copy.
4. **Uncertainty remains visible.** A review folder is safer than a guessed
   topic.
5. **Raw Material remains evidence.** LaTeX notes, editable presentations and
   published outputs belong to their own artifact layers.
6. **Moves are bounded by one lecture.** Never reorganise the whole repository
   in a single operation.
7. **Every move is reversible from a ledger.**
8. **No routine checksum is required.** Use lightweight direct comparison only
   when a specific duplicate decision needs it.
9. **Selecting or configuring a folder never constitutes scanning or
   ingestion.**
10. **The instructor makes the final academic decision.**

## The four artifact layers

| Layer | Contents | Normal treatment |
|---|---|---|
| Lecture Raw Material | Books, chapters, articles, reports, maps, images and datasets | Organise by presentation-derived topic |
| AI-assisted LaTeX Notes | `.tex` sources and their `.pdf` reading copies | Keep as self-contained note projects |
| Presentation Workbench | Editable `.odp`, `.ppt` and `.pptx` files | Keep in the Workbench and edit manually |
| Published Presentation PDFs | Approved classroom-facing PDF exports | Use as the teaching reference and governed output |

An item's provenance does not define its artifact class. For example,
`processed_by_ChatGPT` is not a topic, and a source report does not become an
AI note merely because an AI tool previously processed it.

## Authoritative evidence order

Use evidence in this order:

1. published presentation title, section sequence and slide headings;
2. document title, abstract, table of contents, captions and substantive text;
3. document metadata;
4. local OCR or first-page inspection for scanned material;
5. filename and inherited folder name.

Filename-only or folder-only classifications remain provisional. Where
evidence conflicts, retain the item in review and record the conflict.

## Standard folder model

Topics must be immediate children of the lecture container. This lets the
cockpit show meaningful topics instead of a generic `resources` row.

```text
LEC_RES_4/
├── A01_wheat_rice_regional/
├── A02_rice_wheat_system/
├── A03_pakistan_wheat/
├── B01_bangladesh_wheat/
├── B02_bangladesh_rice/
├── B03_cropping_calendar/
├── B04_pakistan_rice/
├── Z01_cross_topic_reference/
├── Z03_duplicate_or_version_review/
└── ORGANIZATION_MANIFEST.md
```

### Topic naming

Use:

```text
<part><two-digit sequence>_<short_topic_name>
```

Examples:

```text
A01_agricultural_structure
B03_food_policy
C02_ict_ites
```

Rules:

- `A`, `B` and `C` follow the presentation part;
- sequence topics in teaching order, not alphabetically;
- use lowercase `snake_case` after the code;
- retain the controlled topic code once it has been established;
- do not introduce a part or lecture absent from the published sequence;
- use an `AB_` or equivalent shared designation only when the teaching
  taxonomy explicitly requires it.

The controlled course taxonomy is maintained in
[`../config/lecture_topic_taxonomy.yaml`](../config/lecture_topic_taxonomy.yaml).
It is the naming authority; this manual is the procedural authority.

### Review and reference folders

Use the following stable vocabulary going forward:

| Folder | Purpose |
|---|---|
| `Z01_cross_topic_reference` | Broad material relevant to several topics in the same lecture |
| `Z02_cross_lecture_reference` | Material whose main value spans lectures |
| `Z03_duplicate_or_version_review` | Suspected duplicate, near-duplicate or superseded version |
| `Z04_derived_notes_review` | AI summaries, derived notes or analytical outputs needing layer review |
| `Z05_workbench_or_presentation_review` | Editable decks or old presentation outputs found in Raw Material |
| `Z06_archive_review` | Archives requiring inspection before extraction or retention |
| `Z07_empty_or_inaccessible_review` | Zero-byte, damaged, encrypted or unreadable items |
| `Z08_unassigned_review` | Evidence is insufficient or contradictory |

Existing lectures may contain older `Z` names created during the 2026
folderisation cases. Do not rename those folders casually. Apply this
vocabulary to new work and make any legacy rename a separate, ledgered pass.

Review folders are not rubbish bins. Each item still needs a reason and an
instructor decision.

## Classification roles and statuses

Assign an artifact role before choosing a destination:

| Artifact role | Destination rule |
|---|---|
| Primary reading, evidence, image or dataset | Matching A/B/C topic |
| Broad comparative source | Cross-topic or cross-lecture reference |
| Derived summary or AI note | Derived-notes review, then the Notes layer if approved |
| Editable presentation | Workbench/presentation review, then Workbench if approved |
| Old published lecture PDF | Presentation reference/review |
| Suspected copy or alternative version | Duplicate-or-version review |
| Archive | Archive review until inspected |
| Empty or inaccessible file | Empty-or-inaccessible review |
| Ambiguous source | Unassigned review |

Use these decision statuses in inventories and reports:

```text
ASSIGNED_CONFIRMED
ASSIGNED_PROVISIONAL
SHARED_RELEVANCE
REVIEW_UNASSIGNED
DUPLICATE_REVIEW
AI_NOTE_REVIEW
WORKBENCH_REVIEW
SUPPORTING_ASSET
ARCHIVE_REVIEW
```

### Confidence

| Confidence | Evidence | Physical move |
|---|---|---|
| Confirmed | Instructor decision or explicit use/citation in the presentation | Allowed |
| Strong | Title/content and presentation topic clearly agree | Allowed after bounded review |
| Provisional | Filename, metadata or inherited location suggests a match | Not yet |
| Unassigned | Evidence is insufficient or contradictory | Not allowed |

“No orphan” means every file receives an inventory or ledger decision. It does
not mean every file must be forced into an A/B/C topic.

## Standard procedure

### Phase 1 — Establish the lecture boundary

Work on one `LEC_RES_<number>` directory only.

1. Identify all published parts for that lecture.
2. Confirm the natural order: `1A`, `1B`, `2A`, `2B`, and so forth.
3. Do not invent a missing lecture or part. The current supplied presentation
   set contains no published Lecture 9.
4. Record the source root and the presentation locators symbolically in
   durable records; keep absolute paths in machine-local configuration only.

### Phase 2 — Recover the teaching taxonomy

Read the presentation in slide order and record:

- title and stated learning purpose;
- major section headings;
- recurring concepts, places, crops, sectors, institutions and case studies;
- data series and visuals used;
- sources explicitly named on slides;
- transitions between Parts A, B and C.

Create a short set of topic codes in teaching order. Prefer three to five
coherent topics per part over a folder for every minor slide heading.

Compare the proposed codes with
[`../config/lecture_topic_taxonomy.yaml`](../config/lecture_topic_taxonomy.yaml).
If the published deck has materially changed, update the taxonomy only after
instructor review; do not silently reshape it during a file move.

### Phase 3 — Census every physical file

The census must include formats that the cockpit does not normally register.
Record at least:

```text
current_symbolic_locator
physical_type
proposed_primary_topic
additional_relevant_topics
artifact_role
assignment_confidence
decision_status
proposed_destination
reason
```

Use the project inventory helper when appropriate:

```bash
.venv/bin/python scripts/build_resource_topic_inventory.py \
  '/path/to/machine-local/IS529N'
```

This is an explicit operation. Do not add background crawling or scan merely
because a root was selected.

### Phase 4 — Inspect content

Review files in small groups:

- read document titles, abstracts and contents pages;
- inspect spreadsheet headings and variables;
- inspect image subject and caption where known;
- treat supporting images/assets as belonging with the project or source they
  support;
- distinguish original evidence from a summary of that evidence;
- identify editable presentations and LaTeX projects before topical moves.

For a LaTeX project, retain the whole self-contained project when moving it to
the Notes repository. Auxiliary and image dependencies may travel with it,
although the Notes scanner should list only `.tex` and `.pdf`.

Do not classify CSV, ODS, XLSX, SVG or images by file format. Place them with
the topic they measure or illustrate.

### Phase 5 — Prepare the move ledger

Before changing the repository, create:

```text
reports/LEC_RES_<N>_LOCAL_FOLDERISATION_<YYYY-MM-DD>.tsv
```

Required columns:

```text
source_relative_path	destination_relative_path	decision
```

Every source file to be moved gets exactly one row. The decision must state
the academic reason, not merely “cleanup”.

Preflight the ledger:

1. count manifest rows;
2. confirm every source exists;
3. confirm every destination is unique;
4. confirm no destination already exists;
5. confirm paths stay inside the bounded lecture root;
6. confirm review items are not being silently deleted;
7. re-census immediately before execution to detect concurrent user changes.

If a source disappeared or a destination appeared, stop that row and inspect.
Never restore, overwrite or counteract a file the instructor moved manually.

### Phase 6 — Execute the bounded move

1. Create only the listed destination topic/review directories.
2. Move files exactly as recorded in the ledger.
3. Rename a cryptic filename only when the document title is clear and the
   rename is included in the same ledger row.
4. Preserve useful published titles when normalising them would reduce
   recognisability or citation value.
5. Remove only inherited directories proven empty after the move.
6. Do not delete duplicates, archives, empty files or rejected items.
7. Do not modify file contents.

For high-risk or ambiguous lectures, execute one topic group at a time.

### Phase 7 — Verify and rescan

Verify:

- every ledger destination exists;
- every ledger source is absent;
- the before and after physical-file counts agree;
- no unexpected loose file remains;
- no file content was rewritten;
- topic folders remain immediate children of the lecture root;
- external/manual changes are listed separately from the executed ledger.

Then explicitly rescan the relevant cockpit class. Confirm that topic rows and
candidate counts are plausible. A rescan updates visibility; it does not
register candidates.

Run project checks:

```bash
.venv/bin/python scripts/generate_public_file_manifests.py
.venv/bin/python scripts/generate_public_file_manifests.py --check
.venv/bin/python -m unittest \
  tests.test_public_file_manifests \
  tests.test_path_configuration
git diff --check
```

Record exact results in the work report.

### Phase 8 — Instructor review and close-out

Report:

1. lecture and presentation parts used;
2. before/after physical-file counts;
3. topic and review folders created;
4. moved and renamed files;
5. provisional or unresolved decisions;
6. duplicates, derived notes, decks, archives and empty files retained;
7. concurrent manual changes observed;
8. scan and test results;
9. ledger location; and
10. the next bounded lecture recommendation.

Do not commit, push, register candidates or delete review material unless
separately authorised.

## Filename guidance

Prefer a descriptive filename when an inherited name is meaningless, such as
a numeric download identifier. Use lowercase words joined by underscores and
retain the original extension:

```text
615907199.pdf
→ agricultural_trade_facilitation.pdf
```

Do not rename when:

- the title has not been verified;
- the existing name is a recognisable publication title;
- a citation, TeX source or local project depends on it;
- the file is under duplicate/version review;
- the rename would combine two decisions that should be reviewed separately.

Folder naming and file renaming are related but distinct decisions. A source
can be safely placed in a topic without cosmetically renaming it.

## Duplicate and version handling

Routine hashing is unnecessary for this manually governed workflow.

When a specific suspected duplicate affects a decision:

1. compare names, sizes and visible titles;
2. use `cmp` for an exact byte comparison if needed;
3. for PDFs with different wrappers, compare locally extracted text only when
   the decision warrants it;
4. retain both copies in duplicate/version review until the instructor chooses
   the authoritative one;
5. record the relationship and decision.

Do not use SHA-256 as a routine scan field. Do not substitute routine MD5
either; avoiding unnecessary computation is better than using a lighter hash.

## Lessons from the completed cases

| Case | Reusable lesson |
|---|---|
| Lecture 2 | A small loose-file set is the best pilot; broad development reports may span topics |
| Lecture 3 | A generic `resources` folder can hide readings, datasets, media and an editable deck; classify by role before topic |
| Lecture 4 | AI-processing provenance is not a topic; reports stay evidence while the deck receives Workbench review |
| Lecture 5 | Crop datasets belong with cotton or sugarcane topics; old presentation PDFs and summaries require separate review |
| Lecture 7 | Three presentation parts require A/B/C order; derived notes, archives and versions must not be mixed with evidence |
| Lecture 8 | Overlapping names such as `ict` and `ictsector` should be replaced by presentation-derived topics; empty and presentation files remain explicit review work |

Across all cases, the effective pattern was:

```text
presentation sequence
→ controlled topic list
→ complete physical census
→ content-based assignment
→ explicit review lanes
→ TSV move ledger
→ preflight
→ bounded move
→ count and path verification
→ explicit cockpit rescan
```

## Reusable acceptance checklist

Before declaring a lecture dressed, confirm:

- [ ] Every published lecture part was reviewed in natural order.
- [ ] Topic folders match the controlled presentation taxonomy.
- [ ] Topics are immediate children of `LEC_RES_<N>`.
- [ ] Every physical file is represented in the census or move ledger.
- [ ] No classification relies only on a filename.
- [ ] Each file has one primary home.
- [ ] Shared relevance is recorded without duplicate copies.
- [ ] Derived notes, Workbench files and published outputs are separated from raw evidence.
- [ ] Ambiguous, duplicate, archive, empty and inaccessible files remain visible for review.
- [ ] The ledger passed source, destination and traversal preflight.
- [ ] Before and after file totals reconcile.
- [ ] No source content was edited.
- [ ] No review file was deleted without instructor authority.
- [ ] The cockpit rescan was explicit.
- [ ] Tests and manifest checks pass.
- [ ] Absolute machine paths are absent from committed documentation and configuration.

## Related records

- [Presentation-derived taxonomy report](../reports/PRESENTATION_DERIVED_RESOURCE_TAXONOMY_2026-07-27.md)
- [Controlled lecture topic taxonomy](../config/lecture_topic_taxonomy.yaml)
- [Lecture-part pipeline concept note](LECTURE_PART_PIPELINE_CONCEPT_NOTE.md)
- [Raw Material organisation audit](../reports/LECTURE_RAW_MATERIAL_ORGANISATION_AUDIT_2026-07-27.md)
- [Raw-to-LaTeX reshuffle plan](../reports/SAFE_RAW_TO_LATEX_RESHUFFLE_PLAN_2026-07-27.md)
- [Complete topic inventory](../reports/raw_resource_topic_inventory_2026-07-27.csv)
- [Lecture 2 folderisation ledger](../reports/LEC_RES_2_LOCAL_FOLDERISATION_2026-07-27.tsv)
- [Lecture 3 folderisation ledger](../reports/LEC_RES_3_LOCAL_FOLDERISATION_2026-07-27.tsv)
- [Lecture 4 folderisation ledger](../reports/LEC_RES_4_LOCAL_FOLDERISATION_2026-07-27.tsv)
- [Lecture 5 folderisation ledger](../reports/LEC_RES_5_LOCAL_FOLDERISATION_2026-07-27.tsv)
- [Lecture 7 folderisation ledger](../reports/LEC_RES_7_LOCAL_FOLDERISATION_2026-07-27.tsv)
- [Lecture 8 folderisation ledger](../reports/LEC_RES_8_LOCAL_FOLDERISATION_2026-07-27.tsv)
- [Lecture 10 folderisation report](../reports/LEC_RES_10_LOCAL_FOLDERISATION_REPORT_2026-07-27.md)
- [Lecture 10 folderisation ledger](../reports/LEC_RES_10_LOCAL_FOLDERISATION_2026-07-27.tsv)
- [Lecture 11 folderisation report](../reports/LEC_RES_11_LOCAL_FOLDERISATION_REPORT_2026-07-27.md)
- [Lecture 11 folderisation ledger](../reports/LEC_RES_11_LOCAL_FOLDERISATION_2026-07-27.tsv)
- [Lecture 12 folderisation report](../reports/LEC_RES_12_LOCAL_FOLDERISATION_REPORT_2026-07-27.md)
- [Lecture 12 folderisation ledger](../reports/LEC_RES_12_LOCAL_FOLDERISATION_2026-07-27.tsv)
