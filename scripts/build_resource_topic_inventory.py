from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TAXONOMY = PROJECT_ROOT / "config" / "lecture_topic_taxonomy.yaml"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "reports" / "raw_resource_topic_inventory_2026-07-27.csv"
)

# High-confidence assignments based on an existing named topic folder whose
# meaning agrees with the presentation-derived taxonomy.
PREFIX_RULES = (
    ("LEC_RES_1/region_concept/", "IS529N-L01A", "A01_REGION_CONCEPT"),
    ("LEC_RES_1/onto_epistemo/", "IS529N-L01A", "A02_KNOWLEDGE_SOURCES"),
    ("LEC_RES_1/puranas_geo/", "IS529N-L01A", "A02_KNOWLEDGE_SOURCES"),
    ("LEC_RES_1/strabo_ancient/", "IS529N-L01A", "A02_KNOWLEDGE_SOURCES"),
    ("LEC_RES_1/notes_cunningham/", "IS529N-L01A", "A02_KNOWLEDGE_SOURCES"),
    ("LEC_RES_1/aijaz_region_sasia/", "IS529N-L01A", "A01_REGION_CONCEPT"),
    ("LEC_RES_1/geology_him/", "IS529N-L01B", "B01_HIMALAYAN_GEOLOGY"),
    ("LEC_RES_1/monsoon_readings/", "IS529N-L01B", "B03_MONSOON_CLIMATE"),
    ("LEC_RES_1/ohkspate/", "IS529N-L01B", "B02_PHYSIOGRAPHY"),
    ("LEC_RES_2/A02_demography_health/", "IS529N-L02A", "A02_DEMOGRAPHY_HEALTH"),
    ("LEC_RES_2/B01_growth_income/", "IS529N-L02B", "B01_GROWTH_INCOME"),
    ("LEC_RES_3/A01_agricultural_structure/", "IS529N-L03A", "A01_AGRICULTURAL_STRUCTURE"),
    ("LEC_RES_3/A02_agricultural_trade/", "IS529N-L03A", "A02_AGRICULTURAL_TRADE"),
    ("LEC_RES_3/A03_labour_productivity/", "IS529N-L03A", "A03_LABOUR_PRODUCTIVITY"),
    ("LEC_RES_3/A04_landholdings_landuse/", "IS529N-L03A", "A04_LANDHOLDINGS_LANDUSE"),
    ("LEC_RES_3/B01_food_security_indicators/", "IS529N-L03B", "B01_FOOD_SECURITY_INDICATORS"),
    ("LEC_RES_3/B02_nutrition/", "IS529N-L03B", "B02_NUTRITION"),
    ("LEC_RES_3/B03_food_policy/", "IS529N-L03B", "B03_FOOD_POLICY"),
    ("LEC_RES_3/B04_cereals_pulses/", "IS529N-L03B", "B04_CEREALS_PULSES"),
    ("LEC_RES_4/A01_wheat_rice_regional/", "IS529N-L04A", "A01_WHEAT_RICE_REGIONAL"),
    ("LEC_RES_4/A02_rice_wheat_system/", "IS529N-L04A", "A02_RICE_WHEAT_SYSTEM"),
    ("LEC_RES_4/A03_pakistan_wheat/", "IS529N-L04A", "A03_PAKISTAN_WHEAT"),
    ("LEC_RES_4/B01_bangladesh_wheat/", "IS529N-L04B", "B01_BANGLADESH_WHEAT"),
    ("LEC_RES_4/B02_bangladesh_rice/", "IS529N-L04B", "B02_BANGLADESH_RICE"),
    ("LEC_RES_4/B03_cropping_calendar/", "IS529N-L04B", "B03_CROPPING_CALENDAR"),
    ("LEC_RES_4/B04_pakistan_rice/", "IS529N-L04B", "B04_PAKISTAN_RICE"),
    ("LEC_RES_5/A01_cotton_data/", "IS529N-L05A", "A01_COTTON_DATA"),
    ("LEC_RES_5/A02_cotton_pakistan/", "IS529N-L05A", "A02_COTTON_PAKISTAN"),
    ("LEC_RES_5/A03_cotton_india/", "IS529N-L05A", "A03_COTTON_INDIA"),
    ("LEC_RES_5/A04_cotton_processing/", "IS529N-L05A", "A04_COTTON_PROCESSING"),
    ("LEC_RES_5/B01_sugarcane_data/", "IS529N-L05B", "B01_SUGARCANE_DATA"),
    ("LEC_RES_5/B02_sugarcane_india/", "IS529N-L05B", "B02_SUGARCANE_INDIA"),
    ("LEC_RES_5/B03_sugarcane_pakistan/", "IS529N-L05B", "B03_SUGARCANE_PAKISTAN"),
    ("LEC_RES_5/B04_sugar_industry/", "IS529N-L05B", "B04_SUGAR_INDUSTRY"),
    ("LEC_RES_6/agri_policy/", "IS529N-L06A", "A01_SRI_LANKA_AGRICULTURE"),
    ("LEC_RES_6/food_security/", "IS529N-L06A", "A01_SRI_LANKA_AGRICULTURE"),
    ("LEC_RES_6/lanka_tea/", "IS529N-L06A", "A02_TEA_PRODUCTION"),
    ("LEC_RES_6/plantation_crops/", "IS529N-L06B", "B03_COCONUT"),
    ("LEC_RES_7/A01_bhutan_forest_types/", "IS529N-L07A", "A01_BHUTAN_FOREST_TYPES"),
    ("LEC_RES_7/A02_bhutan_forest_governance/", "IS529N-L07A", "A02_BHUTAN_FOREST_GOVERNANCE"),
    ("LEC_RES_7/A03_bhutan_forest_economy/", "IS529N-L07A", "A03_BHUTAN_FOREST_ECONOMY"),
    ("LEC_RES_7/A04_bhutan_conservation/", "IS529N-L07A", "A04_BHUTAN_CONSERVATION"),
    ("LEC_RES_7/B01_nepal_forest_types/", "IS529N-L07B", "B01_NEPAL_FOREST_TYPES"),
    ("LEC_RES_7/B02_nepal_agroforestry/", "IS529N-L07B", "B02_NEPAL_AGROFORESTRY"),
    ("LEC_RES_7/B03_nepal_community_forestry/", "IS529N-L07B", "B03_NEPAL_COMMUNITY_FORESTRY"),
    ("LEC_RES_7/B04_nepal_conservation/", "IS529N-L07B", "B04_NEPAL_CONSERVATION"),
    ("LEC_RES_7/C01_resource_economics/", "IS529N-L07C", "C01_RESOURCE_ECONOMICS"),
    ("LEC_RES_7/C02_resource_political_economy/", "IS529N-L07C", "C02_RESOURCE_POLITICAL_ECONOMY"),
    ("LEC_RES_7/C03_afghan_geology/", "IS529N-L07C", "C03_AFGHAN_GEOLOGY"),
    ("LEC_RES_7/C04_afghan_minerals/", "IS529N-L07C", "C04_AFGHAN_MINERALS"),
    ("LEC_RES_8/A01_industrial_location/", "IS529N-L08A", "A01_INDUSTRIAL_LOCATION"),
    ("LEC_RES_8/A02_industrial_complexes/", "IS529N-L08A", "A02_INDUSTRIAL_COMPLEXES"),
    ("LEC_RES_8/A03_industrial_corridors/", "IS529N-L08A", "A03_INDUSTRIAL_CORRIDORS"),
    ("LEC_RES_8/A04_iron_steel/", "IS529N-L08A", "A04_IRON_STEEL"),
    ("LEC_RES_8/B01_garment_growth/", "IS529N-L08B", "B01_GARMENT_GROWTH"),
    ("LEC_RES_8/B02_garment_labour/", "IS529N-L08B", "B02_GARMENT_LABOUR"),
    ("LEC_RES_8/B03_garment_safety/", "IS529N-L08B", "B03_GARMENT_SAFETY"),
    ("LEC_RES_8/B04_epz_global_value_chains/", "IS529N-L08B", "B04_EPZ_GLOBAL_VALUE_CHAINS"),
    ("LEC_RES_8/C01_service_economy/", "IS529N-L08C", "C01_SERVICE_ECONOMY"),
    ("LEC_RES_8/C02_ict_ites/", "IS529N-L08C", "C02_ICT_ITES"),
    ("LEC_RES_8/C03_fdi_professional_services/", "IS529N-L08C", "C03_FDI_PROFESSIONAL_SERVICES"),
    ("LEC_RES_8/C04_tourism_logistics/", "IS529N-L08C", "C04_TOURISM_LOGISTICS"),
    ("LEC_RES_10/A01_functional_state/", "IS529N-L10A", "A01_FUNCTIONAL_STATE"),
    ("LEC_RES_10/A02_centripetal_centrifugal/", "IS529N-L10A", "A02_CENTRIPETAL_CENTRIFUGAL"),
    ("LEC_RES_10/A03_boundaries_frontiers/", "IS529N-L10A", "A03_BOUNDARIES_FRONTIERS"),
    ("LEC_RES_10/A04_state_formation/", "IS529N-L10A", "A04_STATE_FORMATION"),
    ("LEC_RES_10/A05_state_reorganisation/", "IS529N-L10A", "A05_STATE_REORGANISATION"),
    ("LEC_RES_10/B01_federalism_theory/", "IS529N-L10B", "B01_FEDERALISM_THEORY"),
    ("LEC_RES_10/B02_india_pakistan_federalism/", "IS529N-L10B", "B02_INDIA_PAKISTAN_FEDERALISM"),
    ("LEC_RES_10/B03_ethnic_conflict/", "IS529N-L10B", "B03_ETHNIC_CONFLICT"),
    ("LEC_RES_10/B04_sri_lanka_federalism/", "IS529N-L10B", "B04_SRI_LANKA_FEDERALISM"),
    ("LEC_RES_11/A01_border_theory/", "IS529N-L11A", "A01_BORDER_THEORY"),
    ("LEC_RES_11/A02_bengal_enclaves/", "IS529N-L11A", "A02_BENGAL_ENCLAVES"),
    ("LEC_RES_11/A03_land_boundary_agreement/", "IS529N-L11A", "A03_LAND_BOUNDARY_AGREEMENT"),
    ("LEC_RES_11/A04_border_management/", "IS529N-L11A", "A04_BORDER_MANAGEMENT"),
    ("LEC_RES_11/B01_great_game_boundaries/", "IS529N-L11B", "B01_GREAT_GAME_BOUNDARIES"),
    ("LEC_RES_11/B02_durand_history/", "IS529N-L11B", "B02_DURAND_HISTORY"),
    ("LEC_RES_11/B03_pashtunistan/", "IS529N-L11B", "B03_PASHTUNISTAN"),
    ("LEC_RES_11/B04_durand_contemporary/", "IS529N-L11B", "B04_DURAND_CONTEMPORARY"),
    ("LEC_RES_12/A01_hydropolitics/", "IS529N-L12A", "A01_HYDROPOLITICS"),
    ("LEC_RES_12/A02_river_basin_governance/", "IS529N-L12A", "A02_RIVER_BASIN_GOVERNANCE"),
    ("LEC_RES_12/A03_indus_treaty_history/", "IS529N-L12A", "A03_INDUS_TREATY_HISTORY"),
    ("LEC_RES_12/A04_indus_treaty_politics/", "IS529N-L12A", "A04_INDUS_TREATY_POLITICS"),
    ("LEC_RES_12/B01_india_nepal_water_relations/", "IS529N-L12B", "B01_INDIA_NEPAL_WATER_RELATIONS"),
    ("LEC_RES_12/B02_kosi_gandak/", "IS529N-L12B", "B02_KOSI_GANDAK"),
    ("LEC_RES_12/B03_karnali_mahakali/", "IS529N-L12B", "B03_KARNALI_MAHAKALI"),
    ("LEC_RES_12/B04_nepal_water_politics/", "IS529N-L12B", "B04_NEPAL_WATER_POLITICS"),
    ("LEC_RES_7/forportal_Bhutan/", "IS529N-L07A", "A01_BHUTAN_FOREST_TYPES"),
    ("LEC_RES_7/bhutan_forest_corpus_newpdfs/", "IS529N-L07A", "A01_BHUTAN_FOREST_TYPES"),
    ("LEC_RES_7/forportal_afgmineral/", "IS529N-L07C", "C04_AFGHAN_MINERALS"),
    ("LEC_RES_8/ict/", "IS529N-L08C", "C02_ICT_ITES"),
    ("LEC_RES_8/ictsector/", "IS529N-L08C", "C02_ICT_ITES"),
    ("LEC_RES_8/resources/apparel_lanka/", "IS529N-L08B", "B01_GARMENT_GROWTH"),
    ("LEC_RES_8/resources/industrial_region/", "IS529N-L08A", "A01_INDUSTRIAL_LOCATION"),
    ("LEC_RES_10/resources/federalism/", "IS529N-L10B", "B01_FEDERALISM_THEORY"),
    ("LEC_RES_10/resources/kadeny/", "IS529N-L10B", "B02_INDIA_PAKISTAN_FEDERALISM"),
    ("LEC_RES_10/resources/minghi/", "IS529N-L10A", "A01_FUNCTIONAL_STATE"),
    ("LEC_RES_10/scwatzberg/", "IS529N-L10A", "A04_STATE_FORMATION"),
    ("LEC_RES_11/resources/bdeshborder/", "IS529N-L11A", "A02_BENGAL_ENCLAVES"),
    ("LEC_RES_11/resources/durand/", "IS529N-L11B", "B02_DURAND_HISTORY"),
    ("LEC_RES_12/resources/forportal_indus/", "IS529N-L12A", "A03_INDUS_TREATY_HISTORY"),
    ("LEC_RES_12/resources/iwt/", "IS529N-L12A", "A03_INDUS_TREATY_HISTORY"),
    ("LEC_RES_12/resources/nepal/", "IS529N-L12B", "B01_INDIA_NEPAL_WATER_RELATIONS"),
    ("LEC_RES_12/nepal/", "IS529N-L12B", "B01_INDIA_NEPAL_WATER_RELATIONS"),
)

EXACT_FILE_RULES = {
    "Other/FSI-2023-DOWNLOAD.xlsx": (
        "IS529N-L01A", "A04_REGIONAL_POLITICAL_ECONOMY"
    ),
    "Other/otherstuff/readings/sasia_buzan.pdf": (
        "IS529N-L13", "A02_RSCT"
    ),
    "Other/otherstuff/readings/Borderlines and Borderlands_1n2.pdf": (
        "IS529N-L11A", "A01_BORDER_THEORY"
    ),
    "Other/otherstuff/readings/changed_report_2015_ch1_2.pdf": (
        "IS529N-L02A", "A02_DEMOGRAPHY_HEALTH"
    ),
    "Other/otherstuff/readings/Agriculture and the WTO Creating a Trading System for Development Ingco-Nash.pdf": (
        "IS529N-L03A", "A02_AGRICULTURAL_TRADE"
    ),
    "LEC_RES_3/A03_labour_productivity/API_SL.AGR.EMPL.ZS_DS2_en_csv_v2_4570945.zip": (
        "IS529N-L03A", "A03_LABOUR_PRODUCTIVITY"
    ),
}

SUPPORT_EXTENSIONS = {
    ".aux", ".log", ".out", ".toc", ".nav", ".snm", ".synctex.gz",
    ".xml", ".iml", ".directory", ".gitignore",
}
WORKBENCH_EXTENSIONS = {".odp", ".ppt", ".pptx"}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".7z"}


def extension(path: Path) -> str:
    lower = path.name.casefold()
    if lower.endswith(".synctex.gz"):
        return ".synctex.gz"
    return path.suffix.casefold() or "[none]"


def taxonomy_topics(path: Path) -> set[tuple[str, str]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        (part["id"], topic["code"])
        for part in payload["lecture_parts"]
        for topic in part["topics"]
    }


def lecture_container(relative: str) -> str:
    first = PurePosixPath(relative).parts[0]
    match = re.fullmatch(r"LEC_RES_(\d+)", first, flags=re.IGNORECASE)
    return f"LEC_RES_{int(match.group(1))}" if match else "COURSE_WIDE"


def current_bucket(relative: str) -> str:
    parts = PurePosixPath(relative).parts
    if len(parts) >= 2:
        return PurePosixPath(*parts[:2]).as_posix()
    return parts[0] if parts else ""


def classify(relative: str, ext: str) -> dict[str, str]:
    if relative.startswith("NOTES/"):
        return {
            "part": "", "topic": "", "confidence": "PROVISIONAL",
            "status": "AI_NOTE_REVIEW",
            "basis": "Course-wide NOTES holding area",
        }
    if ext in WORKBENCH_EXTENSIONS:
        return {
            "part": "", "topic": "", "confidence": "PROVISIONAL",
            "status": "WORKBENCH_REVIEW",
            "basis": "Presentation-editing format inside Raw Material",
        }
    if ext in SUPPORT_EXTENSIONS or any(
        part.startswith(".") for part in PurePosixPath(relative).parts
    ):
        return {
            "part": "", "topic": "", "confidence": "STRONG",
            "status": "SUPPORTING_ASSET",
            "basis": "Build, IDE or hidden support file",
        }
    exact = EXACT_FILE_RULES.get(relative)
    if exact:
        return {
            "part": exact[0], "topic": exact[1], "confidence": "STRONG",
            "status": "ASSIGNED_PROVISIONAL",
            "basis": "Filename and presentation topic agree",
        }
    for prefix, part, topic in PREFIX_RULES:
        if relative.startswith(prefix):
            return {
                "part": part, "topic": topic, "confidence": "STRONG",
                "status": "ASSIGNED_PROVISIONAL",
                "basis": f"Existing named folder agrees with {topic}",
            }
    if ext in ARCHIVE_EXTENSIONS:
        return {
            "part": "", "topic": "", "confidence": "PROVISIONAL",
            "status": "ARCHIVE_REVIEW",
            "basis": "Archive requires inspection before topical assignment",
        }
    return {
        "part": "", "topic": "", "confidence": "UNASSIGNED",
        "status": "REVIEW_UNASSIGNED",
        "basis": "No safe assignment from path metadata alone",
    }


def proposed_destination(result: dict[str, str], filename: str) -> str:
    if result["status"] != "ASSIGNED_PROVISIONAL":
        return ""
    part = result["part"].split("-")[-1]
    lecture_match = re.match(r"L0*(\d+)", part)
    if not lecture_match:
        return ""
    lecture = int(lecture_match.group(1))
    folder = result["topic"].casefold()
    return f"FOUNDATIONAL_RESOURCE://LEC_RES_{lecture}/{folder}/{filename}"


def build(root: Path, taxonomy: Path, output: Path) -> dict[str, object]:
    valid_topics = taxonomy_topics(taxonomy)
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: str(item).casefold()):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        ext = extension(path)
        result = classify(relative, ext)
        if result["part"] and (result["part"], result["topic"]) not in valid_topics:
            raise ValueError(
                f"Unknown taxonomy assignment: {result['part']} {result['topic']}"
            )
        rows.append({
            "current_symbolic_locator": f"FOUNDATIONAL_RESOURCE://{relative}",
            "lecture_container": lecture_container(relative),
            "current_bucket": current_bucket(relative),
            "file_name": path.name,
            "extension": ext,
            "bytes": path.stat().st_size,
            "proposed_lecture_part": result["part"],
            "proposed_topic_code": result["topic"],
            "assignment_confidence": result["confidence"],
            "decision_status": result["status"],
            "assignment_basis": result["basis"],
            "proposed_symbolic_locator": proposed_destination(result, path.name),
        })

    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else []
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    statuses = Counter(row["decision_status"] for row in rows)
    return {
        "output": str(output),
        "physical_files": len(rows),
        "statuses": dict(sorted(statuses.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    print(json.dumps(
        build(
            arguments.root.resolve(),
            arguments.taxonomy.resolve(),
            arguments.output.resolve(),
        ),
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
