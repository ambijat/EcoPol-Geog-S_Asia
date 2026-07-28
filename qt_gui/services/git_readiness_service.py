from __future__ import annotations

import json
from pathlib import Path

from gui.services import git_readiness
from qt_gui.database.connection import DatabaseManager


class GitReadinessService:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def report(self, lecture_number: int = 1):
        return git_readiness(self.database.project_root, lecture_number)

    def governance_status(self, lecture_number: int = 1):
        report = self.report(lecture_number)
        ledger_path = self.database.project_root / "course_ledger" / "ledger.jsonl"
        blocks = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        registry_path = self.database.project_root / "resource_registry" / "resources.jsonl"
        registry_count = len([line for line in registry_path.read_text(encoding="utf-8").splitlines() if line.strip()])
        with self.database.connection() as connection:
            pair=connection.execute("select id from lecture_pairs where lecture_number=?",(lecture_number,)).fetchone()
            latest=connection.execute("select * from deliverable_bundles where lecture_pair_id=? order by created_at desc,id desc limit 1",(pair[0],)).fetchone()
            draft_count=connection.execute("select count(*) from draft_ledger_events where lecture_pair_id=?",(pair[0],)).fetchone()[0]
        return {
            **report,
            "ledger_block_count": len(blocks),
            "ledger_chain_tip": blocks[-1]["content_hash"] if blocks else "",
            "registry_record_count": registry_count,
            "historical_preservation_status": "READ_ONLY_CENSUS_BASELINE_AVAILABLE",
            "git_writes_enabled": False,
            "canonical_ledger_writes_enabled": False,
            "latest_deliverable_version": latest["version"] if latest else "NONE",
            "latest_deliverable_state": latest["status"] if latest else "NONE",
            "latest_validation_status": latest["validation_status"] if latest else "NOT_RUN",
            "latest_deliverable_classification": "PRIVATE_LOCAL" if latest else "NOT_APPLICABLE",
            "draft_event_count": draft_count,
            "canonical_ledger_status": "UNCHANGED_READ_ONLY",
        }
