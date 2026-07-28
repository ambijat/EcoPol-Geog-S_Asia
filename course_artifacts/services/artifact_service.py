from __future__ import annotations

import mimetypes
import uuid
from datetime import datetime, timezone

from course_artifacts.database.connection import CourseArtifactDatabase, utc_now
from course_artifacts.domain.models import ArtifactRegistration
from course_artifacts.repositories.artifact_repository import ArtifactRepository
from course_artifacts.repositories.class_repository import ArtifactClassRepository


class ArtifactService:
    def __init__(self, database: CourseArtifactDatabase):
        self.database = database
        self.artifacts = ArtifactRepository(database)
        self.classes = ArtifactClassRepository(database)

    def register(self, registration: ArtifactRegistration) -> int:
        artifact_class = self.classes.get(registration.artifact_class_code)
        title = registration.title.strip()
        if not title:
            raise ValueError("Artifact title is required")
        path = registration.physical_path.resolve() if registration.physical_path else None
        if path is not None and not path.is_file():
            raise FileNotFoundError(path)
        stat = path.stat() if path else None
        now = utc_now()
        values = {
            "artifact_id": f"ART-{uuid.uuid4().hex[:12].upper()}",
            "artifact_class_id": artifact_class["id"],
            "title": title,
            "display_name": title,
            "description": registration.description.strip(),
            "canonical_locator": "",
            "symbolic_locator": registration.symbolic_locator.strip(),
            # Physical roots are machine-local configuration. Artifact records retain
            # only symbolic locators so root changes never rewrite scholarly records.
            "physical_path": "",
            "file_name": path.name if path else "",
            "file_extension": path.suffix.lower() if path else "",
            "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream" if path else "",
            # Retained as an empty compatibility field for the existing database
            # schema. Routine teaching work does not read file contents or hash them.
            "checksum_sha256": "",
            "file_size": stat.st_size if stat else 0,
            "created_time": self._file_time(stat.st_ctime) if stat else "",
            "modified_time": self._file_time(stat.st_mtime) if stat else "",
            "source_repository": registration.source_repository.strip(),
            "provenance": registration.provenance.strip(),
            "creator_or_origin": registration.creator_or_origin.strip(),
            "course_relevance": registration.course_relevance.strip(),
            "access_status": "LOCAL_ONLY",
            "inspection_status": "UNINSPECTED",
            "extraction_status": "NOT_EXTRACTED",
            "review_status": "NOT_REVIEWED",
            "instructor_status": "AWAITING_REVIEW",
            "version_label": registration.version_label.strip(),
            "notes": registration.notes.strip(),
            "created_at": now,
            "updated_at": now,
        }
        artifact_pk = self.artifacts.insert(values)
        if path:
            symbolic_root, relative = self._split_locator(registration.symbolic_locator)
            with self.database.connection() as connection:
                connection.execute(
                    """INSERT INTO artifact_locations(
                    artifact_id,symbolic_root,relative_locator,physical_path,status,checked_at)
                    VALUES (?,?,?,?,?,?)""",
                    (artifact_pk, symbolic_root, relative, "", "AVAILABLE", now),
                )
        return artifact_pk

    def class_counts(self) -> dict[str, dict[str, int]]:
        return self.artifacts.counts()

    def recent(self, limit: int = 8) -> list[dict]:
        return self.artifacts.list()[:limit]

    def browser_safe(self, artifact_pk: int) -> dict:
        artifact = self.artifacts.get(artifact_pk)
        artifact.pop("physical_path", None)
        return artifact

    @staticmethod
    def _split_locator(locator: str) -> tuple[str, str]:
        clean = locator.strip()
        if clean.startswith("<") and ">" in clean:
            root, relative = clean[1:].split(">", 1)
            return root, relative.lstrip("/")
        return "", clean

    @staticmethod
    def _file_time(timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="seconds")
