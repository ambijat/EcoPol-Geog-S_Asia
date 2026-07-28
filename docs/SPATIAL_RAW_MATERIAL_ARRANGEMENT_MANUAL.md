# Spatial Raw Material Arrangement Manual

## Purpose

This is the standard operating reference for maintaining the horizontal,
country/spatial Raw Material repository for IS529N.

Use it alongside—not instead of—the
[presentation-led topical manual](PRESENTATION_LED_RAW_MATERIAL_DRESSING_MANUAL.md).

```text
Topical-systemic repository: Lecture → Part → Topic
Spatial repository: Country/region → Lecture
```

The topical repository answers “what concept or teaching topic does this
support?” The spatial repository answers “where in South Asia does this
evidence concern?”

## Standard physical structure

For a country source:

```text
<country>/
└── LEC_<number>/
    └── <preserved source or legacy subfolder>
```

For genuinely regional material:

```text
REGIONAL_SOUTH_ASIA/
└── LEC_<number>/
```

For bilateral or cross-border material:

```text
CROSS_BORDER/
└── <COUNTRY_PAIR>/
    └── LEC_<number>/
```

Examples:

```text
Bhutan/LEC_7/forestchaps/...
PAKISTAN/LEC_4/pakagri/...
REGIONAL_SOUTH_ASIA/LEC_2/millenium/...
CROSS_BORDER/INDIA_PAKISTAN/LEC_12/industreaty/...
```

Do not copy a bilateral source into both country folders. Give it one
cross-border primary home and relate it to both countries in metadata.

## Country and scope vocabulary

Current physical country names are:

```text
Afghanistan
Bangladesh
Bhutan
INDIA
MALDIVES
NEPAL
PAKISTAN
srilanka
```

The inherited casing is retained because the repository is on removable
storage and case-only renames may be unsafe. Normalise labels in the
application, not by casual physical renames.

Additional governed scopes are:

```text
REGIONAL_SOUTH_ASIA
CROSS_BORDER/AFGHANISTAN_PAKISTAN
CROSS_BORDER/CHINA_INDIA
CROSS_BORDER/INDIA_NEPAL
CROSS_BORDER/INDIA_PAKISTAN
```

Create a new pair only when a source is substantively bilateral. Do not use a
cross-border folder merely because a document mentions another country.

## Lecture assignment

Lecture identity comes from the published presentation taxonomy:

| Folder | Main spatial use |
|---|---|
| `LEC_1` | Region, physiography, Himalaya, monsoon and Indian Ocean |
| `LEC_2` | Population, social and economic indicators |
| `LEC_3` | Agriculture, land, labour and food security |
| `LEC_4` | Wheat and rice |
| `LEC_5` | Cotton and sugarcane |
| `LEC_6` | Sri Lankan agriculture, tea, rubber and coconut |
| `LEC_7` | Forests, minerals and resource political economy |
| `LEC_8` | Industry, steel, garments, services, ICT and energy context |
| `LEC_10` | State formation and federalism |
| `LEC_11` | Borders, enclaves and Afghanistan-Pakistan boundaries |
| `LEC_12` | Indus and India-Nepal water relations |
| `LEC_13` | Regional security |

Do not create `LEC_9`: no published Lecture 9 authority exists. Do not create
Lectures 14 or 15 until their presentation-derived subjects are settled.

When one source supports several lectures, select its strongest teaching use
as the physical home. Record other uses as relationships.

## Classification evidence

Use evidence in this order:

1. published presentation structure;
2. document title, abstract, contents or visible map subject;
3. meaningful inherited country/subject folder;
4. metadata;
5. filename;
6. opaque legacy folder.

Country and lecture are independent decisions. A source can have a clear
country but an unresolved lecture.

Never force a broad syllabus, unknown scan or opaque download into the first
plausible lecture.

## Review lanes

Each known scope may contain:

```text
REVIEW_UNASSIGNED
REVIEW_ARCHIVE
REVIEW_EMPTY_OR_INACCESSIBLE
REVIEW_WORKFLOW_METADATA
REVIEW_DUPLICATE_OR_VERSION
```

Use them as follows:

| Lane | Purpose |
|---|---|
| `REVIEW_UNASSIGNED` | Country is known but lecture evidence is insufficient |
| `REVIEW_ARCHIVE` | ZIP/RAR or similar container awaiting inspection |
| `REVIEW_EMPTY_OR_INACCESSIBLE` | Zero-byte, damaged, encrypted or unreadable item |
| `REVIEW_WORKFLOW_METADATA` | Lock file, move log, cache or application working file |
| `REVIEW_DUPLICATE_OR_VERSION` | Confirmed review need between representations |

Review is not deletion. Preserve the file until the instructor decides.

## Adding new material

For each new source:

1. Identify whether it is country, regional or cross-border.
2. Identify the strongest published lecture relationship.
3. Inspect title/content when the filename is weak.
4. Select one primary physical home.
5. Preserve a meaningful inherited subfolder when it explains provenance.
6. Record a symbolic locator and additional lecture/country relationships.
7. Put uncertain material in the appropriate review lane.
8. Explicitly scan only after the physical intake is complete.

Recommended future locator:

```text
SPATIAL_RESOURCE://PAKISTAN/LEC_4/pakagri/wheat_irrigation_2011.pdf
```

Do not register a spatial file under `FOUNDATIONAL_RESOURCE://`; that scheme
belongs to the topical-systemic repository.

## Duplicate handling across the two axes

The spatial and topical repositories may hold the same physical content for
historical reasons. Do not routinely hash either repository.

For a specific candidate:

1. compare filename, size and visible title;
2. use direct `cmp` when exact identity matters;
3. retain both until the instructor chooses an authority;
4. record `SAME_SOURCE_AS` or `SPATIAL_COPY_OF`;
5. remove a copy only with separate authorisation.

The first implementation found six exact cross-repository matches, including
five Indus Treaty items and one Afghanistan mineral-contracting source. They
were preserved.

## Bounded reorganisation procedure

Before moving:

1. census every physical file;
2. generate an inventory with spatial scope, lecture, confidence, status,
   basis and proposed destination;
3. generate a per-file TSV ledger;
4. verify every source exists;
5. verify every destination is unique and absent;
6. reject paths outside the spatial root;
7. re-census immediately before execution.

During execution:

1. create only listed destination parents;
2. move each file exactly once;
3. retain archives and empty files;
4. do not edit file contents;
5. remove only inherited directories proven empty.

After execution:

1. verify every ledger destination exists;
2. verify every old source path is absent;
3. reconcile the before/after physical-file count;
4. confirm no unsupported lecture folder was created;
5. regenerate project inventories;
6. record concurrent user changes separately;
7. run repository tests.

## Empirical lessons from the first migration

The 663-file `SOUTHASIA_MA` migration established:

- country folders alone were insufficient;
- 129 files required a regional South Asia home;
- 59 files required cross-border India-Pakistan, India-Nepal or China-India
  treatment;
- inherited subfolders such as `agri`, `forestchaps`, `pakagri` and
  `industreaty` were useful provenance and were retained below `LEC_<number>`;
- generic thematic containers such as `millenium`, `federalism`, `ironsteel`
  and `maps sasia` could be safely absorbed under spatial/lecture scope;
- 24 files correctly remained in review rather than receiving guessed
  lectures;
- one Maldives profile justified creating the previously absent country
  scope;
- no physical duplication was needed to represent bilateral relevance.

## Acceptance checklist

- [ ] Every physical file has an inventory row.
- [ ] Spatial scope and lecture were decided separately.
- [ ] Country material sits below `Country/LEC_<number>`.
- [ ] Regional material sits below `REGIONAL_SOUTH_ASIA/LEC_<number>`.
- [ ] Bilateral material has one cross-border home.
- [ ] No `LEC_9` was created.
- [ ] Ambiguous, archive, empty and workflow files remain visible.
- [ ] Every move appears in the TSV ledger.
- [ ] Before and after counts reconcile.
- [ ] No file content was rewritten.
- [ ] Duplicate candidates were not silently deleted.
- [ ] Physical paths remain machine-local.
- [ ] Scanning and registration remain explicit, separate decisions.

## Related records

- [Spatial concept note](SPATIAL_RAW_MATERIAL_CONCEPT_NOTE.md)
- [Implementation report](../reports/SPATIAL_RESOURCE_FOLDERISATION_REPORT_2026-07-27.md)
- [Complete spatial inventory](../reports/spatial_resource_inventory_2026-07-27.csv)
- [Per-file move ledger](../reports/SPATIAL_RESOURCE_FOLDERISATION_2026-07-27.tsv)
