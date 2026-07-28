from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path, PurePosixPath


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "spatial_resource_inventory_2026-07-27.csv"
DEFAULT_LEDGER = PROJECT_ROOT / "reports" / "SPATIAL_RESOURCE_FOLDERISATION_2026-07-27.tsv"

COUNTRIES = {
    "Afghanistan", "Bangladesh", "Bhutan", "INDIA", "NEPAL", "PAKISTAN", "srilanka",
}
ARCHIVES = {".zip", ".rar", ".7z", ".tar", ".gz"}
WORKFLOW_NAMES = {
    "thumbs.db", "missing_paths.txt", "move_log.csv", "ollama_move_log.jsonl",
}


def assigned(scope: str, lecture: int, basis: str, confidence: str = "STRONG"):
    return scope, f"LEC_{lecture}", "ASSIGNED_PROVISIONAL", confidence, basis


def review(scope: str, status: str, basis: str):
    return scope, "", status, "UNASSIGNED", basis


def classify(relative: str, size: int):
    p = PurePosixPath(relative)
    top = p.parts[0]
    low = relative.casefold()
    name = p.name.casefold()
    suffix = Path(p.name).suffix.casefold()

    scope = top if top in COUNTRIES else "REGIONAL_SOUTH_ASIA"
    if size == 0:
        return review(scope, "REVIEW_EMPTY_OR_INACCESSIBLE", "Zero-byte file")
    if suffix in ARCHIVES:
        return review(scope, "REVIEW_ARCHIVE", "Archive requires instructor inspection")
    if name in WORKFLOW_NAMES or name.endswith((".pdf#", ".ppt#")):
        return review(scope, "REVIEW_WORKFLOW_METADATA", "Workflow or desktop metadata")

    if top == "Afghanistan":
        if any(x in low for x in ("mineral", "afgmineral", "geology", "of02-", "myb")):
            return assigned(top, 7, "Afghanistan mineral or geological evidence")
        if "/agri/" in low or "bazar_economy" in low:
            return assigned(top, 3 if "/agri/" in low else 2, "Afghanistan agriculture/economy")
        if any(x in low for x in ("frontier", "fourlines", "map", "nangarhar", "topographische")):
            return assigned(top, 11, "Afghanistan boundary or territorial map")
        if any(x in low for x in ("greatpower", "central asia", "prism_", "china_role", "ngo8", "nlr51")):
            return assigned(top, 13, "Afghanistan regional-security context", "PROVISIONAL")
        return review(top, "REVIEW_UNASSIGNED", "Afghanistan source lacks secure lecture signal")

    if top == "Bangladesh":
        if "mineral" in low:
            return assigned(top, 7, "Bangladesh mineral evidence")
        if "agri" in low:
            return assigned(top, 3, "Bangladesh agricultural evidence")
        return assigned(top, 2, "Bangladesh statistical indicators")

    if top == "Bhutan":
        if any(x in low for x in ("forest", "mineral")):
            return assigned(top, 7, "Bhutan forest or mineral evidence")
        return assigned(top, 3, "Bhutan agricultural statistics")

    if top == "INDIA":
        if name == "as12.pdf":
            return assigned("CROSS_BORDER/INDIA_PAKISTAN", 12, "Indus basin atlas")
        if name == "as7.pdf":
            return assigned("REGIONAL_SOUTH_ASIA", 12, "Ganges basin atlas")
        if name == "fmspe.doc":
            return assigned(top, 3, "Indian crop productivity and agro-climatic zones")
        if name == "regdsprty.doc":
            return assigned(top, 2, "Regional disparities in India")
        if "himalaya" in low:
            return assigned(top, 1, "Indian Himalayan geography")
        if any(x in low for x in ("wheat", "rice")):
            return assigned(top, 4, "Indian wheat/rice evidence")
        if "/agri/" in low:
            return assigned(top, 3, "Indian agriculture")
        if "representing india" in low:
            return assigned(top, 10, "Indian state representation")
        if any(x in low for x in ("planning", "trade", "dairy", "energyresource")):
            return assigned(top, 2, "Indian planning or economic relations", "PROVISIONAL")
        return review(top, "REVIEW_UNASSIGNED", "Indian source lacks secure lecture signal")

    if top == "NEPAL":
        if "nepal hydro/" in low:
            return assigned(top, 12, "Nepal hydropower and water relations")
        if any(x in low for x in ("forest", "mineral")):
            return assigned(top, 7, "Nepal forest or mineral evidence")
        if any(x in low for x in ("economic survey", "nepal in figures", "survey2001", "table_full")):
            return assigned(top, 2, "Nepal economic/statistical indicators")
        if "nepal/" in low:
            return assigned(top, 3, "Nepal agriculture and rural economy", "PROVISIONAL")
        return review(top, "REVIEW_UNASSIGNED", "Nepal source lacks secure lecture signal")

    if top == "PAKISTAN":
        if name == "pak.pdf":
            return assigned(top, 2, "ADB Pakistan development indicators")
        if "poster zahid" in low:
            return assigned(top, 12, "Pakistan dams and economic development")
        if any(x in low for x in ("07 wrs85", "sindhwater", "sindh water res", "role of dams")):
            return assigned(top, 12, "Pakistan water resources and Indus-basin development")
        if any(x in low for x in ("mineral", "mienral", "geolog", "coal", "granite", "mining", "pkmyb", "b2078_frontmatter", "20040801")):
            return assigned(top, 7, "Pakistan minerals and geology")
        if any(x in low for x in ("cotton", "sugar", "merged-20170322")):
            return assigned(top, 5, "Pakistan cotton or sugar economy")
        if any(x in low for x in ("wheat", "rice", "respaper")):
            return assigned(top, 4, "Pakistan wheat/rice evidence")
        if any(x in low for x in ("agri", "crop", "food", "livestock", "land_", "land ", "irrigation", "area and production", "areaproduction", "nfsr", "table06h", "pakdatadistrict", "conversion factors", "converstion factors", "1-5.pdf", "1.5.pdf", "2016-17.pdf", "mpra_paper_32273")):
            return assigned(top, 3, "Pakistan agriculture, food or land use")
        if any(x in low for x in ("industrial", "manufactur", "steel", "cement", "energy", "ch_emr_2009", "file28876")):
            return assigned(top, 8, "Pakistan industry or energy")
        if any(x in low for x in ("federal", "landlord", "baloch", "fata", "regionalk", "manifesto")):
            return assigned(top, 10, "Pakistan federalism, region or state politics", "PROVISIONAL")
        if any(x in low for x in ("gwadar", "greatgame")):
            return assigned(top, 13, "Pakistan regional-security context", "PROVISIONAL")
        if any(x in low for x in ("economic", "statistics", "statistical", "mdg", "foreignaid", "foreign aid", "adb", "monthly", "economy of pakistan", "mpra_1211", "pakistan_2003_en", "data_sasia")):
            return assigned(top, 2, "Pakistan economic/statistical indicators")
        if any(x in low for x in ("nspdf", "subcat_pdf_133")):
            return assigned(top, 8, "Pakistan energy profile")
        if any(x in low for x in ("potawar", "pakistan_resources.jpg")):
            return assigned(top, 1, "Pakistan physical/resource geography")
        if any(x in low for x in ("pakistan studies", "syllabus", "nspdf", "pak.pdf")):
            return review(top, "REVIEW_UNASSIGNED", "Broad Pakistan teaching source")
        if suffix in {".doc", ".docx", ".txt", ".jsonl", ".csv"}:
            return review(top, "REVIEW_WORKFLOW_METADATA", "Unresolved working or metadata file")
        return review(top, "REVIEW_UNASSIGNED", "Pakistan source lacks secure lecture signal")

    if top == "srilanka":
        if name == "exj_82.pdf":
            return assigned(top, 2, "Sri Lankan GIS and socio-economic planning")
        if any(x in low for x in ("agri", "tea", "rubber", "paddy", "wheat", "crop")):
            return assigned(top, 6, "Sri Lankan agriculture and plantation crops")
        if any(x in low for x in ("forest", "mineral")):
            return assigned(top, 7, "Sri Lankan forest or mineral evidence")
        if any(x in low for x in ("annual", "review", "index.htm", "all_sectors", "english-ar")):
            return assigned(top, 2, "Sri Lankan economic/statistical indicators")
        return review(top, "REVIEW_UNASSIGNED", "Sri Lankan source lacks secure lecture signal")

    if top == "Cotton_IndoPak":
        if "pakSurvey_Statistical_Portion".casefold() in low:
            if "agriculture" in low:
                return assigned("PAKISTAN", 3, "Pakistan survey agriculture section")
            if any(x in low for x in ("manufacturing", "energy", "transport")):
                return assigned("PAKISTAN", 8, "Pakistan survey industry/energy section")
            return assigned("PAKISTAN", 2, "Pakistan survey statistical section")
        return assigned("CROSS_BORDER/INDIA_PAKISTAN", 5, "India-Pakistan cotton collection")

    if top == "FOODSECURITY":
        return assigned("REGIONAL_SOUTH_ASIA", 3, "Regional food-security collection")
    if top == "GLCF_RECTIFY":
        return review("REGIONAL_SOUTH_ASIA", "REVIEW_WORKFLOW_METADATA", "Geospatial rectification work file")
    if top == "MinComSum10":
        return assigned("REGIONAL_SOUTH_ASIA", 5 if "cotton" in low else 7, "World commodity reference")
    if top == "cia_2010":
        country_codes = {
            "cia_af.pdf": "Afghanistan", "cia_bg.pdf": "Bangladesh", "cia_bu.pdf": "Bhutan",
            "cia_in2012.pdf": "INDIA", "cia_ml.pdf": "MALDIVES", "cia_np.pdf": "NEPAL",
            "cia_pk.pdf": "PAKISTAN", "cia_sl.pdf": "srilanka",
        }
        return assigned(country_codes.get(name, "REGIONAL_SOUTH_ASIA"), 2, "Country/regional indicator profile")
    if top == "climate":
        if "pakistan_landuse" in low:
            return assigned("PAKISTAN", 3, "Pakistan land-use image")
        return assigned("REGIONAL_SOUTH_ASIA", 1, "South Asian climate and physiography")
    if top == "earthtrends":
        return assigned("PAKISTAN", 7 if "mineral" in low else 2, "Pakistan country profile")
    if top == "energy":
        if "bangla" in low:
            return assigned("Bangladesh", 8, "Bangladesh power/energy")
        if "nepal" in low:
            return assigned("NEPAL", 12, "Nepal energy/hydropower")
        if "lanka" in low:
            return assigned("srilanka", 8, "Sri Lankan energy")
        return assigned("PAKISTAN", 8, "Pakistan energy industry")
    if top == "epPZ7gAM9cW":
        return assigned("REGIONAL_SOUTH_ASIA", 7, "Regional/world mineral statistics")
    if top == "federalism":
        return assigned("REGIONAL_SOUTH_ASIA", 10, "South Asian federalism collection")
    if top == "industreaty":
        if "lanak" in low:
            return assigned("srilanka", 7, "Sri Lankan mineral yearbook")
        if "kosi" in low:
            return assigned("CROSS_BORDER/INDIA_NEPAL", 12, "India-Nepal Kosi material")
        if "chinahydro" in low:
            return assigned("CROSS_BORDER/CHINA_INDIA", 12, "Tibet/India hydropolitical context")
        if "mineral" in low or "commodity" in low:
            return assigned("REGIONAL_SOUTH_ASIA", 7, "Regional mineral/commodity source")
        return assigned("CROSS_BORDER/INDIA_PAKISTAN", 12, "Indus Treaty collection")
    if top == "ironsteel":
        if "pakistan" in low:
            return assigned("PAKISTAN", 8, "Pakistan steel industry")
        if "india" in low:
            return assigned("INDIA", 8, "Indian steel industry")
        return assigned("REGIONAL_SOUTH_ASIA", 8, "Regional iron and steel")
    if top == "ma2010material":
        return assigned("REGIONAL_SOUTH_ASIA", 7, "Regional mineral GIS and statistics")
    if top == "maps sasia":
        if any(x in low for x in ("kashmir", "easternpunjab")):
            return assigned("CROSS_BORDER/INDIA_PAKISTAN", 11, "Kashmir/boundary map")
        if any(x in low for x in ("afghan", "kafiristan")):
            return assigned("Afghanistan", 11, "Afghanistan frontier map")
        if "bhutan" in low:
            return assigned("Bhutan", 7, "Bhutan protected-area/topographic map")
        if "india" in low:
            return assigned("INDIA", 10, "Historical India map")
        if "floods in pak" in low:
            return assigned("PAKISTAN", 1, "Pakistan physical/climate map")
        if name == "thumbs.db":
            return review("REGIONAL_SOUTH_ASIA", "REVIEW_WORKFLOW_METADATA", "Desktop thumbnail cache")
        return assigned("REGIONAL_SOUTH_ASIA", 1, "South Asian regional map")
    if top == "millenium":
        if "nepal" in low:
            return assigned("NEPAL", 2, "Nepal MDG indicators")
        if "pakistan" in low:
            return assigned("PAKISTAN", 2, "Pakistan MDG indicators")
        if name == "thumbs.db":
            return review("REGIONAL_SOUTH_ASIA", "REVIEW_WORKFLOW_METADATA", "Desktop thumbnail cache")
        return assigned("REGIONAL_SOUTH_ASIA", 2, "Regional development indicators")
    if top == "SAARC":
        return assigned("REGIONAL_SOUTH_ASIA", 2, "SAARC regional reference", "PROVISIONAL")
    if top == "steelstats":
        return assigned("REGIONAL_SOUTH_ASIA", 8, "Regional steel statistics")

    if relative == "India Mineral Map.jpg":
        return assigned("INDIA", 7, "India mineral map")
    if relative == "Table of Country-wise export of Cotton Fabrics.JPG":
        return assigned("REGIONAL_SOUTH_ASIA", 5, "Country-wise cotton-fabric trade")
    return review("REGIONAL_SOUTH_ASIA", "REVIEW_UNASSIGNED", "No secure spatial/lecture rule")


def destination(relative: str, scope: str, lecture: str, status: str) -> str:
    p = PurePosixPath(relative)
    top = p.parts[0]
    if lecture:
        base = PurePosixPath(*scope.split("/"), lecture)
    else:
        base = PurePosixPath(*scope.split("/"), status)
    if top == scope and len(p.parts) > 1:
        tail = PurePosixPath(*p.parts[1:])
    else:
        tail = p
    return (base / tail).as_posix()


def build(root: Path, output: Path, ledger: Path) -> dict:
    files = sorted(p for p in root.rglob("*") if p.is_file())
    rows = []
    by_name_size: dict[tuple[str, int], list[str]] = defaultdict(list)
    for path in files:
        rel = path.relative_to(root).as_posix()
        size = path.stat().st_size
        by_name_size[(path.name.casefold(), size)].append(rel)
    for path in files:
        rel = path.relative_to(root).as_posix()
        size = path.stat().st_size
        scope, lecture, status, confidence, basis = classify(rel, size)
        rows.append({
            "source_relative_path": rel,
            "spatial_scope": scope,
            "lecture_folder": lecture,
            "decision_status": status,
            "confidence": confidence,
            "basis": basis,
            "duplicate_candidate_count": len(by_name_size[(path.name.casefold(), size)]),
            "proposed_destination": destination(rel, scope, lecture, status),
        })
    destinations = [r["proposed_destination"] for r in rows]
    if len(destinations) != len(set(destinations)):
        raise ValueError("Proposed destination collision")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    with ledger.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(("source_relative_path", "destination_relative_path", "decision"))
        for row in rows:
            writer.writerow((row["source_relative_path"], row["proposed_destination"], row["basis"]))
    statuses: dict[str, int] = defaultdict(int)
    for row in rows:
        statuses[row["decision_status"]] += 1
    return {"files": len(rows), "statuses": dict(sorted(statuses.items()))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args()
    result = build(args.root.resolve(), args.output.resolve(), args.ledger.resolve())
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
