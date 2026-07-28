from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from gui.pptx_service import SUPPORTED_VISUAL_TYPES, convert_pdf, generate_pptx, render_pdf_thumbnails
from gui.services import utc_now, validate_relative_path
from qt_gui.database.connection import DatabaseManager


SLIDE_DECISIONS = (
    "ACCEPT_DRAFT", "RETURN_TO_NOTES", "RETURN_TO_SLIDE_PLAN", "REPLACE_VISUAL",
    "REORDER", "REMOVE", "REQUIRES_VERIFICATION",
)
DECK_DECISIONS = (
    "DRAFT_ACCEPTED_FOR_FURTHER_REVISION", "RETURNED_FOR_REVISION",
    "TECHNICALLY_READY", "INSTRUCTOR_APPROVED",
)


def sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):digest.update(chunk)
    return digest.hexdigest()


def pdf_page_count(path: Path) -> int:
    result=subprocess.run(["pdfinfo",str(path)],check=True,capture_output=True,text=True)
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):return int(line.split(":",1)[1].strip())
    raise RuntimeError("pdfinfo did not report a page count")


class DeliverableService:
    def __init__(self,database:DatabaseManager):self.database=database

    def _plans(self,connection,number:int,part:str):
        pair=connection.execute("select * from lecture_pairs where lecture_number=?",(number,)).fetchone()
        if pair is None:raise KeyError(number)
        part_row=connection.execute("select * from lecture_parts where lecture_pair_id=? and part=?",(pair["id"],part)).fetchone()
        if part_row is None:raise ValueError("invalid lecture part")
        plans=[dict(r) for r in connection.execute(
            """select * from slide_plan_entries where lecture_pair_id=? and part=? and action!='DELETE'
            and revision_status!='SUPERSEDED_BY_STRUCTURED_REVISION'
            order by case when generation_sequence>0 then generation_sequence else sequence end""",(pair["id"],part))]
        for plan in plans:
            plan["effective_sequence"]=plan["generation_sequence"] or plan["sequence"]
            plan["resource_link_count"]=connection.execute("select count(*) from slide_source_links where slide_plan_id=?",(plan["id"],)).fetchone()[0]
            plan["note_link_count"]=connection.execute("select count(*) from slide_note_links where slide_plan_id=?",(plan["id"],)).fetchone()[0]
            plan["historical_link_count"]=connection.execute("select count(*) from slide_historical_links where slide_plan_id=?",(plan["id"],)).fetchone()[0]
            original=plan["source_independence_status"]=="INSTRUCTOR_ORIGINAL" and bool(plan["instructor_origin_declaration"].strip())
            plan["evidence_complete"]=bool(plan["purpose"].strip() and plan["citation_footer"].strip() and plan["note_link_count"] and ((plan["resource_link_count"] and plan["historical_link_count"]) or original))
        return dict(pair),dict(part_row),plans

    def gate(self,number:int,part:str,status:str="DRAFT") -> dict:
        part=part.upper(); status=status.upper()
        with self.database.connection() as connection:
            pair,part_row,plans=self._plans(connection,number,part)
        errors=[]
        if not plans:errors.append("slide plan does not exist")
        if plans and [p["effective_sequence"] for p in plans]!=list(range(1,len(plans)+1)):errors.append("slide sequence must be contiguous from 1")
        if len({p["slide_id"] for p in plans})!=len(plans):errors.append("duplicate slide identifier")
        if not any(p["evidence_complete"] for p in plans):errors.append("at least one complete evidence chain is required")
        if not pair["weekly_title"].strip() or not part_row["title"].strip():errors.append("lecture and part titles are required")
        for p in plans:
            path=p["visual_asset_path"]
            if path:
                try:validate_relative_path(path)
                except ValueError:errors.append(f'{p["slide_id"]}: absolute or unsafe visual path')
        if status=="APPROVED":
            if any(p["verification_status"]!="VERIFIED" or p["approval_status"]!="INSTRUCTOR_APPROVED" for p in plans):errors.append("approved generation requires every slide verified and instructor-approved")
            if part_row["fidelity_status"]!="F4" or part_row["approval_status"]!="INSTRUCTOR_APPROVED":errors.append("approved generation requires F4 instructor-approved lecture part")
        return {"enabled":not errors,"errors":errors,"plans":plans,"pair":pair,"part":part_row,
                "evidence_complete_count":sum(p["evidence_complete"] for p in plans)}

    def list_bundles(self,number:int,part:str):
        with self.database.connection() as connection:
            return [dict(r) for r in connection.execute(
                """select db.* from deliverable_bundles db join lecture_pairs lp on lp.id=db.lecture_pair_id
                where lp.lecture_number=? and db.part=? order by db.created_at desc,db.id desc""",(number,part))]

    def generate(self,number:int,part:str,status:str="DRAFT") -> dict:
        gate=self.gate(number,part,status)
        if not gate["enabled"]:raise ValueError("generation gate failed: "+"; ".join(gate["errors"]))
        with self.database.connection() as connection:
            result=generate_pptx(connection,self.database.project_root,number,part,status)
            pptx_hash=sha256(result["path"]); now=utc_now()
            sidecar=json.loads(result["sidecar"].read_text(encoding="utf-8")); sidecar.update(
                pptx_sha256=pptx_hash,evidence_complete_slides=gate["evidence_complete_count"],
                generation_gate="PASS",approval_automatic=False,visibility="PRIVATE",
                review_status="REVIEW_REQUIRED",classroom_use_status="NOT_FOR_CLASSROOM_USE",
            )
            result["sidecar"].write_text(json.dumps(sidecar,indent=2,sort_keys=True)+"\n",encoding="utf-8")
            paths=[validate_relative_path(p.resolve().relative_to(self.database.project_root.resolve()).as_posix()) for p in (result["path"],result["sidecar"],result["teaching_brief"])]
            cursor=connection.execute(
                """insert into deliverable_bundles(lecture_pair_id,part,version,status,pptx_path,pptx_sha256,
                sidecar_path,teaching_brief_path,visibility,classroom_use_status,created_at,updated_at)
                values (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (gate["pair"]["id"],part,result["version"],status.upper(),paths[0],pptx_hash,paths[1],paths[2],
                 "PRIVATE","NOT_FOR_CLASSROOM_USE",now,now))
            connection.commit(); result.update(bundle_id=cursor.lastrowid,pptx_sha256=pptx_hash)
            return result

    def bundle(self,bundle_id:int) -> dict:
        with self.database.connection() as connection:
            row=connection.execute("select * from deliverable_bundles where id=?",(bundle_id,)).fetchone()
            if row is None:raise KeyError(bundle_id)
            result=dict(row); result["slide_decisions"]=[dict(r) for r in connection.execute(
                """select sr.*,sp.slide_id,sp.title from slide_review_decisions sr join slide_plan_entries sp
                on sp.id=sr.slide_plan_id where sr.deliverable_bundle_id=? order by sp.sequence""",(bundle_id,))]
            return result

    def render_pdf(self,bundle_id:int) -> dict:
        bundle=self.bundle(bundle_id); pptx=self.database.project_root/bundle["pptx_path"]
        if sha256(pptx)!=bundle["pptx_sha256"]:raise ValueError("PPTX checksum mismatch; rendering refused")
        with self.database.connection() as connection:
            number=connection.execute("select lecture_number from lecture_pairs where id=?",(bundle["lecture_pair_id"],)).fetchone()[0]
        part_dir="part_a_tuesday" if bundle["part"]=="A" else "part_b_friday"
        output=self.database.project_root/f"course/lectures/lecture_{number:02d}/{part_dir}/classroom_pdf"
        try:pdf=convert_pdf(pptx,output)
        except Exception as exc:
            with self.database.connection() as connection:
                connection.execute("update deliverable_bundles set rendering_warnings=?,updated_at=? where id=?",(json.dumps([str(exc)]),utc_now(),bundle_id)); connection.commit()
            raise
        relative=validate_relative_path(pdf.resolve().relative_to(self.database.project_root.resolve()).as_posix()); checksum=sha256(pdf); pages=pdf_page_count(pdf)
        with self.database.connection() as connection:
            connection.execute("""update deliverable_bundles set pdf_path=?,pdf_sha256=?,page_count=?,rendering_tool=?,
            rendering_warnings='[]',updated_at=? where id=?""",(relative,checksum,pages,"LibreOffice headless PDF export",utc_now(),bundle_id)); connection.commit()
        return {"pdf":pdf,"pdf_sha256":checksum,"page_count":pages}

    def generate_thumbnails(self,bundle_id:int) -> list[Path]:
        bundle=self.bundle(bundle_id)
        if not bundle["pdf_path"]:raise ValueError("render the PDF before generating thumbnails")
        pdf=self.database.project_root/bundle["pdf_path"]
        if sha256(pdf)!=bundle["pdf_sha256"]:raise ValueError("PDF checksum mismatch; thumbnail rendering refused")
        with self.database.connection() as connection:
            number=connection.execute("select lecture_number from lecture_pairs where id=?",(bundle["lecture_pair_id"],)).fetchone()[0]
        directory=self.database.project_root/f"course/lectures/lecture_{number:02d}/{'part_a_tuesday' if bundle['part']=='A' else 'part_b_friday'}/previews/{pdf.stem}"
        thumbnails=render_pdf_thumbnails(pdf,directory)
        relative=validate_relative_path(directory.resolve().relative_to(self.database.project_root.resolve()).as_posix())
        with self.database.connection() as connection:
            connection.execute("update deliverable_bundles set thumbnail_directory=?,thumbnail_count=?,updated_at=? where id=?",(relative,len(thumbnails),utc_now(),bundle_id)); connection.commit()
        return thumbnails

    def validate(self,bundle_id:int) -> dict:
        bundle=self.bundle(bundle_id)
        with self.database.connection() as connection:
            pair=connection.execute("select lecture_number,duplication_warnings from lecture_pairs where id=?",(bundle["lecture_pair_id"],)).fetchone()
            _pair,_part,plans=self._plans(connection,pair["lecture_number"],bundle["part"])
        findings=[]
        def add(slide_id,code,message,severity="WARNING",scope="DETERMINISTIC"):
            findings.append({"slide_id":slide_id,"code":code,"message":message,"severity":severity,"scope":scope})
        sequences=[p["effective_sequence"] for p in plans]
        if sequences!=list(range(1,len(plans)+1)):add("DECK","INVALID_ORDER","Slide order is not contiguous","ERROR")
        if len({p["slide_id"] for p in plans})!=len(plans):add("DECK","DUPLICATE_SLIDE_ID","Duplicate slide identifier","ERROR")
        if not any(p["visual_type"]=="REFERENCES" for p in plans):add("DECK","ABSENT_REFERENCES_SLIDE","No references slide is planned")
        if pair["duplication_warnings"].strip():add("DECK","PART_DUPLICATION",pair["duplication_warnings"])
        for p in plans:
            sid=p["slide_id"]
            if not p["purpose"].strip():add(sid,"MISSING_PURPOSE","Purpose is missing")
            if not p["note_link_count"]:add(sid,"MISSING_NOTES","No revised note is linked")
            if not p["evidence_complete"]:add(sid,"MISSING_EVIDENCE","Evidence chain is incomplete")
            if not p["citation_footer"].strip():add(sid,"MISSING_CITATION","Citation footer is missing")
            if p["verification_status"]!="VERIFIED":add(sid,"UNVERIFIED_SLIDE","Slide is not verified")
            if p["action"]=="RETURN_TO_NOTES":add(sid,"UNRESOLVED_FACTUAL_CLAIM","Slide was returned to notes")
            if len(p["speaker_note"])>1200 or len(p["purpose"])>350:add(sid,"EXCESSIVE_TEXT","Text volume may be excessive","WARNING","HEURISTIC")
            if len(p["speaker_note"])>900:add(sid,"FONT_SIZE_RISK","Content density may force small text","WARNING","HEURISTIC")
            if p["visual_type"]=="TEXT_AND_IMAGE" and not p["visual_asset_path"]:add(sid,"MISSING_IMAGE","Image asset is missing")
            if p["visual_type"]=="MAP" and not p["visual_asset_path"]:add(sid,"MISSING_MAP","Map asset is missing")
            if "PLACEHOLDER" in p["title"].upper():add(sid,"EMPTY_PLACEHOLDER","Placeholder remains")
            if p["visual_type"] not in SUPPORTED_VISUAL_TYPES:add(sid,"UNSUPPORTED_VISUAL_TYPE",p["visual_type"],"ERROR")
        pptx=self.database.project_root/bundle["pptx_path"]
        if not pptx.is_file() or sha256(pptx)!=bundle["pptx_sha256"]:add("DECK","OUTPUT_CHECKSUM_MISMATCH","PPTX output checksum mismatch","ERROR")
        if bundle["pdf_path"]:
            pdf=self.database.project_root/bundle["pdf_path"]
            if not pdf.is_file() or sha256(pdf)!=bundle["pdf_sha256"]:add("DECK","OUTPUT_CHECKSUM_MISMATCH","PDF output checksum mismatch","ERROR")
        status="FAIL" if any(f["severity"]=="ERROR" for f in findings) else "REVIEW_REQUIRED" if findings else "PASS"
        report={"status":status,"findings":findings,"geometry_scope":"HEURISTIC_WHERE_MARKED","generated_at":utc_now()}
        report_path=pptx.with_suffix(".validation.json"); report_path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        with self.database.connection() as connection:
            connection.execute("update deliverable_bundles set validation_status=?,validation_report=?,updated_at=? where id=?",(status,json.dumps(report),utc_now(),bundle_id)); connection.commit()
        return report

    def record_slide_decision(self,bundle_id:int,slide_pk:int,decision:str,note:str="") -> None:
        if decision not in SLIDE_DECISIONS:raise ValueError("invalid slide review decision")
        with self.database.connection() as connection:
            connection.execute("""insert into slide_review_decisions(deliverable_bundle_id,slide_plan_id,decision,instructor_note,decided_at)
            values (?,?,?,?,?) on conflict(deliverable_bundle_id,slide_plan_id) do update set decision=excluded.decision,
            instructor_note=excluded.instructor_note,decided_at=excluded.decided_at""",(bundle_id,slide_pk,decision,note,utc_now())); connection.commit()

    def record_deck_decision(self,bundle_id:int,decision:str,note:str="") -> None:
        if decision not in DECK_DECISIONS:raise ValueError("invalid deck review decision")
        bundle=self.bundle(bundle_id); report=json.loads(bundle["validation_report"] or "{}")
        findings=report.get("findings",[])
        if decision=="INSTRUCTOR_APPROVED":
            if bundle["validation_status"]=="NOT_RUN":raise ValueError("validation must run before instructor approval")
            if any(f.get("severity")=="ERROR" for f in findings):raise ValueError("instructor approval is blocked by validation errors")
            if findings and not note.strip():raise ValueError("validation warnings require an explicit instructor override note")
        with self.database.connection() as connection:
            connection.execute("update deliverable_bundles set deck_decision=?,decision_note=?,approved=?,updated_at=? where id=?",(decision,note,int(decision=="INSTRUCTOR_APPROVED"),utc_now(),bundle_id)); connection.commit()
