# Artifact Repository Path Configuration

Physical repository roots are machine-local. The application stores them only in ignored `config/local_paths.json`; the committed `config/local_paths.example.json` contains empty paths.

Writable roots belong inside the active project. Historical, published-source,
topical-source, AI-note-source, and spatial-source locations belong in
`protected_read_only_paths` and must never overlap a writable root.

On first launch, the desktop application displays a native six-row setup wizard when the four required roots are not operational. The fifth and sixth classes (Knowledge Maps and Spatial Raw Material) may remain unconfigured. Until the required roots validate, artifact registration, scanning, and relationship creation remain disabled while Settings stays available.

## Topical and spatial twin roots

Lecture Raw Material (`FOUNDATIONAL_RESOURCE`) and Spatial Raw Material (`SPATIAL_RESOURCE`) are independent, twin repository roots covering the same course content from two lenses:

```text
FOUNDATIONAL_RESOURCE   Lecture → Part → Topic → Source        (topical-systemic axis)
SPATIAL_RESOURCE        Country/regional/cross-border → Lecture → Source   (spatial axis)
```

Each keeps its own configured path, status, access mode, and symbolic scheme; selecting or changing one root never touches the other, and the spatial root is optional and read-only by default. See the [Topical–Spatial Cockpit UX Design](TOPICAL_SPATIAL_COCKPIT_UX_DESIGN.md) and [Spatial Raw Material Arrangement Concept Note](SPATIAL_RAW_MATERIAL_CONCEPT_NOTE.md) for the full rationale.

## Symbolic locators

Artifact records use locators such as:

```text
FOUNDATIONAL_RESOURCE://books/chapter_03.pdf
PRESENTATION_WORKBENCH://week_01/lecture_01.odp
SPATIAL_RESOURCE://CROSS_BORDER/INDIA_PAKISTAN/LEC_12/industreaty/source.pdf
```

`PathResolver` maps these locators to a physical path only inside authorised desktop services. It rejects `..`, absolute-path injection, backslash traversal, and symbolic links that escape the configured root.

## Scanning boundary

Selecting or changing a root does not scan it. Scanning begins only after pressing **Refresh Current Census** or **Rescan**. The read-only scan creates candidate records only when the census changed; an unchanged census is reused. Registration remains a separate instructor action.

Changing a root never rewrites artifact records. The repository-path screen reports symbolic re-resolution as `resolved`, `missing`, or `ambiguous`.
