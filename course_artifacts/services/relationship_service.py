from __future__ import annotations

import uuid

from course_artifacts.database.connection import CourseArtifactDatabase, utc_now
from course_artifacts.domain.models import RelationshipRegistration
from course_artifacts.repositories.artifact_repository import ArtifactRepository
from course_artifacts.repositories.relationship_repository import RelationshipRepository


RELATIONSHIP_STATES = (
    "SYSTEM_SUGGESTED", "IMPORTED", "AI_PROPOSED",
    "INSTRUCTOR_CONFIRMED", "INSTRUCTOR_REJECTED",
)


class RelationshipService:
    def __init__(self, database: CourseArtifactDatabase):
        self.database = database
        self.repository = RelationshipRepository(database)
        self.artifacts = ArtifactRepository(database)

    def create(self, registration: RelationshipRegistration) -> int:
        if registration.source_artifact_id == registration.target_artifact_id:
            raise ValueError("An artifact cannot be related to itself")
        self.artifacts.get(registration.source_artifact_id)
        self.artifacts.get(registration.target_artifact_id)
        relationship_type = next(
            (item for item in self.repository.types(False)
             if item["code"] == registration.relationship_type_code),
            None,
        )
        if relationship_type is None:
            raise ValueError(f"Unknown relationship type: {registration.relationship_type_code}")
        if registration.status not in RELATIONSHIP_STATES:
            raise ValueError(f"Invalid relationship status: {registration.status}")
        if registration.directionality not in {"DIRECTED", "UNDIRECTED"}:
            raise ValueError("Directionality must be DIRECTED or UNDIRECTED")
        return self.repository.insert({
            "relationship_id": f"REL-{uuid.uuid4().hex[:12].upper()}",
            "source_artifact_id": registration.source_artifact_id,
            "target_artifact_id": registration.target_artifact_id,
            "relationship_type_id": relationship_type["id"],
            "directionality": registration.directionality,
            "status": registration.status,
            "confidence": registration.confidence,
            "evidence": registration.evidence.strip(),
            "instructor_note": registration.instructor_note.strip(),
            "created_by": registration.created_by,
            "created_at": utc_now(),
        })

    def confirm(self, relationship_pk: int, note: str = "") -> None:
        self.repository.set_status(
            relationship_pk, "INSTRUCTOR_CONFIRMED", "INSTRUCTOR", note
        )

    def reject(self, relationship_pk: int, note: str = "") -> None:
        self.repository.set_status(
            relationship_pk, "INSTRUCTOR_REJECTED", "INSTRUCTOR", note
        )
