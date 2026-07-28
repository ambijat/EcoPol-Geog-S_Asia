#!/usr/bin/env python3
"""Build governed page-addressable derivatives for the Slide 3 Puranic corpus.

The input PDFs remain authoritative and are never copied or modified. Ali pages are
raw Tesseract candidates. Valdiya preserves the embedded extraction separately from
an image-layer re-extraction that corrects obvious corruption but remains a derivative.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "resources/derived/slide3_puranic_geography"

SOURCES = (
    {
        "filename": "gop_part1.pdf", "resource_id": "IS529N-ALI-GOP-PART-01",
        "title": "The Geography of the Puranas — Introduction (part 1)",
        "author": "Syed Muzafer Ali", "page_count": 14, "printed_offset": 0,
        "citation": "Ali, Syed Muzafer. The Geography of the Puranas. New Delhi: People's Publishing House, 1966, pp. 1–14.",
    },
    {
        "filename": "gop_part2.pdf", "resource_id": "IS529N-ALI-GOP-PART-02",
        "title": "The Geography of the Puranas — Sources of Puranic Geography",
        "author": "Syed Muzafer Ali", "page_count": 11, "printed_offset": 14,
        "citation": "Ali, Syed Muzafer. The Geography of the Puranas. New Delhi: People's Publishing House, 1966, pp. 15–25.",
    },
    {
        "filename": "gop_part3.pdf", "resource_id": "IS529N-ALI-GOP-PART-03",
        "title": "The Geography of the Puranas — Puranic Continents and Oceans",
        "author": "Syed Muzafer Ali", "page_count": 22, "printed_offset": 24,
        "citation": "Ali, Syed Muzafer. The Geography of the Puranas. New Delhi: People's Publishing House, 1966, pp. 25–46.",
    },
    {
        "filename": "gop_part4.pdf", "resource_id": "IS529N-ALI-GOP-PART-04",
        "title": "The Geography of the Puranas — The Mountain System of the Puranas",
        "author": "Syed Muzafer Ali", "page_count": 14, "printed_offset": 45,
        "citation": "Ali, Syed Muzafer. The Geography of the Puranas. New Delhi: People's Publishing House, 1966, pp. 46–59.",
    },
    {
        "filename": "valdiya_ch1.pdf", "resource_id": "IS529N-VALDIYA-GPG-CH01",
        "title": "Geography, Peoples and Geodynamics of India in Puranas and Epics — Preface and Chapter 1",
        "author": "K. S. Valdiya", "page_count": 15,
        "citation": "Valdiya, K. S. Geography, Peoples and Geodynamics of India in Puranas and Epics: A Geologist's Interpretations. New Delhi: Aryan Books International, 2012, preface xi–xiii and pp. 1–11.",
    },
)

EVIDENCE = (
    {
        "evidence_id": "S3-EV-ALI-001", "resource_id": "IS529N-ALI-GOP-PART-01",
        "pdf_page": 1, "printed_page": "1", "classification": "TEXTUALLY_DOCUMENTED",
        "text_form": "VERBATIM_TRANSCRIPTION",
        "topics": ["geographical content", "Bharata"],
        "passage": "The geographical material of the Puranas is mostly contained in their first two books or ‘Laksanas’ which deal with cosmogony, cosmology and cosmography. They include, among other related matters, the origin of the universe and the earth, the oceans and the continents, mountain systems of the world, regions and their people and astronomical geography.",
    },
    {
        "evidence_id": "S3-EV-ALI-002", "resource_id": "IS529N-ALI-GOP-PART-01",
        "pdf_page": 13, "printed_page": "13", "classification": "TEXTUALLY_DOCUMENTED",
        "text_form": "SOURCE_CHECKED_SUMMARY",
        "topics": ["variation among Puranas", "pilgrimage", "interpretive limits"],
        "passage": "The Padma (Bhumi Khanda) illustrates places of pilgrimage; the Agni Purana emphasizes the Gaya region; the Brahma and Varaha Puranas the lands around Mathura and Puri; the Vamana Purana those of Thaneshvara; and the Padma Purana the Ajmer region. Ali cautions that the Puranas were not intended to be textbooks of geography and do not present geographical facts in a consistently logical order.",
    },
    {
        "evidence_id": "S3-EV-ALI-003", "resource_id": "IS529N-ALI-GOP-PART-02",
        "pdf_page": 11, "printed_page": "25", "classification": "TEXTUALLY_DOCUMENTED",
        "text_form": "VERBATIM_TRANSCRIPTION",
        "topics": ["variation among Puranas"],
        "passage": "All the Puranas, though basically identical as regards their geographical content, show variations in their regional accounts, according to their knowledge of various lands acquired through this source.",
    },
    {
        "evidence_id": "S3-EV-ALI-004", "resource_id": "IS529N-ALI-GOP-PART-03",
        "pdf_page": 1, "printed_page": "25", "classification": "TEXTUALLY_DOCUMENTED",
        "text_form": "SOURCE_CHECKED_SUMMARY",
        "topics": ["Jambudvipa", "dvipa traditions"],
        "passage": "A ‘dwipa’ literally means ‘land between two arms of water’; it may signify an island, a peninsula or a doab, and in ancient Sanskrit literature it was also used for a division of land. In the seven-dwipa scheme the central one is Jambu Dwipa, but the order of the other dwipas is not uniform in all the Puranas.",
    },
    {
        "evidence_id": "S3-EV-ALI-005", "resource_id": "IS529N-ALI-GOP-PART-03",
        "pdf_page": 13, "printed_page": "37", "classification": "TEXTUALLY_DOCUMENTED",
        "text_form": "SOURCE_CHECKED_SUMMARY",
        "topics": ["dvipa traditions", "interpretive limits", "metaphor"],
        "passage": "Ali treats ‘dwipa’ as capable of denoting natural or human regions and argues that discrepancies in their location or existence among different Puranas may have historical roots. He also warns that oceans of milk, curd, clarified butter, sugar-cane juice or wine should not be taken too literally.",
    },
    {
        "evidence_id": "S3-EV-ALI-006", "resource_id": "IS529N-ALI-GOP-PART-04",
        "pdf_page": 4, "printed_page": "49", "classification": "MODERN_GEOGRAPHICAL_RECONSTRUCTION",
        "text_form": "SOURCE_CHECKED_SUMMARY",
        "topics": ["Meru", "Puranic mountain system"],
        "passage": "Ali reconstructs Meru as a vast high plateau in the central continent, Jambu Dwipa, rather than an isolated peak, single mountain or individual range. This is Ali's modern geographical reading of descriptions in the Visnu, Matsya, Vayu and Bhagavata Puranas.",
    },
    {
        "evidence_id": "S3-EV-ALI-007", "resource_id": "IS529N-ALI-GOP-PART-04",
        "pdf_page": 7, "printed_page": "52", "classification": "MODERN_GEOGRAPHICAL_RECONSTRUCTION",
        "text_form": "SOURCE_CHECKED_SUMMARY",
        "topics": ["Meru", "Pamir", "Bharatavarsha", "Puranic mountain system"],
        "passage": "Ali concludes, on his stated premises, that the Meru of the Puranas can be identified with the Great Pamir Knot of Asia. He then relates ranges south of Meru—Nisadha, Hemakuta and Himalaya—to the boundaries of Harivarsa, Kimpurusa and Bharata Varsa. This remains Ali's attributed reconstruction, not a consensus identification.",
    },
    {
        "evidence_id": "S3-EV-VAL-001", "resource_id": "IS529N-VALDIYA-GPG-CH01",
        "pdf_page": 2, "printed_page": "xi", "classification": "TEXTUALLY_DOCUMENTED",
        "text_form": "SOURCE_CHECKED_SUMMARY",
        "topics": ["metaphor", "semantic change", "methodological caution"],
        "passage": "Valdiya states that the narratives are full of metaphors and allegories and cautions that meanings of words and phrases have changed over three to four thousand years, so present meanings cannot simply be projected backwards.",
    },
    {
        "evidence_id": "S3-EV-VAL-002", "resource_id": "IS529N-VALDIYA-GPG-CH01",
        "pdf_page": 3, "printed_page": "xii", "classification": "MODERN_GEOLOGICAL_INTERPRETATION",
        "text_form": "VERBATIM_TRANSCRIPTION",
        "topics": ["Meru", "Pamir", "Jambudvipa"],
        "passage": "It emerged that Mount Meru, located at the centre of the continent Jambudweep, was the focal point of what I would like to call the Puranland. It turns out that the Meru is the Puranic name of the Pamir massif of the present.",
        "interpretive_note": "Valdiya's attributed modern geological interpretation; not scholarly consensus.",
    },
    {
        "evidence_id": "S3-EV-VAL-003", "resource_id": "IS529N-VALDIYA-GPG-CH01",
        "pdf_page": 6, "printed_page": "2", "classification": "TEXTUALLY_DOCUMENTED",
        "text_form": "SOURCE_CHECKED_SUMMARY",
        "topics": ["oral transmission", "interpolation", "semantic change"],
        "passage": "Valdiya says the received Puranic history suffered repeated narration, translation, interpolations and interpretation by scholars with differing perceptions; he also describes the accounts as transmitted orally down the generations through samvad.",
    },
    {
        "evidence_id": "S3-EV-VAL-004", "resource_id": "IS529N-VALDIYA-GPG-CH01",
        "pdf_page": 8, "printed_page": "4", "classification": "MODERN_GEOLOGICAL_INTERPRETATION",
        "text_form": "VERBATIM_TRANSCRIPTION",
        "topics": ["pilgrimage", "spatial integration"],
        "passage": "Behind the idea of pilgrimage seems to be the objective of promoting national integration of people by visits of persons of one area to another where the people spoke different language, had different lifestyle, wore different kinds of garments and ate differently.",
        "interpretive_note": "Valdiya's attributed interpretation of pilgrimage's spatial role.",
    },
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def printed_page(source: dict[str, Any], pdf_page: int) -> str:
    if source["filename"] != "valdiya_ch1.pdf":
        return str(pdf_page + int(source["printed_offset"]))
    return {1: "title page", 2: "xi", 3: "xii", 4: "xiii"}.get(pdf_page, str(pdf_page - 4))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--ocr-cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    for source in SOURCES:
        stem = Path(source["filename"]).stem
        source_path = args.source_dir / source["filename"]
        raw_rows = []
        for page in range(1, int(source["page_count"]) + 1):
            page_file = args.ocr_cache / stem / "text" / f"pdf-{page:02d}.txt"
            text = page_file.read_text(encoding="utf-8", errors="replace").rstrip("\f\n")
            raw_rows.append({
                "resource_id": source["resource_id"], "pdf_page": page,
                "printed_page": printed_page(source, page), "raw_text": text,
                "raw_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "derivative_status": "RAW_TEXT_EXTRACTION" if stem == "valdiya_ch1" else "OCR_CANDIDATE",
                "verification_status": "EXTRACTED_UNVERIFIED" if stem == "valdiya_ch1" else "OCR_UNVERIFIED",
                "authoritative_source": source["filename"],
            })
        source_output = args.output / stem
        raw_path = source_output / "raw_pages.jsonl"
        jsonl(raw_path, raw_rows)
        derivatives = [{
            "path": raw_path.relative_to(ROOT).as_posix(), "sha256": digest(raw_path),
            "status": "RAW_PRESERVED" if stem == "valdiya_ch1" else "OCR_CANDIDATES",
            "verification_status": "EXTRACTED_UNVERIFIED" if stem == "valdiya_ch1" else "OCR_UNVERIFIED",
        }]
        if stem == "valdiya_ch1":
            corrected_rows = []
            for row in raw_rows:
                page = row["pdf_page"]
                corrected_file = args.ocr_cache / stem / "corrected_text" / f"pdf-{page:02d}.txt"
                corrected = corrected_file.read_text(encoding="utf-8", errors="replace").rstrip("\f\n")
                corrected_rows.append({
                    **{k: row[k] for k in ("resource_id", "pdf_page", "printed_page", "authoritative_source")},
                    "corrected_text": corrected,
                    "corrected_text_sha256": hashlib.sha256(corrected.encode()).hexdigest(),
                    "derivative_status": "IMAGE_LAYER_REEXTRACTION_CORRECTED_CANDIDATE",
                    "verification_status": "OCR_UNVERIFIED",
                    "raw_derivative": raw_path.relative_to(ROOT).as_posix(),
                })
            corrected_path = source_output / "corrected_pages.jsonl"
            jsonl(corrected_path, corrected_rows)
            derivatives.append({
                "path": corrected_path.relative_to(ROOT).as_posix(), "sha256": digest(corrected_path),
                "status": "CORRECTED_DERIVATIVE_SEPARATE_FROM_RAW",
                "verification_status": "OCR_UNVERIFIED_EXCEPT_SOURCE_CHECKED_EVIDENCE_PASSAGES",
            })
        manifest.append({
            "canonical_resource_id": source["resource_id"], "title": source["title"],
            "author": source["author"], "source_path": str(source_path.resolve()),
            "original_file_sha256": digest(source_path), "page_count": source["page_count"],
            "derivative_file_sha256": derivatives[0]["sha256"], "derivative_files": derivatives,
            "derivative_status": derivatives[0]["status"],
            "verification_status": "SOURCE_HASHED_DERIVATIVE_UNVERIFIED",
            "citation_form": source["citation"], "original_is_authoritative": True,
        })
    bundle = {
        "bundle_id": "L01-DECK-005-S003-PURANIC-EVIDENCE-001",
        "historical_slide_id": "L01-DECK-005-S003",
        "status": "SOURCE_CHECKED_PASSAGES_WITH_ATTRIBUTED_INTERPRETATIONS",
        "academic_rule": "Original PDFs are authoritative; raw OCR and extracted text remain derivatives.",
        "classification_vocabulary": [
            "TEXTUALLY_DOCUMENTED", "MODERN_GEOGRAPHICAL_RECONSTRUCTION",
            "MODERN_GEOLOGICAL_INTERPRETATION",
        ],
        "passages": [
            {**item, "verification_status": "SOURCE_CHECKED", "citation": next(
                source["citation"] for source in SOURCES if source["resource_id"] == item["resource_id"]
            )} for item in EVIDENCE
        ],
    }
    bundle_path = args.output / "SLIDE3_EVIDENCE_BUNDLE.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path = args.output / "SOURCE_MANIFEST.json"
    manifest_path.write_text(json.dumps({"sources": manifest}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(manifest_path)
    print(bundle_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
