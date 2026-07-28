# Protocol — Lecture Mind Maps

**End product:** image files only, one folder per lecture, on the visualisation drive:

```
MA_GRAPHIC_VISUALISATION/IS529N/LEC_<N>/
    LEC_<N>_master_mindmap.png        ← the whole lecture on one image
    slides/slide_NN_mindmap.png       ← one map per slide (PNG)
    slides/slide_NN_mindmap.svg       ← same, vector (zoom / print)
```

Each map traces the same path, left to right:

    Source readings → Theme clusters → Concepts → Slide → Final Presentation

Nothing else goes on that drive — no HTML, no JSON, no scripts. The script lives
here in `scripts/`; data (if ever needed) goes elsewhere via `--data-dir`.

---

## To run the cycle for a lecture

One command. Fill in the four values for the lecture.

```bash
cd <IS529N_PROJECT_ROOT>
python scripts/build_lecture_mindmaps.py \
    --vault      <path to that lecture's LEC_RES_<N>_vault> \
    --deck-pdf   lecture<N>a.pdf \
    --deck-label "Lecture <N>A — <short title>" \
    --lecture    <N> \
    --out        <VISUALISATION_DRIVE>/MA_GRAPHIC_VISUALISATION/IS529N/LEC_<N>
```

That writes the master image + every per-slide image into `LEC_<N>/`. Done.

### Worked example — Lecture 1A (already built)

```bash
python scripts/build_lecture_mindmaps.py \
    --vault      <LEC_RES_1_vault> \
    --deck-pdf   lecture1a.pdf \
    --deck-label "Lecture 1A — South Asia as a Region" \
    --lecture    1 \
    --out        <VISUALISATION_DRIVE>/MA_GRAPHIC_VISUALISATION/IS529N/LEC_1
```

Result: 1 master image + 65 per-slide images (130 files: 65 PNG + 65 SVG).

---

## What the script needs (inputs)

The lecture's **knowledge vault** — a folder with three note subfolders:

| Subfolder | Holds | Used for |
|-----------|-------|----------|
| `01_concepts/` | one `.md` per concept | the Concept tier |
| `02_themes/`   | one `.md` per source-reading cluster (bulleted readings inside) | Theme + Source tiers |
| `04_slides/`   | one `.md` per slide (links to the concepts it teaches) | Slide tier + the chain |

If a lecture has no vault yet, that comes first (same note structure as LEC_1),
then run the command above.

---

## Requirements (one-time)

`networkx`, `matplotlib`, and `graphviz` (both the `python-graphviz` binding and
the `dot` binary). If `dot` is missing: `conda install -c conda-forge graphviz python-graphviz`.

---

## Design note — why theme clusters, not every reading

A single concept is informed by many readings (median ~38 per slide once the
full chain is followed). Drawing every reading on every slide is an unreadable
hairball, so each map summarises sources **per theme cluster** and names the top
few (`+N more` for the rest). The count on each theme node shows the true total.

---

## Options

| Flag | Default | Effect |
|------|---------|--------|
| `--out` | (required) | images-only output folder |
| `--data-dir` | *(off)* | if given, also writes `LEC_<N>_relations.json` **there** (never on the image drive) |
| `--deck-path` | *(empty)* | absolute path of the deck PDF, recorded in the data model |

To rebuild all lectures, run the command once per lecture, changing `<N>`,
`--vault`, `--deck-pdf`, `--deck-label`, and `--out`.
