#!/usr/bin/env python3
"""Register an immutable local resource without modifying the source file."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = PROJECT_ROOT / "resource_registry" / "resources.jsonl"
RESOURCE_ID_RE = re.compile(r"^IS529N-RES-(\d{4,})$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
RESOURCE_TYPE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

SOURCE_CLASSES = {
    "INSTRUCTOR_MATERIAL", "HISTORICAL_RESOURCE", "ONLINE_SOURCE",
    "VERIFIED_EXTERNAL_MATERIAL", "AI_SYNTHESIS",
    "PROVISIONAL_INTERPRETATION", "APPROVED_COURSE_CONTENT",
}
VERIFICATION_STATUSES = {
    "UNVERIFIED", "CHECKSUM_VERIFIED", "SOURCE_CHECKED",
    "FACTUALLY_VERIFIED", "REJECTED",
}
FIDELITY_STATUSES = {"F0", "F1", "F2", "F3", "F4", "F5"}
COPYRIGHT_STATUSES = {
    "UNKNOWN", "INSTRUCTOR_OWNED", "LICENSED", "PUBLIC_DOMAIN",
    "FAIR_USE_REVIEW_REQUIRED", "RESTRICTED", "PERMISSION_GRANTED",
}
APPROVAL_STATUSES = {"DRAFT", "REVIEWED", "APPROVED", "SEALED", "SUPERSEDED"}
CONTROLLED_FIELDS = {
    "resource_id", "local_path", "content_sha256", "created_at", "updated_at"
}
REQUIRED_FIELDS = {
    "resource_id", "title", "resource_type", "source_class", "author",
    "publication_date", "original_location", "local_path", "accessed_date",
    "content_sha256", "course_relevance", "intended_use",
    "verification_status", "fidelity_status", "copyright_status",
    "approval_status", "notes", "created_at", "updated_at",
}


class RegistrationError(ValueError):
    """A safe registration failure."""


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def today_iso() -> str:
    return dt.date.today().isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def infer_resource_type(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return suffix.upper() if suffix else "BINARY"


def parse_date(value: Any, field: str, allow_null: bool = False) -> None:
    if value is None and allow_null:
        return
    if not isinstance(value, str):
        raise RegistrationError(f"{field} must be an ISO date string")
    try:
        dt.date.fromisoformat(value)
    except ValueError as exc:
        raise RegistrationError(f"{field} must use YYYY-MM-DD") from exc


def parse_datetime(value: Any, field: str) -> None:
    if not isinstance(value, str):
        raise RegistrationError(f"{field} must be an ISO date-time string")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RegistrationError(f"{field} is not a valid ISO date-time") from exc
    if parsed.tzinfo is None:
        raise RegistrationError(f"{field} must include a timezone")


def validate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(record)
    extra = set(record) - REQUIRED_FIELDS
    if missing:
        errors.append("missing fields: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("unexpected fields: " + ", ".join(sorted(extra)))
    if errors:
        return errors

    if not isinstance(record["resource_id"], str) or not RESOURCE_ID_RE.fullmatch(record["resource_id"]):
        errors.append("resource_id must match IS529N-RES-0001")
    if not isinstance(record["title"], str) or not record["title"].strip():
        errors.append("title must be a non-empty string")
    if not isinstance(record["resource_type"], str) or not RESOURCE_TYPE_RE.fullmatch(record["resource_type"]):
        errors.append("resource_type must be uppercase snake case")
    for field in ("original_location", "local_path"):
        if not isinstance(record[field], str) or not record[field].strip():
            errors.append(f"{field} must be a non-empty string")
    for field in ("author", "course_relevance", "intended_use", "notes"):
        if record[field] is not None and not isinstance(record[field], str):
            errors.append(f"{field} must be a string or null")
    if record["source_class"] not in SOURCE_CLASSES:
        errors.append("invalid source_class")
    if record["verification_status"] not in VERIFICATION_STATUSES:
        errors.append("invalid verification_status")
    if record["fidelity_status"] not in FIDELITY_STATUSES:
        errors.append("invalid fidelity_status")
    if record["copyright_status"] not in COPYRIGHT_STATUSES:
        errors.append("invalid copyright_status")
    if record["approval_status"] not in APPROVAL_STATUSES:
        errors.append("invalid approval_status")
    if not isinstance(record["content_sha256"], str) or not HASH_RE.fullmatch(record["content_sha256"]):
        errors.append("content_sha256 must be 64 lowercase hexadecimal characters")
    for field, allow_null in (("publication_date", True), ("accessed_date", False)):
        try:
            parse_date(record[field], field, allow_null)
        except RegistrationError as exc:
            errors.append(str(exc))
    for field in ("created_at", "updated_at"):
        try:
            parse_datetime(record[field], field)
        except RegistrationError as exc:
            errors.append(str(exc))
    return errors


def read_registry(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RegistrationError(
                    f"registry line {line_number} is malformed JSON: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise RegistrationError(f"registry line {line_number} is not an object")
            errors = validate_record(value)
            if errors:
                raise RegistrationError(
                    f"registry line {line_number} is invalid: {'; '.join(errors)}"
                )
            records.append(value)
    return records


def next_resource_id(records: list[dict[str, Any]]) -> str:
    numbers = [int(RESOURCE_ID_RE.fullmatch(record["resource_id"]).group(1)) for record in records]
    return f"IS529N-RES-{max(numbers, default=0) + 1:04d}"


def find_checksum_duplicate(records: list[dict[str, Any]], checksum: str) -> dict[str, Any] | None:
    return next((record for record in records if record["content_sha256"] == checksum), None)


def canonical_line(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def atomic_write_registry(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(canonical_line(record))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def prepare_metadata(path: Path, supplied: dict[str, Any]) -> dict[str, Any]:
    conflict = CONTROLLED_FIELDS.intersection(supplied)
    if conflict:
        raise RegistrationError(
            "metadata may not set controlled fields: " + ", ".join(sorted(conflict))
        )
    allowed = REQUIRED_FIELDS - CONTROLLED_FIELDS
    unknown = set(supplied) - allowed
    if unknown:
        raise RegistrationError("unknown metadata fields: " + ", ".join(sorted(unknown)))
    defaults: dict[str, Any] = {
        "title": path.name,
        "resource_type": infer_resource_type(path),
        "source_class": "HISTORICAL_RESOURCE",
        "author": None,
        "publication_date": None,
        "original_location": str(path.resolve()),
        "accessed_date": today_iso(),
        "course_relevance": None,
        "intended_use": None,
        "verification_status": "CHECKSUM_VERIFIED",
        "fidelity_status": "F0",
        "copyright_status": "UNKNOWN",
        "approval_status": "DRAFT",
        "notes": None,
    }
    defaults.update(supplied)
    if defaults["approval_status"] in {"APPROVED", "SEALED"}:
        raise RegistrationError("registration may not claim APPROVED or SEALED status")
    return defaults


def portable_local_path(path: Path, registry_path: Path) -> str:
    """Prefer a project-relative location when the file belongs to the project."""
    project_root = registry_path.resolve().parent.parent
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return str(path.resolve())


def build_record(
    path: Path,
    metadata: dict[str, Any],
    records: list[dict[str, Any]],
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    timestamp = now_iso()
    record = {
        **prepare_metadata(path, metadata),
        "resource_id": next_resource_id(records),
        "local_path": portable_local_path(path, registry_path),
        "content_sha256": sha256_file(path),
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    errors = validate_record(record)
    if errors:
        raise RegistrationError("invalid metadata: " + "; ".join(errors))
    return record


def register_resource(
    source_path: Path,
    metadata: dict[str, Any],
    registry_path: Path = DEFAULT_REGISTRY,
    dry_run: bool = False,
) -> dict[str, Any]:
    source_path = source_path.resolve(strict=True)
    if not source_path.is_file():
        raise RegistrationError("source path must be a regular file")

    if dry_run:
        records = read_registry(registry_path)
        record = build_record(source_path, metadata, records, registry_path)
        duplicate = find_checksum_duplicate(records, record["content_sha256"])
        if duplicate:
            raise RegistrationError(
                f"identical checksum already registered as {duplicate['resource_id']}"
            )
        return record

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = registry_path.parent / ".resources.lock"
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        records = read_registry(registry_path)
        record = build_record(source_path, metadata, records, registry_path)
        duplicate = find_checksum_duplicate(records, record["content_sha256"])
        if duplicate:
            raise RegistrationError(
                f"identical checksum already registered as {duplicate['resource_id']}"
            )
        atomic_write_registry(registry_path, [*records, record])
        return record


def load_metadata(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistrationError(f"cannot load metadata: {exc}") from exc
    if not isinstance(value, dict):
        raise RegistrationError("metadata must be a JSON object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("local_file", type=Path)
    parser.add_argument("--metadata", type=Path, help="JSON metadata object")
    parser.add_argument("--title")
    parser.add_argument("--resource-type")
    parser.add_argument("--source-class", choices=sorted(SOURCE_CLASSES))
    parser.add_argument("--author")
    parser.add_argument("--publication-date")
    parser.add_argument("--original-location")
    parser.add_argument("--accessed-date")
    parser.add_argument("--course-relevance")
    parser.add_argument("--intended-use")
    parser.add_argument("--verification-status", choices=sorted(VERIFICATION_STATUSES))
    parser.add_argument("--fidelity-status", choices=sorted(FIDELITY_STATUSES))
    parser.add_argument("--copyright-status", choices=sorted(COPYRIGHT_STATUSES))
    parser.add_argument("--notes")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        metadata = load_metadata(args.metadata)
        for key, value in vars(args).items():
            if key in {"local_file", "metadata", "dry_run"} or value is None:
                continue
            metadata[key] = value
        record = register_resource(args.local_file, metadata, dry_run=args.dry_run)
        print(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))
        if args.dry_run:
            print("dry run: registry was not modified")
        return 0
    except (OSError, RegistrationError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
