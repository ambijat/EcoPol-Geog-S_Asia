from __future__ import annotations

from collections import Counter, defaultdict
import json
import re
import unicodedata
import uuid
from pathlib import Path, PurePosixPath

from course_artifacts.database.connection import CourseArtifactDatabase, utc_now
from course_artifacts.domain.models import ArtifactRegistration
from course_artifacts.repositories.artifact_repository import ArtifactRepository
from course_artifacts.repositories.class_repository import ArtifactClassRepository
from course_artifacts.repositories.scan_repository import ScanRepository
from course_artifacts.services.artifact_service import ArtifactService
from course_artifacts.services.path_resolver import PathResolver


SUPPORTED_EXTENSIONS = {
    ".pdf", ".odp", ".pptx", ".ppt", ".docx", ".odt", ".txt", ".md",
    ".tex", ".csv", ".xlsx", ".ods", ".jpg", ".jpeg", ".png", ".svg",
}

CANDIDATE_ACTIONS = {
    "AWAITING_REVIEW", "REGISTERED", "IGNORED", "DEFERRED",
    "MARKED_DUPLICATE", "RELATE_TO_EXISTING",
}

AI_REVISION_STATES = {
    "IN_REVISION", "INTEGRATED", "DEFERRED", "REJECTED",
}


class ScanService:
    """Performs explicit read-only discovery and creates candidates only."""

    def __init__(self, database: CourseArtifactDatabase, resolver: PathResolver):
        self.database = database
        self.resolver = resolver
        self.repository = ScanRepository(database)
        self.artifacts = ArtifactRepository(database)
        self.classes = ArtifactClassRepository(database)
        self.artifact_service = ArtifactService(database)
        self.repository.interrupt_running_sessions(utc_now())

    def scan(self, class_code: str, *, force: bool = False) -> int:
        """Record a current read-only census.

        An unchanged census reuses the latest completed session. ``force`` is
        reserved for an explicit audit need; routine refreshes must not multiply
        identical candidate rows.
        """
        validation = self.resolver.validate_all()[class_code]
        if not validation.operational:
            raise OSError(f"Artifact root is unavailable: {class_code} ({validation.status})")
        root = Path(validation.path).resolve(strict=True)
        artifact_class = self.classes.get(class_code)
        accepted_extensions = {
            str(extension).lower()
            for extension in artifact_class["accepted_extensions"]
        } or SUPPORTED_EXTENSIONS
        candidates: list[dict] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in accepted_extensions:
                continue
            try:
                resolved = path.resolve(strict=True)
                file_size = resolved.stat().st_size
            except OSError:
                continue
            if not resolved.is_relative_to(root):
                continue
            candidates.append({
                "relative_path": resolved.relative_to(root).as_posix(),
                "file_extension": resolved.suffix.lower(),
                "file_size": file_size,
            })

        latest_session = self.repository.latest_session(class_code)
        latest_candidates = self.repository.latest_candidates(class_code)
        latest_snapshot = {
            (row["relative_path"], row["file_extension"], row["file_size"])
            for row in latest_candidates
        }
        current_snapshot = {
            (row["relative_path"], row["file_extension"], row["file_size"])
            for row in candidates
        }
        if (
            not force
            and latest_session is not None
            and Path(latest_session["physical_root"]).resolve(strict=False) == root
            and latest_snapshot == current_snapshot
        ):
            return int(latest_session["id"])

        now = utc_now()
        session_pk = self.repository.create_session({
            "scan_id": f"SCAN-{uuid.uuid4().hex[:12].upper()}",
            "symbolic_root": class_code,
            "physical_root": str(root),
            "status": "RUNNING",
            "started_at": now,
        })
        try:
            records = [
                {
                    "scan_session_id": session_pk,
                    "candidate_id": f"CAND-{uuid.uuid4().hex[:12].upper()}",
                    "relative_path": candidate["relative_path"],
                    "file_extension": candidate["file_extension"],
                    # Compatibility column only; routine scans never hash files.
                    "checksum_sha256": "",
                    "file_size": candidate["file_size"],
                    "candidate_status": "AWAITING_REVIEW",
                    "proposed_class_code": class_code,
                }
                for candidate in candidates
            ]
            self.repository.add_candidates(records)
            self.repository.complete_session(session_pk, utc_now(), len(records))
        except Exception:
            self.repository.fail_session(session_pk, utc_now())
            raise
        return session_pk

    def register_candidate(self, candidate_pk: int) -> int:
        candidate = self.repository.get_candidate(candidate_pk)
        if candidate["candidate_status"] in {"REGISTERED", "IGNORED", "MARKED_DUPLICATE"}:
            raise ValueError(f"Candidate is already resolved: {candidate['candidate_status']}")
        locator = f'{candidate["proposed_class_code"]}://{candidate["relative_path"]}'
        physical = self.resolver.resolve(locator)
        artifact_pk = self.artifact_service.register(ArtifactRegistration(
            artifact_class_code=candidate["proposed_class_code"],
            title=physical.stem,
            physical_path=physical,
            symbolic_locator=locator,
            provenance=f'Read-only scan candidate {candidate["candidate_id"]}',
            source_repository=candidate["proposed_class_code"],
        ))
        self.repository.set_status(candidate_pk, "REGISTERED", artifact_pk)
        return artifact_pk

    def decide(
        self, candidate_pk: int, status: str,
        related_artifact_id: int | None = None, note: str = "",
    ) -> None:
        if status not in CANDIDATE_ACTIONS - {"REGISTERED", "AWAITING_REVIEW"}:
            raise ValueError(f"Invalid candidate action: {status}")
        if status == "RELATE_TO_EXISTING":
            if related_artifact_id is None:
                raise ValueError("An existing artifact must be selected")
            self.artifacts.get(related_artifact_id)
        self.repository.set_status(
            candidate_pk, status, related_artifact_id=related_artifact_id, note=note
        )

    @staticmethod
    def _filename_key(path: str) -> str:
        stem = Path(path).stem.strip()
        return unicodedata.normalize("NFKC", stem).casefold()

    @staticmethod
    def _artifact_relative_path(artifact: dict) -> str:
        locator = str(artifact.get("symbolic_locator", "")).strip()
        if "://" in locator:
            return locator.split("://", 1)[1].lstrip("/")
        if locator:
            return locator.rsplit(">", 1)[-1].lstrip("/")
        title = str(artifact.get("title", "")).strip()
        extension = str(artifact.get("file_extension", "")).lower()
        return title if title.lower().endswith(extension) else f"{title}{extension}"

    def with_published_pdf_matches(self, candidates: list[dict]) -> list[dict]:
        """Annotate Workbench candidates with review-only filename matches."""
        published: dict[str, dict] = {}
        for candidate in self.repository.latest_candidates(
            "PUBLISHED_PRESENTATION_PDF"
        ):
            relative_path = candidate["relative_path"]
            published[relative_path.casefold()] = {
                "relative_path": relative_path,
                "registered_artifact_id": None,
                "source": "SCAN_CANDIDATE",
            }
        for artifact in self.artifacts.list("PUBLISHED_PRESENTATION_PDF"):
            relative_path = self._artifact_relative_path(artifact)
            if not relative_path:
                continue
            published[relative_path.casefold()] = {
                "relative_path": relative_path,
                "registered_artifact_id": artifact["id"],
                "source": "REGISTERED_ARTIFACT",
            }

        by_stem: dict[str, list[dict]] = defaultdict(list)
        for match in published.values():
            by_stem[self._filename_key(match["relative_path"])].append(match)

        annotated = []
        for candidate in candidates:
            row = dict(candidate)
            matches = sorted(
                by_stem.get(self._filename_key(row["relative_path"]), []),
                key=lambda item: item["relative_path"].casefold(),
            )
            row["published_pdf_matches"] = matches
            if len(matches) == 1:
                match = matches[0]
                row["published_pdf_match"] = Path(match["relative_path"]).name
                row["published_pdf_match_status"] = (
                    "MATCHED_REGISTERED"
                    if match["registered_artifact_id"] is not None
                    else "MATCHED_CANDIDATE"
                )
                row["published_pdf_match_tooltip"] = (
                    f'Exact filename match: {match["relative_path"]}. '
                    "Proposed relationship: the PDF is EXPORT_OF this "
                    "Workbench presentation. Instructor confirmation required."
                )
            elif len(matches) > 1:
                row["published_pdf_match"] = f"Ambiguous: {len(matches)} PDFs"
                row["published_pdf_match_status"] = "AMBIGUOUS"
                row["published_pdf_match_tooltip"] = (
                    "Multiple exact filename matches: "
                    + " · ".join(item["relative_path"] for item in matches)
                )
            elif published:
                row["published_pdf_match"] = "No PDF filename match"
                row["published_pdf_match_status"] = "NO_MATCH"
                row["published_pdf_match_tooltip"] = (
                    "No case-insensitive exact filename-stem match exists in "
                    "the latest Published PDFs census or registered artifacts."
                )
            else:
                row["published_pdf_match"] = "Scan Published PDFs first"
                row["published_pdf_match_status"] = "PUBLISHED_SCAN_REQUIRED"
                row["published_pdf_match_tooltip"] = (
                    "No registered or explicitly scanned Published PDF is "
                    "available for filename matching."
                )
            annotated.append(row)
        return annotated

    @staticmethod
    def raw_material_topics(
        candidates: list[dict],
    ) -> tuple[list[dict], dict[str, int]]:
        """Aggregate file candidates into instructor-facing topic folders."""
        grouped: dict[str, list[dict]] = defaultdict(list)
        stats = {
            "candidate_files": len(candidates),
            "topic_files": 0,
            "loose_files": 0,
            "system_files": 0,
        }
        for candidate in candidates:
            parts = PurePosixPath(candidate["relative_path"]).parts
            if any(part.startswith(".") for part in parts):
                stats["system_files"] += 1
                continue
            lecture_container = re.fullmatch(
                r"LEC_RES_(\d+)", parts[0], flags=re.IGNORECASE
            )
            if lecture_container:
                if len(parts) < 3:
                    stats["loose_files"] += 1
                    continue
                topic_path = PurePosixPath(parts[0], parts[1]).as_posix()
            else:
                if len(parts) < 2:
                    stats["loose_files"] += 1
                    continue
                topic_path = parts[0]
            grouped[topic_path].append(candidate)
            stats["topic_files"] += 1

        topics = []
        for topic_path, files in grouped.items():
            topic_parts = PurePosixPath(topic_path).parts
            container = topic_parts[0]
            folder = topic_parts[-1]
            lecture_match = re.fullmatch(
                r"LEC_RES_(\d+)", container, flags=re.IGNORECASE
            )
            lecture_group = (
                f"Lecture {int(lecture_match.group(1))}"
                if lecture_match
                else "Course-wide"
            )
            statuses = Counter(file["candidate_status"] for file in files)
            awaiting = statuses.get("AWAITING_REVIEW", 0)
            review_summary = (
                f"{awaiting} awaiting review"
                if len(statuses) == 1 and awaiting
                else " · ".join(
                    f'{count} {status.replace("_", " ").lower()}'
                    for status, count in sorted(statuses.items())
                )
            )
            formats = sorted({
                (file["file_extension"] or "no extension").upper()
                for file in files
            })
            topics.append({
                "topic_label": folder.replace("_", " ").title(),
                "lecture_group": lecture_group,
                "topic_path": topic_path,
                "file_count": len(files),
                "formats": ", ".join(formats),
                "review_summary": review_summary,
                "candidate_ids": [file["id"] for file in files],
            })

        def topic_key(topic: dict) -> tuple:
            lecture = re.fullmatch(r"Lecture (\d+)", topic["lecture_group"])
            container_key = (
                (0, int(lecture.group(1)))
                if lecture
                else (1, topic["lecture_group"].casefold())
            )
            return container_key, topic["topic_label"].casefold()

        return sorted(topics, key=topic_key), stats

    @staticmethod
    def _lecture_number(path: str, prefer_container: bool = False) -> int | None:
        parts = PurePosixPath(path).parts
        if parts:
            container = re.match(
                r"^(?:LEC_RES|LECT|LEC)[ _-]*0*(\d+)(?:\D|$)",
                parts[0], flags=re.IGNORECASE,
            )
            if container:
                number = int(container.group(1))
                return number if 1 <= number <= 15 else None
        if prefer_container:
            return None
        filename = Path(path).stem
        match = re.search(
            r"lecture[ _-]*0*(\d+)", filename, flags=re.IGNORECASE
        )
        if match:
            number = int(match.group(1))
            return number if 1 <= number <= 15 else None
        return None

    def _class_relative_paths(self, class_code: str) -> list[str]:
        paths = {
            candidate["relative_path"]
            for candidate in self.repository.latest_candidates(class_code)
        }
        for artifact in self.artifacts.list(class_code):
            relative_path = self._artifact_relative_path(artifact)
            if relative_path:
                paths.add(relative_path)
        return sorted(paths, key=lambda value: value.casefold())

    def _load_ai_revision_state(self) -> dict:
        with self.database.connection() as connection:
            row = connection.execute(
                """SELECT setting_value FROM application_settings
                WHERE setting_key='ai_revision_queue'"""
            ).fetchone()
        if row is None:
            return {}
        try:
            value = json.loads(row["setting_value"])
        except (TypeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    def set_ai_revision_state(
        self, lecture_number: int, status: str, workbench_path: str = "",
    ) -> None:
        if not 1 <= lecture_number <= 15:
            raise ValueError("Lecture number must be between 1 and 15")
        if status not in AI_REVISION_STATES:
            raise ValueError(f"Invalid AI revision state: {status}")
        state = self._load_ai_revision_state()
        key = str(lecture_number)
        existing = state.get(key, {})
        state[key] = {
            "status": status,
            "workbench_path": workbench_path or existing.get(
                "workbench_path", ""
            ),
            "updated_at": utc_now(),
        }
        self._save_ai_revision_state(state)

    def set_ai_revision_workbench(
        self, lecture_number: int, workbench_path: str,
    ) -> None:
        if not 1 <= lecture_number <= 15:
            raise ValueError("Lecture number must be between 1 and 15")
        if not workbench_path.strip():
            raise ValueError("A Workbench presentation must be selected")
        state = self._load_ai_revision_state()
        key = str(lecture_number)
        existing = state.get(key, {})
        state[key] = {
            "status": existing.get("status", ""),
            "workbench_path": workbench_path,
            "updated_at": utc_now(),
        }
        self._save_ai_revision_state(state)

    def _save_ai_revision_state(self, state: dict) -> None:
        now = utc_now()
        with self.database.connection() as connection:
            connection.execute(
                """INSERT INTO application_settings(
                    setting_key,setting_value,local_only,updated_at
                ) VALUES ('ai_revision_queue',?,1,?)
                ON CONFLICT(setting_key) DO UPDATE SET
                    setting_value=excluded.setting_value,
                    local_only=1,
                    updated_at=excluded.updated_at""",
                (json.dumps(state, sort_keys=True), now),
            )

    def ai_revision_queue(
        self, ai_candidates: list[dict],
    ) -> tuple[list[dict], dict[str, int]]:
        """Build a 15-lecture presentation-revision queue."""
        notes_by_lecture: dict[int, list[dict]] = defaultdict(list)
        unassigned = 0
        for candidate in ai_candidates:
            lecture_number = self._lecture_number(
                candidate["relative_path"], prefer_container=True
            )
            if lecture_number is None:
                unassigned += 1
            else:
                notes_by_lecture[lecture_number].append(candidate)

        workbench_by_lecture: dict[int, list[str]] = defaultdict(list)
        for relative_path in self._class_relative_paths(
            "PRESENTATION_WORKBENCH"
        ):
            lecture_number = self._lecture_number(relative_path)
            if lecture_number is not None:
                workbench_by_lecture[lecture_number].append(relative_path)

        published_by_lecture: dict[int, list[str]] = defaultdict(list)
        for relative_path in self._class_relative_paths(
            "PUBLISHED_PRESENTATION_PDF"
        ):
            lecture_number = self._lecture_number(relative_path)
            if lecture_number is not None:
                published_by_lecture[lecture_number].append(relative_path)

        saved = self._load_ai_revision_state()
        status_labels = {
            "IN_REVISION": "Revision in progress",
            "INTEGRATED": "Integrated into presentation",
            "DEFERRED": "Deferred",
            "REJECTED": "Rejected",
        }
        rows = []
        for lecture_number in range(1, 16):
            notes = notes_by_lecture[lecture_number]
            workbench_paths = workbench_by_lecture[lecture_number]
            published_paths = published_by_lecture[lecture_number]
            persisted = saved.get(str(lecture_number), {})
            persisted_status = persisted.get("status", "")
            if persisted_status in status_labels:
                status = status_labels[persisted_status]
            elif not notes:
                status = "No LaTeX notes"
            elif not workbench_paths:
                status = "Workbench presentation not found"
            else:
                status = "Ready for revision review"
            ai_folders = sorted({
                PurePosixPath(note["relative_path"]).parts[0]
                for note in notes
                if PurePosixPath(note["relative_path"]).parts
            })
            preferred_ai_folder = f"LEC_{lecture_number}"
            try:
                preferred_path = self.resolver.resolve(
                    f"AI_GENERATED_ARTIFACT://{preferred_ai_folder}"
                )
                preferred_exists = preferred_path.is_dir()
            except (ValueError, KeyError, OSError):
                preferred_exists = False
            selected_workbench = persisted.get("workbench_path", "")
            tex_paths = sorted(
                note["relative_path"] for note in notes
                if note["file_extension"].lower() == ".tex"
            )
            pdf_paths = sorted(
                note["relative_path"] for note in notes
                if note["file_extension"].lower() == ".pdf"
            )
            rows.append({
                "lecture_number": lecture_number,
                "lecture_label": f"Lecture {lecture_number}",
                "ai_note_count": len(notes),
                "ai_folder": (
                    preferred_ai_folder
                    if preferred_exists
                    else (ai_folders[0] if ai_folders else preferred_ai_folder)
                ),
                "ai_note_paths": [
                    note["relative_path"] for note in notes
                ],
                "tex_paths": tex_paths,
                "tex_display": (
                    ", ".join(Path(path).name for path in tex_paths)
                    if tex_paths else "None"
                ),
                "tex_display_tooltip": "\n".join(tex_paths),
                "pdf_note_paths": pdf_paths,
                "pdf_note_display": (
                    ", ".join(Path(path).name for path in pdf_paths)
                    if pdf_paths else "None"
                ),
                "pdf_note_display_tooltip": "\n".join(pdf_paths),
                "workbench_paths": workbench_paths,
                "workbench_display": (
                    ", ".join(Path(path).name for path in workbench_paths)
                    if workbench_paths else "Not found"
                ),
                "selected_workbench": selected_workbench,
                "published_paths": published_paths,
                "published_display": (
                    ", ".join(Path(path).name for path in published_paths)
                    if published_paths else "Not published"
                ),
                "revision_status": status,
                "updated_at": persisted.get("updated_at", ""),
            })

        stats = {
            "lectures": 15,
            "ai_notes": sum(len(notes) for notes in notes_by_lecture.values()),
            "tex_sources": sum(
                note["file_extension"].lower() == ".tex"
                for notes in notes_by_lecture.values() for note in notes
            ),
            "pdf_notes": sum(
                note["file_extension"].lower() == ".pdf"
                for notes in notes_by_lecture.values() for note in notes
            ),
            "lectures_with_notes": sum(
                bool(notes) for notes in notes_by_lecture.values()
            ),
            "workbench_presentations": sum(
                len(paths) for paths in workbench_by_lecture.values()
            ),
            "published_pdfs": sum(
                len(paths) for paths in published_by_lecture.values()
            ),
            "unassigned_notes": unassigned,
        }
        return rows, stats
