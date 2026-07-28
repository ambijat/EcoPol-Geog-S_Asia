# Topical–Spatial Cockpit UX Design

## Status and purpose

This note re-examines the current IS529N desktop cockpit after two completed
resource-organisation exercises:

1. **presentation-led reverse engineering**, which organised Lecture Raw
   Material as `Lecture → Part → Topic`; and
2. **spatial engineering**, which organised the South Asia collection as
   `Country/region/cross-border scope → Lecture`.

The proposed UX principle is:

> **One course, one lecture workflow, two evidence lenses.**

The instructor should not experience the two repositories as unrelated file
managers. The cockpit should let the instructor begin with a lecture, a topic
or a place, pivot between them, and carry selected evidence into the
Presentation Workbench without changing source files.

This is a design and implementation boundary. It does not itself change the
application, path configuration, database or source repositories.

## What the re-examination found

### What already works

The current application has several sound foundations:

- the course title is the dominant identity;
- artifact roots are machine-local and symbolic locators are exportable;
- choosing a root does not scan it;
- scanning is explicit, read-only and creates candidates only;
- the existing Lecture Raw Material scan is summarised by immediate topic
  folder instead of flattening every contained file;
- Workbench files can be compared with published PDFs by lecture filename;
- the LaTeX revision view operates by lecture and lists only `.tex` and `.pdf`;
- columns are resizable, tables scroll, and actions are selection-gated;
- source repositories remain separate from the application source tree; and
- routine scanning does not hash files.

These behaviours should be preserved.

### Where the present UX is still database-led

The home screen and navigation are primarily organised around artifact
classes, counts, candidate records and relationship queues. That is useful for
governance, but it is not the instructor's main mental model.

The instructor's normal question is closer to:

```text
What do I need for Lecture 12A, what evidence do I have,
which countries or cross-border cases strengthen it,
which notes are ready, and which Workbench file should I update?
```

The current cockpit requires that question to be reconstructed across:

- Lecture Raw Material;
- AI-assisted LaTeX Notes;
- Presentation Workbench;
- Published PDFs;
- Scan Candidates; and
- Artifact Relationships.

The two reorganisation exercises now supply the missing organising structure.

## The combined information model

### Stable spine: lecture and lecture part

The stable user-facing identity should be the lecture part:

```text
IS529N-L01A
IS529N-L01B
IS529N-L02A
IS529N-L02B
…
```

The lecture part joins the production chain:

```text
Topical evidence ───────┐
Spatial evidence ───────┼──→ LaTeX analysis ──→ Workbench ──→ Published PDF
Instructor judgement ───┘
```

A lecture-level source may support Part A, Part B, both, or remain awaiting
assignment. Filename inference may propose a link but must not silently make
that academic decision.

### Evidence lens 1: topical-systemic

```text
Lecture → Part → Topic → Source
```

This lens answers:

- What concept, process, crop, sector or political issue does the source
  support?
- Where does it occur in the published teaching sequence?
- Is the evidence assigned, shared or awaiting review?

The authority is
[`../config/lecture_topic_taxonomy.yaml`](../config/lecture_topic_taxonomy.yaml).

### Evidence lens 2: spatial

```text
Country / regional / cross-border scope → Lecture → Source
```

This lens answers:

- Where in South Asia does the source concern?
- Is it national, regional or genuinely cross-border?
- Which lecture uses that spatial case?

Countries, `REGIONAL_SOUTH_ASIA` and `CROSS_BORDER` must be visually distinct.
A bilateral source must not be shown as if it belonged exclusively to one
country.

### Evidence lens 3: matrix

The matrix is a derived navigation aid:

```text
                    India  Pakistan  Nepal  Bangladesh  Regional  Cross-border
Lecture 2              4       8       6        5          28          —
Lecture 7              —       —      41        —           6          —
Lecture 12             —       —      12        —           3         50
```

Cells show counts, not quality. Selecting a cell opens the underlying
filtered evidence. A tooltip or detail pane should show:

- topic and lecture-part coverage;
- formats;
- assigned and review counts; and
- whether any topical/spatial counterpart has been identified.

The matrix must never imply that an empty cell is a syllabus defect. It means
only that no source is currently visible under that intersection.

## Proposed navigation hierarchy

Keep the navigation concise:

```text
Cockpit Home
Lecture Pipeline
Published PDFs
Presentation Workbench
Lecture Evidence
AI-Assisted Notes
Knowledge Maps
Artifact Relationships
Review Queue
Repository Paths
Settings
```

Changes from the current hierarchy:

- **Lecture Raw Material** becomes **Lecture Evidence** and provides the two
  lenses within one workspace.
- **Scan Candidates** becomes **Review Queue**, because scanning is a means,
  not the instructor's goal.
- **Lecture Pipeline** becomes the principal teaching workflow.
- artifact-class codes remain internal and do not appear as prominent labels.

The underlying artifact classes may remain visible in advanced metadata and
path settings.

## Cockpit Home

The home screen should lead with teaching progress rather than database
totals.

### Primary section: lecture cards

Each card represents one natural teaching unit:

```text
Lecture 12A · Hydropolitics and the Indus Water Treaty

Topical evidence       4 topics · 65 sources
Spatial evidence       Pakistan · Regional · India–Pakistan
LaTeX notes            2 TeX · 2 reading PDFs
Workbench              LECTURE12a.odp
Published              LECTURE12a.pdf
Instructor review      3 unresolved items

[Open Pipeline]
```

Cards should be ordered naturally—1A, 1B, 2A, 2B, 3A—not lexically as 1, 10,
11, 12, 2.

### Secondary section: course attention

Show only actionable summaries:

- lecture parts missing a Workbench file;
- Workbench files without a published counterpart;
- unassigned evidence;
- spatial items in review;
- proposed relationships awaiting confirmation; and
- revisions awaiting an instructor decision.

Raw database counts remain available under an **Artifact Overview** disclosure
or settings/diagnostics screen.

## Lecture Pipeline workspace

The pipeline should be the instructor's main working screen.

```text
Lecture [12]   Part [A]     Hydropolitics and the Indus Water Treaty

Evidence
  Topics:  A01 Hydropolitics · A02 Basin Governance
           A03 Treaty History · A04 Treaty Politics
  Places:  Pakistan · Regional South Asia · India–Pakistan

Analysis
  LaTeX:   2 source notes · 2 PDF reading copies

Production
  Workbench: LECTURE12a.odp       [Open Workbench]

Publication
  PDF:       LECTURE12a.pdf       [Compare]

Instructor state
  Inputs under review             [Review Evidence]
```

Recommended actions:

- Open Topical Evidence
- Open Spatial Evidence
- Review Selected Sources
- Open LaTeX Notes
- Open Workbench
- Compare Published PDF
- Assign to Part A / Part B / Both
- Propose Relationship
- Mark Applied in Workbench
- Approve for Publication

The screen records and navigates decisions. It must not silently edit a
presentation or mark it published.

## Lecture Evidence workspace

### Lens selector

Use a visible segmented selector:

```text
[ Topics ] [ Places ] [ Matrix ]
```

The selected lecture and filters survive when the instructor switches lenses.
For example, switching from Lecture 12 in Topics to Places should reveal the
spatial evidence for Lecture 12, not reset to the complete repository.

### Shared filter bar

```text
Lecture | Part | Topic | Place | Format | Review state | Search
```

Only relevant controls need to be enabled for each lens. Filters operate on
the latest explicit census or registered metadata; changing a filter must not
rescan a disk.

### Topics lens

Use the existing topic-folder aggregation and add the presentation-derived
label:

| Topic | Part | Lecture | Sources | Formats | Review |
|---|---|---:|---:|---|---|
| A03 Indus Treaty History | A | 12 | 18 | PDF, DOCX | 2 unresolved |

Selecting a topic reveals:

- its controlled taxonomy label;
- source count and formats;
- spatial coverage already known;
- related notes, Workbench and published presentation;
- unresolved review items; and
- **Open Topic Folder**.

Folder opening remains explicit and read-only.

### Places lens

Start with cards or a tree:

```text
Countries
  Afghanistan
  Bangladesh
  Bhutan
  India
  Maldives
  Nepal
  Pakistan
  Sri Lanka

Regional
  South Asia

Cross-border
  Afghanistan–Pakistan
  China–India
  India–Nepal
  India–Pakistan
```

Selecting a place displays only lecture folders that physically exist.
Do not create or display invented empty lecture folders. Natural lecture
ordering is mandatory.

The row-level display should be:

| Lecture | Spatial scope | Preserved collection | Sources | Review |
|---:|---|---|---:|---|
| 12 | India–Pakistan | industreaty | 50 | 1 version review |

### Matrix lens

Rows are lectures or lecture parts; columns are spatial scopes. The first
release should use a table with keyboard-accessible cells rather than a custom
graphic. This keeps the view responsive, inexpensive and screen-reader
tractable.

Provide:

- frozen lecture labels;
- horizontal and vertical scrolling;
- a text alternative such as “Lecture 12, India–Pakistan, 50 sources”;
- natural lecture sorting;
- column selection/filtering; and
- a detail pane opened from Enter, Space or double-click.

## Review Queue

The present Scan Candidates screen mixes discovery mechanics with academic
decisions. Retain explicit scan behaviour but organise the result around why
the instructor needs to act.

Recommended tabs:

```text
Newly Discovered
Needs Assignment
Duplicate or Version Review
Workflow / Archive / Empty
Relationship Proposals
Deferred
```

Within **Newly Discovered**, keep a root/lens selector and display:

- topical scans as topic folders;
- spatial scans as scope + lecture groups;
- Workbench scans in natural lecture order with PDF matches;
- LaTeX scans as one row per lecture; and
- published PDFs as publication candidates.

For topic and spatial group rows, use actions such as:

- Open Folder
- Inspect Sources
- Assign to Lecture Part
- Propose Relationship
- Defer

Do not make **Register** the dominant action for grouped source evidence.
Registration remains available for a specific governed artifact when needed.

## Path and symbolic-locator model

### Recommended internal class

Add an optional sixth internal artifact class:

```text
code: SPATIAL_RESOURCE
label: Spatial Raw Material
symbolic scheme: SPATIAL_RESOURCE://
default access: read_only
required on first launch: no
```

Example:

```text
SPATIAL_RESOURCE://CROSS_BORDER/INDIA_PAKISTAN/LEC_12/industreaty/source.pdf
```

This is preferable to adding a second physical root to
`FOUNDATIONAL_RESOURCE`, because:

- each symbolic scheme continues to identify one provenance authority;
- path validation remains simple;
- root changes do not make records ambiguous;
- the topical root is not overwritten;
- scans can apply the correct aggregation rule; and
- the existing optional Knowledge Maps class remains intact.

The application may present Topical and Spatial sources together in
**Lecture Evidence** even though their roots remain separate internally.

### Path-setting behaviour

Repository Paths should show:

```text
Lecture Raw Material — Topical
Spatial Raw Material — Countries and Regions
```

The spatial root is optional and read-only by default. If it is offline, the
cockpit continues to operate and shows:

```text
Spatial evidence unavailable — external volume offline
```

No scan is triggered when the root is selected, enabled, validated or opened.

## Relationship vocabulary

Preserve the existing relationships and add, after schema/config review:

```text
SUPPORTS_LECTURE
SUPPORTS_LECTURE_PART
SUPPORTS_TOPIC
SUPPORTS_COUNTRY_CASE
SAME_SOURCE_AS
SPATIAL_COPY_OF
```

These relationships serve different purposes:

- `SUPPORTS_TOPIC` connects evidence to the topical taxonomy;
- `SUPPORTS_COUNTRY_CASE` adds spatial relevance without copying a file;
- `SUPPORTS_LECTURE_PART` records the instructor-approved teaching use;
- `SAME_SOURCE_AS` records equivalent representations without choosing an
  authority; and
- `SPATIAL_COPY_OF` records a historically duplicated spatial copy after
  instructor confirmation.

Do not infer equivalence from filename and size alone. A targeted direct byte
comparison may support one manual decision; routine checksums remain
unnecessary.

## Four principal user journeys

### 1. Start from a lecture

1. Open Cockpit Home.
2. Choose Lecture 12A.
3. Review its four presentation-derived topics.
4. Switch to Places to see Pakistan, Regional South Asia and India–Pakistan
   evidence.
5. Select evidence for the current teaching purpose.
6. inspect related LaTeX notes.
7. Open the linked Workbench presentation.
8. record which reviewed inputs are proposed for integration.
9. manually apply accepted changes in the presentation editor.
10. compare and approve the eventual published PDF.

### 2. Start from a country

1. Open Lecture Evidence → Places.
2. Choose Nepal.
3. See only lectures with Nepal evidence.
4. choose Lecture 12.
5. pivot to Topics and locate the related water-treaty topic.
6. open the Lecture 12B pipeline.

### 3. Review newly arranged material

1. Open Review Queue.
2. explicitly scan the selected topical or spatial root.
3. inspect grouped folders rather than hundreds of flattened files.
4. assign, relate, defer or retain in review.
5. do not move, register or delete a source merely because it was found.

### 4. Prepare a Workbench update

1. select a lecture part;
2. assemble a bounded topical and spatial evidence set;
3. review its LaTeX analysis;
4. compare it with the current Workbench and published PDF;
5. create inspectable slide-level proposals;
6. accept, edit, defer or reject each proposal;
7. open the Workbench and apply accepted changes manually; and
8. record completion separately from publication approval.

## Responsiveness, accessibility and performance

### Responsive behaviour

- At 1500 px, show the evidence list and contextual detail side by side.
- At 1200 px, keep the filter bar wrapped to two rows if needed.
- At 1100 × 700, stack the detail pane below the table or open it as a dialog.
- All table columns remain manually resizable and horizontally reachable.
- Maintenance actions may move into a **More Actions** menu.
- Never truncate navigation labels with accidental ellipses.

### Keyboard and accessibility

- give the lens selector, filter bar, evidence table and detail actions a
  deliberate tab order;
- expose complete text in tooltips and accessible descriptions;
- activate table rows using Enter as well as double-click;
- encode status using text, not colour alone;
- provide a textual alternative for every matrix cell; and
- return focus to the originating row after closing a detail view.

### Resource use

- never crawl either repository in the background;
- scan only after an explicit instructor action;
- cache the small latest-census metadata needed for filtering;
- aggregate topic and spatial folders without repeatedly opening binaries;
- inspect document content only for a selected bounded task;
- do not calculate routine checksums;
- do not load all 663 spatial files into rich previews at once; and
- show counts from the latest census with its date and root status.

## Bounded implementation sequence

### Phase 0 — interaction prototype

Create a read-only fixture prototype for Lecture 12A/12B using existing
inventory and taxonomy records. Validate:

- Topics, Places and Matrix language;
- natural lecture ordering;
- the lecture card and pipeline layout; and
- whether the instructor can reach the Workbench in fewer steps.

No database migration is needed for this prototype.

### Phase 1 — optional spatial root

Add `SPATIAL_RESOURCE` to class configuration, local-path defaults, path
settings and tests.

Requirements:

- optional on first launch;
- read-only default;
- independent `SPATIAL_RESOURCE://` resolution;
- traversal and symlink-escape protection;
- no automatic scan; and
- external-volume failure must not block the four required roots.

If artifact-class rows are seeded from configuration at start-up, prefer that
existing configuration path over an avoidable migration. Add a migration only
if persistent schema changes are actually required. Do not alter migrations
001 or 002.

### Phase 2 — spatial grouping and review

Add an explicit spatial scan summariser:

```text
scope → lecture → preserved collection → source counts
```

It should hide workflow/system files from the normal academic view while
retaining their review counts. It must not flatten all 663 files into the
primary table.

### Phase 3 — unified Lecture Evidence workspace

Build Topics and Places lenses over latest-census metadata. Preserve current
folder-opening and path-validation behaviour. Add the Matrix only after the
two list lenses are usable at 1100 × 700.

### Phase 4 — Lecture Pipeline

Join:

- controlled lecture-part taxonomy;
- topical evidence;
- spatial evidence;
- LaTeX notes;
- Workbench filename proposals; and
- published PDF filename proposals.

All inferred links remain visibly provisional until instructor confirmation.

### Phase 5 — relationship and knowledge-map integration

Use confirmed lecture/topic/place relationships to produce Knowledge Maps.
The map is a derived overview, not the authoritative place where source
assignments are made.

## Recommended first vertical slice

Pilot Lecture 12, including Parts A and B.

It is the strongest test because it contains:

- a clear topical distinction between the Indus and India–Nepal;
- national, regional and cross-border evidence;
- existing Workbench and published presentation identities;
- known possible overlap between topical and spatial collections; and
- an academic need to distinguish shared basin evidence from bilateral cases.

The pilot should answer one practical question:

> Can the instructor move from Lecture 12A or 12B to the right topical and
> spatial evidence, then open the correct Workbench presentation, without
> navigating through database-management concepts?

## Acceptance criteria

The first implementation is acceptable only when:

1. the cockpit presents one Lecture Evidence workspace with Topics and Places
   lenses;
2. the topical and spatial roots remain separate physical and symbolic
   authorities;
3. the optional spatial root cannot block first launch or normal operation;
4. no root selection, lens change or filter action starts a scan;
5. topical scans show presentation-derived topic folders;
6. spatial scans show scope and lecture groups rather than one flattened file
   list;
7. lectures sort naturally;
8. regional and cross-border sources are not falsely assigned to one country;
9. switching lenses preserves the selected lecture and applicable filters;
10. Lecture 12A and 12B are independently visible;
11. inferred part, PDF and counterpart links remain provisional;
12. the Workbench is visibly the editable presentation target;
13. source repositories remain unchanged;
14. routine scans perform no hashing;
15. offline removable storage does not crash or disable the required cockpit;
16. controls remain reachable at 1100 × 700;
17. keyboard navigation and complete accessible labels are provided; and
18. existing path-security, explicit-scan and instructor-approval behaviour
    remains covered by tests.

## Preservation boundary

Do not change during this UX work:

- the topical or spatial source files;
- presentation registration rules;
- the Workbench-to-PDF instructor confirmation rule;
- PathResolver traversal protection;
- machine-local absolute-path storage;
- migrations 001 and 002;
- the browser sidecar;
- the legacy Qt application;
- ledger history; or
- the rule that registration, relationship confirmation and publication are
  explicit instructor decisions.

## Related references

- [Lecture-Part Knowledge-to-Publication Pipeline](LECTURE_PART_PIPELINE_CONCEPT_NOTE.md)
- [Presentation-Led Raw Material Dressing Manual](PRESENTATION_LED_RAW_MATERIAL_DRESSING_MANUAL.md)
- [Spatial Raw Material Arrangement Concept Note](SPATIAL_RAW_MATERIAL_CONCEPT_NOTE.md)
- [Spatial Raw Material Arrangement Manual](SPATIAL_RAW_MATERIAL_ARRANGEMENT_MANUAL.md)
