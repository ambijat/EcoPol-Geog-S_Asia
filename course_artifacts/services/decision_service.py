from __future__ import annotations

import uuid

from course_artifacts.database.connection import CourseArtifactDatabase, utc_now
from course_artifacts.repositories.decision_repository import DecisionRepository


class DecisionService:
    def __init__(self, database: CourseArtifactDatabase):
        self.repository = DecisionRepository(database)

    def create(
        self, decision_type: str, subject_type: str, subject_id: str,
        summary: str, detail: str = "",
    ) -> int:
        return self.repository.create({
            "decision_id": f"DEC-{uuid.uuid4().hex[:12].upper()}",
            "decision_type": decision_type,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "summary": summary,
            "detail": detail,
            "state": "PENDING",
            "created_at": utc_now(),
        })

    def ensure_fifth_class_decision(self) -> None:
        existing = self.repository.list()
        fifth_decisions = [
            item for item in existing
            if item["decision_type"] == "FIFTH_CLASS_DEFINITION"
        ]
        with self.repository.database.connection() as connection:
            fifth_class = connection.execute(
                "SELECT label,status FROM artifact_classes WHERE code=?",
                ("INSTRUCTOR_DEFINED_CLASS_5",),
            ).fetchone()
        settled = bool(fifth_class and fifth_class["status"] == "ACTIVE")
        if settled:
            note = (
                "Instructor defined the fifth class as Knowledge Maps and "
                "Visualisations: portable visual exports only; live Obsidian "
                "vaults and Neo4j databases remain external."
            )
            if not fifth_decisions:
                decision_pk = self.create(
                    "FIFTH_CLASS_DEFINITION", "ARTIFACT_CLASS",
                    "INSTRUCTOR_DEFINED_CLASS_5",
                    "Define the fifth artifact class",
                    "The class definition was supplied explicitly by the instructor.",
                )
                self.repository.resolve(decision_pk, "ACCEPTED", note)
            else:
                for item in fifth_decisions:
                    if item["state"] == "PENDING":
                        self.repository.resolve(item["id"], "ACCEPTED", note)
            return
        if fifth_decisions:
            return
        self.create(
            "FIFTH_CLASS_DEFINITION", "ARTIFACT_CLASS", "INSTRUCTOR_DEFINED_CLASS_5",
            "Define the fifth artifact class",
            "The label, academic meaning, accepted extensions, and relationship suggestions await instructor definition.",
        )
