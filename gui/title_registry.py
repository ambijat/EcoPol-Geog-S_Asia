from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

from gui.services import utc_now


WEEKLY_FILE = Path("course/lecture_titles.txt")
PART_FILE = Path("course/lecture_part_titles.txt")
PENDING_TITLE = "Pending instructor confirmation"
TITLE_STATUSES = (
    "HISTORICALLY_EXTRACTED", "FILENAME_INFERRED", "WORKING_DRAFT",
    "INSTRUCTOR_CONFIRMED", "PENDING",
)


@dataclass(frozen=True)
class TitleRegistryError(ValueError):
    errors: tuple[str, ...]

    def __str__(self) -> str:
        return "; ".join(self.errors)


def valid_weekly_ids() -> set[str]:
    return {f"L{number:02d}" for number in range(1, 16)}


def valid_part_ids() -> set[str]:
    return {f"L{number:02d}{part}" for number in range(1, 16) for part in "AB"}


def parse_title_text(text: str, valid_ids: set[str], label: str) -> dict[str, str]:
    records: dict[str, str] = {}
    errors = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.count("|") != 1:
            errors.append(f"{label}:{line_number}: expected exactly one vertical-bar delimiter")
            continue
        identifier, title = (part.strip() for part in line.split("|", 1))
        if identifier not in valid_ids:
            errors.append(f"{label}:{line_number}: unknown identifier {identifier or '<blank>'}")
        elif identifier in records:
            errors.append(f"{label}:{line_number}: duplicate identifier {identifier}")
        elif not title:
            errors.append(f"{label}:{line_number}: blank title for {identifier}")
        else:
            records[identifier] = title
    missing = sorted(valid_ids - records.keys())
    if missing:
        errors.append(f"{label}: missing identifiers: {', '.join(missing)}")
    if errors:
        raise TitleRegistryError(tuple(errors))
    return records


def parse_title_file(path: Path, valid_ids: set[str]) -> dict[str, str]:
    return parse_title_text(path.read_text(encoding="utf-8"), valid_ids, path.name)


def load_title_files(project_root: Path) -> tuple[dict[str, str], dict[str, str]]:
    errors = []
    weekly = parts = None
    for path, identifiers, target in (
        (project_root / WEEKLY_FILE, valid_weekly_ids(), "weekly"),
        (project_root / PART_FILE, valid_part_ids(), "parts"),
    ):
        try:
            parsed = parse_title_file(path, identifiers)
            if target == "weekly":
                weekly = parsed
            else:
                parts = parsed
        except (OSError, TitleRegistryError) as exc:
            errors.extend(exc.errors if isinstance(exc, TitleRegistryError) else (str(exc),))
    if errors:
        raise TitleRegistryError(tuple(errors))
    return weekly or {}, parts or {}


def title_precedence(title_source: str, title_status: str) -> int:
    if title_status == "INSTRUCTOR_CONFIRMED":
        return 50
    if title_status == "WORKING_DRAFT":
        return 40
    if title_source == "TITLE_REGISTRY":
        return 30
    if title_status == "HISTORICALLY_EXTRACTED":
        return 20
    if title_status == "FILENAME_INFERRED":
        return 10
    return 0


def propose_title_sync(connection: sqlite3.Connection, project_root: Path) -> int:
    weekly, parts = load_title_files(project_root)
    cursor = connection.execute(
        """INSERT INTO title_sync_batches(status,created_at,source_weekly_file,source_part_file)
        VALUES ('PROPOSED',?,?,?)""",
        (utc_now(), WEEKLY_FILE.as_posix(), PART_FILE.as_posix()),
    )
    batch_id = cursor.lastrowid
    for target_type, records in (("LECTURE_PAIR", weekly), ("LECTURE_PART", parts)):
        for identifier, proposed in records.items():
            if target_type == "LECTURE_PAIR":
                row = connection.execute(
                    "SELECT weekly_title AS title,title_status,title_confirmed FROM lecture_pairs WHERE lecture_id=?",
                    (f"IS529N-{identifier}",),
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT title,title_status,title_confirmed FROM lecture_parts WHERE identifier=?",
                    (f"IS529N-{identifier[:3]}-{identifier[3]}",),
                ).fetchone()
            conflict = bool(row["title_confirmed"] and row["title"] != proposed)
            reason = "INSTRUCTOR_CONFIRMED_TITLE_PROTECTED" if conflict else "UNCHANGED" if row["title"] == proposed else "TITLE_REGISTRY_UPDATE"
            connection.execute(
                """INSERT INTO title_sync_proposals(batch_id,target_type,target_identifier,
                current_title,proposed_title,conflict,reason) VALUES (?,?,?,?,?,?,?)""",
                (batch_id, target_type, identifier, row["title"], proposed, int(conflict), reason),
            )
            if conflict:
                connection.execute(
                    """INSERT INTO title_registry_conflicts(batch_id,target_identifier,protected_title,
                    proposed_title,created_at) VALUES (?,?,?,?,?)""",
                    (batch_id, identifier, row["title"], proposed, utc_now()),
                )
    connection.commit()
    return batch_id


def apply_selected_title_sync(
    connection: sqlite3.Connection, batch_id: int, proposal_ids: set[int] | None = None,
) -> int:
    batch = connection.execute("SELECT status FROM title_sync_batches WHERE id=?", (batch_id,)).fetchone()
    if batch is None or batch["status"] != "PROPOSED":
        raise ValueError("title sync batch is unavailable or already resolved")
    changed = 0
    for proposal in connection.execute(
        "SELECT * FROM title_sync_proposals WHERE batch_id=? ORDER BY id", (batch_id,)
    ):
        if proposal_ids is not None and proposal["id"] not in proposal_ids:
            continue
        if proposal["conflict"] or proposal["current_title"] == proposal["proposed_title"]:
            continue
        status = "PENDING" if proposal["proposed_title"] == PENDING_TITLE else "HISTORICALLY_EXTRACTED"
        if proposal["target_type"] == "LECTURE_PAIR":
            connection.execute(
                """UPDATE lecture_pairs SET weekly_title=?,title_source='TITLE_REGISTRY',
                title_status=?,title_confirmed=0,title_last_synced_at=? WHERE lecture_id=?""",
                (proposal["proposed_title"], status, utc_now(), f"IS529N-{proposal['target_identifier']}"),
            )
        else:
            identifier = proposal["target_identifier"]
            connection.execute(
                """UPDATE lecture_parts SET title=?,title_source='TITLE_REGISTRY',
                title_status=?,title_confirmed=0,title_last_synced_at=? WHERE identifier=?""",
                (proposal["proposed_title"], status, utc_now(), f"IS529N-{identifier[:3]}-{identifier[3]}"),
            )
        changed += 1
    connection.execute(
        "UPDATE title_sync_batches SET status='APPLIED',applied_at=? WHERE id=?",
        (utc_now(), batch_id),
    )
    connection.commit()
    return changed


def apply_title_sync(connection: sqlite3.Connection, batch_id: int) -> int:
    return apply_selected_title_sync(connection, batch_id)


def edit_title(
    connection: sqlite3.Connection, target_type: str, identifier: str, title: str,
    confirmed: bool,
) -> None:
    title = title.strip()
    if not title:
        raise ValueError("title may not be blank")
    status = "INSTRUCTOR_CONFIRMED" if confirmed else "WORKING_DRAFT"
    if target_type == "LECTURE_PAIR" and identifier in valid_weekly_ids():
        connection.execute(
            """UPDATE lecture_pairs SET weekly_title=?,title_source='MANUAL_GUI',title_status=?,
            title_confirmed=?,title_last_synced_at=? WHERE lecture_id=?""",
            (title, status, int(confirmed), utc_now(), f"IS529N-{identifier}"),
        )
    elif target_type == "LECTURE_PART" and identifier in valid_part_ids():
        connection.execute(
            """UPDATE lecture_parts SET title=?,title_source='MANUAL_GUI',title_status=?,
            title_confirmed=?,title_last_synced_at=? WHERE identifier=?""",
            (title, status, int(confirmed), utc_now(), f"IS529N-{identifier[:3]}-{identifier[3]}"),
        )
    else:
        raise ValueError("unknown title target")
    connection.commit()


def atomic_registry_write(path: Path, records: dict[str, str], header: str) -> Path:
    backup = path.with_name(path.name + ".bak")
    if path.exists():
        shutil.copy2(path, backup)
    text = header + "\n" + "\n".join(f"{identifier}|{records[identifier]}" for identifier in sorted(records)) + "\n"
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
    return backup


def export_confirmed_titles(connection: sqlite3.Connection, project_root: Path) -> tuple[Path, Path]:
    weekly, parts = load_title_files(project_root)
    for row in connection.execute("SELECT lecture_id,weekly_title FROM lecture_pairs WHERE title_confirmed=1"):
        weekly[row["lecture_id"].replace("IS529N-", "")] = row["weekly_title"]
    for row in connection.execute("SELECT identifier,title FROM lecture_parts WHERE title_confirmed=1"):
        parts[row["identifier"].replace("IS529N-", "").replace("-", "")] = row["title"]
    weekly_backup = atomic_registry_write(
        project_root / WEEKLY_FILE, weekly,
        "# Title registry. Instructor-confirmed GUI titles take precedence. Format: ID|Title",
    )
    part_backup = atomic_registry_write(
        project_root / PART_FILE, parts,
        "# Title registry. Instructor-confirmed GUI titles take precedence. Format: ID|Title",
    )
    return weekly_backup, part_backup
