#!/usr/bin/env python3
"""Build project-guide edition 1.2 without repaginating edition 1.0.

The DOCX is rebuilt from the archived edition 1.0 package by appending OOXML.
LibreOffice renders only the new addendum. ``pdfunite`` then joins the original
25-page PDF and the addendum PDF, preserving the original publication pages.

Run with system Python while LibreOffice is listening on port 2002:

    libreoffice --headless \
      --accept='socket,host=localhost,port=2002;urp;StarOffice.ServiceManager'
    /usr/bin/python3 scripts/update_project_guide_culmination.py
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

import uno
from com.sun.star.beans import PropertyValue
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GUIDE_DIR = PROJECT_ROOT / "project_face_guide"
ARCHIVE_DIR = GUIDE_DIR / "archive" / "edition_1.0"
FILE_STEM = "IS529N_Project_Guide_and_Expert_Operator_Manual"
BASE_DOCX = ARCHIVE_DIR / f"{FILE_STEM}.docx"
BASE_PDF = ARCHIVE_DIR / f"{FILE_STEM}.pdf"
DOCX_PATH = GUIDE_DIR / f"{FILE_STEM}.docx"
PDF_PATH = GUIDE_DIR / f"{FILE_STEM}.pdf"
ADDENDUM_TITLE = "Culmination Addendum — Teacher Incubation and Shareable Freeze"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"

ET.register_namespace("w", WORD_NS)


@dataclass(frozen=True)
class Paragraph:
    style: str
    text: str
    page_break: bool = False


def heading(text: str, *, first: bool = False) -> Paragraph:
    return Paragraph("Heading1" if first else "Heading2", text, first)


def body(text: str) -> Paragraph:
    return Paragraph("BodyText", text)


def bullet(text: str) -> Paragraph:
    return body(f"• {text}")


def check(text: str) -> Paragraph:
    return body(f"☑ {text}")


ADDENDUM = (
    heading(ADDENDUM_TITLE, first=True),
    body(
        "This controlled addendum records the instructor rulings of 28 July 2026 "
        "and governs the path from pilot operation to a shareable project state. "
        "It preserves the original preamble and earlier manual body. Where more "
        "specific, it controls the culmination phase."
    ),
    heading("E.1 Academic baseline"),
    bullet(
        "The inherited 65-slide Lecture 1A editable presentation is the canonical "
        "F0 pilot master. Its identity has been accepted; its content and classroom "
        "fitness remain subject to teacher incubation."
    ),
    bullet(
        "The 15-slide v0.5 presentation is a synoptic companion: an additional "
        "overview layer that summarises the master. It is not a shortened, revised, "
        "or replacement master."
    ),
    bullet(
        "Technical validation, rendering, registration, or lineage does not confer "
        "academic approval or F4 classroom status."
    ),
    heading("E.2 Teacher incubation"),
    body(
        "The teacher incubates the 65-slide master in bounded review units: opening "
        "slides 1–2; KC01 slides 3–18; KC02 19–27; KC03 28–39; KC04 40–46; "
        "KC05 47–56; KC06 57–60; and closing slides 61–65. Each unit receives one "
        "explicit decision: RETAIN, REVISE, MERGE, REMOVE, or MOVE_TO_NOTES. A new "
        "derivative is generated only from recorded teacher decisions."
    ),
    heading("E.3 Culmination doctrine"),
    body(
        "The project now favours correction, clarity, preservation, verification, "
        "and bounded handoff. New capability is deferred unless it prevents data "
        "loss, corrects a material fault, protects restricted material, completes "
        "teacher incubation, or is necessary for a reproducibly shareable "
        "projection. Vocabulary, schemas, paths, and interfaces should stabilise; "
        "dead complexity should be removed."
    ),
    heading("E.4 Freeze states"),
    body("WORKING → FREEZE_CANDIDATE → SHAREABLE_FREEZE → RELEASED"),
    bullet("FREEZE_CANDIDATE: the project is being stabilised and audited."),
    bullet(
        "SHAREABLE_FREEZE: an exact reviewed projection can be handed to another "
        "authorised person without undocumented local dependencies."
    ),
    bullet(
        "RELEASED: a separately authorised publication or distribution action has "
        "occurred."
    ),
    body(
        "A shareable freeze is not classroom approval, an F4 decision, semester "
        "closure, or a claim that teacher incubation is complete."
    ),
    heading("E.5 Shareable projection boundary"),
    body(
        "Self-authored project material is freely shareable under CC0 1.0. It may "
        "be copied, changed, taught from, or redistributed without asking "
        "permission. No separate clearance ritual is required."
    ),
    body(
        "The projection excludes source repositories, local databases, caches, "
        "previews, working notes, student or assessment data, credentials, "
        "machine-specific paths, and imported files not created for this project. "
        "This is a practical safety boundary, not a proprietary claim."
    ),
    heading("E.6 Shareable-freeze gate"),
    check("Teacher-incubation status and unresolved academic decisions are stated truthfully."),
    check("The exact shareable file projection is generated and reviewed."),
    check("Repository validation, relevant tests, and ledger validation pass."),
    check(
        "The exact projection is checked for credentials, restricted data, private "
        "locations, absolute paths, and imported files."
    ),
    check("Local-only binaries, databases, caches, and previews are absent."),
    check("Guide checksums, limitations, and handoff instructions are current."),
    check("The tracked working tree is clean at the selected freeze commit."),
    check("The instructor's free-sharing ruling of 28 July 2026 is recorded."),
    body(
        "Tagging, pushing, deploying, or distributing remains a separate action "
        "requiring separate authority."
    ),
    heading("E.7 Change control after freeze"),
    body(
        "After SHAREABLE_FREEZE, changes are limited to security or privacy "
        "corrections, data-loss prevention, material factual or validation faults, "
        "authorised release corrections, and explicitly approved academic "
        "decisions. Other ideas are deferred."
    ),
    heading("E.8 Current determination"),
    body(
        "As of 28 July 2026 the project is SHAREABLE_FREEZE. The candidate "
        "allowlist and automated checks are current, and self-authored project "
        "material is freely shareable under CC0 1.0. Lecture 1A teacher incubation "
        "remains open and must not be represented as complete. No push, deployment, "
        "or public release is implied by this freeze."
    ),
    heading("Culmination principle"),
    body(
        "Freeze is an act of clarity: every included object has a reason, every "
        "excluded object has a boundary, and technical polish never impersonates "
        "academic judgement."
    ),
)


def qname(local_name: str) -> str:
    return f"{{{WORD_NS}}}{local_name}"


def ooxml_paragraph(item: Paragraph) -> ET.Element:
    paragraph = ET.Element(qname("p"))
    properties = ET.SubElement(paragraph, qname("pPr"))
    style = ET.SubElement(properties, qname("pStyle"))
    style.set(qname("val"), item.style)
    if item.page_break:
        ET.SubElement(properties, qname("pageBreakBefore"))
    run = ET.SubElement(paragraph, qname("r"))
    text = ET.SubElement(run, qname("t"))
    text.set(f"{{{XML_NS}}}space", "preserve")
    text.text = item.text
    return paragraph


def build_docx() -> None:
    if not BASE_DOCX.is_file():
        raise FileNotFoundError(f"Missing preserved source: {BASE_DOCX}")

    with zipfile.ZipFile(BASE_DOCX, "r") as source:
        document_xml = source.read("word/document.xml")
        root = ET.fromstring(document_xml)

        replacements = 0
        for text in root.iter(qname("t")):
            if text.text and "Publication edition 1.0" in text.text:
                text.text = text.text.replace(
                    "Publication edition 1.0", "Publication edition 1.2"
                )
                replacements += 1
            if text.text and ADDENDUM_TITLE in text.text:
                raise RuntimeError("Archived source already contains the addendum")
        if replacements != 1:
            raise RuntimeError(f"Expected one edition marker; found {replacements}")

        document_body = root.find(f".//{qname('body')}")
        if document_body is None:
            raise RuntimeError("DOCX has no document body")
        section_properties = document_body.find(qname("sectPr"))
        insertion_index = (
            list(document_body).index(section_properties)
            if section_properties is not None
            else len(document_body)
        )
        for item in ADDENDUM:
            document_body.insert(insertion_index, ooxml_paragraph(item))
            insertion_index += 1

        updated_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        temporary_path = DOCX_PATH.with_suffix(".docx.tmp")
        with zipfile.ZipFile(temporary_path, "w") as target:
            for entry in source.infolist():
                payload = (
                    updated_xml
                    if entry.filename == "word/document.xml"
                    else source.read(entry.filename)
                )
                target.writestr(entry, payload)
        temporary_path.replace(DOCX_PATH)


def property_value(name: str, value: object) -> PropertyValue:
    item = PropertyValue()
    item.Name = name
    item.Value = value
    return item


def connect_desktop():
    local_context = uno.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_context
    )
    context = resolver.resolve(
        "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
    )
    return context.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", context
    )


def render_addendum_pdf(output_path: Path) -> None:
    desktop = connect_desktop()
    document = desktop.loadComponentFromURL(
        "private:factory/swriter",
        "_blank",
        0,
        (property_value("Hidden", True),),
    )
    if document is None:
        raise RuntimeError("Could not create addendum document")

    try:
        page_styles = document.StyleFamilies.getByName("PageStyles")
        page_style = page_styles.getByName("Default Page Style")
        page_style.FooterIsOn = True
        page_style.FooterText.String = "Culmination Addendum | Edition 1.2 | July 2026"

        text = document.Text
        for item in ADDENDUM:
            cursor = text.createTextCursor()
            cursor.gotoEnd(False)
            cursor.ParaStyleName = {
                "Heading1": "Heading 1",
                "Heading2": "Heading 2",
                "BodyText": "Text body",
            }[item.style]
            text.insertString(cursor, item.text, False)
            text.insertControlCharacter(cursor, PARAGRAPH_BREAK, False)

        document.storeToURL(
            uno.systemPathToFileUrl(str(output_path)),
            (
                property_value("FilterName", "writer_pdf_Export"),
                property_value("Overwrite", True),
            ),
        )
    finally:
        document.close(True)


def build_pdf() -> None:
    if not BASE_PDF.is_file():
        raise FileNotFoundError(f"Missing preserved source: {BASE_PDF}")
    if shutil.which("pdfunite") is None:
        raise RuntimeError("pdfunite is required")

    with tempfile.TemporaryDirectory(prefix="is529n-guide-") as temporary_directory:
        addendum_pdf = Path(temporary_directory) / "addendum.pdf"
        joined_pdf = Path(temporary_directory) / "edition_1_2.pdf"
        render_addendum_pdf(addendum_pdf)
        subprocess.run(
            ["pdfunite", str(BASE_PDF), str(addendum_pdf), str(joined_pdf)],
            check=True,
        )
        shutil.copyfile(joined_pdf, PDF_PATH)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    build_docx()
    build_pdf()
    print(f"DOCX_SHA256={sha256(DOCX_PATH)}")
    print(f"PDF_SHA256={sha256(PDF_PATH)}")


if __name__ == "__main__":
    main()
