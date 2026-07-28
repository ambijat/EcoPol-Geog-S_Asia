#!/usr/bin/env python3
"""Append to and verify the IS 529 N hash-linked course ledger."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = PROJECT_ROOT / "course_ledger" / "ledger.jsonl"
GENESIS_PREVIOUS_HASH = "0" * 64

BLOCK_DEFAULTS: dict[str, Any] = {
    "block_type": "WORKFLOW_EVENT",
    "course_code": "IS 529 N",
    "semester": "Semester 2026",
    "academic_year": "2026",
    "date": None,
    "time_created": None,
    "class_date": None,
    "created_by": "AI teaching assistant",
    "approved_by": None,
    "title": None,
    "source_material": [],
    "summary": None,
    "topics_planned": [],
    "topics_covered": [],
    "topics_deferred": [],
    "readings_used": [],
    "classroom_activities": [],
    "student_questions": [],
    "instructor_observations": [],
    "decisions_taken": [],
    "follow_up_actions": [],
    "fidelity_status": "F0 — Unverified draft",
    "confidentiality_status": "NO_STUDENT_DATA",
    "approval_status": "DRAFT",
    "record_mode": "CONTEMPORANEOUS",
    "event_time": None,
    "event_time_precision": "UNKNOWN",
    "recorded_at": None,
    "evidence": [],
    "certainty": "UNVERIFIED",
    "repository_scope": ["PROJECT_FOLDER"],
    "related_files": [],
    "related_commit": None,
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def canonical_bytes(block: dict[str, Any]) -> bytes:
    payload = {key: value for key, value in block.items() if key != "content_hash"}
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def calculate_hash(block: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(block)).hexdigest()


def read_blocks(handle: Any) -> list[dict[str, Any]]:
    handle.seek(0)
    blocks: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(handle, start=1):
        if not raw_line.strip():
            continue
        try:
            blocks.append(json.loads(raw_line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"ledger line {line_number} is invalid JSON: {exc}") from exc
    return blocks


def verify_blocks(blocks: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    expected_previous = GENESIS_PREVIOUS_HASH
    for expected_number, block in enumerate(blocks, start=1):
        label = f"block {expected_number}"
        if block.get("block_number") != expected_number:
            errors.append(
                f"{label}: block_number is {block.get('block_number')!r}, expected {expected_number}"
            )
        if block.get("previous_block_hash") != expected_previous:
            errors.append(f"{label}: previous_block_hash does not match the chain")
        observed_hash = block.get("content_hash")
        calculated_hash = calculate_hash(block)
        if observed_hash != calculated_hash:
            errors.append(f"{label}: content_hash does not match canonical content")
        if not isinstance(observed_hash, str):
            errors.append(f"{label}: content_hash is missing or invalid")
            expected_previous = ""
        else:
            expected_previous = observed_hash
    return errors


def build_block(
    event: dict[str, Any], block_number: int, previous_hash: str
) -> dict[str, Any]:
    unexpected = set(event).intersection(
        {"block_number", "previous_block_hash", "content_hash"}
    )
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise ValueError(f"chain-controlled fields may not be supplied: {names}")

    block = dict(BLOCK_DEFAULTS)
    block.update(event)
    recorded_at = block.get("recorded_at") or utc_now()
    block["recorded_at"] = recorded_at
    block["time_created"] = block.get("time_created") or recorded_at
    block["date"] = block.get("date") or recorded_at[:10]
    block["block_number"] = block_number
    block["previous_block_hash"] = previous_hash

    missing = [key for key, value in block.items() if key in {"title", "summary"} and not value]
    if missing:
        raise ValueError(f"required event fields are empty: {', '.join(missing)}")
    block["content_hash"] = calculate_hash(block)
    return block


def append_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        existing = read_blocks(handle)
        errors = verify_blocks(existing)
        if errors:
            raise ValueError("existing ledger failed verification: " + "; ".join(errors))

        previous_hash = (
            existing[-1]["content_hash"] if existing else GENESIS_PREVIOUS_HASH
        )
        appended: list[dict[str, Any]] = []
        for offset, event in enumerate(events, start=1):
            block = build_block(event, len(existing) + offset, previous_hash)
            handle.seek(0, os.SEEK_END)
            handle.write(json.dumps(block, ensure_ascii=False, sort_keys=True) + "\n")
            previous_hash = block["content_hash"]
            appended.append(block)
        handle.flush()
        os.fsync(handle.fileno())
        return appended


def load_event_file(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return data
    raise ValueError("event file must contain one JSON object or an array of objects")


def command_append(args: argparse.Namespace) -> int:
    events = load_event_file(args.event_file)
    appended = append_events(events)
    for block in appended:
        print(
            f"appended block {block['block_number']}: "
            f"{block['block_type']} {block['content_hash']}"
        )
    return 0


def command_verify(_: argparse.Namespace) -> int:
    if not LEDGER_PATH.exists():
        print(f"ledger does not exist: {LEDGER_PATH}")
        return 1
    with LEDGER_PATH.open("r", encoding="utf-8") as handle:
        blocks = read_blocks(handle)
    errors = verify_blocks(blocks)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    tip = blocks[-1]["content_hash"] if blocks else GENESIS_PREVIOUS_HASH
    print(f"verified {len(blocks)} blocks")
    print(f"chain tip: {tip}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    append_parser = subparsers.add_parser("append", help="append JSON event blocks")
    append_parser.add_argument("event_file", type=Path)
    append_parser.set_defaults(func=command_append)

    verify_parser = subparsers.add_parser("verify", help="verify the complete chain")
    verify_parser.set_defaults(func=command_verify)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
