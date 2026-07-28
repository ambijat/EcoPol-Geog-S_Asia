# IS529N Course Artifact Cockpit — Instructor Walkthrough

## What the cockpit does

The cockpit connects five kinds of course material without changing source
files automatically:

1. Published Presentation PDFs — the classroom-facing output.
2. Presentation Workbench — editable ODP/PPT/PPTX presentations.
3. Lecture Raw Material — topic folders containing sources and working
   material.
4. AI-assisted LaTeX Notes — structured notes used during presentation revision
   revision. Only `.tex` sources and `.pdf` reading copies are listed.
5. Knowledge Maps — portable mind maps, canvases and graph exports.

Its core cycle is:

```text
configure folders
→ scan explicitly
→ review candidates
→ register selected material
→ relate evidence and versions
→ revise the Workbench presentation
→ confirm instructor decisions
→ produce or update published and visual outputs
```

Selecting a folder never scans it. Scanning never registers a file.
Registration never edits the selected source.

The proposed next-stage architecture connecting each Lecture Part A/B across
raw material, LaTeX notes, Workbench production and published output is
described in
[`LECTURE_PART_PIPELINE_CONCEPT_NOTE.md`](LECTURE_PART_PIPELINE_CONCEPT_NOTE.md).

## A recommended first cycle

### 1. Configure repository paths

On first launch, use **Browse…** for the four required roots:

- Published Presentation PDFs — `read_only`
- Presentation Workbench — `read_write`
- Lecture Raw Material — `read_only`
- AI-assisted LaTeX Notes — `read_write`

Knowledge Maps is optional. When its separate folder is ready, configure it as
`read_write`. Do not select an entire Obsidian vault or a live Neo4j database
directory.

Close or finish the wizard after all four required rows validate. The bottom
status bar should say that the artifact roots are available. No folder has been
scanned yet.

### 2. Establish the published PDF census

Open **Published PDFs**, then press **Refresh Current Census**.

The application moves to **Scan Candidates** and lists only PDFs from the
latest explicit scan. Select a row and use:

- **Register** to admit that PDF into the artifact catalogue.
- **Ignore** to close the candidate without registering it.
- **Defer** to leave the decision for later.
- **Mark as Duplicate** to record a duplicate decision.
- **Relate to Existing Artifact** to associate the candidate with an already
  registered record without registering it.

Register one representative PDF before continuing.

### 3. Establish the editable presentation census

Open **Presentation Workbench**, then press **Refresh Current Census**.

ODP, PPTX and PPT files are listed in lecture order:
`lecture1a`, `lecture1b`, `lecture2a`, `lecture2b`, and so on.

The **Published PDF match** column shows the filename match proposed for each
editable presentation. It is only a proposal; confirm the relationship later.
Register the Workbench presentation you intend to revise.

### 4. Review Lecture Raw Material by topic

Open **Lecture Raw Material**, then press **Refresh Current Census**.

This view deliberately summarizes folders as topics instead of flooding the
screen with every contained file. **Open Topic Folder** opens the selected
folder read-only. To register one particular source, return to the class
workspace and use **Register File**.

### 5. Run the AI presentation-revision cycle

Open **AI-assisted LaTeX Notes**, then press **Refresh LaTeX Notes** or
**Refresh LaTeX Notes**. LaTeX build auxiliaries such as `.aux`, `.log`,
`.out`, `.toc`, and `.synctex.gz` are ignored.

The result is a fixed 15-lecture revision queue:

- **Open LaTeX Notes** opens that lecture's LaTeX-note folder.
- **Link Workbench** chooses the editable presentation for the lecture.
- **Begin Revision** records “Revision in progress” and opens the linked ODP.
- **Mark Integrated** records that the notes were integrated.
- **Defer** postpones the revision.
- **Reject** records that the note set will not be used.

The application does not edit the ODP itself. LibreOffice or the associated
desktop application performs the actual presentation editing.

### 6. Confirm the publication relationship

Open **Artifact Relationships** and press **Create Relationship**.

Choose the Workbench presentation as source, `PUBLISHED_AS` as the
relationship, and its PDF as target. Save it as a suggestion or confirmed
record. If saved as a suggestion, select it and press
**Confirm Relationship** after reviewing the evidence.

Only instructor-confirmed relationships are academically authoritative.

### 7. Create a Knowledge Map

Configure the separate Knowledge Maps root, open **Knowledge Maps**, and use:

- **Create Mind Map** to create and register a minimal portable `.mm` file.
- **Import Visualization** to register an existing supported visualization.
- **Scan Visualizations** to discover portable map and graph files.
- **Link Supporting Artifacts** to connect a map to its evidence.
- **Mark Reviewed** after checking the visualization.
- **Export Neo4j Bundle** to create timestamped nodes and relationships CSVs.

The export does not connect to or modify a live Neo4j database.

### 8. Resolve instructor decisions

Open **Instructor Decisions**. Select a pending row, enter an optional
resolution note, and choose:

- **Accept**
- **Reject**
- **Defer**
- **Needs More Evidence**
- **Edit and Accept**

This is the final authority checkpoint for inferred or proposed information.

## Global toolbar

| Button | Current behaviour |
|---|---|
| Cockpit Home | Returns to the five-class overview. |
| Refresh All | Reloads database-backed counts, tables, statuses and paths. It does not scan folders. |
| Find Duplicates | Explains the manual duplicate workflow. Use **Scan Candidates**, select a row, then choose **Mark as Duplicate**. |
| Relationship Map | Informational placeholder. The visual relationship map is not implemented yet. |
| Processing Queue | Informational placeholder. No AI API execution or processing engine is present. |
| Instructor Decisions | Opens the decision queue. |
| Settings | Opens artifact-class configuration. |

## Sidebar destinations

| Destination | Purpose |
|---|---|
| Cockpit Home | Overall counts and entry cards. |
| Published PDFs | Registered classroom PDFs. |
| Presentation Workbench | Registered editable presentations. |
| Lecture Raw Material | Registered topic-organized sources. |
| AI-assisted LaTeX Notes | AI-assisted `.tex` notes and `.pdf` reading copies; its scan view becomes the 15-lecture revision queue. |
| Knowledge Maps | Portable visualizations and graph exports. |
| Artifact Relationships | Create and review links between registered artifacts. |
| Scan Candidates | Latest explicit scan results for the selected class. |
| Instructor Decisions | Instructor authority queue. |
| Repository Paths | Configure, validate and manage local roots. |
| Settings | Edit class labels, descriptions, formats and relationship suggestions. |

## Repository Paths buttons

| Button | Current behaviour |
|---|---|
| Browse | Selects a folder; does not scan it. |
| Validate | Rechecks existence, access mode, conflicts and availability. |
| Open Folder | Opens the selected configured root in the file manager. |
| Rescan | Explicitly scans the selected root and opens Scan Candidates. |
| Clear | Removes only the machine-local root setting; artifact records remain unchanged. |
| Enable or Disable | Turns resolution and scanning for that root on or off. |
| Change Access Mode | Selects `read_only`, `read_write` or `configurable`. |
| Accept Conflict | Explicitly accepts a source-tree or shared-root conflict after confirmation. |

## Artifact-class workspace buttons

For the first four classes:

| Button | Current behaviour |
|---|---|
| Add Artifact | Opens the same registration dialog as Register File. |
| Register File | Registers one selected local file with a symbolic locator. |
| Refresh Current Census | Performs a read-only scan; an unchanged census is reused rather than duplicated. |
| Refresh Census | Reloads registered records; it does not scan the disk. |
| Create Relationship | Opens relationship creation, using the selected record when available. |
| Configure Path | Opens Repository Paths with the current class selected. |

For Knowledge Maps, the corresponding buttons are **Create Mind Map**,
**Import Visualization**, **Scan Visualizations**, **Refresh Census**, and
**Link Supporting Artifacts**.

## Selected-record actions

These actions currently work:

- **Open** / **Open Visualization** — opens the resolved local file.
- **Relate** / **Link Supporting Artifacts** — opens relationship creation.
- **Show Relationships** — currently opens relationship creation for the
  selected record.
- **Mark Reviewed** — updates inspection and instructor-review status.
- **Archive** — hides the artifact from normal views without deleting its file.
- **Preview Graph** — currently opens the visualization in its associated
  desktop application.
- **Export Neo4j Bundle** — creates portable graph CSV exports.

These visible controls are placeholders and currently perform no action:

- Preview
- Inspect
- Edit Metadata
- Show Provenance
- Send to AI Queue
- Locate Missing File

The provenance panel itself displays the selected record's locator, source
repository, review state and provenance.

## Artifact Relationships buttons

These work:

- **Create Relationship**
- **Confirm Relationship**
- **Reject Suggested Relationship**

These are visible placeholders and currently perform no action:

- Reverse Direction
- Change Relationship Type
- Add Evidence
- Add Instructor Note
- Remove Relationship
- Open Source Artifact
- Open Target Artifact

## Simulation result

On 2026-07-27 a temporary, synthetic end-to-end cycle completed successfully:

- all five roots validated;
- five candidates were discovered;
- four selected candidates plus one newly created mind map produced five
  registered artifacts;
- `lecture1a.odp` matched `lecture1a.pdf`;
- two relationships were instructor-confirmed;
- the AI queue contained 15 lecture rows;
- Lecture 1 moved to `Integrated into presentation`;
- a mind map received a symbolic locator;
- a timestamped Neo4j nodes/relationships bundle was created;
- no real repository or course source was accessed.

This simulation proves the core controlled cycle works. It also identifies the
placeholder controls above as the main UX debt for the next bounded pass.
