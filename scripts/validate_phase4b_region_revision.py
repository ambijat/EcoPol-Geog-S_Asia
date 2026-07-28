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
DB_PATH = ROOT / "gui/database/is529n_cockpit.sqlite3"
DECK_ROOT = ROOT / "course/lectures/lecture_01/part_a_tuesday"
PPTX = DECK_ROOT / "deck_source/IS529N_L01A_v0.3_REVISED.pptx"
PDF = DECK_ROOT / "classroom_pdf/IS529N_L01A_v0.3_REVISED.pdf"
SIDECAR = PPTX.with_suffix(".metadata.json")
BRIEF = PPTX.with_suffix(".teaching_brief.md")
VALIDATION = PPTX.with_suffix(".validation.json")
LOCAL_NOTE = DECK_ROOT / "student_notes/understanding_region_regionalisation_and_actorness_DRAFT.md"
FORBIDDEN = "territory as actor"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    checks: list[str] = []

    def require(condition: bool, label: str) -> None:
        if not condition:
            raise AssertionError(label)
        checks.append(label)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    note = connection.execute(
        "SELECT * FROM revised_notes WHERE note_id='IS529N-L01-A-N001'"
    ).fetchone()
    require(note is not None, "N001 exists")
    note_text = " ".join(str(note[key]) for key in ("claim", "explanation", "evidence"))
    for term in (
        "Hettne", "not an inevitable sequence", "identity", "actorness", "space", "function",
        "scale", "territory", "structure", "programme", "actor", "environment", "action space",
        "action unit", "horizontal", "vertical", "does not prove South Asian unity",
        "To what extent does South Asia possess geographical coherence, functional interdependence, shared identity, institutional structure, and collective actorness?",
    ):
        require(term.lower() in note_text.lower(), f"N001 includes {term}")
    require(note["instructor_status"] == "WORKING_DRAFT", "N001 is WORKING_DRAFT")
    require(note["review_status"] == "REQUIRES_INSTRUCTOR_REVIEW", "N001 requires instructor review")
    require(note["verification_status"] != "VERIFIED", "N001 is not marked verified")

    inherited = connection.execute(
        "SELECT * FROM slide_plan_entries WHERE slide_id='IS529N-L01-A-S002'"
    ).fetchone()
    snapshot = connection.execute(
        "SELECT * FROM slide_supersession_records WHERE original_slide_id='IS529N-L01-A-S002'"
    ).fetchone()
    require(inherited["revision_status"] == "SUPERSEDED_BY_STRUCTURED_REVISION", "S002 supersession marked")
    require(snapshot is not None, "S002 prior content snapshot exists")
    require(sha256_text(snapshot["prior_content_json"]) == snapshot["prior_content_sha256"], "S002 snapshot checksum valid")
    prior = json.loads(snapshot["prior_content_json"])
    for field in (
        "slide_id", "sequence", "title", "purpose", "action", "historical_slide_sources", "note_ids",
        "resource_ids", "visual_type", "visual_asset_path", "speaker_note", "citation_footer",
        "verification_status", "approval_status",
    ):
        require(inherited[field] == prior[field], f"S002 preserves {field}")

    slides = {row["slide_id"]: row for row in connection.execute(
        "SELECT * FROM slide_plan_entries WHERE slide_id IN (?,?,?)",
        ("IS529N-L01-A-S002A", "IS529N-L01-A-S002B", "IS529N-L01-A-S002C"),
    )}
    require(set(slides) == {"IS529N-L01-A-S002A", "IS529N-L01-A-S002B", "IS529N-L01-A-S002C"}, "S002A–S002C exist")
    require(slides["IS529N-L01-A-S002A"]["title"] == "Hettne’s Progression of Regionalisation", "S002A title correct")
    require(slides["IS529N-L01-A-S002B"]["title"] == "Schmitt-Egner’s Regional-System Model", "S002B title correct")
    require(slides["IS529N-L01-A-S002C"]["title"] == "Does South Asia Constitute a Region?", "South Asia bridge title correct")
    require([slides[key]["generation_sequence"] for key in sorted(slides)] == [2, 3, 4], "structured slides render contiguously")
    for slide in slides.values():
        require(slide["verification_status"] == "REQUIRES_INSTRUCTOR_REVIEW", f"{slide['slide_id']} requires review")
        require(slide["approval_status"] == "WORKING_DRAFT", f"{slide['slide_id']} is a working draft")
        require(bool(slide["citation_footer"].strip()), f"{slide['slide_id']} has citation attribution")

    require(LOCAL_NOTE.is_file(), "local student note exists")
    local_text = LOCAL_NOTE.read_text(encoding="utf-8")
    require("status: DRAFT_NOT_FOR_STUDENT_USE" in local_text, "local note status correct")
    require("visibility: LOCAL_ONLY" in local_text and "published: false" in local_text, "local note remains local and unpublished")
    required_headings = (
        "Meaning of a region", "Region as geographical space", "Hettne’s progression of regionalisation",
        "Schmitt-Egner’s regional-system model", "Action space and action unit", "Identity and actorness",
        "Applying the framework to South Asia", "Limits of the framework", "Classroom questions", "Selected references",
    )
    for heading in required_headings:
        require(f"## {required_headings.index(heading) + 1}. {heading}" in local_text, f"local note section: {heading}")
    require("does not establish" in local_text.lower() or "cannot by itself demonstrate" in local_text.lower(),
            "local note avoids asserting South Asian unity")

    topic = connection.execute(
        "SELECT * FROM triangulation_topics WHERE triangulation_topic_id='TRI-L01-A-REGION-001'"
    ).fetchone()
    require(topic["status"] == "PARTIAL_CONVERGENCE", "triangulation remains partial")
    evidence = {row["evidence_layer"]: row for row in connection.execute(
        "SELECT * FROM triangulation_evidence WHERE triangulation_topic_id=?", (topic["id"],)
    )}
    require(evidence["RAW_RESOURCE_LAYER"]["treatment_level"] == 4, "raw source inspected and integrated")
    require(evidence["WEBSITE_LEARNING_LAYER"]["verification_status"] != "VERIFIED", "website explanatory gap persists")
    require("local draft" in evidence["WEBSITE_LEARNING_LAYER"]["notes"].lower(), "website gap records local draft")

    candidates = {row["candidate_id"]: row for row in connection.execute(
        "SELECT * FROM candidate_registry_records WHERE triangulation_topic_id=?", (topic["id"],)
    )}
    require(candidates["REG-CAND-L01A-HIST-001"]["admission_status"] == "ELIGIBLE_FOR_INSTRUCTOR_ADMISSION", "ODP candidate eligible")
    require(candidates["REG-CAND-L01A-HIST-001"]["candidate_role"] == "INHERITED_TEACHING_ARTEFACT", "ODP role correct")
    require(candidates["REG-CAND-L01A-RAW-001"]["candidate_role"] == "SCHOLARLY_CONCEPTUAL_SOURCE", "article role correct")
    require(candidates["REG-CAND-L01A-WEB-001"]["admission_status"] == "INDEX_RECORD_ONLY", "Wikidot is index only")
    require(candidates["REG-CAND-L01A-WEB-001"]["record_function"] == "NOT_A_TOPIC_NOTE", "Wikidot is not a topic note")
    require(not any(row["canonical_registration_performed"] for row in candidates.values()), "no candidate admitted canonically")

    bundle = connection.execute("SELECT * FROM deliverable_bundles WHERE version='v0.3'").fetchone()
    require(bundle is not None and bundle["status"] == "REVISED", "v0.3 separately versioned as REVISED")
    require(bundle["visibility"] == "PRIVATE", "v0.3 is private")
    require(bundle["validation_status"] == "REVIEW_REQUIRED", "v0.3 validation requires review")
    require(bundle["classroom_use_status"] == "NOT_FOR_CLASSROOM_USE" and not bundle["approved"], "v0.3 not for classroom use")
    for artefact in (PPTX, PDF, SIDECAR, BRIEF, VALIDATION):
        require(artefact.is_file(), f"v0.3 artefact exists: {artefact.name}")
    require(len(list((DECK_ROOT / "previews/IS529N_L01A_v0.3_REVISED").glob("slide-*.png"))) == 18,
            "v0.3 has 18 thumbnails")
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
    require(sidecar["visibility"] == "PRIVATE" and sidecar["review_status"] == "REVIEW_REQUIRED", "sidecar governance correct")
    sidecar_ids = [slide["slide_id"] for slide in sidecar["slides"]]
    require("IS529N-L01-A-S002" not in sidecar_ids, "superseded S002 excluded from v0.3")
    require(all(slide_id in sidecar_ids for slide_id in slides), "structured slides included in v0.3")

    with zipfile.ZipFile(PPTX) as archive:
        pptx_text = " ".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in archive.namelist() if name.endswith(".xml")
        )
    pdf_text = subprocess.run(
        ["pdftotext", str(PDF), "-"], check=True, capture_output=True, text=True
    ).stdout
    active_db_text = " ".join(
        " ".join(str(row[key]) for key in ("title", "purpose", "speaker_note", "citation_footer"))
        for row in slides.values()
    ) + " " + note_text
    active_outputs = " ".join((pptx_text, pdf_text, SIDECAR.read_text(), BRIEF.read_text(), local_text, active_db_text))
    require(FORBIDDEN not in active_outputs.lower(), "unsupported territorial-actorness phrase removed from active outputs")
    require("From Territorial Space to Regional Actorness" in pdf_text, "replacement wording present")
    require("not an inevitable" in active_outputs.lower(), "Hettne progression is explicitly non-inevitable")
    require("Territories do not literally act" in pptx_text, "territorial agency correction appears in speaker notes")

    require((ROOT / "resource_registry/resources.jsonl").read_bytes() == b"", "canonical registry remains empty")
    require(sum(1 for _ in (ROOT / "course_ledger/ledger.jsonl").open(encoding="utf-8")) == 9, "ledger remains nine blocks")
    require(sha256(ROOT / "SEMESTER2026_Course_Governance_Preamble.md") ==
            "befdd646dad35b2c3d5eb01f1978907edae10eb4c46e7655356c52d0f418fc67", "preamble unchanged")
    require(sha256(ROOT / "course_ledger/ledger.jsonl") ==
            "b89366916f756f56519c2c9315833a65bd8b673ddef9683be10ea38438347f84", "ledger unchanged")

    print(json.dumps({
        "status": "PASS", "check_count": len(checks), "pptx_sha256": sha256(PPTX),
        "pdf_sha256": sha256(PDF), "checks": checks,
    }, indent=2, ensure_ascii=False))
    return 0


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2), file=sys.stderr)
        raise
