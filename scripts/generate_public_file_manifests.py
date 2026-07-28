#!/usr/bin/env python3
"""Generate the explicit public-candidate and local-only file manifests."""

from __future__ import annotations

import argparse
from fnmatch import fnmatch
import os
import re
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INCLUDE_PATH = Path("reports/public_include_manifest.txt")
EXCLUDE_PATH = Path("reports/public_exclude_manifest.txt")

PUBLIC_ROOT_FILES = {
    ".gitignore", "LICENSE", "README.md", "index.html",
    "requirements-gui.txt", "requirements-qt.txt",
    "requirements-desktop.txt", "launch_cockpit.sh", "launch_cockpit.bat",
}
PUBLIC_PREFIXES = (
    "course/", "docs/", "gui/", "public/",
    "resource_registry/", "schemas/",
    "scripts/", "templates/", "tests/", "qt_gui/", "course_artifacts/", "desktop/",
)
PUBLIC_REPORTS = {
    "reports/.gitkeep", "reports/ledger_governance_issues.md",
    "reports/public_exclude_manifest.txt", "reports/public_include_manifest.txt",
    "reports/repository_validation.md", "reports/terminology_migration.md",
    "reports/OWNER_ARTEFACT_MAP.md",
}
PUBLIC_CONFIG = {
    "config/public_projection_paths.example.json",
    "config/artifact_classes.yaml",
    "config/lecture_topic_taxonomy.yaml",
    "config/relationship_types.yaml",
    "config/local_paths.example.json",
}
PUBLIC_LEDGER_SUPPORT = {"course_ledger/README.md", "course_ledger/drafts/README.md"}

EXCLUDE_RULES = (
    "SEMESTER2026_Course_Governance_Preamble.md",
    "project_face_guide/**",
    "course_ledger/ledger.jsonl",
    "course_ledger/retrospective_events_2026-07-20.json",
    "course_ledger/events/**",
    "course_ledger/drafts/gui/**",
    "course_ledger/drafts/qt/**",
    "config/public_projection_paths.local.json",
    "config/local_paths.json",
    "reports/source_census.json",
    "reports/source_census.md",
    "reports/past_assessment_census.json",
    "reports/repository_validation.json",
    "reports/gui_acceptance/**",
    "reports/qt_gui_acceptance/**",
    "reports/desktop_artifact_acceptance/**",
    "reports/historical_lecture_title_extraction.json",
    "reports/historical_lecture_title_extraction.md",
    "reports/LECTURE_1A_KC01_PILOT_STATUS.md",
    "reports/L01A_KC01_S003_AI_BRIDGE_STATUS.md",
    "docs/CODEX_IMPLEMENTATION_MANDATE_BROWSER_FIRST_LECTURE_REINFORCEMENT.md",
    "docs/HOSTED_SOURCE_GOVERNANCE_DRAFT.md",
    "online_sources/**",
    "student_data/**", "**/student_data/**", "attendance/**", "**/attendance/**",
    "grades/**", "**/grades/**", "marks/**", "**/marks/**",
    "answer_scripts/**", "**/answer_scripts/**", "private_communications/**",
    "**/private_communications/**", "course/assessments/drafts/**",
    "course/assessments/restricted/**", "course/instructor_materials/**",
    "resources/offline_originals/**", "resources/online_snapshots/**",
    "resources/past_course_runs/**", "resources/past_assessments/**",
    "resources/instructor_originals/**", "google_drive_downloads/**",
    "drive_downloads/**", "online_captures/**", "bulk_captures/**",
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx",
    "*credentials*.json", "*secrets*.json", "secrets/**", "credentials/**",
    "__pycache__/**", "*.pyc", ".pytest_cache/**", ".venv/**", "venv/**",
    "env/**", "build/**", "dist/**", "tmp/**", "temp/**",
    "gui/database/**", "gui/local_state/**",
    "local_state/**", "working_derivatives/**", "exports/**",
    "processing_packets/**", "imported_ai_outputs/**", "logs/**",
    "qt_gui/local_state/**", "qt_gui/local_state/historical_derivatives/**",
    "qt_gui/local_state/triangulation/**", "qt_gui/local_state/website_learning/**",
    "qt_gui/local_state/raw_resource_annotations/**", "resource_registry/candidates/**",
    "resource_registry/.resources.lock",
    "course/lectures/**/student_learning_packages/**", "course/lectures/**/student_notes/**",
    "course/ai_assisted_notes/**",
    "reports/triangulation_live/**",
    "qt_gui/build/**", "qt_gui/dist/**", "qt_gui/**/*.log",
    "course/lecture_titles.txt.bak", "course/lecture_part_titles.txt.bak",
    "course/lectures/**/deck_source/*_DRAFT.pptx",
    "course/lectures/**/deck_source/*_REVISED.pptx",
    "course/lectures/**/deck_source/*_DRAFT.metadata.json",
    "course/lectures/**/deck_source/*_REVISED.metadata.json",
    "course/lectures/**/deck_source/*_DRAFT.teaching_brief.md",
    "course/lectures/**/deck_source/*_REVISED.teaching_brief.md",
    "course/lectures/**/deck_source/*.pptx",
    "course/lectures/**/deck_source/*.metadata.json",
    "course/lectures/**/deck_source/*.teaching_brief.md",
    "course/lectures/**/deck_source/*.validation.json",
    "course/lectures/**/classroom_pdf/*.pdf",
    "course/lectures/**/previews/**",
    "course/lectures/**/classroom_pdf/*_DRAFT.pdf",
    "course/lectures/**/classroom_pdf/*_REVISED.pdf",
    "course/lectures/**/previews/**",
    "*.pdf", "*.ppt", "*.pptx", "*.odp", "*.doc", "*.docx", "*.xls",
    "*.xlsx", "*.zip", "*.7z", "*.rar",
)

MACHINE_PATHS = (
    re.compile(r"(?<![A-Za-z0-9])/(?:home|media|mnt|run/media|Users|Volumes)/[^\s`\"'\]\[{}<>|]+"),
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:\\(?:[^\s`\"'<>|]+\\)*[^\s`\"'<>|]*"),
)


class ManifestError(ValueError):
    """Raised when a public candidate violates the projection boundary."""


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def is_public_candidate(relative: str) -> bool:
    if relative in PUBLIC_ROOT_FILES | PUBLIC_REPORTS | PUBLIC_CONFIG | PUBLIC_LEDGER_SUPPORT:
        return True
    if relative.startswith("resources/") and relative.endswith("/.gitkeep"):
        return True
    if relative == "course/instructor_materials/.gitkeep":
        return True
    if any(fnmatch(relative, pattern) for pattern in EXCLUDE_RULES):
        return False
    if relative.startswith("docs/"):
        return relative != "docs/HOSTED_SOURCE_GOVERNANCE_DRAFT.md"
    if relative.startswith("resources/"):
        return False
    if relative.startswith("course_ledger/") or relative.startswith("reports/") or relative.startswith("config/"):
        return False
    if relative.startswith("gui/") and any(
        token in relative for token in ("/__pycache__/", "/database/", "/local_state/")
    ):
        return False
    if relative.startswith("course/instructor_materials/"):
        return False
    return relative.startswith(PUBLIC_PREFIXES)


def reject_machine_paths(root: Path, candidates: list[str]) -> None:
    violations: list[str] = []
    for relative in candidates:
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in MACHINE_PATHS:
            if pattern.search(text):
                violations.append(relative)
                break
    if violations:
        raise ManifestError("machine-specific absolute path in public candidate: " + ", ".join(violations))


def generate(root: Path, *, dry_run: bool = False, check: bool = False) -> dict[str, object]:
    candidates = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
        and is_public_candidate(path.relative_to(root).as_posix())
    )
    reject_machine_paths(root, candidates)
    include_text = "\n".join(candidates) + "\n"
    exclude_text = "\n".join(EXCLUDE_RULES) + "\n"
    if check:
        if (root / INCLUDE_PATH).read_text(encoding="utf-8") != include_text:
            raise ManifestError("public include manifest is stale")
        if (root / EXCLUDE_PATH).read_text(encoding="utf-8") != exclude_text:
            raise ManifestError("public exclude manifest is stale")
    elif not dry_run:
        atomic_write(root / INCLUDE_PATH, include_text)
        atomic_write(root / EXCLUDE_PATH, exclude_text)
    return {
        "candidate_count": len(candidates),
        "exclude_rule_count": len(EXCLUDE_RULES),
        "dry_run": dry_run,
        "check": check,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    result = generate(arguments.root.resolve(), dry_run=arguments.dry_run, check=arguments.check)
    print(f"public candidates: {result['candidate_count']}")
    print(f"exclude rules: {result['exclude_rule_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
