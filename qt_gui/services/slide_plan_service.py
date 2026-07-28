from __future__ import annotations

import json

from gui.services import SLIDE_ACTIONS, VISUAL_TYPES, add_slide_plan, utc_now
from qt_gui.database.connection import DatabaseManager


class SlidePlanService:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def list_for_part(self, number: int, part: str):
        with self.database.connection() as connection:
            return [dict(row) for row in connection.execute(
                """SELECT sp.* FROM slide_plan_entries sp JOIN lecture_pairs lp
                ON lp.id=sp.lecture_pair_id WHERE lp.lecture_number=? AND sp.part=? ORDER BY sp.sequence""",
                (number, part),
            )]

    def list_for_lecture(self, number: int):
        with self.database.connection() as connection:
            return [dict(row) for row in connection.execute(
                """SELECT sp.* FROM slide_plan_entries sp JOIN lecture_pairs lp
                ON lp.id=sp.lecture_pair_id WHERE lp.lecture_number=? ORDER BY sp.part,sp.sequence""", (number,))]

    def create(self, number: int, values: dict[str, str]) -> str:
        with self.database.connection() as connection:
            return add_slide_plan(connection, number, values)

    def move(self, slide_pk: int, direction: int) -> None:
        if direction not in {-1, 1}:
            raise ValueError("direction must be -1 or 1")
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM slide_plan_entries WHERE id=?", (slide_pk,)).fetchone()
            if row is None:
                raise KeyError(slide_pk)
            other = connection.execute(
                """SELECT * FROM slide_plan_entries WHERE lecture_pair_id=? AND part=? AND sequence=?""",
                (row["lecture_pair_id"], row["part"], row["sequence"] + direction),
            ).fetchone()
            if other is None:
                return
            connection.execute("UPDATE slide_plan_entries SET sequence=-1 WHERE id=?", (row["id"],))
            connection.execute("UPDATE slide_plan_entries SET sequence=? WHERE id=?", (row["sequence"], other["id"]))
            connection.execute("UPDATE slide_plan_entries SET sequence=? WHERE id=?", (other["sequence"], row["id"]))
            connection.commit()

    def detail(self, slide_pk: int) -> dict:
        with self.database.connection() as connection:
            slide = connection.execute("SELECT * FROM slide_plan_entries WHERE id=?", (slide_pk,)).fetchone()
            if slide is None:
                raise KeyError(slide_pk)
            return {
                "slide": dict(slide),
                "resources": [dict(r) for r in connection.execute(
                    """SELECT r.id,r.resource_id,r.title FROM resources r JOIN slide_source_links sl
                    ON sl.resource_id=r.id WHERE sl.slide_plan_id=?""", (slide_pk,))],
                "notes": [dict(r) for r in connection.execute(
                    """SELECT rn.id,rn.note_id,rn.topic FROM revised_notes rn JOIN slide_note_links sn
                    ON sn.note_id=rn.id WHERE sn.slide_plan_id=?""", (slide_pk,))],
                "historical_slides": [dict(r) for r in connection.execute(
                    """SELECT hs.id,hs.historical_slide_id,hs.title FROM historical_slides hs
                    JOIN slide_historical_links sh ON sh.historical_slide_id=hs.id WHERE sh.slide_plan_id=?""", (slide_pk,))],
            }

    def save(self, slide_pk: int, values: dict, actor: str = "Instructor") -> None:
        if values.get("part") not in {"A", "B"}:
            raise ValueError("invalid slide-plan part")
        if values.get("action") not in SLIDE_ACTIONS or values.get("visual_type") not in VISUAL_TYPES:
            raise ValueError("invalid slide action or visual type")
        resource_pks = [int(item) for item in values.get("resource_pks", [])]
        note_pks = [int(item) for item in values.get("note_pks", [])]
        historical_pks = [int(item) for item in values.get("historical_slide_pks", [])]
        with self.database.connection() as connection:
            if connection.execute("SELECT id FROM slide_plan_entries WHERE id=?", (slide_pk,)).fetchone() is None:
                raise KeyError(slide_pk)
            connection.execute(
                """UPDATE slide_plan_entries SET title=?,purpose=?,action=?,visual_type=?,speaker_note=?,
                citation_footer=?,verification_status=?,approval_status=?,updated_at=?,updated_by=? WHERE id=?""",
                (values["title"], values.get("purpose", ""), values["action"], values["visual_type"],
                 values.get("speaker_note", ""), values.get("citation_footer", ""),
                 values.get("verification_status", "NOT_YET_VERIFIED"),
                 values.get("approval_status", "WORKING_DRAFT"), utc_now(), actor, slide_pk),
            )
            for table in ("slide_source_links", "slide_note_links", "slide_historical_links"):
                connection.execute(f"DELETE FROM {table} WHERE slide_plan_id=?", (slide_pk,))
            for resource_pk in resource_pks:
                connection.execute(
                    "INSERT INTO slide_source_links(slide_plan_id,resource_id,link_role,created_at) VALUES (?,?,'CITATION_SOURCE',?)",
                    (slide_pk, resource_pk, utc_now()),
                )
            for note_pk in note_pks:
                connection.execute(
                    "INSERT INTO slide_note_links(slide_plan_id,note_id,created_at) VALUES (?,?,?)",
                    (slide_pk, note_pk, utc_now()),
                )
            for historical_pk in historical_pks:
                connection.execute(
                    "INSERT INTO slide_historical_links(slide_plan_id,historical_slide_id,created_at) VALUES (?,?,?)",
                    (slide_pk, historical_pk, utc_now()),
                )
            def identifiers(table: str, column: str, pks: list[int]) -> list[str]:
                if not pks:
                    return []
                marks = ",".join("?" for _ in pks)
                return [r[0] for r in connection.execute(f"SELECT {column} FROM {table} WHERE id IN ({marks})", pks)]
            connection.execute(
                """UPDATE slide_plan_entries SET resource_ids=?,note_ids=?,historical_slide_sources=? WHERE id=?""",
                (json.dumps(identifiers("resources", "resource_id", resource_pks)),
                 json.dumps(identifiers("revised_notes", "note_id", note_pks)),
                 json.dumps(identifiers("historical_slides", "historical_slide_id", historical_pks)), slide_pk),
            )
            connection.commit()

    def link_options(self, number: int) -> dict:
        with self.database.connection() as connection:
            pair = connection.execute("SELECT id FROM lecture_pairs WHERE lecture_number=?", (number,)).fetchone()
            return {
                "resources": [dict(r) for r in connection.execute(
                    """SELECT r.id,r.resource_id,r.title FROM resources r JOIN resource_assignments ra
                    ON ra.resource_id=r.id WHERE ra.lecture_pair_id=? ORDER BY r.resource_id""", (pair[0],))],
                "notes": [dict(r) for r in connection.execute(
                    "SELECT id,note_id,topic FROM revised_notes WHERE lecture_pair_id=? ORDER BY note_id", (pair[0],))],
                "historical_slides": [dict(r) for r in connection.execute(
                    """SELECT hs.id,hs.historical_slide_id,hs.title FROM historical_slides hs JOIN historical_decks hd
                    ON hd.id=hs.deck_id WHERE hd.lecture_pair_id=? ORDER BY hs.historical_slide_id""", (pair[0],))],
            }
