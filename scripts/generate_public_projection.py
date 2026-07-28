#!/usr/bin/env python3
"""Generate public-safe, explicitly non-canonical IS529N projections."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path("config/public_projection_paths.local.json")
CANONICAL_PREAMBLE = Path("SEMESTER2026_Course_Governance_Preamble.md")
CANONICAL_LEDGER = Path("course_ledger/ledger.jsonl")
CANONICAL_RETROSPECTIVE = Path(
    "course_ledger/retrospective_events_2026-07-20.json"
)
PUBLIC_PREAMBLE = Path(
    "public/governance/SEMESTER2026_Course_Governance_Preamble_PUBLIC.md"
)
PUBLIC_LEDGER = Path("public/ledger/ledger_public.jsonl")
PUBLIC_RETROSPECTIVE = Path(
    "public/ledger/retrospective_events_2026-07-20_PUBLIC.json"
)
PUBLIC_MANIFEST = Path("public/reports/public_projection_manifest.json")

ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])/(?:home|media|mnt|run/media|srv|opt|var|tmp|Users|Volumes)/[^\s`\"'\]\[{}<>|]+"),
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:\\(?:[^\s`\"'<>|]+\\)*[^\s`\"'<>|]*"),
)
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(
        r"(?i)\b(?:api[_ -]?key|access[_ -]?token|password|passwd|secret)"
        r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}"
    ),
)
STUDENT_IDENTIFIER_PATTERNS = (
    re.compile(
        r"(?i)\b(?:student[_ -]?(?:id|name|email)|roll[_ -]?(?:number|no))"
        r"\s*[:=]\s*['\"]?[A-Za-z0-9_@.+-]{2,}"
    ),
    re.compile(r"(?i)\bregistration[_ -]?(?:number|no)\s*[:=]\s*[A-Za-z0-9_-]{3,}"),
)
LOCAL_OPERATIONAL_PATTERNS = (
    (
        "LOCAL_GIT_COMMIT_IDENTIFIER",
        re.compile(r"\b[0-9a-f]{40}\b"),
        "<LOCAL_GIT_COMMIT>",
    ),
)

PUBLIC_LEDGER_FIELDS = (
    "block_type",
    "title",
    "date",
    "event_time",
    "event_time_precision",
    "record_mode",
    "approval_status",
    "approved_by",
    "fidelity_status",
    "certainty",
    "summary",
    "topics_planned",
    "topics_covered",
    "topics_deferred",
    "decisions_taken",
    "follow_up_actions",
    "corrections_recorded",
    "governance_effect",
    "hosted_source_governance_status",
    "substantive_course_content_adoption",
    "primary_end_product",
)


class ProjectionError(ValueError):
    """Raised when public projection safety cannot be established."""


@dataclass(frozen=True)
class RedactionRule:
    category: str
    source: str
    replacement: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def load_rules(path: Path) -> list[RedactionRule]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"cannot read redaction configuration {path}: {exc}") from exc
    records = payload.get("redactions") if isinstance(payload, dict) else None
    if not isinstance(records, list) or not records:
        raise ProjectionError("redaction configuration requires a non-empty redactions list")
    rules: list[RedactionRule] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ProjectionError(f"redaction rule {index} must be an object")
        values = [record.get(key) for key in ("category", "source", "replacement")]
        if not all(isinstance(value, str) and value for value in values):
            raise ProjectionError(f"redaction rule {index} has an empty or invalid field")
        category, source, replacement = values
        if not (source.startswith("/") or re.match(r"^[A-Za-z]:\\", source)):
            raise ProjectionError(f"redaction rule {index} source must be an absolute path")
        if not re.fullmatch(r"<[A-Z0-9_]+>", replacement):
            raise ProjectionError(f"redaction rule {index} replacement must be symbolic")
        rules.append(RedactionRule(category, source.rstrip("/\\"), replacement))
    return sorted(rules, key=lambda rule: len(rule.source), reverse=True)


def redact_text(text: str, rules: list[RedactionRule]) -> tuple[str, Counter[str]]:
    counts: Counter[str] = Counter()
    for rule in rules:
        observed = text.count(rule.source)
        if observed:
            text = text.replace(rule.source, rule.replacement)
            counts[rule.category] += observed
    for category, pattern, replacement in LOCAL_OPERATIONAL_PATTERNS:
        text, observed = pattern.subn(replacement, text)
        if observed:
            counts[category] += observed
    reject_unsafe_text(text)
    return text, counts


def reject_unsafe_text(text: str) -> None:
    unresolved: list[str] = []
    for pattern in ABSOLUTE_PATH_PATTERNS:
        unresolved.extend(match.group(0) for match in pattern.finditer(text))
    if unresolved:
        examples = ", ".join(sorted(set(unresolved))[:3])
        raise ProjectionError(f"unresolved absolute path remains: {examples}")
    if EMAIL_PATTERN.search(text):
        raise ProjectionError("email address detected in public projection")
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        raise ProjectionError("credential or secret pattern detected in public projection")
    if any(pattern.search(text) for pattern in STUDENT_IDENTIFIER_PATTERNS):
        raise ProjectionError("student identifier pattern detected in public projection")


def redact_value(value: Any, rules: list[RedactionRule]) -> tuple[Any, Counter[str]]:
    if isinstance(value, str):
        return redact_text(value, rules)
    if isinstance(value, list):
        result: list[Any] = []
        counts: Counter[str] = Counter()
        for item in value:
            redacted, item_counts = redact_value(item, rules)
            result.append(redacted)
            counts.update(item_counts)
        return result, counts
    if isinstance(value, dict):
        result_dict: dict[str, Any] = {}
        counts = Counter()
        for key, item in value.items():
            redacted, item_counts = redact_value(item, rules)
            result_dict[key] = redacted
            counts.update(item_counts)
        return result_dict, counts
    return value, Counter()


def project_preamble(source: bytes, rules: list[RedactionRule]) -> tuple[bytes, Counter[str]]:
    body, counts = redact_text(source.decode("utf-8"), rules)
    header = (
        "---\n"
        "document_type: PUBLIC_REDACTED_PROJECTION\n"
        "canonical_source: LOCAL_PRIVATE_GOVERNANCE_RECORD\n"
        "authoritative: false\n"
        "public_safe: true\n"
        "---\n\n"
    )
    output = (header + body).encode("utf-8")
    reject_unsafe_text(output.decode("utf-8"))
    return output, counts


def project_ledger(source: bytes, rules: list[RedactionRule]) -> tuple[bytes, Counter[str]]:
    lines: list[str] = []
    counts: Counter[str] = Counter()
    for line_number, raw_line in enumerate(source.decode("utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            block = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ProjectionError(f"canonical ledger line {line_number} is invalid: {exc}") from exc
        redacted_block, block_counts = redact_value(block, rules)
        counts.update(block_counts)
        projected: dict[str, Any] = {
            "projection_type": "PUBLIC_REDACTED_PROJECTION",
            "canonical_authority": "LOCAL_PRIVATE_LEDGER",
            "cryptographic_status": "NON_CANONICAL",
            "canonical_block_number": redacted_block.get("block_number"),
            "canonical_content_hash": redacted_block.get("content_hash"),
            "previous_canonical_block_reference": redacted_block.get("previous_block_hash"),
        }
        for field in PUBLIC_LEDGER_FIELDS:
            if field in redacted_block:
                projected[field] = redacted_block[field]
        encoded = json.dumps(projected, ensure_ascii=False, sort_keys=True)
        reject_unsafe_text(encoded)
        lines.append(encoded)
    return ("\n".join(lines) + "\n").encode("utf-8"), counts


def project_retrospective(
    source: bytes, rules: list[RedactionRule]
) -> tuple[bytes, Counter[str]]:
    try:
        events = json.loads(source.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectionError(f"canonical retrospective record is invalid: {exc}") from exc
    if not isinstance(events, list):
        raise ProjectionError("canonical retrospective record must be a JSON array")
    projected_events: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            raise ProjectionError(f"retrospective event {index} is not an object")
        redacted_event, event_counts = redact_value(event, rules)
        counts.update(event_counts)
        projected: dict[str, Any] = {
            "projection_type": "PUBLIC_REDACTED_PROJECTION",
            "canonical_authority": "LOCAL_PRIVATE_RETROSPECTIVE_EVENT_RECORD",
            "cryptographic_status": "NON_CANONICAL",
            "canonical_event_index": index,
        }
        for field in PUBLIC_LEDGER_FIELDS:
            if field in redacted_event:
                projected[field] = redacted_event[field]
        projected_events.append(projected)
    output = (json.dumps(projected_events, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    reject_unsafe_text(output.decode("utf-8"))
    return output, counts


def symbolic_source(path: Path) -> str:
    return f"<ACTIVE_PROJECT_ROOT>/{path.as_posix()}"


def manifest_bytes(
    generated_at: str,
    source_records: list[tuple[Path, Path, bytes, bytes, Counter[str]]],
) -> bytes:
    records = []
    for source_path, output_path, source_data, output_data, counts in source_records:
        records.append(
            {
                "canonical_source": symbolic_source(source_path),
                "public_output": output_path.as_posix(),
                "canonical_source_sha256": sha256_bytes(source_data),
                "public_projection_sha256": sha256_bytes(output_data),
                "checksum_label": "PUBLIC_PROJECTION_FILE_SHA256",
                "redaction_count": sum(counts.values()),
                "redaction_categories": dict(sorted(counts.items())),
                "generation_timestamp": generated_at,
                "projection_status": "PUBLIC_REDACTED_PROJECTION",
                "validation_status": "PASSED",
            }
        )
    payload = {
        "document_type": "PUBLIC_PROJECTION_MANIFEST",
        "authoritative": False,
        "canonical_authority": "LOCAL_PRIVATE_RECORDS",
        "generation_timestamp": generated_at,
        "projection_status": "PUBLIC_REDACTED_PROJECTION",
        "validation_status": "PASSED",
        "records": records,
    }
    output = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    reject_unsafe_text(output.decode("utf-8"))
    return output


def generate_projection(
    project_root: Path,
    config_path: Path,
    *,
    dry_run: bool = False,
    generated_at: str | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    config_path = config_path if config_path.is_absolute() else project_root / config_path
    rules = load_rules(config_path)
    generated_at = generated_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    source_paths = (CANONICAL_PREAMBLE, CANONICAL_LEDGER, CANONICAL_RETROSPECTIVE)
    source_data = {path: (project_root / path).read_bytes() for path in source_paths}
    source_hashes = {path: sha256_bytes(data) for path, data in source_data.items()}

    preamble_data, preamble_counts = project_preamble(source_data[CANONICAL_PREAMBLE], rules)
    ledger_data, ledger_counts = project_ledger(source_data[CANONICAL_LEDGER], rules)
    retrospective_data, retrospective_counts = project_retrospective(
        source_data[CANONICAL_RETROSPECTIVE], rules
    )
    records = [
        (CANONICAL_PREAMBLE, PUBLIC_PREAMBLE, source_data[CANONICAL_PREAMBLE], preamble_data, preamble_counts),
        (CANONICAL_LEDGER, PUBLIC_LEDGER, source_data[CANONICAL_LEDGER], ledger_data, ledger_counts),
        (
            CANONICAL_RETROSPECTIVE,
            PUBLIC_RETROSPECTIVE,
            source_data[CANONICAL_RETROSPECTIVE],
            retrospective_data,
            retrospective_counts,
        ),
    ]
    manifest_data = manifest_bytes(generated_at, records)

    if not dry_run:
        for _, output_path, _, output_data, _ in records:
            atomic_write_bytes(project_root / output_path, output_data)
        atomic_write_bytes(project_root / PUBLIC_MANIFEST, manifest_data)

    for path, expected_hash in source_hashes.items():
        if sha256_bytes((project_root / path).read_bytes()) != expected_hash:
            raise ProjectionError(f"canonical source changed during generation: {path}")

    return {
        "dry_run": dry_run,
        "generation_timestamp": generated_at,
        "validation_status": "PASSED",
        "outputs": [
            {
                "path": output_path.as_posix(),
                "redaction_count": sum(counts.values()),
                "redaction_categories": dict(sorted(counts.items())),
                "sha256": sha256_bytes(output_data),
            }
            for _, output_path, _, output_data, counts in records
        ],
        "manifest_sha256": sha256_bytes(manifest_data),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = generate_projection(args.project_root, args.config, dry_run=args.dry_run)
    except (OSError, ProjectionError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
