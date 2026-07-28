from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TriangulationTopic:
    triangulation_topic_id: str
    lecture_id: str
    part: str
    topic: str
    central_question: str = ""
    historical_slide_ids: tuple[str, ...] = field(default_factory=tuple)
    working_note_ids: tuple[str, ...] = field(default_factory=tuple)
    slide_plan_ids: tuple[str, ...] = field(default_factory=tuple)
    status: str = "INCOMPLETE"


@dataclass(frozen=True)
class TriangulationEvidence:
    evidence_id: str
    evidence_layer: str
    source_identifier: str
    source_title: str = ""
    source_type: str = ""
    symbolic_location: str = ""
    source_sha256: str = ""
    treatment_level: int = 0
    alignment_level: str = "UNRESOLVED"
    evidentiary_value: str = "UNKNOWN"
    verification_status: str = "NOT_YET_VERIFIED"
    currency_status: str = "DATE_UNCERTAIN"


@dataclass(frozen=True)
class TriangulationClaim:
    claim_id: str
    claim_text: str
    origin_layer: str
    verification_status: str = "NOT_YET_VERIFIED"
    support_level: str = "UNKNOWN"
    contradiction_status: str = "UNRESOLVED"
    currency_status: str = "DATE_UNCERTAIN"


@dataclass(frozen=True)
class TriangulationFinding:
    finding_type: str
    summary: str
    evidence_gap: str
    recommended_action: str
    instructor_status: str = "ADVISORY"


@dataclass(frozen=True)
class TriangulationDecision:
    recommended_action: str
    instructor_decision: str = "NOT_YET_DECIDED"
    instructor_comment: str = ""
    confirmed: bool = False


@dataclass(frozen=True)
class WebsiteNote:
    website_note_id: str
    page_title: str
    page_url: str
    lecture_id: str
    part: str
    topic: str
    ai_generation_status: str = "UNKNOWN_ORIGIN"
    verification_status: str = "NOT_YET_VERIFIED"


@dataclass(frozen=True)
class WebsiteLinkRecord:
    website_link_id: str
    page_url: str
    link_label: str
    inspection_status: str = "METADATA_ONLY"
    download_authorised: bool = False


@dataclass(frozen=True)
class StudentLearningPackage:
    learning_package_id: str
    lecture_id: str
    part: str
    classroom_deck_id: int | None = None
    website_note_ids: tuple[str, ...] = field(default_factory=tuple)
    raw_resource_ids: tuple[str, ...] = field(default_factory=tuple)
    public_link_ids: tuple[str, ...] = field(default_factory=tuple)
    verification_status: str = "NOT_YET_VERIFIED"
    public_approval_status: str = "NOT_APPROVED"
    instructor_status: str = "WORKING_DRAFT"
