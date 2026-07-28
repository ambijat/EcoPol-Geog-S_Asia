from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = PROJECT_ROOT / "local_state" / "database" / "course_artifacts.sqlite3"
DEFAULT_CLASS_CONFIG = PROJECT_ROOT / "config" / "artifact_classes.yaml"
DEFAULT_RELATIONSHIP_CONFIG = PROJECT_ROOT / "config" / "relationship_types.yaml"
DEFAULT_LOCAL_PATHS = PROJECT_ROOT / "config" / "local_paths.json"


@dataclass(frozen=True)
class CourseArtifactConfig:
    project_root: Path = PROJECT_ROOT
    database_path: Path = DEFAULT_DATABASE
    class_config_path: Path = DEFAULT_CLASS_CONFIG
    relationship_config_path: Path = DEFAULT_RELATIONSHIP_CONFIG
    local_paths_path: Path = DEFAULT_LOCAL_PATHS

    def resolved(self) -> "CourseArtifactConfig":
        return CourseArtifactConfig(
            project_root=self.project_root.resolve(),
            database_path=self.database_path.resolve(),
            class_config_path=self.class_config_path.resolve(),
            relationship_config_path=self.relationship_config_path.resolve(),
            local_paths_path=self.local_paths_path.resolve(),
        )
