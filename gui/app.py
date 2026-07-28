from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Iterator
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from gui.database import DEFAULT_DATABASE, PROJECT_ROOT, initialise
from gui.lean_revision_service import LeanRevisionService
from gui.pptx_service import (
    convert_and_record_pdf, generate_pptx, libreoffice_available,
    thumbnail_rendering_available, validate_deck_plan,
)
from gui.services import (
    HISTORICAL_STATUSES, NOTE_ORIGINS, SLIDE_ACTIONS, TEACHING_FUNCTIONS,
    VISUAL_TYPES, add_historical_slide, add_note, add_slide_plan, assign_resource,
    dashboard, git_readiness, lecture_context, prepare_draft_event, save_class_record,
    save_verification_record,
    set_part_approval, update_historical_slide_status, update_pair,
    update_slide_decision,
)
from gui.reinforcement_service import ReinforcementError, ReinforcementService
from gui.title_registry import (
    TitleRegistryError, apply_title_sync, edit_title, export_confirmed_titles,
    propose_title_sync,
)


GUI_ROOT = Path(__file__).resolve().parent


def create_app(project_root: Path = PROJECT_ROOT, database_path: Path = DEFAULT_DATABASE) -> FastAPI:
    project_root = project_root.resolve()
    database_path = database_path.resolve()
    connection = initialise(database_path, project_root / "reports/source_census.json")
    connection.close()

    app = FastAPI(title="IS529N Course Production Cockpit", version="0.1.0")
    app.state.project_root = project_root
    app.state.database_path = database_path
    app.mount("/static", StaticFiles(directory=GUI_ROOT / "static"), name="static")
    templates = Jinja2Templates(directory=GUI_ROOT / "web_templates")

    @contextmanager
    def db() -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(app.state.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def context(connection: sqlite3.Connection, number: int, section: str, **extra):
        payload = lecture_context(connection, number)
        payload.update(
            section=section, lecture_number=number,
            historical_statuses=HISTORICAL_STATUSES, teaching_functions=TEACHING_FUNCTIONS,
            note_origins=NOTE_ORIGINS, slide_actions=SLIDE_ACTIONS, visual_types=VISUAL_TYPES,
            libreoffice_available=libreoffice_available(),
            thumbnail_rendering_available=thumbnail_rendering_available(), **extra,
        )
        return payload

    @app.get("/")
    def semester_dashboard(request: Request):
        with db() as connection:
            return templates.TemplateResponse(
                request=request, name="dashboard.html",
                context={"lectures": dashboard(connection), "section": "dashboard"},
            )

    def title_screen_context(connection: sqlite3.Connection, batch_id: int | None = None, **extra):
        pairs = [dict(row) for row in connection.execute(
            """SELECT lp.*,
            (SELECT COUNT(*) FROM title_evidence te WHERE te.lecture_pair_id=lp.id) AS evidence_count
            FROM lecture_pairs lp ORDER BY lecture_number"""
        )]
        parts = [dict(row) for row in connection.execute(
            "SELECT * FROM lecture_parts ORDER BY lecture_pair_id,part"
        )]
        evidence = [dict(row) for row in connection.execute(
            "SELECT * FROM title_evidence ORDER BY lecture_pair_id,target_identifier,source_filename"
        )]
        proposals = []
        if batch_id is not None:
            proposals = [dict(row) for row in connection.execute(
                "SELECT * FROM title_sync_proposals WHERE batch_id=? ORDER BY target_identifier", (batch_id,)
            )]
        payload = {
            "section": "titles", "pairs": pairs, "parts": parts, "evidence": evidence,
            "batch_id": batch_id, "proposals": proposals,
        }
        payload.update(extra)
        return payload

    @app.get("/titles")
    def title_management(request: Request, batch: int | None = None, message: str = ""):
        with db() as connection:
            return templates.TemplateResponse(
                request=request, name="titles.html",
                context=title_screen_context(connection, batch, message=message, errors=[]),
            )

    @app.post("/titles/reload")
    def title_reload(request: Request):
        with db() as connection:
            try:
                batch_id = propose_title_sync(connection, app.state.project_root)
            except TitleRegistryError as exc:
                return templates.TemplateResponse(
                    request=request, name="titles.html", status_code=422,
                    context=title_screen_context(connection, errors=list(exc.errors), message="Registry validation failed"),
                )
        return RedirectResponse(f"/titles?batch={batch_id}", status_code=303)

    @app.post("/titles/reload/{batch_id}/confirm")
    def title_reload_confirm(batch_id: int):
        with db() as connection:
            changed = apply_title_sync(connection, batch_id)
        return RedirectResponse(f"/titles?message=Applied+{changed}+title+changes", status_code=303)

    @app.post("/titles/{target_type}/{identifier}")
    async def title_edit(request: Request, target_type: str, identifier: str):
        form = await request.form()
        with db() as connection:
            edit_title(connection, target_type, identifier, str(form.get("title", "")), bool(form.get("confirmed")))
        return RedirectResponse("/titles?message=Title+saved", status_code=303)

    @app.post("/titles/export")
    def title_export():
        with db() as connection:
            export_confirmed_titles(connection, app.state.project_root)
        return RedirectResponse("/titles?message=Confirmed+titles+exported+with+local+backups", status_code=303)

    @app.get("/lectures/{number}")
    def workspace(request: Request, number: int):
        with db() as connection:
            return templates.TemplateResponse(
                request=request, name="workspace.html", context=context(connection, number, "workspace")
            )

    @app.post("/lectures/{number}")
    async def workspace_update(request: Request, number: int):
        values = dict(await request.form())
        with db() as connection:
            update_pair(connection, number, values)
        return RedirectResponse(f"/lectures/{number}", status_code=303)

    @app.get("/lectures/{number}/resources")
    def resources(request: Request, number: int):
        with db() as connection:
            return templates.TemplateResponse(
                request=request, name="resources.html", context=context(connection, number, "resources")
            )

    @app.post("/lectures/{number}/resources/{resource_pk}")
    def resource_assign(
        number: int, resource_pk: int,
        part: Annotated[str, Form()], classification: Annotated[str, Form()],
        centrality: Annotated[str, Form()],
    ):
        with db() as connection:
            assign_resource(connection, number, resource_pk, part, classification, centrality)
        return RedirectResponse(f"/lectures/{number}/resources", status_code=303)

    @app.get("/lectures/{number}/decks")
    def decks(request: Request, number: int):
        with db() as connection:
            return templates.TemplateResponse(
                request=request, name="decks.html", context=context(connection, number, "decks")
            )

    @app.post("/lectures/{number}/decks/{deck_pk}/slides")
    async def deck_slide_add(request: Request, number: int, deck_pk: int):
        values = dict(await request.form())
        with db() as connection:
            add_historical_slide(connection, deck_pk, values)
        return RedirectResponse(f"/lectures/{number}/decks", status_code=303)

    @app.post("/lectures/{number}/slides/{slide_pk}/status")
    def slide_status(number: int, slide_pk: int, status: Annotated[str, Form()]):
        with db() as connection:
            update_historical_slide_status(connection, slide_pk, status)
        return RedirectResponse(f"/lectures/{number}/decks", status_code=303)

    @app.get("/lectures/{number}/notes")
    def notes(request: Request, number: int):
        with db() as connection:
            return templates.TemplateResponse(
                request=request, name="notes.html", context=context(connection, number, "notes")
            )

    @app.post("/lectures/{number}/notes")
    async def note_add(request: Request, number: int):
        values = dict(await request.form())
        with db() as connection:
            add_note(connection, number, values)
        return RedirectResponse(f"/lectures/{number}/notes", status_code=303)

    @app.get("/lectures/{number}/slide-plan")
    def slide_plan(request: Request, number: int):
        with db() as connection:
            return templates.TemplateResponse(
                request=request, name="slide_plan.html", context=context(connection, number, "slide_plan")
            )

    @app.post("/lectures/{number}/slide-plan")
    async def slide_plan_add(request: Request, number: int):
        values = dict(await request.form())
        with db() as connection:
            add_slide_plan(connection, number, values)
        return RedirectResponse(f"/lectures/{number}/slide-plan", status_code=303)

    def reinforcement_response(
        request: Request, connection: sqlite3.Connection, *, stage: str = "overview",
        message: str = "", error: str = "", status_code: int = 200,
    ):
        payload = ReinforcementService(connection, app.state.project_root).workspace(stage)
        payload.update(
            request=request, section="reinforcement", message=message, error=error,
            lecture_route_id="IS529N-L01-A",
        )
        return templates.TemplateResponse(
            request=request, name="reinforcement.html", context=payload, status_code=status_code
        )

    def lean_revision_response(
        request: Request, connection: sqlite3.Connection, *, unit_id: str = "",
        message: str = "", error: str = "", status_code: int = 200,
    ):
        payload = LeanRevisionService(connection, app.state.project_root).workspace(unit_id)
        payload.update(
            request=request, section="reinforcement", message=message, error=error,
            lecture_route_id="IS529N-L01-A",
        )
        return templates.TemplateResponse(
            request=request, name="lean_revision.html", context=payload, status_code=status_code
        )

    @app.get("/lectures/{lecture_id}/reinforcement")
    def reinforcement_workspace(
        request: Request, lecture_id: str, stage: str = "overview",
        message: str = "", error: str = "", view: str = "lean", unit: str = "",
    ):
        if lecture_id != "IS529N-L01-A":
            raise HTTPException(status_code=404, detail="Only the Lecture 1A KC01 pilot is active")
        with db() as connection:
            if view != "legacy" and stage == "overview":
                return lean_revision_response(
                    request, connection, unit_id=unit, message=message, error=error
                )
            return reinforcement_response(
                request, connection, stage=stage, message=message, error=error
            )

    @app.get("/lectures/{lecture_id}/reinforcement/lean/{unit_id}/download")
    def lean_revision_download(lecture_id: str, unit_id: str):
        if lecture_id != "IS529N-L01-A":
            raise HTTPException(status_code=404)
        with db() as connection:
            try:
                unit = LeanRevisionService(connection, app.state.project_root).unit(unit_id)
            except ReinforcementError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
        if not unit["packet_markdown"]:
            raise HTTPException(status_code=404, detail="Prepare the AI packet first")
        return PlainTextResponse(
            unit["packet_markdown"], media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={unit_id}_AI_PACKET.md"},
        )

    @app.post("/lectures/{lecture_id}/reinforcement/lean/action")
    async def lean_revision_action(request: Request, lecture_id: str):
        if lecture_id != "IS529N-L01-A":
            raise HTTPException(status_code=404)
        form = await request.form()
        command = str(form.get("command", ""))
        target_id = str(form.get("target_id", ""))
        message = "Action recorded"
        active_id = target_id
        with db() as connection:
            service = LeanRevisionService(connection, app.state.project_root)
            try:
                if command == "SAVE_LEAN_DRAFT":
                    unit = service.save_draft(
                        unit_type=str(form.get("unit_type", "")),
                        slide_ids=[str(value) for value in form.getlist("slide_ids")],
                        instructor_query=str(form.get("instructor_query", "")),
                        source_mode=str(form.get("source_mode", "")),
                        selected_source_ids=[str(value) for value in form.getlist("selected_source_ids")],
                        direct_source_text=str(form.get("direct_sources", "")),
                    )
                    active_id = unit["unit_id"]
                    message = f"{active_id} draft saved"
                elif command == "PREPARE_LEAN_PACKET":
                    unit = service.prepare_packet(target_id)
                    message = f"{unit['unit_id']} AI packet prepared"
                elif command == "PASTE_VALIDATE_LEAN_RESULT":
                    result = service.paste_and_validate(target_id, str(form.get("structured_result", "")))
                    if not result["valid"]:
                        return lean_revision_response(
                            request, connection, unit_id=target_id,
                            error="Revision rejected: " + "; ".join(result["errors"]), status_code=422,
                        )
                    message = "AI revision validated and ready to compare"
                elif command == "SAVE_LEAN_INSTRUCTOR_EDIT":
                    unit = service.unit(target_id)
                    slides = []
                    for slide_id in unit["slide_ids_json"]:
                        number = int(slide_id.rsplit("S", 1)[-1])
                        slides.append({
                            "slide_id": slide_id,
                            "title": str(form.get(f"title_{number}", "")).strip(),
                            "student_visible_content": [line.strip() for line in str(
                                form.get(f"visible_{number}", "")
                            ).splitlines() if line.strip()],
                            "speaker_notes": str(form.get(f"notes_{number}", "")).strip(),
                            "visual_recommendation": str(form.get(f"visual_{number}", "")).strip(),
                            "transition_from_previous": str(form.get(f"from_{number}", "")).strip(),
                            "transition_to_next": str(form.get(f"to_{number}", "")).strip(),
                        })
                    proposal = unit["proposal"]
                    service.save_instructor_edit(target_id, {
                        "unit_id": target_id, "slides": slides,
                        "sources_used": proposal.get("sources_used", []),
                        "claims_qualified": proposal.get("claims_qualified", []),
                    })
                    message = "Instructor edit saved"
                elif command == "ACCEPT_LEAN_CONTENT":
                    service.accept_content(target_id, str(form.get("accepted_by", "Instructor")))
                    message = "Intellectual revision accepted; artefact attachment remains optional"
                elif command == "RETURN_LEAN_REVISION":
                    service.return_revision(target_id, str(form.get("return_note", "")))
                    message = "Revision returned with the prior result preserved"
                elif command == "ATTACH_LEAN_ARTEFACT":
                    upload = form.get("attachment")
                    content = await upload.read() if getattr(upload, "filename", "") else None
                    service.attach_artefact(
                        target_id, reference=str(form.get("reference", "")),
                        filename=str(getattr(upload, "filename", "")), content=content,
                    )
                    message = "Artefact attached after content acceptance"
                else:
                    raise ReinforcementError("unknown lean revision command")
            except (ReinforcementError, json.JSONDecodeError, ValueError) as exc:
                return lean_revision_response(
                    request, connection, unit_id=active_id, error=str(exc), status_code=422
                )
        query = urlencode({"unit": active_id, "message": message})
        return RedirectResponse(f"/lectures/{lecture_id}/reinforcement?{query}", status_code=303)

    @app.get("/lectures/{lecture_id}/reinforcement/historical/{slide_id}/thumbnail")
    def reinforcement_thumbnail(lecture_id: str, slide_id: str):
        if lecture_id != "IS529N-L01-A":
            raise HTTPException(status_code=404)
        with db() as connection:
            path = ReinforcementService(connection, app.state.project_root).thumbnail_path(slide_id)
        if path is None:
            raise HTTPException(status_code=404, detail="Thumbnail unavailable")
        return FileResponse(path, media_type="image/png", filename=f"{slide_id}.png")

    @app.get("/lectures/{lecture_id}/reinforcement/export-prompt")
    def reinforcement_export_prompt(lecture_id: str):
        if lecture_id != "IS529N-L01-A":
            raise HTTPException(status_code=404)
        with db() as connection:
            body = ReinforcementService(connection, app.state.project_root).export_analysis_prompt()
        return PlainTextResponse(
            body, headers={"Content-Disposition": "attachment; filename=KC01_analysis_prompt.json"}
        )

    @app.get("/lectures/{lecture_id}/reinforcement/ai-update-packets/{packet_id}/download")
    def reinforcement_download_ai_update_packet(lecture_id: str, packet_id: str):
        if lecture_id != "IS529N-L01-A":
            raise HTTPException(status_code=404)
        with db() as connection:
            try:
                packet = ReinforcementService(connection, app.state.project_root).ai_update_packet(packet_id)
            except ReinforcementError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
        return PlainTextResponse(
            packet["packet_markdown"], media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=IS529N_L01A_KC01_S003_UPDATE_PACKET.md"},
        )

    @app.get("/lectures/{lecture_id}/reinforcement/ai-update-packets/{packet_id}/attachment")
    def reinforcement_download_revised_slide(lecture_id: str, packet_id: str):
        if lecture_id != "IS529N-L01-A":
            raise HTTPException(status_code=404)
        with db() as connection:
            try:
                path = ReinforcementService(
                    connection, app.state.project_root
                ).reinforced_attachment_path(packet_id)
            except ReinforcementError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
        if path is None:
            raise HTTPException(status_code=404, detail="No uploaded revised-slide derivative")
        return FileResponse(path, filename=path.name)

    @app.post("/lectures/{lecture_id}/reinforcement/import")
    async def reinforcement_import(request: Request, lecture_id: str):
        if lecture_id != "IS529N-L01-A":
            raise HTTPException(status_code=404)
        form = await request.form()
        with db() as connection:
            service = ReinforcementService(connection, app.state.project_root)
            try:
                counts = service.import_ai_draft(str(form.get("structured_result", "")))
            except ReinforcementError as exc:
                return reinforcement_response(
                    request, connection, stage="patterns", error=str(exc), status_code=422
                )
        query = urlencode({"view": "legacy", "stage": "patterns", "message": f"Imported {counts['knowledge_units']} units and {counts['patterns']} patterns for review"})
        return RedirectResponse(f"/lectures/{lecture_id}/reinforcement?{query}", status_code=303)

    @app.post("/lectures/{lecture_id}/reinforcement/action")
    async def reinforcement_action(request: Request, lecture_id: str):
        if lecture_id != "IS529N-L01-A":
            raise HTTPException(status_code=404)
        form = await request.form()
        command = str(form.get("command", ""))
        target_id = str(form.get("target_id", ""))
        value = str(form.get("value", ""))
        comment = str(form.get("comment", ""))
        stage = str(form.get("return_stage", "overview"))
        message = "Action recorded"
        with db() as connection:
            service = ReinforcementService(connection, app.state.project_root)
            try:
                if command == "OPEN_HISTORICAL":
                    service.open_historical(); stage = "historical"; message = "Historical slides 3–18 opened read-only"
                elif command == "SELECT_CLUSTER":
                    service.select_cluster(target_id); stage = "clusters"; message = f"{target_id} selected"
                elif command == "FIND_RESOURCES":
                    count = service.find_aligned_resources(); stage = "resources"; message = f"LEC_RES_1 profiles ready ({count} new)"
                elif command == "HISTORICAL_DECISION":
                    service.historical_decision(target_id, value, comment); stage = "historical"
                elif command == "PREPARE_AI_UPDATE_PACKET":
                    packet = service.prepare_ai_update_packet(
                        target_id, support_override=str(form.get("support_override", "")) == "1"
                    ); stage = "historical"
                    message = f"{packet['packet_id']} slide-specific corpus is ready"
                elif command == "MARK_AI_PACKET_COPIED":
                    service.mark_ai_packet_copied(target_id); stage = "historical"
                    message = "Packet copied successfully"
                elif command == "MARK_AI_PACKET_SENT":
                    service.mark_ai_packet_sent(target_id); stage = "historical"
                    message = "Packet marked as sent to external AI"
                elif command == "PASTE_AI_UPDATE_RESULT":
                    service.paste_ai_update_result(
                        target_id, str(form.get("structured_result", "")),
                        free_form_override=str(form.get("free_form_override", "")) == "1",
                    )
                    stage = "historical"; message = "Draft pasted; validate it before comparison"
                elif command == "VALIDATE_AI_UPDATE_RESULT":
                    validation = service.validate_ai_update_result(target_id); stage = "historical"
                    if not validation["valid"]:
                        return reinforcement_response(
                            request, connection, stage=stage,
                            error="Result rejected: " + "; ".join(validation["errors"]), status_code=422,
                        )
                    message = "Structured draft validated for instructor comparison"
                elif command == "OPEN_INSTRUCTOR_EDITING":
                    service.open_instructor_editing(target_id); stage = "historical"
                    message = "Instructor editing view opened; the raw AI draft remains preserved"
                elif command == "SAVE_INSTRUCTOR_EDIT":
                    service.save_instructor_edit(target_id, {
                        "updated_slide_title": str(form.get("updated_slide_title", "")),
                        "student_visible_content": [line.strip() for line in str(form.get("student_visible_content", "")).splitlines() if line.strip()],
                        "speaker_notes": str(form.get("speaker_notes", "")),
                        "visual_recommendation": str(form.get("visual_recommendation", "")),
                        "source_citations": [line.strip() for line in str(form.get("source_citations", "")).splitlines() if line.strip()],
                        "relationship_to_previous_slide": str(form.get("relationship_to_previous_slide", "")),
                        "relationship_to_next_slide": str(form.get("relationship_to_next_slide", "")),
                        "claims_requiring_verification": [line.strip() for line in str(form.get("claims_requiring_verification", "")).splitlines() if line.strip()],
                    }); stage = "historical"; message = "Instructor-edited draft saved separately"
                elif command == "WAIVE_INSTRUCTOR_EDIT":
                    service.save_instructor_edit(target_id, {}, waive=True); stage = "historical"
                    message = "Instructor editing explicitly waived"
                elif command == "MARK_MANUALLY_APPLIED":
                    service.record_manual_application(
                        target_id, str(form.get("application_note", "")),
                        str(form.get("applied_by", "")),
                        str(form.get("slide_file_or_version_reference", "")),
                    ); stage = "historical"; message = "Manual slide application recorded"
                elif command == "ATTACH_REVISED_SLIDE":
                    upload = form.get("attachment")
                    content = await upload.read() if getattr(upload, "filename", "") else None
                    service.attach_reinforced_slide(
                        target_id, reference=str(form.get("reinforced_slide_reference", "")),
                        checksum=str(form.get("reinforced_slide_checksum", "")),
                        filename=str(getattr(upload, "filename", "")), content=content,
                    ); stage = "historical"; message = "Revised slide derivative attached locally"
                elif command == "ACCEPT_REINFORCED_SLIDE":
                    service.accept_reinforced_slide(
                        target_id, str(form.get("unresolved_claims_disposition", ""))
                    ); stage = "historical"; message = "Reinforced Slide 3 accepted locally"
                elif command == "RETURN_AI_UPDATE_FOR_REVISION":
                    service.return_ai_update_for_revision(
                        target_id, str(form.get("return_reason", "")),
                        str(form.get("return_target", "")),
                    ); stage = "historical"; message = "Proposal returned; prior revision preserved"
                elif command == "RESOURCE_ACTION":
                    service.resource_action(target_id, value, comment); stage = "resources"
                elif command == "EXTRACT_UNITS":
                    count = service.extract_knowledge_units(); stage = "units"; message = f"Knowledge units ready ({count} new)"
                elif command == "UNIT_ACTION":
                    service.unit_action(target_id, value); stage = "units"
                elif command == "SELECT_ROTATION":
                    service.select_rotation(value); stage = "patterns"; message = f"{value} rotation selected"
                elif command == "GENERATE_PATTERNS":
                    count = service.generate_patterns(); stage = "patterns"; message = f"Candidate patterns ready ({count} new)"
                elif command == "PATTERN_ACTION":
                    other = str(form.get("other_pattern_id", ""))
                    service.pattern_action(target_id, value, other_pattern_id=other,
                                           value=str(form.get("edit_value", "")), comment=comment)
                    stage = "choice" if value in {"SELECT", "CONFIRM_PATTERN"} else "patterns"
                elif command == "GENERATE_SLIDES":
                    count = service.generate_reinforced_slides(); stage = "slides"; message = f"Reinforced sequence ready ({count} slides)"
                elif command == "SLIDE_ACTION":
                    service.slide_action(target_id, value, comment); stage = "slides"
                elif command == "START_REHEARSAL":
                    rehearsal_id = service.start_rehearsal(); stage = "rehearsal"; message = f"Rehearsal {rehearsal_id} started"
                elif command == "REHEARSAL_EVENT":
                    service.rehearsal_event(
                        str(form.get("rehearsal_id", "")), value, slide_id=target_id,
                        elapsed_seconds=int(form.get("elapsed_seconds", 0) or 0), comment=comment,
                    )
                    stage = "acceptance" if value == "END_REHEARSAL" else "rehearsal"
                elif command == "ACCEPTANCE_ACTION":
                    acceptance_id = service.accept_cluster(value, comment); stage = "acceptance"; message = f"Ruling stored as {acceptance_id}"
                else:
                    raise ReinforcementError("unknown reinforcement command")
            except (ReinforcementError, json.JSONDecodeError, ValueError) as exc:
                return reinforcement_response(
                    request, connection, stage=stage, error=str(exc), status_code=422
                )
        query = urlencode({"view": "legacy", "stage": stage, "message": message})
        return RedirectResponse(f"/lectures/{lecture_id}/reinforcement?{query}", status_code=303)

    @app.post("/lectures/{number}/slide-plan/{slide_pk}/decision")
    def slide_plan_decision(
        number: int, slide_pk: int, decision: Annotated[str, Form()]
    ):
        with db() as connection:
            update_slide_decision(connection, slide_pk, decision)
        return RedirectResponse(f"/lectures/{number}/slide-plan", status_code=303)

    @app.get("/lectures/{number}/deliverables")
    def deliverables(request: Request, number: int):
        with db() as connection:
            pair_context = context(connection, number, "deliverables")
            pair_context["validation_a"] = validate_deck_plan(connection, pair_context["pair"]["id"], "A")
            pair_context["validation_b"] = validate_deck_plan(connection, pair_context["pair"]["id"], "B")
            return templates.TemplateResponse(request=request, name="deliverables.html", context=pair_context)

    @app.post("/lectures/{number}/deliverables/generate")
    async def deliverable_generate(request: Request, number: int):
        form = await request.form()
        part = str(form.get("part", "A"))
        status = str(form.get("status", "DRAFT"))
        with db() as connection:
            result = generate_pptx(connection, app.state.project_root, number, part, status)
            if form.get("render_pdf") and libreoffice_available():
                convert_and_record_pdf(
                    connection, app.state.project_root, number, part, result, status
                )
        return RedirectResponse(f"/lectures/{number}/deliverables", status_code=303)

    @app.post("/lectures/{number}/deliverables/validate")
    def deliverable_validate(number: int, part: Annotated[str, Form()]):
        with db() as connection:
            pair_id = connection.execute(
                "SELECT id FROM lecture_pairs WHERE lecture_number=?", (number,)
            ).fetchone()[0]
            report = validate_deck_plan(connection, pair_id, part)
            save_verification_record(connection, pair_id, part, report)
        return RedirectResponse(f"/lectures/{number}/deliverables", status_code=303)

    @app.post("/lectures/{number}/approve")
    def approve_part(number: int, part: Annotated[str, Form()]):
        with db() as connection:
            set_part_approval(connection, number, part)
        return RedirectResponse(f"/lectures/{number}/deliverables", status_code=303)

    @app.get("/lectures/{number}/class-record")
    def class_record(request: Request, number: int):
        with db() as connection:
            return templates.TemplateResponse(
                request=request, name="class_record.html", context=context(connection, number, "class_record")
            )

    @app.post("/lectures/{number}/class-record")
    async def class_record_save(request: Request, number: int):
        values = dict(await request.form())
        with db() as connection:
            save_class_record(connection, number, values)
        return RedirectResponse(f"/lectures/{number}/class-record", status_code=303)

    @app.post("/lectures/{number}/draft-event")
    def draft_event(number: int, event_type: Annotated[str, Form()]):
        with db() as connection:
            try:
                prepare_draft_event(connection, app.state.project_root, number, event_type)
            except FileExistsError:
                pass
        return RedirectResponse(f"/lectures/{number}/class-record", status_code=303)

    @app.get("/governance")
    def governance(request: Request, lecture: int = 1):
        report = git_readiness(app.state.project_root, lecture)
        with db() as connection:
            pair = connection.execute(
                "SELECT id FROM lecture_pairs WHERE lecture_number=?", (lecture,)
            ).fetchone()
            connection.execute(
                """INSERT INTO git_readiness_reports(lecture_pair_id,generated_at,branch,latest_commit,
                modified_count,untracked_count,validation_state,report_json) VALUES (?,?,?,?,?,?,?,?)""",
                (pair[0], report["generated_at"], report["branch"], report["latest_commit"],
                 len(report["modified_files"]), len(report["untracked_files"]),
                 report["validation_state"], json.dumps(report)),
            )
            connection.commit()
        return templates.TemplateResponse(
            request=request, name="governance.html",
            context={"section": "governance", "report": report, "lecture_number": lecture},
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "ai_service": "DISABLED", "canonical_ledger_writes": "DISABLED"}

    return app


app = create_app()
