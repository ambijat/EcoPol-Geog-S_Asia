"""Read-only adapter exposing lecture, part and knowledge-cluster information
from the browser lecture cockpit database to the desktop artifact cockpit.

Architectural boundary
----------------------
The browser lecture database is the source of truth for lecture pairs, lecture
parts, knowledge clusters, teaching questions, slide ranges, lecture workflow
status and deliverable references. The desktop artifact database is the source
of truth for artifact classes, scan sessions, scan candidates, registered
artifacts, relationships and instructor artifact decisions.

This module reads the browser database only. It contains no desktop SQL: the
lecture-level candidate pool figures are obtained from
``course_artifacts.services.candidate_pool_service``, which reads the desktop
database through its own read-only connection. The two databases are never
merged and neither is written to.

Result contract
---------------
``lecture_evidence_rows(lecture_number, part="A")`` returns one dict per
knowledge cluster, in natural cluster order (``slide_start``, then
``cluster_id``). Every row carries exactly the keys in :data:`ROW_KEYS`:

===========================  ==========================================================
Key                          Meaning
===========================  ==========================================================
``lecture_number``           int, from ``lecture_pairs.lecture_number``
``part``                     str, ``"A"`` or ``"B"``
``lecture_id``               str, ``lecture_parts.identifier`` (falls back to
                             ``lecture_pairs.lecture_id`` + part)
``cluster_id``               str, e.g. ``"KC01"``
``cluster_title``            str, ``lecture_knowledge_clusters.title``
``slide_range``              str, ``"<start>-<end>"``; ``UNAVAILABLE`` if unrecorded
``teaching_question``        str, ``lecture_knowledge_clusters.thematic_function``
``topical_evidence_count``   int | ``UNMAPPED`` | ``UNAVAILABLE``
``spatial_evidence_count``   int | ``UNMAPPED`` | ``UNAVAILABLE``
``ai_note_count``            int | ``UNMAPPED`` | ``UNAVAILABLE``
``workbench_status``         str, strongest statement the data model supports
``published_pdf_status``     str, strongest statement the data model supports
``instructor_review_status`` str, cluster status + part approval status
``next_action``              str, deterministic plain-language next action
===========================  ==========================================================

Evidence-count semantics
------------------------
Counts are never fabricated and zero is never inferred from missing rows:

* an **int** is returned only when an explicit cluster-level mapping exists for
  that category. Concretely, for Lecture 1A KC01 this is
  ``cluster_resource_alignments``: five rows (``KC01-S3-PURANA-01..05``,
  ``resource_group_id='LEC_RES_1'``), each a source-checked, page-referenced
  excerpt tagged ``cluster_alignment='DIRECT_SLIDE3_EVIDENCE'``, dated
  2026-07-22 — a real, already-curated evidence mapping, not a placeholder;
* :data:`UNMAPPED` is returned when the mapping structure exists for the
  category but carries no entry for this cluster — candidates may well exist
  in the repository, they have simply not been mapped (KC02–KC06 today);
* ``0`` is returned only when the cluster's own resource workflow stage is
  recorded ``COMPLETE`` and the mapping structure explicitly holds no items,
  i.e. an affirmative "mapped, and empty";
* :data:`UNAVAILABLE` is returned when the browser schema cannot express the
  category at all. ``cluster_resource_alignments.resource_id`` references the
  browser's own ``resources`` table only, which classifies material by
  ``source_layer`` (instructor original, past course run, raw resource, raw
  scholarly) and has no spatial-resource or AI-note dimension — there is no
  column or foreign key path by which a desktop ``SPATIAL_RESOURCE`` or
  ``AI_GENERATED_ARTIFACT`` scan candidate could ever be recorded here. Those
  two categories are therefore reported ``UNAVAILABLE`` at cluster grain, not
  guessed and not conflated with "not yet mapped".

A separate, lecture-wide (never cluster-level) candidate pool for all three
categories is available from
``course_artifacts.services.candidate_pool_service`` — see
``lecture_evidence_pool_summary()`` below. It answers a different question
("how much raw material has this lecture's scan census attributed to it") and
is deliberately never used to fill in a per-cluster count, so a lecture-wide
total is never mistaken for cluster-level evidence.

No AI is used anywhere in this module. All derivations are deterministic.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LECTURE_DATABASE = (
    PROJECT_ROOT / "gui" / "database" / "is529n_cockpit.sqlite3"
)
SYMBOLIC_LECTURE_DATABASE = "<PROJECT_ROOT>/gui/database/is529n_cockpit.sqlite3"

UNMAPPED = "UNMAPPED"
UNAVAILABLE = "UNAVAILABLE"

REQUIRED_TABLES = (
    "lecture_pairs",
    "lecture_parts",
    "lecture_knowledge_clusters",
)
OPTIONAL_TABLES = (
    "deliverable_bundles",
    "cluster_resource_alignments",
)

ROW_KEYS = (
    "lecture_number",
    "part",
    "lecture_id",
    "cluster_id",
    "cluster_title",
    "slide_range",
    "teaching_question",
    "topical_evidence_count",
    "spatial_evidence_count",
    "ai_note_count",
    "workbench_status",
    "published_pdf_status",
    "instructor_review_status",
    "next_action",
)


class LectureEvidenceError(RuntimeError):
    """Base domain error for the lecture evidence adapter."""


class LectureDatabaseUnavailable(LectureEvidenceError):
    """The browser lecture database is absent or cannot be opened read-only."""


class LectureDatabaseIncompatible(LectureEvidenceError):
    """The browser lecture database lacks tables this adapter depends on."""


@dataclass(frozen=True)
class LectureEvidenceRow:
    """Stable, documented row contract. See :data:`ROW_KEYS`."""

    lecture_number: int
    part: str
    lecture_id: str
    cluster_id: str
    cluster_title: str
    slide_range: str
    teaching_question: str
    topical_evidence_count: int | str
    spatial_evidence_count: int | str
    ai_note_count: int | str
    workbench_status: str
    published_pdf_status: str
    instructor_review_status: str
    next_action: str

    def as_dict(self) -> dict:
        return asdict(self)


@contextmanager
def read_only_connection(database_path: Path) -> Iterator[sqlite3.Connection]:
    """Open the lecture database read-only and close it deterministically.

    The browser application's own ``connect()`` factory is deliberately not used:
    it creates the parent directory and is paired with a migration routine, so it
    can initialise or upgrade the file. This adapter must never do either.
    """
    if not database_path.exists():
        raise LectureDatabaseUnavailable(
            "The lecture cockpit database was not found at "
            f"{SYMBOLIC_LECTURE_DATABASE}. Start the browser lecture cockpit "
            "once to create it, or pass an explicit database path to "
            "LectureEvidenceService."
        )
    try:
        connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    except sqlite3.Error as error:  # pragma: no cover - platform dependent
        raise LectureDatabaseUnavailable(
            "The lecture cockpit database at "
            f"{SYMBOLIC_LECTURE_DATABASE} could not be opened read-only: {error}"
        ) from error
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        yield connection
    finally:
        connection.close()


class LectureEvidenceService:
    """Read-only lecture/cluster reader over the browser lecture database."""

    def __init__(
        self,
        database_path: Path | str | None = None,
        pool_service: "CandidatePoolService | None" = None,
    ):
        self.database_path = Path(
            database_path or DEFAULT_LECTURE_DATABASE
        ).resolve()
        self._pool_service = pool_service

    @property
    def pool_service(self) -> "CandidatePoolService":
        if self._pool_service is None:
            from course_artifacts.services.candidate_pool_service import (
                CandidatePoolService,
            )

            self._pool_service = CandidatePoolService()
        return self._pool_service

    # ------------------------------------------------------------------ public
    def lecture_evidence_rows(
        self, lecture_number: int, part: str = "A"
    ) -> list[dict]:
        """Return one row per knowledge cluster, in natural cluster order.

        An unknown lecture number or part returns an empty list; that is a
        documented not-found result, not an error.
        """
        part = (part or "").strip().upper()
        with read_only_connection(self.database_path) as connection:
            self._require_schema(connection)
            pair = connection.execute(
                "SELECT id, lecture_id, lecture_number FROM lecture_pairs "
                "WHERE lecture_number=?",
                (lecture_number,),
            ).fetchone()
            if pair is None:
                return []
            part_row = connection.execute(
                "SELECT identifier, lifecycle_status, approval_status "
                "FROM lecture_parts WHERE lecture_pair_id=? AND part=?",
                (pair["id"], part),
            ).fetchone()
            clusters = connection.execute(
                "SELECT id, cluster_id, title, slide_start, slide_end, "
                "thematic_function, status, workflow_state "
                "FROM lecture_knowledge_clusters "
                "WHERE lecture_pair_id=? AND part=? "
                "ORDER BY slide_start, cluster_id",
                (pair["id"], part),
            ).fetchall()
            if not clusters:
                return []
            bundle = self._current_bundle(connection, pair["id"], part)
            alignments = self._alignment_counts(connection)

        lecture_id = self._lecture_identifier(pair, part_row, part)
        approval = (
            part_row["approval_status"] if part_row is not None else UNAVAILABLE
        ) or UNAVAILABLE
        workbench = self._workbench_status(bundle)
        published = self._published_pdf_status(bundle)

        rows: list[LectureEvidenceRow] = []
        for cluster in clusters:
            workflow = self._workflow_stages(cluster["workflow_state"])
            topical = self._topical_count(cluster["id"], alignments, workflow)
            rows.append(
                LectureEvidenceRow(
                    lecture_number=int(pair["lecture_number"]),
                    part=part,
                    lecture_id=lecture_id,
                    cluster_id=cluster["cluster_id"],
                    cluster_title=cluster["title"] or "",
                    slide_range=self._slide_range(cluster),
                    teaching_question=cluster["thematic_function"] or "",
                    topical_evidence_count=topical,
                    # cluster_resource_alignments.resource_id only ever
                    # references the browser's own `resources` table, which
                    # has no spatial or AI-note classification — see the
                    # module docstring.
                    spatial_evidence_count=UNAVAILABLE,
                    ai_note_count=UNAVAILABLE,
                    workbench_status=workbench,
                    published_pdf_status=published,
                    instructor_review_status=(
                        f"{cluster['status'] or UNAVAILABLE} · "
                        f"part {approval}"
                    ),
                    next_action=self._next_action(
                        cluster_status=cluster["status"] or "",
                        workflow=workflow,
                        topical=topical,
                    ),
                )
            )
        return [row.as_dict() for row in rows]

    def lecture_evidence_pool_summary(self, lecture_number: int) -> dict:
        """Lecture-level unallocated candidate pools.

        Delegates to the desktop artifact database reader; no desktop SQL is
        issued from this module. Returned separately from cluster rows because a
        lecture-level pool is explicitly *not* a cluster mapping.
        """
        return self.pool_service.lecture_pool_summary(lecture_number)

    # ----------------------------------------------------------------- schema
    @staticmethod
    def _require_schema(connection: sqlite3.Connection) -> None:
        present = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        missing = [name for name in REQUIRED_TABLES if name not in present]
        if missing:
            raise LectureDatabaseIncompatible(
                "The lecture cockpit database at "
                f"{SYMBOLIC_LECTURE_DATABASE} is missing required tables: "
                f"{', '.join(missing)}. Run the browser lecture cockpit's own "
                "migrations; this adapter never creates or upgrades schema."
            )

    # ------------------------------------------------------------- derivation
    @staticmethod
    def _lecture_identifier(pair, part_row, part: str) -> str:
        if part_row is not None and (part_row["identifier"] or "").strip():
            return part_row["identifier"].strip()
        base = (pair["lecture_id"] or "").strip()
        return f"{base}-{part}" if base else UNAVAILABLE

    @staticmethod
    def _slide_range(cluster) -> str:
        start, end = cluster["slide_start"], cluster["slide_end"]
        if start is None or end is None:
            return UNAVAILABLE
        return f"{int(start)}-{int(end)}"

    @staticmethod
    def _workflow_stages(workflow_state: str | None) -> dict:
        import json

        try:
            stages = json.loads(workflow_state or "{}")
        except (TypeError, ValueError):
            return {}
        return stages if isinstance(stages, dict) else {}

    @staticmethod
    def _alignment_counts(connection: sqlite3.Connection) -> dict | None:
        """Explicit cluster-level source mapping, keyed by cluster primary key.

        Each value is ``{"mapped": int, "undecided": int}``: how many alignment
        rows exist for the cluster, and how many still record an undecided
        instructor action. ``None`` is returned when the mapping structure
        itself is absent, which the caller reports as UNAVAILABLE rather than
        UNMAPPED.
        """
        present = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "cluster_resource_alignments" not in present:
            return None
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(cluster_resource_alignments)"
            )
        }
        undecided_sql = (
            "SUM(CASE WHEN instructor_action IN ('', 'NOT_YET_DECIDED') "
            "THEN 1 ELSE 0 END)"
            if "instructor_action" in columns
            else "0"
        )
        return {
            row["cluster_id"]: {
                "mapped": int(row["mapped"]),
                "undecided": int(row["undecided"] or 0),
            }
            for row in connection.execute(
                f"SELECT cluster_id, COUNT(*) AS mapped, "
                f"{undecided_sql} AS undecided "
                "FROM cluster_resource_alignments GROUP BY cluster_id"
            )
        }

    @staticmethod
    def _topical_count(
        cluster_pk: int, alignments: dict | None, workflow: dict
    ) -> int | str:
        if alignments is None:
            return UNAVAILABLE
        if cluster_pk in alignments:
            return alignments[cluster_pk]["mapped"]
        # No mapping row for this cluster. Zero is asserted only when the
        # cluster's own resource stage records the mapping as finished.
        if str(workflow.get("resources", "")).upper() == "COMPLETE":
            return 0
        return UNMAPPED

    @staticmethod
    def _current_bundle(
        connection: sqlite3.Connection, pair_pk: int, part: str
    ):
        present = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "deliverable_bundles" not in present:
            return None
        return connection.execute(
            "SELECT version, status, approved, visibility, "
            "classroom_use_status, validation_status, pptx_path, pdf_path, "
            "page_count FROM deliverable_bundles "
            "WHERE lecture_pair_id=? AND part=? ORDER BY id DESC LIMIT 1",
            (pair_pk, part),
        ).fetchone()

    @staticmethod
    def _workbench_status(bundle) -> str:
        """Strongest honest statement about the editable deck.

        Deliverable bundles are recorded per lecture part, not per cluster, and
        approval is a separate recorded flag. Both facts are stated explicitly
        rather than being collapsed into a claim of "current" or "approved".
        """
        if bundle is None:
            return UNAVAILABLE
        if not (bundle["pptx_path"] or "").strip():
            return "PART_LEVEL · NO_EDITABLE_DECK_REFERENCED"
        approval = (
            "INSTRUCTOR_APPROVED" if int(bundle["approved"] or 0)
            else "NOT_APPROVED"
        )
        return (
            f"PART_LEVEL · DELIVERABLE_REFERENCED {bundle['version']} "
            f"{bundle['status']} · {approval}"
        )

    @staticmethod
    def _published_pdf_status(bundle) -> str:
        """Strongest honest statement about the rendered PDF.

        A recorded path plus page count establishes that a PDF is *referenced*;
        it does not establish that the deck is published or cleared for the
        classroom, so the recorded visibility and classroom-use flags are shown.
        """
        if bundle is None:
            return UNAVAILABLE
        if not (bundle["pdf_path"] or "").strip():
            return "PART_LEVEL · NO_PDF_REFERENCED"
        pages = bundle["page_count"]
        pages_text = f"{int(pages)} pages" if pages else "page count unrecorded"
        return (
            f"PART_LEVEL · PDF_REFERENCED {bundle['version']} · {pages_text} · "
            f"{bundle['visibility'] or UNAVAILABLE} · "
            f"{bundle['classroom_use_status'] or UNAVAILABLE}"
        )

    @staticmethod
    def _next_action(
        cluster_status: str, workflow: dict, topical: int | str
    ) -> str:
        """One plain-language next action, from recorded state only.

        Deterministic ladder, first match wins. No AI, no heuristics over file
        names, no inference from anything the databases do not record.
        """
        stage = {
            key: str(value).upper() for key, value in workflow.items()
        }
        if cluster_status.upper() == "NOT_STARTED":
            return "Begin cluster preparation"
        if stage.get("acceptance") == "COMPLETE":
            return "No action required"
        if stage.get("acceptance") == "READY":
            return "Cluster awaiting instructor acceptance"
        if stage.get("slides") in {"READY", "REVIEW_REQUIRED"}:
            return "Review proposed slide reinforcement"
        if stage.get("patterns") in {"READY", "REVIEW_REQUIRED"}:
            return "Select knowledge pattern"
        if stage.get("resources") in {"READY", "IN_PROGRESS", "RETURNED"}:
            return "Map source groups to this cluster"
        if stage.get("cluster") == "READY":
            return "Review teaching question"
        if topical == UNMAPPED:
            return "Map source groups to this cluster"
        return "Continue cluster preparation"


def lecture_evidence_rows(lecture_number: int, part: str = "A") -> list[dict]:
    """Module-level convenience wrapper around :class:`LectureEvidenceService`."""
    return LectureEvidenceService().lecture_evidence_rows(lecture_number, part)


def lecture_evidence_pool_summary(lecture_number: int) -> dict:
    """Module-level convenience wrapper for the lecture-level pool summary."""
    return LectureEvidenceService().lecture_evidence_pool_summary(lecture_number)
