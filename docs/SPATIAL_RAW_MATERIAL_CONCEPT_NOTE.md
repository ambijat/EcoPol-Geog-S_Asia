# Spatial Raw Material Arrangement Concept Note

Status: concept implemented and empirically verified on 27 July 2026. The
resulting operating rules are maintained in the
[Spatial Raw Material Arrangement Manual](SPATIAL_RAW_MATERIAL_ARRANGEMENT_MANUAL.md).
The proposed integration of this spatial axis with the topical axis in the
desktop cockpit is defined in the
[Topical–Spatial Cockpit UX Design](TOPICAL_SPATIAL_COCKPIT_UX_DESIGN.md).

## Purpose

IS529N now requires two complementary ways of finding source material:

```text
Vertical / topical-systemic axis
Lecture → Part → Topic → Source

Horizontal / spatial axis
Country or regional scope → Lecture → Source
```

The existing Lecture Raw Material repository remains the vertical authority.
The legacy `SOUTHASIA_MA` collection will become the horizontal spatial
repository. Neither axis replaces the other.

## Evidence from the initial census

The read-only census of `SOUTHASIA_MA` found:

```text
physical files: 663
directories: 53
size: approximately 772 MB
symbolic links: 0
empty files: 1
```

The collection currently mixes:

- country containers;
- bilateral crop collections;
- South-Asia-wide indicators and maps;
- lecture themes such as federalism, the Indus Treaty and iron and steel;
- format/workflow folders;
- opaque download identifiers; and
- loose regional images.

It is therefore not yet a country arrangement even though many country signals
already exist.

The largest country collections are Pakistan, Nepal, Sri Lanka, Afghanistan
and Bhutan. Maldives material currently appears only inside regional/CIA
collections.

## Spatial identity model

The first physical level represents spatial scope. The second level represents
the lecture:

```text
Afghanistan/
├── LEC_2/
├── LEC_7/
├── LEC_11/
└── REVIEW_UNASSIGNED/

Bangladesh/
├── LEC_2/
├── LEC_3/
├── LEC_4/
├── LEC_7/
└── REVIEW_UNASSIGNED/
```

Existing country spellings may be retained during the first implementation to
avoid risky case-only renames on removable storage. Display labels can be
normalised independently.

The lecture folder is deliberately lecture-level, not part-level. A country's
source may support Part A, Part B or several topics. Topic-level detail remains
authoritative in the vertical repository and in metadata relationships.

## Regional and cross-border material

A country-first system must not falsely assign a regional or bilateral source
to one country. One physical source must still have one primary home.

Use:

```text
REGIONAL_SOUTH_ASIA/
└── LEC_<number>/

CROSS_BORDER/
├── INDIA_PAKISTAN/
│   └── LEC_<number>/
├── INDIA_NEPAL/
│   └── LEC_<number>/
└── AFGHANISTAN_PAKISTAN/
    └── LEC_<number>/
```

Examples:

- South-Asia-wide development indicators → `REGIONAL_SOUTH_ASIA/LEC_2`;
- India-Pakistan cotton comparison → `CROSS_BORDER/INDIA_PAKISTAN/LEC_5`;
- Indus Water Treaty → `CROSS_BORDER/INDIA_PAKISTAN/LEC_12`;
- India-Nepal hydropower → `CROSS_BORDER/INDIA_NEPAL/LEC_12`;
- Durand Line or Afghanistan-Pakistan frontier →
  `CROSS_BORDER/AFGHANISTAN_PAKISTAN/LEC_11`.

This is more accurate and more economical than copying the same file into both
country folders.

## Spatial country set

Use these instructor-facing scopes:

```text
Afghanistan
Bangladesh
Bhutan
INDIA
MALDIVES
NEPAL
PAKISTAN
srilanka
REGIONAL_SOUTH_ASIA
CROSS_BORDER
```

The first seven existing country directory names and `srilanka` are retained
physically during the bounded migration. `MALDIVES`, `REGIONAL_SOUTH_ASIA` and
`CROSS_BORDER` may be created as explicit writable organisational folders.

## Lecture authority

Lecture assignments follow
[`../config/lecture_topic_taxonomy.yaml`](../config/lecture_topic_taxonomy.yaml)
and the presentation-derived sequence:

| Lecture | Spatially useful subject |
|---:|---|
| 1 | Region, physiography, Himalaya, monsoon and Indian Ocean |
| 2 | Population, social and economic indicators |
| 3 | Agriculture, trade, labour, land use and food security |
| 4 | Wheat and rice systems |
| 5 | Cotton and sugarcane |
| 6 | Tea, rubber, coconut and Sri Lankan agriculture |
| 7 | Bhutan/Nepal forests and Afghanistan minerals |
| 8 | Industry, garments, steel, services and ICT |
| 10 | State formation and federalism |
| 11 | Borders, Bengal enclaves and Afghanistan-Pakistan boundaries |
| 12 | Indus and India-Nepal water relations |
| 13 | Regional security |

There is no published Lecture 9 presentation, so `LEC_9` must not be invented.
Lecture 14 and 15 assignments likewise require a future published teaching
authority.

## Classification authority

Use evidence in this order:

1. published presentation structure;
2. existing country and meaningful subject folder;
3. document title, abstract, table of contents or visible map subject;
4. document metadata;
5. filename;
6. inherited generic/opaque folder name.

An ambiguous item goes to a review lane; it is not forced into a lecture.

## Review lanes

At spatial-root level:

```text
REVIEW_UNASSIGNED/
REVIEW_DUPLICATE_OR_VERSION/
REVIEW_ARCHIVE/
REVIEW_EMPTY_OR_INACCESSIBLE/
REVIEW_WORKFLOW_METADATA/
```

Country is retained in the inventory even for an unresolved lecture. If the
country itself is uncertain, use the root review lane.

The review folders are temporary decision queues, not deletion queues.

## Relationship with the vertical repository

The first census found:

- 17 same-name/same-size groups within `SOUTHASIA_MA`;
- six same-name/same-size matches between the spatial and vertical
  repositories.

These are duplicate candidates, not automatic duplicates. The first migration
must preserve them and record their possible counterpart. Direct byte
comparison may be used later for a specific instructor decision; routine
hashing is unnecessary.

Future persistent locators should be separate:

```text
FOUNDATIONAL_RESOURCE://LEC_RES_12/A03_indus_treaty_history/...
SPATIAL_RESOURCE://CROSS_BORDER/INDIA_PAKISTAN/LEC_12/...
```

A relationship can then record:

```text
SPATIAL_COPY_OF
SAME_SOURCE_AS
SUPPORTS_COUNTRY_CASE
SUPPORTS_LECTURE
```

Physical absolute paths remain machine-local.

## Application integration boundary

The spatial repository should eventually receive its own configurable root and
symbolic scheme. It must not be silently folded into the existing single
Lecture Raw Material root.

Recommended future cockpit presentation:

```text
Lecture Raw Material
├── Topical-Systemic View
└── Spatial/Country View
```

Both views should point to governed records. Selecting a spatial root must not
scan it. Scanning remains explicit and creates candidates only.

The physical reorganisation can precede this application feature, but no
spatial file should be registered under the vertical symbolic root.

## Bounded implementation method

1. Generate a complete 663-file spatial inventory.
2. Assign spatial scope and lecture independently.
3. Mark confidence and unresolved items.
4. Produce a per-file proposed-move ledger.
5. Confirm every source exists and each destination is unique.
6. Move one legacy top-level collection at a time.
7. Preserve file contents and archives.
8. Remove only empty inherited directories.
9. Reconcile all 663 physical files.
10. Record cross-repository duplicate candidates without deleting them.
11. Write the reference manual only after the implementation reveals the
    practical exceptions.

## Acceptance criteria

The spatial implementation is acceptable only when:

1. all 663 initial files are represented in the inventory;
2. every moved file has one old and one new relative path;
3. country and lecture are separate recorded decisions;
4. every country has lecture folders only where evidence exists;
5. regional and bilateral sources are not falsely assigned to one country;
6. no `LEC_9` is invented;
7. ambiguous, archive, duplicate and empty items remain visible;
8. no source content is rewritten;
9. before/after counts reconcile;
10. no automatic registration or routine hashing occurs; and
11. the empirical reference manual records the final rules and exceptions.
