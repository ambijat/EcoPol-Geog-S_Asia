from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArtifactRegistration:
    artifact_class_code: str
    title: str
    physical_path: Path | None = None
    symbolic_locator: str = ""
    description: str = ""
    provenance: str = ""
    creator_or_origin: str = ""
    source_repository: str = ""
    course_relevance: str = ""
    version_label: str = ""
    notes: str = ""


@dataclass(frozen=True)
class RelationshipRegistration:
    source_artifact_id: int
    target_artifact_id: int
    relationship_type_code: str
    directionality: str = "DIRECTED"
    status: str = "SYSTEM_SUGGESTED"
    confidence: str = "UNASSESSED"
    evidence: str = ""
    instructor_note: str = ""
    created_by: str = "INSTRUCTOR"
