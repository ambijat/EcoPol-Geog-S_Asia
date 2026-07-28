#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "gui/database/is529n_cockpit.sqlite3"
BASE = ROOT / "course/lectures/lecture_01/part_a_tuesday"
STEM = "IS529N_L01A_v0.4_REVISED"
PPTX = BASE / "deck_source" / f"{STEM}.pptx"
PDF = BASE / "classroom_pdf" / f"{STEM}.pdf"
SIDECAR = BASE / "deck_source" / f"{STEM}.metadata.json"
BRIEF = BASE / "deck_source" / f"{STEM}.teaching_brief.md"
VALIDATION = BASE / "deck_source" / f"{STEM}.validation.json"
NOTE = BASE / "student_notes/understanding_region_regionalisation_and_actorness_DRAFT.md"
V03_MANIFEST = ROOT / "reports/qt_gui_acceptance/phase4b_structured_revision/generated_checksums.sha256"
V04_MANIFEST = ROOT / "reports/qt_gui_acceptance/phase4b_structured_revision/amendment_v04_checksums.sha256"
PROPOSITION = (
    "South Asia is strongly constituted as a geographical, ecological, historical and cultural region, "
    "but remains weakly consolidated as an institutional and collective political actor."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_manifest(path: Path) -> bool:
    return subprocess.run(
        ["sha256sum", "-c", str(path.relative_to(ROOT))], cwd=ROOT,
        text=True, capture_output=True,
    ).returncode == 0


def main() -> int:
    passed: list[str] = []

    def require(condition: bool, label: str) -> None:
        if not condition:
            raise AssertionError(label)
        passed.append(label)

    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row

    migrations = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
    require(migrations >= 9, "migration 009 applied")

    cluster = connection.execute(
        "SELECT * FROM historical_resource_clusters WHERE cluster_id='SA-REGION-CLUSTER-001'"
    ).fetchone()
    require(cluster is not None, "South Asia resource cluster recorded")
    require(cluster["symbolic_location"] == "<HISTORICAL_RESOURCE_REPOSITORY>/unsorted/southasia_resources",
            "cluster symbolic location correct")
    require(cluster["resource_count"] == 8 and cluster["type_summary"] == "7 PDF; 1 ODS",
            "cluster count and types correct")
    items = list(connection.execute(
        "SELECT * FROM historical_resource_cluster_items WHERE cluster_id=?", (cluster["id"],)
    ))
    require(len(items) == 8, "all eight cluster items recorded")
    use_states = {row["historical_use"] for row in items}
    for state in ("EXTENSIVELY_USED", "PARTLY_USED_LINEAGE_UNCONFIRMED", "UNUSED_BUT_ALIGNED", "UNUSED"):
        require(state in use_states, f"cluster use category recorded: {state}")
    alignments = {row["alignment"] for row in items}
    require("LOW_ALIGNMENT" in alignments and "OUT_OF_DOMAIN" in alignments,
            "low-alignment and out-of-domain items recorded")
    require("lacks dedicated physical" in cluster["notes"], "cluster evidence gaps recorded")

    expected_dimensions = (
        "geographical contiguity", "common physical structures",
        "ecological and river-system interdependence", "monsoon and climatic unity",
        "historical routes and mobility", "empires and political interaction",
        "colonial territorial consolidation", "Partition and fragmentation",
        "literature and intellectual traditions", "cultural and religious interaction",
        "linguistic continuities", "civilisational connections", "economic interdependence",
        "regional institutions", "shared and contested regional identity", "limited collective actorness",
    )
    dimensions = list(connection.execute("SELECT * FROM south_asia_argument_dimensions ORDER BY dimension_id"))
    require(len(dimensions) == 16, "sixteen South Asia argument dimensions recorded")
    require(tuple(row["dimension"] for row in dimensions) == expected_dimensions, "dimension sequence exact")
    for row in dimensions:
        for field in ("historical_slides", "raw_resources", "website_material", "degree_of_historical_use",
                      "underused_material", "verification_status", "recommended_teaching_role"):
            require(bool(row[field]), f"{row['dimension_id']} has {field}")
        require(json.loads(row["website_material"]) == ["WIKI-REGION-SOUTHASIA:INDEX_ONLY_NO_VERIFIED_CLAIMS"],
                f"{row['dimension_id']} website material is index-only")
    require(any(row["degree_of_historical_use"] == "EXTENSIVE" for row in dimensions),
            "strongly represented dimensions identified")
    require(any(json.loads(row["underused_material"]) for row in dimensions), "underused materials identified")
    require(any("EVIDENCE_REQUIRED" in row["verification_status"] for row in dimensions),
            "dimensions requiring evidence identified")

    inherited = connection.execute(
        "SELECT * FROM slide_plan_entries WHERE slide_id='IS529N-L01-A-S002'"
    ).fetchone()
    snapshot = connection.execute(
        "SELECT * FROM slide_supersession_records WHERE original_slide_id='IS529N-L01-A-S002'"
    ).fetchone()
    require(inherited["revision_status"] == "SUPERSEDED_BY_STRUCTURED_REVISION", "S002 remains preserved and superseded")
    require(snapshot is not None, "S002 preservation snapshot remains present")
    require(hashlib.sha256(snapshot["prior_content_json"].encode()).hexdigest() == snapshot["prior_content_sha256"],
            "S002 preservation snapshot checksum valid")

    rows = list(connection.execute(
        "SELECT * FROM slide_plan_entries WHERE generation_sequence BETWEEN 2 AND 16 ORDER BY generation_sequence"
    ))
    by_id = {row["slide_id"]: row for row in rows}
    a, b, bridge = (by_id[f"IS529N-L01-A-S002{x}"] for x in ("A", "B", "C"))
    require("under two minutes" in a["speaker_note"] and "under two minutes" in b["speaker_note"],
            "conceptual warm-up limited to two short segments")
    five = ("geographical coherence", "functional interdependence", "shared identity",
            "institutionalisation", "regional actorness")
    require(all(term in a["purpose"] for term in five), "five assessment dimensions stated")
    require("Hettne supplies" in a["speaker_note"] and "Schmitt-Egner defines" in b["speaker_note"],
            "corrected theory distinction retained")
    require(bridge["title"] == "In what senses is South Asia a region?", "application bridge title exact")
    eight = ("geographical", "ecological", "historical", "cultural", "economic", "institutional", "political", "actorness")
    require(all(term in bridge["purpose"] for term in eight), "application bridge introduces eight dimensions")
    require(PROPOSITION in bridge["speaker_note"] and "hypothesis to test" in bridge["speaker_note"],
            "working proposition is explicitly provisional")
    substantive = [by_id[f"IS529N-L01-A-S{number:03d}"] for number in range(3, 15)]
    require(len(substantive) == 12, "twelve substantive South Asia slides follow the bridge")
    require(all(json.loads(row["note_ids"]) == ["IS529N-L01-A-N002"] for row in substantive),
            "substantive slides link the South Asia synthesis note")
    require(all(row["approval_status"] == "WORKING_DRAFT" for row in (a, b, bridge, *substantive)),
            "amended slide sequence remains working draft")

    n002 = connection.execute("SELECT * FROM revised_notes WHERE note_id='IS529N-L01-A-N002'").fetchone()
    require(n002 is not None and n002["claim"] == PROPOSITION, "N002 records the exact proposition")
    require(n002["verification_status"] != "VERIFIED" and n002["review_status"] == "REQUIRES_INSTRUCTOR_REVIEW",
            "N002 is provisional and requires review")

    note_text = NOTE.read_text(encoding="utf-8")
    require("status: DRAFT_NOT_FOR_STUDENT_USE" in note_text and "visibility: LOCAL_ONLY" in note_text
            and "published: false" in note_text, "student note remains local, draft and unpublished")
    headings = (
        "Why South Asia is treated as a region", "Physical and ecological coherence",
        "Historical and civilisational interaction", "Cultural and linguistic continuities",
        "Economic and functional interdependence", "Political fragmentation",
        "Weak institutional regionalism", "South Asia's limited regional actorness", "A qualified conclusion",
    )
    require(all(f"## {index}. {heading}" in note_text for index, heading in enumerate(headings, 1)),
            "student note contains the nine required South Asia sections")
    require(PROPOSITION in note_text and "not finally verified" in note_text,
            "student note treats proposition as provisional")

    topic = connection.execute(
        "SELECT * FROM triangulation_topics WHERE triangulation_topic_id='TRI-L01-A-REGION-001'"
    ).fetchone()
    require(topic["status"] == "PARTIAL_CONVERGENCE", "triangulation remains partial")

    bundle = connection.execute("SELECT * FROM deliverable_bundles WHERE version='v0.4'").fetchone()
    require(bundle is not None and bundle["status"] == "REVISED", "v0.4 bundle recorded separately")
    require(bundle["visibility"] == "PRIVATE" and bundle["validation_status"] == "REVIEW_REQUIRED",
            "v0.4 is private and requires review")
    require(bundle["classroom_use_status"] == "NOT_FOR_CLASSROOM_USE" and not bundle["approved"],
            "v0.4 is not approved for classroom use")
    require(bundle["page_count"] == 18 and bundle["thumbnail_count"] == 18, "v0.4 has 18 pages and thumbnails")
    for path in (PPTX, PDF, SIDECAR, BRIEF, VALIDATION):
        require(path.is_file(), f"v0.4 artefact exists: {path.name}")
    require(sha256(PPTX) == bundle["pptx_sha256"] and sha256(PDF) == bundle["pdf_sha256"],
            "v0.4 primary checksums match database")
    validation = json.loads(VALIDATION.read_text())
    require(validation["status"] == "REVIEW_REQUIRED", "deterministic validation remains review-required")
    require(not any(item["severity"] == "ERROR" for item in validation["findings"]), "v0.4 has zero validation errors")

    with zipfile.ZipFile(PPTX) as archive:
        pptx_text = " ".join(archive.read(name).decode(errors="ignore") for name in archive.namelist() if name.endswith(".xml"))
    pdf_text = subprocess.run(["pdftotext", str(PDF), "-"], check=True, text=True, capture_output=True).stdout
    active = " ".join((pptx_text, pdf_text, SIDECAR.read_text(), BRIEF.read_text(), note_text))
    require("territory as actor" not in active.lower(), "unsupported territorial-actorness phrase absent from v0.4")
    require("From Territorial Space to Regional Actorness" in pdf_text, "replacement wording present")
    require(check_manifest(V03_MANIFEST), "all 23 preserved v0.3 artefacts remain unchanged")
    require(check_manifest(V04_MANIFEST), "all 24 v0.4 amendment artefacts match manifest")

    require((ROOT / "resource_registry/resources.jsonl").read_bytes() == b"", "canonical registry remains empty")
    require(sum(1 for _ in (ROOT / "course_ledger/ledger.jsonl").open()) == 9, "ledger remains nine blocks")
    require(sha256(ROOT / "SEMESTER2026_Course_Governance_Preamble.md") ==
            "befdd646dad35b2c3d5eb01f1978907edae10eb4c46e7655356c52d0f418fc67", "preamble unchanged")
    require(sha256(ROOT / "course_ledger/ledger.jsonl") ==
            "b89366916f756f56519c2c9315833a65bd8b673ddef9683be10ea38438347f84", "ledger unchanged")

    print(json.dumps({
        "status": "PASS", "check_count": len(passed), "pptx_sha256": sha256(PPTX),
        "pdf_sha256": sha256(PDF), "validation_warning_count": len(validation["findings"]), "checks": passed,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2), file=sys.stderr)
        raise
