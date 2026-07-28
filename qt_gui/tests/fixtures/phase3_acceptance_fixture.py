from __future__ import annotations

from gui.services import utc_now
from qt_gui.database.connection import DatabaseManager


FIXTURE_LABEL="NON_SUBSTANTIVE_ACCEPTANCE_FIXTURE"
CLASSROOM_WARNING="NOT_FOR_CLASSROOM_USE"


def seed_phase3_fixture(database:DatabaseManager) -> dict[str,int]:
    """Create structural evidence only; no substantive course scholarship."""
    with database.connection() as connection:
        pair=connection.execute("select id from lecture_pairs where lecture_number=1").fetchone()[0]
        connection.execute("""insert into resources(resource_id,title,source_locator,provenance,source_layer,file_type,
        historical_status,content_sha256,verification_status) values ('P3-R1',?,
        '<SYNTHETIC_FIXTURE>/phase3-resource.txt',?,'SYNTHETIC','.txt','SYNTHETIC',?,'VERIFIED')""",
        (FIXTURE_LABEL,CLASSROOM_WARNING,"a"*64))
        resource=connection.execute("select id from resources where resource_id='P3-R1'").fetchone()[0]
        connection.execute("insert into resource_assignments(resource_id,lecture_pair_id,part,assigned_by,updated_at) values (?,?,'A','Application',?)",(resource,pair,utc_now()))
        connection.execute("""insert into historical_decks(deck_id,lecture_pair_id,title,source_locator,file_type,
        source_layer,content_sha256) values ('P3-D1',?,?, '<SYNTHETIC_FIXTURE>/phase3-deck.pdf','.pdf','SYNTHETIC',?)""",(pair,FIXTURE_LABEL,"b"*64))
        deck=connection.execute("select id from historical_decks where deck_id='P3-D1'").fetchone()[0]
        connection.execute("""insert into historical_slides(historical_slide_id,deck_id,historical_slide_number,title,
        text_extract,current_status,approval_status) values ('P3-HS1',?,1,?,?,'RETAIN','WORKING_DRAFT')""",(deck,FIXTURE_LABEL,CLASSROOM_WARNING))
        historical=connection.execute("select id from historical_slides where historical_slide_id='P3-HS1'").fetchone()[0]
        connection.execute("""insert into revised_notes(note_id,lecture_pair_id,part,topic,claim,teaching_function,
        created_by,note_origin,instructor_status,verification_status,instructor_origin_declared) values
        ('P3-N1',?,'A',?,?, 'CONCEPT','Application','INSTRUCTOR_AUTHORED','WORKING_DRAFT','VERIFIED',1)""",(pair,FIXTURE_LABEL,CLASSROOM_WARNING))
        note=connection.execute("select id from revised_notes where note_id='P3-N1'").fetchone()[0]
        connection.execute("insert into note_source_links(note_id,resource_id,created_at) values (?,?,?)",(note,resource,utc_now()))
        connection.execute("insert into note_historical_slide_links(note_id,historical_slide_id,created_at) values (?,?,?)",(note,historical,utc_now()))
        connection.execute("""insert into slide_plan_entries(slide_id,lecture_pair_id,part,sequence,title,purpose,action,
        note_ids,resource_ids,historical_slide_sources,visual_type,speaker_note,citation_footer,verification_status,
        approval_status,updated_at,updated_by) values ('P3-S1',?,'A',1,?,?,'ADD','[\"P3-N1\"]','[\"P3-R1\"]',
        '[\"P3-HS1\"]','CONCEPT',?,?, 'VERIFIED','WORKING_DRAFT',?,'Application')""",
        (pair,FIXTURE_LABEL,CLASSROOM_WARNING,CLASSROOM_WARNING,"Synthetic fixture citation",utc_now()))
        slide=connection.execute("select id from slide_plan_entries where slide_id='P3-S1'").fetchone()[0]
        connection.execute("insert into slide_source_links(slide_plan_id,resource_id,created_at) values (?,?,?)",(slide,resource,utc_now()))
        connection.execute("insert into slide_note_links(slide_plan_id,note_id,created_at) values (?,?,?)",(slide,note,utc_now()))
        connection.execute("insert into slide_historical_links(slide_plan_id,historical_slide_id,created_at) values (?,?,?)",(slide,historical,utc_now()))
        connection.commit();return {"pair":pair,"resource":resource,"deck":deck,"historical":historical,"note":note,"slide":slide}
