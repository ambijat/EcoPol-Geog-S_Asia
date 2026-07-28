from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from gui.services import utc_now, validate_relative_path
from qt_gui.database.connection import DatabaseManager


class LedgerDraftService:
    TYPES={"LECTURE_PAIR_APPROVED","CLASS_SESSION_COMPLETED","TOPIC_DEFERRED","LECTURE_RETROSPECTIVE"}
    def __init__(self, database: DatabaseManager):
        self.database = database

    def prepare(self, number: int, event_type: str):
        if event_type not in self.TYPES:raise ValueError("unsupported draft ledger event")
        with self.database.connection() as connection:
            pair=connection.execute("select * from lecture_pairs where lecture_number=?",(number,)).fetchone()
            sessions=[dict(r) for r in connection.execute("select * from class_session_records where lecture_pair_id=? and instructor_validation_status='INSTRUCTOR_VALIDATED'",(pair["id"],))]
            if not sessions:raise ValueError("an instructor-validated class record is required")
            timestamp=utc_now(); token=timestamp.replace(":","").replace("+00:00","Z").replace("-","")
            event_id=f'{pair["lecture_id"]}-{event_type}-{token}-DRAFT'
            relative=validate_relative_path(f"course_ledger/drafts/qt/{event_id}.json")
            payload={"event_id":event_id,"event_type":event_type,"lecture_id":pair["lecture_id"],
                     "lecture_title":pair["weekly_title"],"approval_status":"DRAFT","canonical_append_authorised":False,
                     "canonical_block_number":None,"canonical_hash":None,"class_sessions":[s["session_id"] for s in sessions],
                     "created_by":"Application","created_at":timestamp}
            self.validate(payload); path=self.database.project_root/relative; path.parent.mkdir(parents=True,exist_ok=True)
            descriptor,name=tempfile.mkstemp(prefix=f".{path.name}.",dir=path.parent)
            try:
                with os.fdopen(descriptor,"w",encoding="utf-8") as handle:json.dump(payload,handle,indent=2,sort_keys=True);handle.write("\n");handle.flush();os.fsync(handle.fileno())
                if path.exists():raise FileExistsError(relative)
                os.replace(name,path)
            finally:
                if Path(name).exists():Path(name).unlink()
            connection.execute("insert into draft_ledger_events(event_id,lecture_pair_id,event_type,relative_path,payload_json,created_at) values (?,?,?,?,?,?)",(event_id,pair["id"],event_type,relative,json.dumps(payload),timestamp));connection.commit()
            return path

    @staticmethod
    def validate(payload:dict) -> None:
        required={"event_id","event_type","lecture_id","approval_status","canonical_append_authorised","created_at"}
        missing=required-payload.keys()
        if missing:raise ValueError("draft event missing: "+", ".join(sorted(missing)))
        if payload["approval_status"]!="DRAFT" or payload["canonical_append_authorised"] is not False:raise ValueError("draft event governance boundary invalid")
        if payload.get("canonical_block_number") is not None or payload.get("canonical_hash") is not None:raise ValueError("draft event may not carry canonical block metadata")

    def list_for_lecture(self,number:int):
        with self.database.connection() as connection:
            return [dict(r) for r in connection.execute("""select dle.* from draft_ledger_events dle join lecture_pairs lp
            on lp.id=dle.lecture_pair_id where lp.lecture_number=? order by dle.created_at desc""",(number,))]
