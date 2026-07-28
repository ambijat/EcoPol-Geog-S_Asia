from __future__ import annotations

import csv
from datetime import datetime, timezone
from html import escape
import re
from pathlib import Path

from course_artifacts.database.connection import CourseArtifactDatabase
from course_artifacts.domain.models import ArtifactRegistration
from course_artifacts.repositories.artifact_repository import ArtifactRepository
from course_artifacts.repositories.relationship_repository import RelationshipRepository
from course_artifacts.services.artifact_service import ArtifactService
from course_artifacts.services.path_resolver import PathResolver


VISUALIZATION_CLASS_CODE = "INSTRUCTOR_DEFINED_CLASS_5"


class VisualizationService:
    """Creates portable visual artifacts without managing a vault or graph database."""

    def __init__(self, database: CourseArtifactDatabase, resolver: PathResolver):
        self.resolver = resolver
        self.artifacts = ArtifactRepository(database)
        self.relationships = RelationshipRepository(database)
        self.artifact_service = ArtifactService(database)

    def create_mind_map(self, title: str) -> int:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("A mind-map title is required")
        root = self._writable_root()
        filename = self._safe_stem(clean_title) + ".mm"
        target = (root / filename).resolve(strict=False)
        self._require_inside_root(root, target)
        if target.exists():
            raise FileExistsError(f"A visualisation already exists: {filename}")
        target.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<map version="1.0.1">\n'
            f'  <node TEXT="{escape(clean_title, quote=True)}"/>\n'
            "</map>\n",
            encoding="utf-8",
        )
        try:
            locator = self.resolver.to_symbolic(VISUALIZATION_CLASS_CODE, target)
            return self.artifact_service.register(ArtifactRegistration(
                artifact_class_code=VISUALIZATION_CLASS_CODE,
                title=clean_title,
                physical_path=target,
                symbolic_locator=locator,
                description="Instructor-created portable mind map",
                provenance="Created explicitly in the Knowledge Maps and Visualisations workspace",
                creator_or_origin="Instructor",
                source_repository="KNOWLEDGE_MAP_REPOSITORY",
            ))
        except Exception:
            target.unlink(missing_ok=True)
            raise

    def export_neo4j_bundle(self, artifact_pk: int) -> tuple[Path, Path]:
        selected = self.artifacts.get(artifact_pk)
        if selected["class_code"] != VISUALIZATION_CLASS_CODE:
            raise ValueError("Neo4j export requires a Knowledge Maps artifact")
        root = self._writable_root()
        export_root = (root / "neo4j_exports").resolve(strict=False)
        self._require_inside_root(root, export_root)
        export_root.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        stem = f'{self._safe_stem(selected["artifact_id"].lower())}_{stamp}'
        nodes_path = export_root / f"{stem}_nodes.csv"
        relationships_path = export_root / f"{stem}_relationships.csv"
        relationships = self.relationships.list(artifact_pk)
        artifact_ids = {artifact_pk}
        for relationship in relationships:
            artifact_ids.add(relationship["source_artifact_id"])
            artifact_ids.add(relationship["target_artifact_id"])
        nodes = [self.artifacts.get(identifier) for identifier in sorted(artifact_ids)]
        with nodes_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow((
                "artifact_id:ID", "title", "class_code",
                "symbolic_locator", ":LABEL",
            ))
            for artifact in nodes:
                writer.writerow((
                    artifact["artifact_id"], artifact["title"],
                    artifact["class_code"], artifact["symbolic_locator"],
                    "CourseArtifact",
                ))
        with relationships_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow((":START_ID", ":END_ID", ":TYPE", "status"))
            for relationship in relationships:
                writer.writerow((
                    relationship["source_identifier"],
                    relationship["target_identifier"],
                    relationship["relationship_type"],
                    relationship["status"],
                ))
        return nodes_path, relationships_path

    def _writable_root(self) -> Path:
        validation = self.resolver.validate_all()[VISUALIZATION_CLASS_CODE]
        if validation.status != "AVAILABLE_WRITABLE" or not validation.enabled:
            raise OSError(
                "Configure an enabled, writable Knowledge Maps root before "
                "creating or exporting visualisations"
            )
        return Path(validation.path).resolve(strict=True)

    @staticmethod
    def _safe_stem(value: str) -> str:
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._-")
        if not stem:
            raise ValueError("The title does not contain a usable filename")
        return stem

    @staticmethod
    def _require_inside_root(root: Path, target: Path) -> None:
        if target == root or not target.is_relative_to(root):
            raise ValueError("Visualisation output resolves outside its configured root")
