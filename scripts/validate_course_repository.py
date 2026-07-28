#!/usr/bin/env python3
"""Validate the controlled IS529N repository and write JSON/Markdown reports."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from course_ledger import read_blocks, verify_blocks
from register_resource import RegistrationError, read_registry, validate_record


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DIRECTORIES = [
    "resources/offline_originals", "resources/online_snapshots",
    "resources/past_course_runs", "resources/past_assessments",
    "resources/instructor_originals", "resource_registry/source_manifests",
    "resource_registry/duplicate_reports", "course/charter", "course/syllabus",
    "course/modules", "course/sessions", "course/assessments",
    "course/student_materials", "course/instructor_materials",
    "course/website_exports", "course/retrospective_reviews", "templates", "reports",
]
ORIGINAL_PREFIXES = (
    "resources/offline_originals/", "resources/online_snapshots/",
    "resources/past_course_runs/", "resources/past_assessments/",
    "resources/instructor_originals/",
)
ORIGINAL_SOURCE_CLASSES = {
    "INSTRUCTOR_MATERIAL", "HISTORICAL_RESOURCE", "ONLINE_SOURCE",
    "VERIFIED_EXTERNAL_MATERIAL",
}
DERIVATIVE_SOURCE_CLASSES = {
    "AI_SYNTHESIS", "PROVISIONAL_INTERPRETATION", "APPROVED_COURSE_CONTENT",
}


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def resolve_record_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def project_relative(project_root: Path, path: Path) -> str | None:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return None


def validate_repository(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    missing_directories = [
        name for name in REQUIRED_DIRECTORIES if not (project_root / name).is_dir()
    ]
    errors.extend(f"missing required directory: {name}" for name in missing_directories)

    registry_path = project_root / "resource_registry" / "resources.jsonl"
    records: list[dict[str, Any]] = []
    if not registry_path.is_file():
        errors.append("missing resource registry: resource_registry/resources.jsonl")
    else:
        try:
            records = read_registry(registry_path)
        except RegistrationError as exc:
            errors.append(str(exc))

    identifiers: dict[str, int] = {}
    hashes: dict[str, list[str]] = {}
    for index, record in enumerate(records, start=1):
        for message in validate_record(record):
            errors.append(f"resource record {index}: {message}")
        resource_id = record.get("resource_id")
        if isinstance(resource_id, str):
            if resource_id in identifiers:
                errors.append(
                    f"duplicate resource identifier {resource_id} at records "
                    f"{identifiers[resource_id]} and {index}"
                )
            identifiers[resource_id] = index
        checksum = record.get("content_sha256")
        if isinstance(checksum, str):
            hashes.setdefault(checksum, []).append(str(resource_id))

        local_value = record.get("local_path")
        if not isinstance(local_value, str):
            continue
        local_path = resolve_record_path(project_root, local_value)
        if not local_path.is_file():
            errors.append(f"{resource_id}: referenced local file does not exist: {local_value}")
            continue
        relative = project_relative(project_root, local_path)
        if relative is None:
            continue
        in_originals = any(relative.startswith(prefix) for prefix in ORIGINAL_PREFIXES)
        in_course = relative.startswith("course/")
        source_class = record.get("source_class")
        if source_class in ORIGINAL_SOURCE_CLASSES and in_course:
            errors.append(
                f"{resource_id}: original source class is stored under generated course outputs"
            )
        if source_class in DERIVATIVE_SOURCE_CLASSES and in_originals:
            errors.append(
                f"{resource_id}: derivative source class is stored under immutable originals"
            )

    duplicate_hashes = {
        checksum: resource_ids for checksum, resource_ids in hashes.items()
        if len(resource_ids) > 1
    }
    for checksum, resource_ids in duplicate_hashes.items():
        errors.append(
            f"duplicate content hash {checksum}: {', '.join(resource_ids)}"
        )

    ledger_path = project_root / "course_ledger" / "ledger.jsonl"
    ledger_count = 0
    ledger_tip: str | None = None
    ledger_errors: list[str] = []
    if not ledger_path.is_file():
        ledger_errors.append("course ledger is missing")
    else:
        try:
            with ledger_path.open("r", encoding="utf-8") as handle:
                blocks = read_blocks(handle)
            ledger_count = len(blocks)
            ledger_errors = verify_blocks(blocks)
            ledger_tip = blocks[-1].get("content_hash") if blocks else None
        except (OSError, ValueError) as exc:
            ledger_errors.append(str(exc))
    errors.extend(f"ledger: {message}" for message in ledger_errors)

    if not records:
        warnings.append("resource registry is valid but currently empty")

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "valid": not errors,
        "summary": {
            "error_count": len(errors),
            "warning_count": len(warnings),
            "resource_record_count": len(records),
            "duplicate_hash_group_count": len(duplicate_hashes),
            "ledger_block_count": ledger_count,
            "ledger_chain_tip": ledger_tip,
        },
        "checks": {
            "required_directories": {
                "valid": not missing_directories,
                "missing": missing_directories,
            },
            "resource_registry": {
                "valid": not any("resource" in item.lower() for item in errors),
                "record_count": len(records),
                "duplicate_hashes": duplicate_hashes,
            },
            "course_ledger": {
                "valid": not ledger_errors,
                "block_count": ledger_count,
                "chain_tip": ledger_tip,
            },
            "original_derivative_separation": {
                "valid": not any("source class" in item for item in errors),
            },
        },
        "errors": errors,
        "warnings": warnings,
    }


def markdown_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Repository Validation",
        "",
        f"- Generated: `{result['generated_at']}`",
        f"- Valid: `{'YES' if result['valid'] else 'NO'}`",
        f"- Resource records: `{summary['resource_record_count']}`",
        f"- Duplicate hash groups: `{summary['duplicate_hash_group_count']}`",
        f"- Ledger blocks: `{summary['ledger_block_count']}`",
        f"- Ledger tip: `{summary['ledger_chain_tip']}`",
        f"- Errors: `{summary['error_count']}`",
        f"- Warnings: `{summary['warning_count']}`",
        "",
        "## Errors",
        "",
    ]
    lines.extend(f"- {item}" for item in result["errors"])
    if not result["errors"]:
        lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in result["warnings"])
    if not result["warnings"]:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def write_reports(project_root: Path, result: dict[str, Any]) -> None:
    reports = project_root / "reports"
    atomic_write_text(
        reports / "repository_validation.json",
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(reports / "repository_validation.md", markdown_report(result))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = validate_repository(PROJECT_ROOT)
    write_reports(PROJECT_ROOT, result)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
