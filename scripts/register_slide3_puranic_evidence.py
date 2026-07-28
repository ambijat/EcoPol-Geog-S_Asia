#!/usr/bin/env python3
"""Register the governed Slide 3 Puranic corpus and rebuild only its AI packet."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from gui.database import DEFAULT_DATABASE  # noqa: E402
from gui.reinforcement_service import ReinforcementService  # noqa: E402


DERIVATIVE_ROOT = PROJECT_ROOT / "resources/derived/slide3_puranic_geography"
SLIDE_ID = "L01-DECK-005-S003"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def encoded(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()
    manifest = json.loads((DERIVATIVE_ROOT / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))["sources"]
    bundle = json.loads((DERIVATIVE_ROOT / "SLIDE3_EVIDENCE_BUNDLE.json").read_text(encoding="utf-8"))
    source_by_id = {item["canonical_resource_id"]: item for item in manifest}
    connection = sqlite3.connect(args.database, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    outcome: dict[str, object] = {}
    try:
        connection.execute("BEGIN IMMEDIATE")
        cluster = connection.execute(
            """SELECT c.* FROM lecture_knowledge_clusters c JOIN lecture_pairs lp
            ON lp.id=c.lecture_pair_id WHERE c.cluster_id='KC01'
            AND lp.lecture_id='IS529N-L01' AND c.part='A'"""
        ).fetchone()
        slide = connection.execute(
            """SELECT hs.* FROM historical_slides hs JOIN historical_decks hd ON hd.id=hs.deck_id
            WHERE hs.historical_slide_id=? AND hs.historical_slide_number=3
            AND hd.deck_id='L01-DECK-005'""", (SLIDE_ID,),
        ).fetchone()
        if cluster is None or slide is None:
            raise RuntimeError("bounded L01A/KC01/Slide 3 state is missing")
        decision = json.loads(cluster["historical_slide_decisions"] or "{}").get(SLIDE_ID, {})
        if decision.get("decision") != "UPDATE" or not str(decision.get("comment", "")).strip():
            raise RuntimeError("Slide 3 requires an existing UPDATE decision and intervention note")
        pair_id = cluster["lecture_pair_id"]
        resource_pks: dict[str, int] = {}
        created_resources = []
        for source in manifest:
            resource_id = source["canonical_resource_id"]
            row = connection.execute("SELECT * FROM resources WHERE resource_id=?", (resource_id,)).fetchone()
            if row is not None and row["content_sha256"] != source["original_file_sha256"]:
                raise RuntimeError(f"resource hash conflict for {resource_id}")
            if row is None:
                cursor = connection.execute(
                    """INSERT INTO resources(resource_id,title,source_locator,provenance,source_layer,
                    file_type,historical_status,source_quality,factual_currency_status,intended_use,
                    copyright_status,verification_status,content_sha256,classification,centrality,
                    excluded,source_type,classification_confidence,instructor_status,instructor_comment,
                    extraction_status,updated_at,updated_by)
                    VALUES (?,?,?,'User-authorized archival source; original remains authoritative; repository derivatives are non-authoritative.',
                    'RAW_RESOURCE_LAYER','PDF','HISTORICAL_READ_ONLY','SCHOLARLY_MONOGRAPH_EXCERPT',
                    'HISTORICAL_INTERPRETIVE_SOURCE','Lecture 1A Slide 3 evidence only',
                    'REVIEW_REQUIRED','CHECKSUM_VERIFIED_SELECTED_PASSAGES_SOURCE_CHECKED',?,
                    'LECTURE1A_SOURCE','CORE',0,'HISTORICAL_FILE','HIGH','NOT_REVIEWED','',?,?,'Application')""",
                    (resource_id, source["title"], source["source_path"],
                     source["original_file_sha256"], source["derivative_status"], now()),
                )
                resource_pk = int(cursor.lastrowid)
                created_resources.append(resource_id)
            else:
                resource_pk = int(row["id"])
            resource_pks[resource_id] = resource_pk
            connection.execute(
                "INSERT OR IGNORE INTO resource_assignments(resource_id,lecture_pair_id,part) VALUES (?,?,'A')",
                (resource_pk, pair_id),
            )
        target_ids = tuple(source_by_id)
        marks = ",".join("?" for _ in target_ids)
        connection.execute(
            f"DELETE FROM cluster_resource_alignments WHERE cluster_id=? AND source_identifier IN ({marks})",
            (cluster["id"], *target_ids),
        )
        connection.execute(
            "DELETE FROM knowledge_units WHERE cluster_id=? AND knowledge_unit_id LIKE 'S3-EV-%'",
            (cluster["id"],),
        )
        passages_by_source: dict[str, list[dict[str, object]]] = {key: [] for key in target_ids}
        for passage in bundle["passages"]:
            passages_by_source[passage["resource_id"]].append(passage)
        for index, resource_id in enumerate(target_ids, start=1):
            source = source_by_id[resource_id]
            passages = passages_by_source[resource_id]
            derivative = source["derivative_files"][0]["path"]
            pages = sorted({f"printed p. {p['printed_page']} / PDF p. {p['pdf_page']}" for p in passages})
            connection.execute(
                """INSERT INTO cluster_resource_alignments(alignment_id,cluster_id,resource_id,
                source_identifier,resource_group_id,title,author,publication_year,resource_type,
                symbolic_location,main_subjects,cluster_alignment,matching_historical_slides,
                current_use_level,source_quality,currency_status,maps_or_figures,
                relevant_pages_or_sections,recommended_use,verification_status,
                generated_recommendation,instructor_action,instructor_comment,created_at,updated_at)
                VALUES (?,?,?,?,'LEC_RES_1',?,?,?,'PDF',?,?,?,'[3]','PARTIALLY_USED',
                'SCHOLARLY_MONOGRAPH_EXCERPT','HISTORICAL_INTERPRETIVE_SOURCE',?,?,?,
                'SOURCE_CHECKED_SELECTED_PASSAGES_RAW_DERIVATIVE_UNVERIFIED',?,
                'NOT_YET_DECIDED','',?,?)""",
                (f"KC01-S3-PURANA-{index:02d}", cluster["id"], resource_pks[resource_id],
                 resource_id, source["title"], source["author"],
                 "2012" if resource_id.startswith("IS529N-VALDIYA") else "1966",
                 f"<SLIDE3_PURANIC_DERIVATIVES>/{Path(derivative).relative_to('resources/derived/slide3_puranic_geography')}",
                 encoded(sorted({topic for p in passages for topic in p["topics"]})),
                 "DIRECT_SLIDE3_EVIDENCE", "SOURCE_IMAGE_REVIEW_REQUIRED_FOR_FIGURES",
                 "; ".join(pages),
                 "Use only source-checked passages with exact printed/PDF page correspondence; attribute reconstructions.",
                 "Primary Slide 3 corpus; do not promote raw OCR or attributed reconstruction to consensus.",
                 now(), now()),
            )
        for passage in bundle["passages"]:
            resource_id = passage["resource_id"]
            unit_type = "QUOTATION" if passage["text_form"] == "VERBATIM_TRANSCRIPTION" else (
                "LIMITATION" if any(topic in {"interpretive limits", "metaphor", "semantic change", "interpolation"}
                                    for topic in passage["topics"]) else "CLAIM"
            )
            page_ref = f"printed p. {passage['printed_page']} (PDF p. {passage['pdf_page']})"
            connection.execute(
                """INSERT INTO knowledge_units(knowledge_unit_id,cluster_id,resource_id,
                source_identifier,historical_slide_ids,unit_type,unit_text,source_pages,
                source_location,verification_status,alignment_score,temporal_scope,spatial_scope,
                pedagogical_value,candidate_slide_role,instructor_status,origin,created_at,updated_at)
                VALUES (?,?,?,?,'["L01-DECK-005-S003"]',?,?,?,?, 'SOURCE_CHECKED',0.98,
                'PURANIC_TEXTS_AND_MODERN_INTERPRETATION','South Asia and Central Asia',?,?,
                'REVIEW_CANDIDATE','SOURCE_CHECKED_DERIVATIVE',?,?)""",
                (passage["evidence_id"], cluster["id"], resource_pks[resource_id], resource_id,
                 unit_type, passage["passage"], page_ref,
                 f"<SLIDE3_PURANIC_DERIVATIVES>/SLIDE3_EVIDENCE_BUNDLE.json#{passage['evidence_id']}",
                 "Exact page-addressable evidence; original PDF image remains authoritative.",
                 passage["classification"], now(), now()),
            )
        packet_rows = list(connection.execute(
            "SELECT id,packet_id FROM slide_ai_update_packets WHERE cluster_id=? AND historical_slide_id=?",
            (cluster["id"], slide["id"]),
        ))
        packet_pks = [row["id"] for row in packet_rows]
        revisions_deleted = 0
        if packet_pks:
            packet_marks = ",".join("?" for _ in packet_pks)
            revisions_deleted = connection.execute(
                f"DELETE FROM slide_ai_update_revisions WHERE packet_id IN ({packet_marks})", packet_pks
            ).rowcount
        packets_deleted = connection.execute(
            "DELETE FROM slide_ai_update_packets WHERE cluster_id=? AND historical_slide_id=?",
            (cluster["id"], slide["id"]),
        ).rowcount
        packet = ReinforcementService(connection, PROJECT_ROOT).prepare_ai_update_packet(SLIDE_ID)
        if any(connection.execute("PRAGMA foreign_key_check")):
            raise RuntimeError("foreign-key check failed")
        connection.execute("COMMIT")
        outcome = {
            "created_resources": created_resources, "registered_resource_ids": list(target_ids),
            "knowledge_units": len(bundle["passages"]), "alignments": len(target_ids),
            "packets_deleted": packets_deleted, "revisions_deleted": revisions_deleted,
            "packet_id": packet["packet_id"], "packet_state": packet["lifecycle_state"],
            "transaction": "COMMITTED",
        }
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()
    print(json.dumps(outcome, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
