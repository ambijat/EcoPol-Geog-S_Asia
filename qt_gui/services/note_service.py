from __future__ import annotations

import json

from gui.services import NOTE_ORIGINS, TEACHING_FUNCTIONS, add_note, utc_now
from qt_gui.database.connection import DatabaseManager


class NoteService:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def list_for_lecture(self, number: int):
        with self.database.connection() as connection:
            return [dict(row) for row in connection.execute(
                """SELECT rn.* FROM revised_notes rn JOIN lecture_pairs lp
                ON lp.id=rn.lecture_pair_id WHERE lp.lecture_number=? ORDER BY rn.id""", (number,)
            )]

    def create(self, number: int, values: dict[str, str]) -> str:
        with self.database.connection() as connection:
            return add_note(connection, number, values)

    def detail(self, note_pk: int) -> dict:
        with self.database.connection() as connection:
            note = connection.execute("SELECT * FROM revised_notes WHERE id=?", (note_pk,)).fetchone()
            if note is None:
                raise KeyError(note_pk)
            return {
                "note": dict(note),
                "resources": [dict(r) for r in connection.execute(
                    """SELECT r.id,r.resource_id,r.title FROM resources r JOIN note_source_links nl
                    ON nl.resource_id=r.id WHERE nl.note_id=?""", (note_pk,))],
                "historical_slides": [dict(r) for r in connection.execute(
                    """SELECT hs.id,hs.historical_slide_id,hs.title FROM historical_slides hs
                    JOIN note_historical_slide_links nl ON nl.historical_slide_id=hs.id WHERE nl.note_id=?""", (note_pk,))],
            }

    def save(self, note_pk: int, values: dict, actor: str = "Instructor") -> None:
        if values.get("part") not in {"A", "B", "SHARED"}:
            raise ValueError("invalid note part")
        if values.get("teaching_function") not in TEACHING_FUNCTIONS:
            raise ValueError("invalid teaching function")
        if values.get("note_origin") not in NOTE_ORIGINS:
            raise ValueError("invalid note provenance class")
        status = values.get("instructor_status", "WORKING_DRAFT")
        verification = values.get("verification_status", "NOT_YET_VERIFIED")
        source_pks = [int(item) for item in values.get("resource_pks", [])]
        historical_pks = [int(item) for item in values.get("historical_slide_pks", [])]
        origin_declared = bool(values.get("instructor_origin_declared"))
        if verification == "VERIFIED" and not source_pks and not origin_declared:
            raise ValueError("verification requires a source or explicit instructor-origin declaration")
        with self.database.connection() as connection:
            if connection.execute("SELECT id FROM revised_notes WHERE id=?", (note_pk,)).fetchone() is None:
                raise KeyError(note_pk)
            connection.execute(
                """UPDATE revised_notes SET part=?,topic=?,claim=?,explanation=?,evidence=?,date_relevance=?,
                confidence=?,teaching_function=?,suggested_slide=?,note_origin=?,verification_status=?,
                instructor_status=?,instructor_origin_declared=?,updated_at=?,updated_by=? WHERE id=?""",
                (values["part"], values["topic"], values.get("claim", ""), values.get("explanation", ""),
                 values.get("evidence", ""), values.get("date_relevance", ""), values.get("confidence", "UNVERIFIED"),
                 values["teaching_function"], values.get("suggested_slide", ""), values["note_origin"],
                 verification, status, int(origin_declared), utc_now(), actor, note_pk),
            )
            connection.execute("DELETE FROM note_source_links WHERE note_id=?", (note_pk,))
            for resource_pk in source_pks:
                connection.execute(
                    "INSERT INTO note_source_links(note_id,resource_id,link_role,created_at) VALUES (?,?,'EVIDENCE_SOURCE',?)",
                    (note_pk, resource_pk, utc_now()),
                )
            connection.execute("DELETE FROM note_historical_slide_links WHERE note_id=?", (note_pk,))
            for historical_pk in historical_pks:
                connection.execute(
                    "INSERT INTO note_historical_slide_links(note_id,historical_slide_id,created_at) VALUES (?,?,?)",
                    (note_pk, historical_pk, utc_now()),
                )
            connection.execute(
                "UPDATE revised_notes SET source_ids=?,historical_slide_ids=? WHERE id=?",
                (json.dumps([r[0] for r in connection.execute(
                    "SELECT resource_id FROM resources WHERE id IN (%s)" % ",".join("?" * len(source_pks)), source_pks
                )]) if source_pks else "[]",
                 json.dumps([r[0] for r in connection.execute(
                    "SELECT historical_slide_id FROM historical_slides WHERE id IN (%s)" % ",".join("?" * len(historical_pks)), historical_pks
                 )]) if historical_pks else "[]", note_pk),
            )
            connection.commit()

    def duplicate(self, note_pk: int) -> str:
        detail = self.detail(note_pk)
        note = detail["note"]
        return self.create(int(note["note_id"].split("-L")[1][:2]), {
            "part": note["part"], "topic": f'{note["topic"]} (copy)', "claim": note["claim"],
            "explanation": note["explanation"], "evidence": note["evidence"],
            "teaching_function": note["teaching_function"], "created_by": "Instructor",
            "note_origin": note["note_origin"], "instructor_status": "WORKING_DRAFT",
        })

    def link_options(self, number: int) -> dict:
        with self.database.connection() as connection:
            pair = connection.execute("SELECT id FROM lecture_pairs WHERE lecture_number=?", (number,)).fetchone()
            return {
                "resources": [dict(r) for r in connection.execute(
                    """SELECT r.id,r.resource_id,r.title FROM resources r JOIN resource_assignments ra
                    ON ra.resource_id=r.id WHERE ra.lecture_pair_id=? ORDER BY r.resource_id""", (pair[0],))],
                "historical_slides": [dict(r) for r in connection.execute(
                    """SELECT hs.id,hs.historical_slide_id,hs.title FROM historical_slides hs JOIN historical_decks hd
                    ON hd.id=hs.deck_id WHERE hd.lecture_pair_id=? ORDER BY hs.historical_slide_id""", (pair[0],))],
            }
