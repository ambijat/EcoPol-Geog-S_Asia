from __future__ import annotations

import json
import re
import sqlite3
import subprocess
from fnmatch import fnmatch
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


LIFECYCLE = (
    "UNMAPPED", "RESOURCES_MAPPED", "NOTES_PREPARED", "SLIDE_PLAN_APPROVED",
    "DECK_DRAFTED", "VERIFIED", "INSTRUCTOR_APPROVED", "TAUGHT",
    "POST_CLASS_RECORDED", "ARCHIVED",
)
HISTORICAL_STATUSES = (
    "RETAIN", "REVISE", "REPLACE", "MOVE_TO_PART_A", "MOVE_TO_PART_B",
    "MERGE", "SPLIT", "VERIFY", "ARCHIVE", "SUPPLEMENTARY_PART_C",
)
TEACHING_FUNCTIONS = (
    "DEFINITION", "CONCEPT", "CAUSAL_ARGUMENT", "HISTORICAL_BACKGROUND",
    "COMPARISON", "MAP_INTERPRETATION", "DATA_INTERPRETATION", "CASE_STUDY",
    "DISCUSSION_PROMPT", "SYNTHESIS",
)
NOTE_ORIGINS = (
    "INSTRUCTOR_AUTHORED", "HISTORICALLY_EXTRACTED", "EXTERNALLY_PASTED_AI_DRAFT",
    "VERIFIED_EXTERNAL_MATERIAL", "HISTORICAL_NOTE", "APPROVED_FINAL_NOTE",
)
SLIDE_ACTIONS = (
    "ADD", "RETAIN", "REVISE", "REPLACE", "MERGE", "SPLIT", "MOVE", "DELETE",
    "APPROVE", "RETURN_TO_NOTES",
)
VISUAL_TYPES = (
    "TITLE", "SECTION", "CONCEPT", "TEXT_AND_IMAGE", "MAP", "DATA_TABLE",
    "CHART", "CHART_PLACEHOLDER", "COMPARISON", "DISCUSSION", "SYNTHESIS", "REFERENCES",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def as_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def json_list(value: str) -> str:
    return json.dumps(as_list(value), ensure_ascii=False)


def validate_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or value.startswith("~"):
        raise ValueError("path must be repository-relative and may not traverse upward")
    if re.match(r"^[A-Za-z]:", value):
        raise ValueError("Windows absolute paths are not allowed")
    return path.as_posix()


def dashboard(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """SELECT lp.*,
        MAX(CASE WHEN p.part='A' THEN p.title END) AS part_a_title,
        MAX(CASE WHEN p.part='A' THEN p.lifecycle_status END) AS part_a_status,
        MAX(CASE WHEN p.part='A' THEN p.title_status END) AS part_a_title_status,
        MAX(CASE WHEN p.part='A' THEN p.title_confirmed END) AS part_a_title_confirmed,
        MAX(CASE WHEN p.part='B' THEN p.title END) AS part_b_title,
        MAX(CASE WHEN p.part='B' THEN p.lifecycle_status END) AS part_b_status,
        MAX(CASE WHEN p.part='B' THEN p.title_status END) AS part_b_title_status,
        MAX(CASE WHEN p.part='B' THEN p.title_confirmed END) AS part_b_title_confirmed,
        COUNT(DISTINCT hd.id) AS historical_decks,
        COUNT(DISTINCT ra.id) AS mapped_resources,
        COUNT(DISTINCT rn.id) AS revised_notes,
        COUNT(DISTINCT sp.id) AS planned_slides,
        COUNT(DISTINCT d.id) AS deliverables,
        COUNT(DISTINCT dle.id) AS draft_events,
        COUNT(DISTINCT te.id) AS title_evidence_count,
        MAX(vr.status) AS verification_status,
        COUNT(DISTINCT CASE WHEN p.approval_status='INSTRUCTOR_APPROVED' THEN p.id END) AS approved_parts,
        COUNT(DISTINCT CASE WHEN p.class_status!='NOT_CONDUCTED' THEN p.id END) AS conducted_parts
        FROM lecture_pairs lp
        JOIN lecture_parts p ON p.lecture_pair_id=lp.id
        LEFT JOIN historical_decks hd ON hd.lecture_pair_id=lp.id
        LEFT JOIN resource_assignments ra ON ra.lecture_pair_id=lp.id AND ra.part!='UNCLASSIFIED'
        LEFT JOIN revised_notes rn ON rn.lecture_pair_id=lp.id
        LEFT JOIN slide_plan_entries sp ON sp.lecture_pair_id=lp.id
        LEFT JOIN deliverables d ON d.lecture_pair_id=lp.id
        LEFT JOIN draft_ledger_events dle ON dle.lecture_pair_id=lp.id
        LEFT JOIN title_evidence te ON te.lecture_pair_id=lp.id
        LEFT JOIN verification_records vr ON vr.lecture_pair_id=lp.id
        GROUP BY lp.id ORDER BY lp.lecture_number"""
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["slide_plan_status"] = "PLANNED" if item["planned_slides"] else "NOT_STARTED"
        item["deliverable_status"] = "GENERATED" if item["deliverables"] else "NOT_STARTED"
        item["verification_status"] = item["verification_status"] or "NOT_STARTED"
        item["approval_summary"] = "INSTRUCTOR_APPROVED" if item["approved_parts"] == 2 else "NOT_APPROVED"
        item["class_conduct_status"] = "TAUGHT" if item["conducted_parts"] == 2 else "NOT_CONDUCTED"
        item["ledger_event_status"] = "DRAFT_PREPARED" if item["draft_events"] else "NONE"
        item["needs_title_confirmation"] = not (
            item["title_confirmed"] and item["part_a_title_confirmed"] and item["part_b_title_confirmed"]
        )
        result.append(item)
    return result


def lecture_context(connection: sqlite3.Connection, number: int) -> dict[str, Any]:
    pair = connection.execute(
        "SELECT * FROM lecture_pairs WHERE lecture_number=?", (number,)
    ).fetchone()
    if pair is None:
        raise KeyError(number)
    pair_id = pair["id"]
    resources = [dict(row) for row in connection.execute(
        """SELECT r.*, ra.part AS assignment FROM resources r
        JOIN resource_assignments ra ON ra.resource_id=r.id
        WHERE ra.lecture_pair_id=? ORDER BY r.resource_id""", (pair_id,)
    )]
    for resource in resources:
        token = f'%"{resource["resource_id"]}"%'
        resource["notes_linked"] = connection.execute(
            "SELECT COUNT(*) FROM revised_notes WHERE lecture_pair_id=? AND source_ids LIKE ?",
            (pair_id, token),
        ).fetchone()[0]
        resource["slides_linked"] = connection.execute(
            "SELECT COUNT(*) FROM slide_plan_entries WHERE lecture_pair_id=? AND resource_ids LIKE ?",
            (pair_id, token),
        ).fetchone()[0]
    return {
        "pair": dict(pair),
        "parts": [dict(row) for row in connection.execute(
            "SELECT * FROM lecture_parts WHERE lecture_pair_id=? ORDER BY part", (pair_id,)
        )],
        "resources": resources,
        "decks": [dict(row) for row in connection.execute(
            "SELECT * FROM historical_decks WHERE lecture_pair_id=? ORDER BY deck_id", (pair_id,)
        )],
        "slides": [dict(row) for row in connection.execute(
            """SELECT hs.*, hd.deck_id FROM historical_slides hs
            JOIN historical_decks hd ON hd.id=hs.deck_id WHERE hd.lecture_pair_id=?
            ORDER BY hd.deck_id, hs.historical_slide_number""", (pair_id,)
        )],
        "notes": [dict(row) for row in connection.execute(
            "SELECT * FROM revised_notes WHERE lecture_pair_id=? ORDER BY id", (pair_id,)
        )],
        "slide_plan": [dict(row) for row in connection.execute(
            "SELECT * FROM slide_plan_entries WHERE lecture_pair_id=? ORDER BY part, sequence", (pair_id,)
        )],
        "deliverables": [dict(row) for row in connection.execute(
            "SELECT * FROM deliverables WHERE lecture_pair_id=? ORDER BY created_at DESC", (pair_id,)
        )],
        "sessions": [dict(row) for row in connection.execute(
            "SELECT * FROM class_session_records WHERE lecture_pair_id=? ORDER BY part", (pair_id,)
        )],
        "draft_events": [dict(row) for row in connection.execute(
            "SELECT * FROM draft_ledger_events WHERE lecture_pair_id=? ORDER BY created_at DESC", (pair_id,)
        )],
        "title_evidence": [dict(row) for row in connection.execute(
            "SELECT * FROM title_evidence WHERE lecture_pair_id=? ORDER BY target_identifier,source_filename", (pair_id,)
        )],
    }


def update_pair(connection: sqlite3.Connection, number: int, values: dict[str, str]) -> None:
    allowed = (
        "weekly_central_question", "weekly_argument",
        "relationship_between_parts", "concepts_introduced_in_a",
        "applications_developed_in_b", "shared_resources", "duplication_warnings",
        "unresolved_gaps", "assessment_alignment", "instructor_status",
    )
    assignments = ",".join(f"{field}=?" for field in allowed)
    connection.execute(
        f"UPDATE lecture_pairs SET {assignments} WHERE lecture_number=?",
        tuple(values.get(field, "") for field in allowed) + (number,),
    )
    connection.commit()


def assign_resource(
    connection: sqlite3.Connection, number: int, resource_pk: int, part: str,
    classification: str, centrality: str,
) -> None:
    if part not in {"SHARED", "A", "B", "BOTH", "SUPPLEMENTARY", "UNCLASSIFIED", "ARCHIVE_ONLY", "EXCLUDED"}:
        raise ValueError("invalid part assignment")
    pair_id = connection.execute(
        "SELECT id FROM lecture_pairs WHERE lecture_number=?", (number,)
    ).fetchone()[0]
    connection.execute(
        "UPDATE resource_assignments SET part=? WHERE resource_id=? AND lecture_pair_id=?",
        (part, resource_pk, pair_id),
    )
    connection.execute(
        "UPDATE resources SET classification=?, centrality=?, excluded=? WHERE id=?",
        (classification, centrality, int(classification == "EXCLUDE"), resource_pk),
    )
    if part != "UNCLASSIFIED":
        connection.execute(
            "UPDATE lecture_pairs SET lifecycle_status='RESOURCES_MAPPED' WHERE id=? AND lifecycle_status='UNMAPPED'",
            (pair_id,),
        )
    connection.commit()


def add_historical_slide(connection: sqlite3.Connection, deck_pk: int, values: dict[str, Any]) -> str:
    deck = connection.execute("SELECT deck_id FROM historical_decks WHERE id=?", (deck_pk,)).fetchone()
    if deck is None:
        raise KeyError(deck_pk)
    slide_number = int(values["historical_slide_number"])
    slide_id = f"{deck['deck_id']}-S{slide_number:03d}"
    connection.execute(
        """INSERT INTO historical_slides(
        historical_slide_id,deck_id,historical_slide_number,title,visual_preview,text_extract,current_status,reason,
        factual_update_required,visual_update_required,target_part,target_sequence,
        linked_resource_ids,linked_note_ids,instructor_comment)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            slide_id, deck_pk, slide_number, values.get("title", ""),
            validate_relative_path(values["visual_preview"]) if values.get("visual_preview") else "",
            values.get("text_extract", ""),
            values.get("current_status", "VERIFY"), values.get("reason", ""),
            int(bool(values.get("factual_update_required"))),
            int(bool(values.get("visual_update_required"))), values.get("target_part", ""),
            int(values["target_sequence"]) if values.get("target_sequence") else None,
            json_list(values.get("linked_resource_ids", "")),
            json_list(values.get("linked_note_ids", "")), values.get("instructor_comment", ""),
        ),
    )
    connection.commit()
    return slide_id


def update_historical_slide_status(connection: sqlite3.Connection, slide_pk: int, status: str) -> None:
    if status not in HISTORICAL_STATUSES:
        raise ValueError("invalid historical-slide status")
    connection.execute("UPDATE historical_slides SET current_status=? WHERE id=?", (status, slide_pk))
    connection.commit()


def record_historical_derivative(
    connection: sqlite3.Connection, deck_pk: int, derivative_type: str,
    relative_path: str, historical_slide_pk: int | None = None,
) -> None:
    if derivative_type not in {"PREVIEW", "TEXT_EXTRACT"}:
        raise ValueError("invalid historical derivative type")
    deck = connection.execute(
        "SELECT source_locator,content_sha256 FROM historical_decks WHERE id=?", (deck_pk,)
    ).fetchone()
    if deck is None:
        raise KeyError(deck_pk)
    connection.execute(
        """INSERT INTO historical_derivatives(deck_id,historical_slide_id,derivative_type,
        relative_path,source_locator,source_sha256,generated_at) VALUES (?,?,?,?,?,?,?)""",
        (deck_pk, historical_slide_pk, derivative_type, validate_relative_path(relative_path),
         deck["source_locator"], deck["content_sha256"], utc_now()),
    )
    connection.commit()


def add_note(connection: sqlite3.Connection, number: int, values: dict[str, str]) -> str:
    if values["teaching_function"] not in TEACHING_FUNCTIONS:
        raise ValueError("invalid teaching function")
    if values["note_origin"] not in NOTE_ORIGINS:
        raise ValueError("invalid note origin")
    pair_id = connection.execute(
        "SELECT id FROM lecture_pairs WHERE lecture_number=?", (number,)
    ).fetchone()[0]
    next_id = connection.execute("SELECT COUNT(*)+1 FROM revised_notes WHERE lecture_pair_id=?", (pair_id,)).fetchone()[0]
    note_id = f"IS529N-L{number:02d}-N{next_id:03d}"
    cursor = connection.execute(
        """INSERT INTO revised_notes(note_id,lecture_pair_id,part,topic,claim,explanation,
        evidence,source_ids,date_relevance,confidence,teaching_function,suggested_slide,
        created_by,note_origin,instructor_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            note_id, pair_id, values["part"], values["topic"], values["claim"],
            values.get("explanation", ""), values.get("evidence", ""),
            json_list(values.get("source_ids", "")), values.get("date_relevance", ""),
            values.get("confidence", "UNVERIFIED"), values["teaching_function"],
            values.get("suggested_slide", ""), values["created_by"], values["note_origin"],
            values.get("instructor_status", "NOT_REVIEWED"),
        ),
    )
    for resource_id in as_list(values.get("source_ids", "")):
        resource = connection.execute(
            "SELECT id FROM resources WHERE resource_id=?", (resource_id,)
        ).fetchone()
        if resource is not None:
            connection.execute(
                """INSERT OR IGNORE INTO note_source_links(
                note_id,resource_id,link_role,created_at) VALUES (?,?,?,?)""",
                (cursor.lastrowid, resource["id"], "EVIDENCE_SOURCE", utc_now()),
            )
    connection.execute(
        "UPDATE lecture_pairs SET lifecycle_status='NOTES_PREPARED' WHERE id=? AND lifecycle_status IN ('UNMAPPED','RESOURCES_MAPPED')",
        (pair_id,),
    )
    connection.commit()
    return note_id


def add_slide_plan(connection: sqlite3.Connection, number: int, values: dict[str, str]) -> str:
    if values["action"] not in SLIDE_ACTIONS or values["visual_type"] not in VISUAL_TYPES:
        raise ValueError("invalid slide action or visual type")
    if values.get("visual_asset_path"):
        validate_relative_path(values["visual_asset_path"])
    pair_id = connection.execute(
        "SELECT id FROM lecture_pairs WHERE lecture_number=?", (number,)
    ).fetchone()[0]
    part = values["part"]
    sequence = int(values["sequence"])
    slide_id = f"IS529N-L{number:02d}-{part}-S{sequence:03d}"
    cursor = connection.execute(
        """INSERT INTO slide_plan_entries(slide_id,lecture_pair_id,part,sequence,title,purpose,
        action,historical_slide_sources,note_ids,resource_ids,visual_type,visual_asset_path,
        speaker_note,citation_footer,verification_status,approval_status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            slide_id, pair_id, part, sequence, values["title"], values["purpose"],
            values["action"], json_list(values.get("historical_slide_sources", "")),
            json_list(values.get("note_ids", "")), json_list(values.get("resource_ids", "")),
            values["visual_type"], values.get("visual_asset_path", ""),
            values.get("speaker_note", ""), values.get("citation_footer", ""),
            values.get("verification_status", "NOT_STARTED"),
            values.get("approval_status", "NOT_REVIEWED"),
        ),
    )
    for resource_id in as_list(values.get("resource_ids", "")):
        resource = connection.execute(
            "SELECT id FROM resources WHERE resource_id=?", (resource_id,)
        ).fetchone()
        if resource is not None:
            connection.execute(
                """INSERT OR IGNORE INTO slide_source_links(
                slide_plan_id,resource_id,link_role,created_at) VALUES (?,?,?,?)""",
                (cursor.lastrowid, resource["id"], "CITATION_SOURCE", utc_now()),
            )
    connection.commit()
    return slide_id


def update_slide_decision(
    connection: sqlite3.Connection, slide_pk: int, decision: str, comment: str = ""
) -> None:
    mapping = {
        "ACCEPT": ("APPROVE", "INSTRUCTOR_APPROVED"),
        "REVISE": ("REVISE", "RETURNED"),
        "RETURN_TO_NOTES": ("RETURN_TO_NOTES", "RETURNED"),
        "REPLACE_VISUAL": ("REPLACE", "RETURNED"),
        "MOVE": ("MOVE", "NOT_REVIEWED"),
        "REMOVE": ("DELETE", "NOT_REVIEWED"),
    }
    if decision not in mapping:
        raise ValueError("invalid instructor slide decision")
    action, approval = mapping[decision]
    connection.execute(
        "UPDATE slide_plan_entries SET action=?, approval_status=? WHERE id=?",
        (action, approval, slide_pk),
    )
    slide = connection.execute(
        "SELECT lecture_pair_id FROM slide_plan_entries WHERE id=?", (slide_pk,)
    ).fetchone()
    if slide is None:
        raise KeyError(slide_pk)
    connection.execute(
        """INSERT INTO approval_decisions(lecture_pair_id,object_type,object_id,
        decision,comment,decided_by,decided_at) VALUES (?,'SLIDE_PLAN_ENTRY',?,?,?,?,?)""",
        (slide["lecture_pair_id"], slide_pk, decision, comment, "INSTRUCTOR", utc_now()),
    )
    connection.commit()


def save_class_record(connection: sqlite3.Connection, number: int, values: dict[str, str]) -> str:
    pair_id = connection.execute(
        "SELECT id FROM lecture_pairs WHERE lecture_number=?", (number,)
    ).fetchone()[0]
    part = values["part"]
    session_id = f"IS529N-L{number:02d}-{part}-SESSION"
    fields = (
        "scheduled_date", "actual_date", "slides_planned", "slides_covered", "slides_omitted",
        "oral_material_added", "student_questions", "conceptual_difficulties", "time_management",
        "topics_deferred", "follow_up_actions", "impact_on_next_session",
        "instructor_validation_status",
    )
    connection.execute(
        f"""INSERT INTO class_session_records(session_id,lecture_pair_id,part,{','.join(fields)})
        VALUES (?,?,?,{','.join('?' for _ in fields)})
        ON CONFLICT(lecture_pair_id,part) DO UPDATE SET
        {','.join(f'{field}=excluded.{field}' for field in fields)}""",
        (session_id, pair_id, part) + tuple(values.get(field, "") for field in fields),
    )
    if values.get("actual_date"):
        lifecycle = (
            "POST_CLASS_RECORDED"
            if values.get("instructor_validation_status") == "INSTRUCTOR_VALIDATED"
            else "TAUGHT"
        )
        connection.execute(
            "UPDATE lecture_parts SET class_status='TAUGHT', lifecycle_status=? WHERE lecture_pair_id=? AND part=?",
            (lifecycle, pair_id, part),
        )
    connection.commit()
    return session_id


def set_part_approval(connection: sqlite3.Connection, number: int, part: str) -> None:
    pair_id = connection.execute(
        "SELECT id FROM lecture_pairs WHERE lecture_number=?", (number,)
    ).fetchone()[0]
    outstanding = connection.execute(
        """SELECT COUNT(*) FROM slide_plan_entries WHERE lecture_pair_id=? AND part=?
        AND action!='DELETE' AND (verification_status!='VERIFIED' OR approval_status!='INSTRUCTOR_APPROVED')""",
        (pair_id, part),
    ).fetchone()[0]
    planned = connection.execute(
        "SELECT COUNT(*) FROM slide_plan_entries WHERE lecture_pair_id=? AND part=? AND action!='DELETE'",
        (pair_id, part),
    ).fetchone()[0]
    if not planned or outstanding:
        raise ValueError("all retained slides must be verified and instructor-approved")
    connection.execute(
        "UPDATE lecture_parts SET fidelity_status='F4', approval_status='INSTRUCTOR_APPROVED', lifecycle_status='INSTRUCTOR_APPROVED' WHERE lecture_pair_id=? AND part=?",
        (pair_id, part),
    )
    part_row = connection.execute(
        "SELECT id FROM lecture_parts WHERE lecture_pair_id=? AND part=?", (pair_id, part)
    ).fetchone()
    connection.execute(
        """INSERT INTO approval_decisions(lecture_pair_id,object_type,object_id,
        decision,comment,decided_by,decided_at) VALUES (?,'LECTURE_PART',?,'APPROVE','',?,?)""",
        (pair_id, part_row["id"], "INSTRUCTOR", utc_now()),
    )
    connection.commit()


def prepare_draft_event(connection: sqlite3.Connection, project_root: Path, number: int, event_type: str) -> Path:
    if event_type not in {"LECTURE_PAIR_APPROVED", "CLASS_SESSION_COMPLETED", "TOPIC_DEFERRED", "LECTURE_RETROSPECTIVE"}:
        raise ValueError("unsupported draft ledger event")
    pair = connection.execute(
        "SELECT * FROM lecture_pairs WHERE lecture_number=?", (number,)
    ).fetchone()
    event_id = f"IS529N-L{number:02d}-{event_type}-DRAFT"
    relative = validate_relative_path(f"course_ledger/drafts/gui/{event_id}.json")
    payload = {
        "event_id": event_id,
        "block_type": event_type,
        "lecture_id": pair["lecture_id"],
        "title": pair["weekly_title"],
        "approval_status": "DRAFT",
        "approved_by": None,
        "canonical_append_authorised": False,
        "created_at": utc_now(),
    }
    path = project_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"draft event already exists: {relative}")
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    connection.execute(
        "INSERT INTO draft_ledger_events(event_id,lecture_pair_id,event_type,relative_path,payload_json,created_at) VALUES (?,?,?,?,?,?)",
        (event_id, pair["id"], event_type, relative, json.dumps(payload), payload["created_at"]),
    )
    connection.commit()
    return path


def classify_public_path(path: str, include: set[str], exclude: set[str]) -> str:
    if any(fnmatch(path, pattern) for pattern in exclude) or path.endswith((".sqlite", ".sqlite3", ".db")):
        return "PRIVATE_LOCAL"
    if path in include:
        return "PUBLIC_CANDIDATE"
    return "REVIEW_REQUIRED"


def save_verification_record(
    connection: sqlite3.Connection, pair_id: int, part: str, report: dict[str, Any]
) -> None:
    unresolved = sum(
        1 for item in report["warnings"] if item["warning"] == "unresolved factual claim"
    )
    connection.execute(
        """INSERT INTO verification_records(lecture_pair_id,part,status,
        unresolved_high_risk_claims,report_json,updated_at) VALUES (?,?,?,?,?,?)
        ON CONFLICT(lecture_pair_id,part) DO UPDATE SET status=excluded.status,
        unresolved_high_risk_claims=excluded.unresolved_high_risk_claims,
        report_json=excluded.report_json,updated_at=excluded.updated_at""",
        (pair_id, part, report["status"], unresolved, json.dumps(report), utc_now()),
    )
    connection.commit()


def git_readiness(project_root: Path, lecture_number: int) -> dict[str, Any]:
    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=project_root, text=True, capture_output=True, check=True
        )
        return result.stdout.strip()
    branch = git("branch", "--show-current")
    latest = git("log", "-1", "--format=%H %s")
    status_lines = git("status", "--porcelain=v1", "--untracked-files=all").splitlines()
    modified = [line[3:] for line in status_lines if line and not line.startswith("??")]
    untracked = [line[3:] for line in status_lines if line.startswith("??")]
    include_path = project_root / "reports/public_include_manifest.txt"
    exclude_path = project_root / "reports/public_exclude_manifest.txt"
    include = set(include_path.read_text().splitlines()) if include_path.exists() else set()
    exclude = {
        line for line in exclude_path.read_text().splitlines()
        if line and not line.startswith("#")
    } if exclude_path.exists() else set()
    prefix = f"course/lectures/lecture_{lecture_number:02d}/"
    selected = sorted(path for path in modified + untracked if path.startswith(prefix))
    return {
        "course_title": "Economic and Political Geography of South Asia",
        "cockpit_identity": "IS529N Semester 2026 Paired Lecture Production Cockpit",
        "lecture_number": lecture_number,
        "branch": branch,
        "latest_commit": latest,
        "modified_files": modified,
        "untracked_files": untracked,
        "validation_state": "RUN_SEPARATELY",
        "selected_lecture_files": [
            {"path": path, "classification": classify_public_path(path, include, exclude)}
            for path in selected
        ],
        "proposed_commit_bundle": selected,
        "automatic_commit_enabled": False,
        "generated_at": utc_now(),
    }
