from __future__ import annotations

from gui.services import utc_now
from qt_gui.database.connection import DatabaseManager


class ResourceService:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def list_for_lecture(self, number: int):
        with self.database.connection() as connection:
            pair = connection.execute("SELECT id FROM lecture_pairs WHERE lecture_number=?", (number,)).fetchone()
            return [dict(row) for row in connection.execute(
                """SELECT r.*,ra.part AS assignment,
                (SELECT COUNT(*) FROM note_source_links nl WHERE nl.resource_id=r.id) AS linked_note_count,
                (SELECT COUNT(*) FROM slide_source_links sl WHERE sl.resource_id=r.id) AS linked_slide_count
                FROM resources r JOIN resource_assignments ra ON ra.resource_id=r.id
                WHERE ra.lecture_pair_id=? ORDER BY ra.part,r.resource_id""", (pair[0],)
            )]

    def assign(self, number: int, resource_pk: int, part: str, classification: str,
               centrality: str, comment: str = "", actor: str = "Instructor") -> None:
        parts = {"SHARED", "A", "B", "BOTH", "SUPPLEMENTARY", "UNCLASSIFIED", "ARCHIVE_ONLY", "EXCLUDED"}
        classifications = {"CENTRAL", "SUPPORTING", "CONCEPTUAL", "MAP", "DATA", "CASE_STUDY",
                           "HISTORICAL_BACKGROUND", "CLASSROOM_ILLUSTRATION", "VERIFICATION_REQUIRED",
                           "ARCHIVE_ONLY", "EXCLUDE"}
        if part not in parts or classification not in classifications:
            raise ValueError("invalid resource assignment or classification")
        if centrality not in {"CENTRAL", "SUPPORTING"}:
            raise ValueError("invalid resource centrality")
        with self.database.connection() as connection:
            pair = connection.execute("SELECT id FROM lecture_pairs WHERE lecture_number=?", (number,)).fetchone()
            current = connection.execute(
                """SELECT ra.part,r.classification FROM resource_assignments ra JOIN resources r
                ON r.id=ra.resource_id WHERE ra.resource_id=? AND ra.lecture_pair_id=?""",
                (resource_pk, pair[0]),
            ).fetchone()
            if current is None:
                raise KeyError(resource_pk)
            now = utc_now()
            connection.execute(
                "UPDATE resource_assignments SET part=?,assigned_by=?,updated_at=? WHERE resource_id=? AND lecture_pair_id=?",
                (part, actor, now, resource_pk, pair[0]),
            )
            connection.execute(
                """UPDATE resources SET classification=?,centrality=?,excluded=?,instructor_comment=?,
                instructor_status='WORKING_CLASSIFICATION',updated_at=?,updated_by=? WHERE id=?""",
                (classification, centrality, int(part == "EXCLUDED" or classification == "EXCLUDE"),
                 comment, now, actor, resource_pk),
            )
            connection.execute(
                """INSERT INTO resource_classification_history(resource_id,lecture_pair_id,old_part,new_part,
                old_classification,new_classification,changed_by,changed_at,instructor_comment)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (resource_pk, pair[0], current["part"], part, current["classification"],
                 classification, actor, now, comment),
            )
            if part != "UNCLASSIFIED":
                connection.execute(
                    "UPDATE lecture_pairs SET lifecycle_status='RESOURCES_MAPPED' WHERE id=? AND lifecycle_status='UNMAPPED'",
                    (pair[0],),
                )
            connection.commit()

    def detail(self, resource_pk: int) -> dict:
        with self.database.connection() as connection:
            resource = connection.execute(
                """SELECT r.*,ra.part AS assignment FROM resources r JOIN resource_assignments ra
                ON ra.resource_id=r.id WHERE r.id=?""", (resource_pk,)
            ).fetchone()
            if resource is None:
                raise KeyError(resource_pk)
            return {
                "resource": dict(resource),
                "notes": [dict(r) for r in connection.execute(
                    """SELECT rn.note_id,rn.topic FROM revised_notes rn JOIN note_source_links nl
                    ON nl.note_id=rn.id WHERE nl.resource_id=? ORDER BY rn.note_id""", (resource_pk,))],
                "slides": [dict(r) for r in connection.execute(
                    """SELECT sp.slide_id,sp.title FROM slide_plan_entries sp JOIN slide_source_links sl
                    ON sl.slide_plan_id=sp.id WHERE sl.resource_id=? ORDER BY sp.slide_id""", (resource_pk,))],
                "decks": [dict(r) for r in connection.execute(
                    """SELECT DISTINCT hd.deck_id,hd.title FROM historical_decks hd JOIN historical_slides hs
                    ON hs.deck_id=hd.id WHERE hs.linked_resource_ids LIKE ? ORDER BY hd.deck_id""",
                    (f'%"{resource["resource_id"]}"%',))],
                "history": [dict(r) for r in connection.execute(
                    "SELECT * FROM resource_classification_history WHERE resource_id=? ORDER BY changed_at DESC", (resource_pk,))],
            }
