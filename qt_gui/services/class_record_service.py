from __future__ import annotations

from datetime import date

from gui.services import utc_now
from qt_gui.database.connection import DatabaseManager


class ClassRecordService:
    FIELDS=("scheduled_date","actual_date","slides_planned","slides_covered","slides_omitted",
            "oral_material_added","student_questions","conceptual_difficulties","time_management",
            "topics_deferred","follow_up_actions","impact_on_next_session","instructor_validation_status",
            "retrospective_entry_explanation")

    def __init__(self,database:DatabaseManager):self.database=database

    def load(self,number:int,part:str) -> dict:
        with self.database.connection() as connection:
            row=connection.execute("""select csr.* from class_session_records csr join lecture_pairs lp
            on lp.id=csr.lecture_pair_id where lp.lecture_number=? and csr.part=?""",(number,part)).fetchone()
            if row:return dict(row)
            pair=connection.execute("select lecture_id from lecture_pairs where lecture_number=?",(number,)).fetchone()
            return {"session_id":f'{pair["lecture_id"]}-{part}-SESSION',"part":part,**{field:"" for field in self.FIELDS}}

    def save(self,number:int,part:str,values:dict,actor:str="Instructor") -> str:
        if part not in {"A","B"}:raise ValueError("invalid class-record part")
        status=values.get("instructor_validation_status","NOT_REVIEWED")
        if status not in {"NOT_REVIEWED","WORKING_DRAFT","INSTRUCTOR_VALIDATED"}:raise ValueError("invalid class-record validation status")
        actual=values.get("actual_date",""); scheduled=values.get("scheduled_date",""); explanation=values.get("retrospective_entry_explanation","").strip()
        today=date.today()
        if status=="INSTRUCTOR_VALIDATED" and not actual:raise ValueError("a completed class record requires the actual class date")
        if actual and date.fromisoformat(actual)>today and not explanation:raise ValueError("a future actual date requires an explicit retrospective-entry explanation")
        if status=="INSTRUCTOR_VALIDATED" and scheduled and date.fromisoformat(scheduled)>today and not explanation:raise ValueError("completion before the scheduled class date requires an explicit retrospective-entry explanation")
        with self.database.connection() as connection:
            pair=connection.execute("select id,lecture_id from lecture_pairs where lecture_number=?",(number,)).fetchone()
            session_id=f'{pair["lecture_id"]}-{part}-SESSION'
            fields=self.FIELDS+("updated_at","updated_by")
            payload={**values,"updated_at":utc_now(),"updated_by":actor}
            connection.execute(
                f"""insert into class_session_records(session_id,lecture_pair_id,part,{','.join(fields)})
                values (?,?,?,{','.join('?' for _ in fields)}) on conflict(lecture_pair_id,part) do update set
                {','.join(f'{field}=excluded.{field}' for field in fields)}""",
                (session_id,pair["id"],part)+tuple(payload.get(field,"") for field in fields),
            )
            if actual:
                lifecycle="POST_CLASS_RECORDED" if status=="INSTRUCTOR_VALIDATED" else "TAUGHT"
                connection.execute("update lecture_parts set class_status='TAUGHT',lifecycle_status=? where lecture_pair_id=? and part=?",(lifecycle,pair["id"],part))
            connection.commit(); return session_id

    def validated_records(self,number:int):
        with self.database.connection() as connection:
            return [dict(r) for r in connection.execute("""select csr.* from class_session_records csr join lecture_pairs lp
            on lp.id=csr.lecture_pair_id where lp.lecture_number=? and csr.instructor_validation_status='INSTRUCTOR_VALIDATED'""",(number,))]
