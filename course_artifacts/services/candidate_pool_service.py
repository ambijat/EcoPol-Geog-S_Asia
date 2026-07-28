"""Read-only lecture-level candidate pool counts from the desktop artifact
database.

This module exists so that no desktop SQL appears inside the browser-database
adapter (``lecture_evidence_service``). It reads the desktop artifact database
— the source of truth for scan sessions, scan candidates and registered
artifacts — and never writes to it.

A candidate pool is *not* a cluster mapping. These figures say how much material
a scan census attributed to a lecture; they say nothing about which knowledge
cluster any item supports. The summary therefore always carries
``mapping_status`` so a caller cannot mistake a pool total for evidence counts.

Census semantics
----------------
Historical scan sessions are retained in the database, so counting every
``scan_candidates`` row would count the same file once per rescan. This module
mirrors ``ScanRepository.latest_candidates``: for each artifact class it uses
the most recent ``COMPLETED`` scan session for that symbolic root, which is the
current census.

Lecture attribution
-------------------
A candidate belongs to lecture *N* when any segment of its class-relative path
is a lecture container token — ``LEC_N``, ``LEC_RES_N`` or ``LECT_N``, with
optional separators and leading zeros. Matching any segment (not only the first)
is required because the spatial resource root is organised country-first
(``PAKISTAN/LEC_1/...``). The rule is reported in the summary as
``attribution_rule`` so the derivation is visible to the reader.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from course_artifacts.config import CourseArtifactConfig


SYMBOLIC_ARTIFACT_DATABASE = (
    "<PROJECT_ROOT>/local_state/database/course_artifacts.sqlite3"
)

TOPICAL_CLASS = "FOUNDATIONAL_RESOURCE"
SPATIAL_CLASS = "SPATIAL_RESOURCE"
AI_NOTE_CLASS = "AI_GENERATED_ARTIFACT"

POOL_CLASSES = {
    "topical_candidate_pool": TOPICAL_CLASS,
    "spatial_candidate_pool": SPATIAL_CLASS,
    "ai_note_candidate_pool": AI_NOTE_CLASS,
}

LECTURE_SEGMENT = re.compile(r"(?:LEC_RES|LECT|LEC)[ _-]*0*(\d+)", re.IGNORECASE)
MAXIMUM_LECTURE = 15

UNAVAILABLE = "UNAVAILABLE"


class CandidatePoolUnavailable(RuntimeError):
    """The desktop artifact database is absent or cannot be opened read-only."""


@contextmanager
def read_only_connection(database_path: Path) -> Iterator[sqlite3.Connection]:
    """Open the artifact database read-only and close it deterministically."""
    if not database_path.exists():
        raise CandidatePoolUnavailable(
            "The desktop artifact database was not found at "
            f"{SYMBOLIC_ARTIFACT_DATABASE}. Start the desktop cockpit once to "
            "create it, or pass an explicit database path."
        )
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        yield connection
    finally:
        connection.close()


def lecture_of(relative_path: str) -> int | None:
    """Lecture number implied by a class-relative path, or ``None``."""
    for segment in Path(relative_path).parts:
        match = LECTURE_SEGMENT.fullmatch(segment)
        if match:
            number = int(match.group(1))
            if 1 <= number <= MAXIMUM_LECTURE:
                return number
    return None


class CandidatePoolService:
    """Read-only counts of unallocated scan candidates per lecture."""

    def __init__(self, config: CourseArtifactConfig | None = None):
        self.config = (config or CourseArtifactConfig()).resolved()
        self.database_path = self.config.database_path

    def lecture_pool_summary(self, lecture_number: int) -> dict:
        """Candidate pool totals for one lecture.

        Returns ``UNAVAILABLE`` for a category whose class has no completed scan
        census, so an absent scan is never reported as a pool of zero.
        """
        summary: dict = {
            "lecture_number": int(lecture_number),
            "mapping_status": "UNMAPPED",
            "source": "latest COMPLETED scan session per artifact class",
            "attribution_rule": (
                "any path segment matching LEC_<n> / LEC_RES_<n> / LECT_<n>"
            ),
            "census_sessions": {},
        }
        with read_only_connection(self.database_path) as connection:
            for key, class_code in POOL_CLASSES.items():
                session = connection.execute(
                    "SELECT id, scan_id, completed_at FROM scan_sessions "
                    "WHERE symbolic_root=? AND status='COMPLETED' "
                    "ORDER BY id DESC LIMIT 1",
                    (class_code,),
                ).fetchone()
                if session is None:
                    summary[key] = UNAVAILABLE
                    summary["census_sessions"][class_code] = UNAVAILABLE
                    continue
                paths = [
                    row["relative_path"]
                    for row in connection.execute(
                        "SELECT relative_path FROM scan_candidates "
                        "WHERE scan_session_id=?",
                        (session["id"],),
                    )
                ]
                summary[key] = sum(
                    1 for path in paths if lecture_of(path) == lecture_number
                )
                summary["census_sessions"][class_code] = {
                    "scan_id": session["scan_id"],
                    "completed_at": session["completed_at"],
                    "census_files": len(paths),
                }
        return summary
