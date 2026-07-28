from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from course_artifacts.config import CourseArtifactConfig


REQUIRED_ROOTS = (
    "PUBLISHED_PRESENTATION_PDF",
    "PRESENTATION_WORKBENCH",
    "FOUNDATIONAL_RESOURCE",
    "AI_GENERATED_ARTIFACT",
)

DEFAULT_ROOTS = {
    "PUBLISHED_PRESENTATION_PDF": "read_only",
    "PRESENTATION_WORKBENCH": "read_write",
    "FOUNDATIONAL_RESOURCE": "read_only",
    "AI_GENERATED_ARTIFACT": "read_write",
    "INSTRUCTOR_DEFINED_CLASS_5": "read_write",
    "SPATIAL_RESOURCE": "read_only",
}

VALID_STATUSES = {
    "AVAILABLE", "AVAILABLE_READ_ONLY", "AVAILABLE_WRITABLE", "MISSING",
    "INACCESSIBLE", "REMOVABLE_VOLUME_OFFLINE", "CONFLICTING_ROOT",
}

LOCATOR_PATTERN = re.compile(r"^([A-Z][A-Z0-9_]*)://(.+)$")


@dataclass(frozen=True)
class RootValidation:
    code: str
    path: str
    access_mode: str
    enabled: bool
    status: str
    detail: str = ""

    @property
    def operational(self) -> bool:
        if not self.enabled:
            return False
        if self.access_mode == "read_write":
            return self.status == "AVAILABLE_WRITABLE"
        return self.status in {"AVAILABLE", "AVAILABLE_READ_ONLY", "AVAILABLE_WRITABLE"}


class LocalPathStore:
    """Persists absolute roots only in an ignored machine-local JSON file."""

    def __init__(self, config: CourseArtifactConfig | None = None):
        self.config = (config or CourseArtifactConfig()).resolved()
        self.path = self.config.local_paths_path

    def load(self) -> dict:
        payload = {
            "version": 1,
            "artifact_roots": {},
            "protected_read_only_paths": [],
        }
        if self.path.is_file():
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload.setdefault("protected_read_only_paths", [])
        roots = payload.setdefault("artifact_roots", {})
        for code, access_mode in DEFAULT_ROOTS.items():
            roots.setdefault(code, {
                "path": "",
                "access_mode": access_mode,
                "enabled": True,
                "allow_inside_project": access_mode == "read_write",
                "allow_shared_root": False,
            })
        return payload

    def save(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def update(self, code: str, **values) -> dict:
        payload = self.load()
        if code not in DEFAULT_ROOTS:
            raise KeyError(f"Unknown artifact root: {code}")
        payload["artifact_roots"][code].update(values)
        self.save(payload)
        return payload["artifact_roots"][code]


class PathResolver:
    def __init__(self, config: CourseArtifactConfig | None = None):
        self.config = (config or CourseArtifactConfig()).resolved()
        self.store = LocalPathStore(self.config)

    def validate_all(self) -> dict[str, RootValidation]:
        roots = self.store.load()["artifact_roots"]
        resolved_paths: dict[str, Path] = {}
        for code, item in roots.items():
            raw = str(item.get("path", "")).strip()
            if raw:
                try:
                    resolved_paths[code] = Path(raw).expanduser().resolve(strict=False)
                except OSError:
                    pass
        results: dict[str, RootValidation] = {}
        for code in DEFAULT_ROOTS:
            item = roots[code]
            results[code] = self._validate_one(code, item, roots, resolved_paths)
        return results

    def _validate_one(
        self, code: str, item: dict, roots: dict, resolved_paths: dict[str, Path],
    ) -> RootValidation:
        raw = str(item.get("path", "")).strip()
        access_mode = str(item.get("access_mode", DEFAULT_ROOTS[code]))
        enabled = bool(item.get("enabled", True))
        if not raw:
            return RootValidation(code, "", access_mode, enabled, "MISSING", "Not configured")
        path = Path(raw).expanduser()
        if not path.is_absolute():
            return RootValidation(
                code, raw, access_mode, enabled, "INACCESSIBLE",
                "Configured repository root must be an absolute local path",
            )
        if not path.exists():
            status = (
                "REMOVABLE_VOLUME_OFFLINE"
                if self._looks_removable(path) else "MISSING"
            )
            return RootValidation(code, raw, access_mode, enabled, status)
        if not path.is_dir() or not os.access(path, os.R_OK | os.X_OK):
            return RootValidation(code, raw, access_mode, enabled, "INACCESSIBLE")
        resolved = path.resolve()
        if access_mode == "read_write":
            protected_paths = (
                Path(value).expanduser().resolve(strict=False)
                for value in self.store.load()["protected_read_only_paths"]
                if str(value).strip()
            )
            if any(
                resolved == protected
                or resolved.is_relative_to(protected)
                or protected.is_relative_to(resolved)
                for protected in protected_paths
            ):
                return RootValidation(
                    code,
                    raw,
                    access_mode,
                    enabled,
                    "CONFLICTING_ROOT",
                    "Writable roots may not overlap a protected read-only source",
                )
        project = self.config.project_root.resolve()
        if (
            not bool(item.get("allow_inside_project", False))
            and (resolved == project or resolved.is_relative_to(project))
        ):
            return RootValidation(
                code, raw, access_mode, enabled, "CONFLICTING_ROOT",
                "Root is inside the application source tree",
            )
        if not bool(item.get("allow_shared_root", False)):
            conflicts = [
                other for other, other_path in resolved_paths.items()
                if other != code and other_path == resolved
                and not bool(roots[other].get("allow_shared_root", False))
            ]
            if conflicts:
                return RootValidation(
                    code, raw, access_mode, enabled, "CONFLICTING_ROOT",
                    f"Same root as {', '.join(sorted(conflicts))}",
                )
        writable = os.access(path, os.W_OK)
        if access_mode == "read_write":
            status = "AVAILABLE_WRITABLE" if writable else "AVAILABLE_READ_ONLY"
        elif access_mode == "read_only":
            status = "AVAILABLE_READ_ONLY"
        else:
            status = "AVAILABLE_WRITABLE" if writable else "AVAILABLE"
        return RootValidation(code, raw, access_mode, enabled, status)

    def operational(self) -> bool:
        results = self.validate_all()
        return all(results[code].operational for code in REQUIRED_ROOTS)

    def resolve(self, symbolic_locator: str) -> Path:
        code, relative = self.parse(symbolic_locator)
        root = self._configured_root(code)
        relative_path = PurePosixPath(relative)
        if (
            relative_path.is_absolute()
            or any(part in {"..", "."} for part in relative_path.parts)
            or "\\" in relative
        ):
            raise ValueError("Path traversal or absolute path injection is not permitted")
        root_resolved = root.resolve(strict=True)
        candidate = (root_resolved / Path(*relative_path.parts)).resolve(strict=False)
        if candidate == root_resolved or not candidate.is_relative_to(root_resolved):
            raise ValueError("Symbolic locator resolves outside its configured root")
        return candidate

    def to_symbolic(self, code: str, physical_path: Path) -> str:
        root = self._configured_root(code).resolve(strict=True)
        candidate = physical_path.expanduser().resolve(strict=True)
        if not candidate.is_relative_to(root):
            raise ValueError("Selected file is outside the configured artifact root")
        relative = candidate.relative_to(root).as_posix()
        return f"{code}://{relative}"

    def reresolution_report(self, artifacts: list[dict]) -> list[dict]:
        report = []
        for artifact in artifacts:
            locator = artifact.get("symbolic_locator", "")
            outcome = "missing"
            detail = ""
            try:
                locator_code, _ = self.parse(locator)
                if locator_code != artifact.get("class_code"):
                    outcome = "ambiguous"
                    detail = "Locator root does not match artifact class"
                else:
                    physical = self.resolve(locator)
                    if not physical.is_file():
                        outcome = "missing"
                    else:
                        outcome = "resolved"
            except (ValueError, KeyError, FileNotFoundError, OSError) as exc:
                detail = str(exc)
            report.append({
                "artifact_id": artifact.get("artifact_id", ""),
                "symbolic_locator": locator,
                "outcome": outcome,
                "detail": detail,
            })
        return report

    def parse(self, locator: str) -> tuple[str, str]:
        match = LOCATOR_PATTERN.fullmatch(locator.strip())
        if not match:
            raise ValueError("Locator must use ARTIFACT_CLASS://relative/path syntax")
        code, relative = match.groups()
        if code not in DEFAULT_ROOTS:
            raise KeyError(f"Unknown symbolic root: {code}")
        return code, relative

    def _configured_root(self, code: str) -> Path:
        item = self.store.load()["artifact_roots"].get(code)
        if not item or not item.get("enabled", True) or not str(item.get("path", "")).strip():
            raise FileNotFoundError(f"Artifact root is not configured: {code}")
        validation = self.validate_all()[code]
        if not validation.operational:
            raise OSError(f"Artifact root is unavailable: {code} ({validation.status})")
        return Path(validation.path).expanduser()

    @staticmethod
    def _looks_removable(path: Path) -> bool:
        value = str(path)
        return value.startswith(("/media/", "/mnt/", "/run/media/"))
