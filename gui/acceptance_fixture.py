"""Build a synthetic, local-only acceptance fixture for the cockpit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from gui.database import initialise
from gui.pptx_service import convert_pdf, generate_pptx, render_pdf_thumbnails, validate_deck_plan
from gui.services import add_note, add_slide_plan, prepare_draft_event


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "gui_acceptance"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path) -> dict[str, object]:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"acceptance output already exists: {output}")
    output.mkdir(parents=True, exist_ok=True)
    database = output / "fixture.sqlite3"
    connection = initialise(database, output / "no-source-census.json")
    pair_id = connection.execute(
        "SELECT id FROM lecture_pairs WHERE lecture_number=1"
    ).fetchone()[0]
    connection.execute(
        """INSERT INTO resources(resource_id,title,source_locator,provenance,source_layer,
        file_type,historical_status,content_sha256,classification,centrality)
        VALUES ('FIXTURE-R001','Synthetic acceptance source','<SYNTHETIC_FIXTURE>/source.txt',
        'Synthetic acceptance evidence; not course content','SYNTHETIC_FIXTURE','.txt',
        'NON_HISTORICAL_SYNTHETIC',?,'CONCEPT','SUPPORTING')""",
        ("f" * 64,),
    )
    resource_pk = connection.execute(
        "SELECT id FROM resources WHERE resource_id='FIXTURE-R001'"
    ).fetchone()[0]
    connection.execute(
        "INSERT INTO resource_assignments(resource_id,lecture_pair_id,part) VALUES (?,?,'A')",
        (resource_pk, pair_id),
    )
    connection.commit()
    add_note(connection, 1, {
        "part": "A", "topic": "Synthetic workflow fixture",
        "claim": "This synthetic note demonstrates provenance wiring and is not course content.",
        "explanation": "Used only for local acceptance of the production workflow.",
        "evidence": "Synthetic fixture record", "source_ids": "FIXTURE-R001",
        "date_relevance": "NOT_APPLICABLE", "confidence": "SYNTHETIC",
        "teaching_function": "CONCEPT", "suggested_slide": "1",
        "created_by": "ACCEPTANCE_FIXTURE", "note_origin": "INSTRUCTOR_AUTHORED",
        "instructor_status": "NOT_REVIEWED",
    })
    add_slide_plan(connection, 1, {
        "part": "A", "sequence": "1", "title": "Synthetic provenance demonstration",
        "purpose": "Exercise structural slide generation without adopting academic content.",
        "action": "ADD", "historical_slide_sources": "",
        "note_ids": "IS529N-L01-N001", "resource_ids": "FIXTURE-R001",
        "visual_type": "CONCEPT", "visual_asset_path": "",
        "speaker_note": "Acceptance fixture only; do not teach as course content.",
        "citation_footer": "FIXTURE-R001 · SYNTHETIC ACCEPTANCE SOURCE",
        "verification_status": "VERIFIED", "approval_status": "NOT_REVIEWED",
    })
    artefact_dir = output / "fixtures"
    result = generate_pptx(connection, PROJECT_ROOT, 1, "A", "DRAFT", artefact_dir)
    pdf = convert_pdf(result["path"], artefact_dir)
    thumbnails = render_pdf_thumbnails(pdf, artefact_dir / "thumbnails")
    draft_event = prepare_draft_event(
        connection, output / "workspace", 1, "LECTURE_RETROSPECTIVE"
    )
    validation = validate_deck_plan(connection, pair_id, "A")
    generated = [result["path"], result["sidecar"], result["teaching_brief"], pdf, *thumbnails, draft_event]
    manifest = {
        "fixture_type": "SYNTHETIC_LOCAL_ACCEPTANCE_EVIDENCE",
        "substantive_course_content": False,
        "historical_source_bytes_accessed": False,
        "canonical_ledger_modified": False,
        "canonical_preamble_modified": False,
        "database": database.relative_to(PROJECT_ROOT).as_posix(),
        "validation": validation,
        "artefacts": [
            {
                "relative_path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in generated
        ],
    }
    manifest_path = output / "acceptance_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    connection.close()
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    manifest = build(arguments.output.resolve())
    print(f"fixture artefacts: {len(manifest['artefacts'])}")
    print(f"validation: {manifest['validation']['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
