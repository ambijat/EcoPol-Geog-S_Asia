#!/usr/bin/env python3
"""
build_lecture_mindmaps.py — reusable pipeline that turns one lecture's
knowledge vault into a mind-map set:

    <vault>/  (01_concepts, 02_themes, 04_slides notes)
        │
        ▼
    --out  (the visualisation drive — IMAGE FILES ONLY):
      ├── LEC_N_master_mindmap.png            static 5-layer master map
      └── slides/slide_NN_mindmap.{png,svg}   one compact map per slide

    --data-dir (optional, off the visualisation drive):
      └── LEC_N_relations.json                the data contract (nodes, edges, closures)

RULE: the visualisation drive holds only images. The relations JSON is written
only if --data-dir is given (a different location), never into --out.

The five layers, and the path every per-slide map traces left-to-right:
    Source readings → Theme clusters → Concepts → Slides → Final Presentation

Usage:
    python build_lecture_mindmaps.py \
        --vault  /path/to/LEC_RES_N_vault \
        --deck-pdf lecture2a.pdf \
        --deck-label "Lecture 2A — <title>" \
        --lecture 2 \
        --out    <VISUALISATION_DRIVE>/MA_GRAPHIC_VISUALISATION/IS529N/LEC_2 \
        [--data-dir /some/other/place]        # optional JSON output

Requires: networkx, graphviz (python-graphviz + the `dot` binary), matplotlib.

This is the exact logic used to build LEC_1; it is parameterised so LEC_2…LEC_15
follow the identical structure. The per-slide template, colour palette, and edge
typing are all defined here — edit once, re-run per lecture.
"""
import argparse, glob, json, os, re, textwrap

# ---- 5-layer palette (shared by master map, per-slide maps, gallery) --------
PAL = {"slide": "#81b29a", "concept": "#3d5a80", "theme": "#e07a5f",
       "deck": "#f2cc8f", "source": "#8d99ae"}
FONT = "Clear Sans"


# ---------------------------------------------------------------- note parsing
def _rd(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_vault(vault):
    """Parse 01_concepts / 02_themes / 04_slides note folders into a model."""
    def notes(sub):
        d = os.path.join(vault, sub)
        return sorted(glob.glob(os.path.join(d, "*.md"))) if os.path.isdir(d) else []

    def title_of(txt, fallback):
        m = re.search(r"^#\s+(.+)$", txt, re.M)
        return m.group(1).strip() if m else fallback

    def links(txt):
        return re.findall(r"\[\[([^\]]+)\]\]", txt)

    concepts, themes, slides = {}, {}, {}
    for p in notes("01_concepts"):
        t = _rd(p); k = os.path.splitext(os.path.basename(p))[0]
        concepts[k] = {"label": title_of(t, k), "links": links(t)}
    for p in notes("02_themes"):
        t = _rd(p); k = os.path.splitext(os.path.basename(p))[0]
        # source readings named in a theme note (bullet lines / filenames)
        srcs = re.findall(r"^[\-\*]\s+(.+)$", t, re.M)
        themes[k] = {"label": title_of(t, k), "sources": [s.strip() for s in srcs],
                     "links": links(t)}
    for p in notes("04_slides"):
        t = _rd(p); k = os.path.splitext(os.path.basename(p))[0]
        m = re.search(r"slide[_\-]?(\d+)", k, re.I)
        num = int(m.group(1)) if m else None
        one = ""
        mo = re.search(r"^>\s*(.+)$", t, re.M) or re.search(r"^\*(.+)\*$", t, re.M)
        if mo:
            one = mo.group(1).strip()
        slides[k] = {"num": num, "label": title_of(t, k), "one_line": one,
                     "links": links(t)}
    return concepts, themes, slides


# --------------------------------------------------------------- graph + edges
def build_graph(concepts, themes, slides, deck_pdf, deck_label, deck_path=""):
    """Return the relations dict: nodes, typed edges, per-slide closures."""
    nodes, edges = [], []
    DECK = {"id": "deck::lecture", "type": "deck", "label": deck_label,
            "pdf": deck_pdf, "path": deck_path}
    nodes.append(DECK)

    # source readings become their own nodes (deduped by cleaned name)
    src_id = {}
    def src_node(name):
        key = "src::" + re.sub(r"\W+", "_", name.lower())[:60]
        if key not in src_id:
            src_id[key] = True
            nodes.append({"id": key, "type": "source", "label": name})
        return key

    for k, c in concepts.items():
        nodes.append({"id": f"concept::{k}", "type": "concept", "label": c["label"]})
    for k, t in themes.items():
        nodes.append({"id": f"theme::{k}", "type": "theme", "label": t["label"]})
        for s in t["sources"]:
            sid = src_node(s)
            edges.append({"source": sid, "target": f"theme::{k}", "rel": "part_of"})

    # theme -> concept ("informs")   and  slide -> concept ("teaches")
    label2concept = {c["label"].lower(): f"concept::{k}" for k, c in concepts.items()}
    for k, t in themes.items():
        for L in t["links"]:
            cid = label2concept.get(L.lower())
            if cid:
                edges.append({"source": f"theme::{k}", "target": cid, "rel": "informs"})

    slide_chains = {}
    for k, s in slides.items():
        if s["num"] is None:
            continue
        sid = f"slide::{s['num']:02d}"
        nodes.append({"id": sid, "type": "slide", "label": s["label"]})
        cids = [label2concept[L.lower()] for L in s["links"] if L.lower() in label2concept]
        for cid in cids:
            edges.append({"source": sid, "target": cid, "rel": "teaches"})
            edges.append({"source": cid, "target": DECK["id"], "rel": "in_deck"})
        # transitive closure: slide -> concepts -> themes -> sources
        c2t = {}
        for e in edges:
            if e["rel"] == "informs":
                c2t.setdefault(e["target"], []).append(e["source"])
        t2s = {}
        for e in edges:
            if e["rel"] == "part_of":
                t2s.setdefault(e["target"], []).append(e["source"])
        thset, srcset = [], []
        for cid in cids:
            for tid in c2t.get(cid, []):
                if tid not in thset:
                    thset.append(tid)
                for ss in t2s.get(tid, []):
                    if ss not in srcset:
                        srcset.append(ss)
        slide_chains[sid] = {"num": s["num"], "slide": sid, "title": s["label"],
                             "one_line": s["one_line"], "concepts": cids,
                             "themes": thset, "sources": srcset}
    return {"deck": DECK, "nodes": nodes, "edges": edges, "slide_chains": slide_chains}


# ------------------------------------------------------------ per-slide render
def _wrap(s, w=26):
    return "\\n".join(textwrap.wrap(s, w)) or s

def _clean_src(fn):
    b = fn.rsplit("/", 1)[-1]
    return re.sub(r"\.(pdf|odt|docx|txt|md|tex|jpg|png)$", "", b, flags=re.I)


def render_slide_maps(rel, outdir, lecture_label, max_named_src=3):
    from graphviz import Digraph
    nodes = {n["id"]: n for n in rel["nodes"]}
    DECK = rel["deck"]
    c2t, t2s = {}, {}
    for e in rel["edges"]:
        if e["rel"] == "informs": c2t.setdefault(e["target"], []).append(e["source"])
        if e["rel"] == "part_of": t2s.setdefault(e["target"], []).append(e["source"])
    os.makedirs(outdir, exist_ok=True)

    def one(snum, fmt):
        ch = rel["slide_chains"][f"slide::{snum:02d}"]
        g = Digraph(f"slide{snum}", format=fmt)
        g.attr(rankdir="LR", bgcolor="#fbf9f4", splines="spline", fontname=FONT,
               nodesep="0.30", ranksep="1.2 equally", pad="0.35")
        g.attr("node", fontname=FONT, fontsize="12", style="filled", color="#333", penwidth="1")
        g.attr("edge", color="#b7b7b7", penwidth="1.0", arrowsize="0.65")
        title = nodes[ch["slide"]]["label"].split("—", 1)[-1].strip()
        g.node("SL", f"Slide {snum}\\n{_wrap(title,24)}", shape="box", style="filled,rounded",
               fillcolor=PAL["slide"], fontcolor="white", fontsize="15", penwidth="2")
        if ch["one_line"]:
            g.node("OL", _wrap(ch["one_line"], 44), shape="note", fillcolor="#eef3ee",
                   fontsize="10", fontcolor="#3a3a3a")
            g.edge("SL", "OL", style="dotted", arrowhead="none", color="#c4c4c4")
        g.node("DECK", f"Final Presentation\\n{lecture_label}\\n({DECK['pdf']})", shape="folder",
               fillcolor=PAL["deck"], fontsize="12", penwidth="2")
        concept_ids = ch["concepts"]
        theme_to_concepts = {}
        for cid in concept_ids:
            for tid in c2t.get(cid, []):
                theme_to_concepts.setdefault(tid, set()).add(cid)
        if not concept_ids:
            g.node("NOC", "(framing slide —\\nno mapped concept)", shape="box",
                   fillcolor="#eee", fontsize="11")
            g.edge("SL", "NOC"); g.edge("NOC", "DECK", label="in deck", fontsize="8",
                                        fontcolor="#b7962f", color="#d9b96a")
        cmap = {}
        for ci, cid in enumerate(concept_ids):
            cn = f"C{ci}"; cmap[cid] = cn
            g.node(cn, _wrap(nodes[cid]["label"], 20), shape="box", style="filled,rounded",
                   fillcolor=PAL["concept"], fontcolor="white", fontsize="13", penwidth="1.5")
            g.edge("SL", cn, label="teaches", fontsize="9", fontcolor="#3d5a80", color="#7f96b3")
            g.edge(cn, "DECK", label="in deck", fontsize="8", fontcolor="#b7962f", color="#d9b96a")
        for ti, (tid, cset) in enumerate(sorted(theme_to_concepts.items())):
            tn = f"T{ti}"; srcs = t2s.get(tid, [])
            named = [_clean_src(nodes[s]["label"]) for s in srcs[:max_named_src]]
            extra = len(srcs) - len(named)
            lbl = _wrap(nodes[tid]["label"], 22) + f"  ({len(srcs)} src)"
            if named:
                lbl += "\\n" + "\\n".join("• " + n[:28] for n in named)
                if extra > 0: lbl += f"\\n  +{extra} more"
            g.node(tn, lbl, shape="box", style="filled,rounded", fillcolor="#f4d9cf",
                   color=PAL["theme"], fontsize="10", fontcolor="#5a2f22")
            for cid in cset:
                g.edge(tn, cmap[cid], color=PAL["theme"])
        return g.render(filename=f"{outdir}/slide_{snum:02d}_mindmap", cleanup=True)

    nums = sorted(int(k.split("::")[1]) for k in rel["slide_chains"])
    for snum in nums:
        one(snum, "png"); one(snum, "svg")
    return nums


# ------------------------------------------------- master map (static PNG image)
def render_master_png(rel, out_png, deck_label, dpi=140):
    """Static 5-tier master map as a PNG (visualisation drive = images only)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    nodes = {n["id"]: n for n in rel["nodes"]}
    tier = {"source": 0, "theme": 1, "concept": 2, "slide": 3, "deck": 4}
    bytier = {}
    for n in rel["nodes"]:
        bytier.setdefault(n["type"], []).append(n["id"])

    SPAN = 100.0
    pos = {}
    for tname, members in bytier.items():
        members = sorted(members, key=lambda x: nodes[x]["label"].lower())
        k = len(members)
        for i, nid in enumerate(members):
            y = SPAN * (1 - (i / (k - 1) if k > 1 else 0.5))
            pos[nid] = (tier[tname] * 30.0, y)

    fig, ax = plt.subplots(figsize=(20, 13))
    fig.patch.set_facecolor("#fbf9f4"); ax.set_facecolor("#fbf9f4")
    ecolor = {"part_of": "#c8cfd8", "informs": "#eab8a8", "teaches": "#9fb0c7", "in_deck": "#e6cf9a"}
    for e in rel["edges"]:
        if e["source"] in pos and e["target"] in pos:
            x0, y0 = pos[e["source"]]; x1, y1 = pos[e["target"]]
            ax.plot([x0, x1], [y0, y1], color=ecolor.get(e["rel"], "#ddd"), lw=0.5, alpha=0.5, zorder=1)
    size = {"deck": 1100, "concept": 520, "theme": 340, "source": 80, "slide": 150}
    for tname, members in bytier.items():
        xs = [pos[n][0] for n in members]; ys = [pos[n][1] for n in members]
        ax.scatter(xs, ys, s=size[tname], c=PAL[tname], edgecolors="#333", linewidths=0.5, zorder=3)
    for nid, n in nodes.items():
        if n["type"] in ("deck", "concept"):
            x, y = pos[nid]
            ax.annotate(n["label"][:32], (x, y), fontsize=8.5 if n["type"] == "concept" else 12,
                        fontweight="bold" if n["type"] == "deck" else "normal",
                        ha="center", va="center", zorder=4,
                        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.8))
    heads = {"source": "Source readings", "theme": "Theme clusters", "concept": "Concepts",
             "slide": "Slides", "deck": "Presentation"}
    for tname, xt in tier.items():
        ax.text(xt * 30.0, SPAN + 7, heads[tname], ha="center", fontsize=13, fontweight="bold", color="#444")
    ax.set_title(f"{deck_label} — Master Mind Map  ·  "
                 "Source readings → Theme clusters → Concepts → Slides → Final Presentation",
                 fontsize=15, fontweight="bold", pad=20)
    leg = [Patch(fc=PAL[k], ec="#333", label=v) for k, v in
           [("source", "Source reading"), ("theme", "Theme cluster"), ("concept", "Concept"),
            ("slide", "Slide"), ("deck", "Presentation deck")]]
    ax.legend(handles=leg, loc="lower center", ncol=5, frameon=False, fontsize=11, bbox_to_anchor=(0.5, -0.03))
    ax.set_ylim(-8, SPAN + 12); ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight", facecolor="#fbf9f4")
    plt.close(fig)
    return out_png


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", required=True, help="path to LEC_RES_N_vault (has 01_concepts/02_themes/04_slides)")
    ap.add_argument("--deck-pdf", required=True, help="canonical lecture PDF filename, e.g. lecture2a.pdf")
    ap.add_argument("--deck-label", required=True, help='e.g. "Lecture 2A — <title>"')
    ap.add_argument("--lecture", required=True, help="lecture number, e.g. 2")
    ap.add_argument("--out", required=True, help="IMAGES-ONLY output folder, e.g. .../MA_GRAPHIC_VISUALISATION/IS529N/LEC_2")
    ap.add_argument("--deck-path", default="", help="optional absolute path of the deck PDF")
    ap.add_argument("--data-dir", default="", help="optional dir (OFF the visualisation drive) for LEC_N_relations.json")
    a = ap.parse_args()

    N = a.lecture
    os.makedirs(os.path.join(a.out, "slides"), exist_ok=True)
    concepts, themes, slides = parse_vault(a.vault)
    rel = build_graph(concepts, themes, slides, a.deck_pdf, a.deck_label, a.deck_path)

    # --out receives images only:
    render_slide_maps(rel, os.path.join(a.out, "slides"), a.deck_label)   # slide_NN_mindmap.{png,svg}
    render_master_png(rel, os.path.join(a.out, f"LEC_{N}_master_mindmap.png"), a.deck_label)

    # the relations JSON is data, not an image — written only if a separate dir is given
    if a.data_dir:
        os.makedirs(a.data_dir, exist_ok=True)
        json.dump(rel, open(os.path.join(a.data_dir, f"LEC_{N}_relations.json"), "w", encoding="utf-8"), indent=1)

    print(f"LEC_{N} built → {a.out} (images only)")
    print(f"  slides: {len(rel['slide_chains'])}  concepts: {len(concepts)}  "
          f"themes: {len(themes)}  edges: {len(rel['edges'])}")
    if a.data_dir:
        print(f"  relations JSON → {a.data_dir}")


if __name__ == "__main__":
    main()
