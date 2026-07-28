from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from course_artifacts.config import CourseArtifactConfig, DEFAULT_CLASS_CONFIG, DEFAULT_RELATIONSHIP_CONFIG
from course_artifacts.database.connection import CourseArtifactDatabase
from course_artifacts.domain.models import ArtifactRegistration
from course_artifacts.services.artifact_service import ArtifactService


class CourseArtifactFilesystemTests(unittest.TestCase):
    def test_registration_never_modifies_source_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "read_only_source.odp"
            source.write_bytes(b"synthetic odp fixture bytes")
            before = (source.read_bytes(), source.stat().st_mtime_ns)
            database = CourseArtifactDatabase(CourseArtifactConfig(
                project_root=root,
                database_path=root / "local_state/database/test.sqlite3",
                class_config_path=DEFAULT_CLASS_CONFIG,
                relationship_config_path=DEFAULT_RELATIONSHIP_CONFIG,
            ))
            database.initialise()
            ArtifactService(database).register(ArtifactRegistration(
                artifact_class_code="PRESENTATION_WORKBENCH",
                title="Read-only ODP fixture",
                physical_path=source,
                symbolic_locator="<PRESENTATION_WORKBENCH>/read_only_source.odp",
            ))
            after = (source.read_bytes(), source.stat().st_mtime_ns)
            self.assertEqual(before, after)
            with database.connection() as connection:
                checksum = connection.execute(
                    "SELECT checksum_sha256 FROM artifacts"
                ).fetchone()[0]
            self.assertEqual(checksum, "")


if __name__ == "__main__":
    unittest.main()
