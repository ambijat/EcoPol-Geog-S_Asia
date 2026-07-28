"""Capture local, synthetic acceptance evidence for the course artifact desktop shell."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from course_artifacts.config import CourseArtifactConfig, DEFAULT_CLASS_CONFIG, DEFAULT_RELATIONSHIP_CONFIG
from course_artifacts.domain.models import ArtifactRegistration, RelationshipRegistration
from desktop.config import DesktopConfig, STYLE_SHEET, WATERMARK
from desktop.dialogs.relationship_dialog import RelationshipDialog
from desktop.dialogs.first_launch_wizard import FirstLaunchPathWizard
from course_artifacts.services.path_resolver import DEFAULT_ROOTS, LocalPathStore, PathResolver
from desktop.main_window import MainWindow


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "desktop_artifact_acceptance"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite acceptance evidence: {output}")
    output.mkdir(parents=True, exist_ok=True)
    screenshots = output / "screenshots"
    screenshots.mkdir()
    course_artifacts = CourseArtifactConfig(
        database_path=output / "fixture.sqlite3",
        class_config_path=DEFAULT_CLASS_CONFIG,
        relationship_config_path=DEFAULT_RELATIONSHIP_CONFIG,
        local_paths_path=output / "local_paths.json",
    )
    roots = output / "fixture_roots"
    store = LocalPathStore(course_artifacts)
    for code in DEFAULT_ROOTS:
        path = roots / code.lower()
        path.mkdir(parents=True)
        values = {"path": str(path), "allow_inside_project": True}
        if code == "INSTRUCTOR_DEFINED_CLASS_5":
            values["access_mode"] = "read_write"
        store.update(code, **values)
    foundational = roots / "foundational_resource"
    published = roots / "published_presentation_pdf"
    published_file = published / "fixtures/published-lecture.pdf"
    published_file.parent.mkdir()
    published_file.write_bytes(b"synthetic published presentation acceptance fixture")
    source_file = foundational / "fixtures/source-chapter.pdf"
    source_file.parent.mkdir()
    source_file.write_bytes(b"synthetic source chapter acceptance fixture")
    topic_fixtures = {
        "LEC_RES_1/aijaz_region_sasia": ("regional-framework.pdf", "map.png"),
        "LEC_RES_1/development_indicators": ("indicators.pdf", "chart.jpg"),
        "LEC_RES_1/geology_him": ("himalayan-geology.pdf", "tectonics.docx"),
        "LEC_RES_1/monsoon_readings": ("monsoon.pdf",),
        "LEC_RES_1/notes_cunningham": ("historical-research-notes.txt",),
        "LEC_RES_1/onto_epistemo": ("ontology.pdf",),
        "LEC_RES_1/puranas_geo": ("mythic-topography.pdf", "map.png"),
        "LEC_RES_1/region_concept": ("regional-theory.pdf",),
        "LEC_RES_1/strabo_ancient": ("ancient-geography.docx",),
        "LEC_RES_2/development": ("human-development.pdf",),
    }
    for topic_path, filenames in topic_fixtures.items():
        topic = foundational / topic_path
        topic.mkdir(parents=True)
        for filename in filenames:
            (topic / filename).write_bytes(
                f"synthetic topic fixture {topic_path}/{filename}".encode()
            )
    (foundational / "LEC_RES_1/ORGANIZATION_MANIFEST.md").write_text(
        "synthetic loose container manifest", encoding="utf-8"
    )
    (foundational / "LEC_RES_1/.claude").mkdir()
    (foundational / "LEC_RES_1/.claude/state.md").write_text(
        "synthetic hidden system fixture", encoding="utf-8"
    )
    workbench_file = (
        roots / "presentation_workbench" / "fixtures/workbench-v0.1.odp"
    )
    workbench_file.parent.mkdir()
    workbench_file.write_bytes(b"synthetic ODP acceptance fixture")
    ai_notes = roots / "ai_generated_artifact"
    for number in range(1, 16):
        (ai_notes / f"LEC_{number}").mkdir()
    (ai_notes / "LEC_1/revision-outline.tex").write_text(
        "\\section{Synthetic AI-assisted revision outline}", encoding="utf-8"
    )
    (ai_notes / "LEC_1/source-comparison.pdf").write_bytes(
        b"Synthetic AI source comparison"
    )
    (ai_notes / "LEC_2/revision-outline.tex").write_text(
        "\\section{Synthetic lecture two revision outline}", encoding="utf-8"
    )
    for number in range(1, 21):
        for variant in ("a", "b"):
            basename = f"lecture{number}{variant}"
            lecture = (
                roots / "presentation_workbench"
                / f"lecture_{number:02}" / f"{basename}.odp"
            )
            lecture.parent.mkdir(exist_ok=True)
            lecture.write_bytes(
                f"synthetic ODP acceptance fixture {basename}".encode()
            )
            published_lecture = published / f"{basename}.pdf"
            published_lecture.write_bytes(
                f"synthetic published PDF acceptance fixture {basename}".encode()
            )
    (
        roots / "presentation_workbench" / "unsorted" / "unrelated-source.pdf"
    ).parent.mkdir()
    (
        roots / "presentation_workbench" / "unsorted" / "unrelated-source.pdf"
    ).write_bytes(b"must not enter the workbench candidate census")
    (foundational / "fixtures/unregistered-map.svg").write_text(
        "<svg xmlns=\"http://www.w3.org/2000/svg\"/>", encoding="utf-8"
    )
    visual_root = roots / "instructor_defined_class_5"
    (visual_root / "regional-concepts.canvas").write_text(
        '{"nodes": [], "edges": []}\n', encoding="utf-8"
    )
    (visual_root / "lecture-sequence.graphml").write_text(
        "<graphml/>\n", encoding="utf-8"
    )
    config = DesktopConfig(course_artifacts, STYLE_SHEET, WATERMARK)
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("IS529N Economic and Political Geography of South Asia")
    app.setApplicationDisplayName(
        "IS529N — Economic and Political Geography of South Asia"
    )
    app.setOrganizationName("IS529N Semester 2026")
    if STYLE_SHEET.is_file():
        app.setStyleSheet(STYLE_SHEET.read_text(encoding="utf-8"))
    window = MainWindow(config)
    source = window.artifact_service.register(ArtifactRegistration(
        "FOUNDATIONAL_RESOURCE", "Synthetic source chapter",
        physical_path=source_file,
        symbolic_locator="FOUNDATIONAL_RESOURCE://fixtures/source-chapter.pdf",
        provenance="Synthetic acceptance fixture; no instructor source bytes",
    ))
    workbench = window.artifact_service.register(ArtifactRegistration(
        "PRESENTATION_WORKBENCH", "Synthetic ODP workbench v0.1",
        physical_path=workbench_file,
        symbolic_locator="PRESENTATION_WORKBENCH://fixtures/workbench-v0.1.odp",
        provenance="Synthetic acceptance fixture",
    ))
    window.relationship_service.create(RelationshipRegistration(
        source, workbench, "CANDIDATE_INGREDIENT_FOR",
        status="SYSTEM_SUGGESTED", evidence="Synthetic relationship evidence",
    ))
    window.refresh_all()
    window.resize(1500, 900)
    window.show()
    app.processEvents()
    records: list[dict] = []

    def save(name: str):
        window.repaint()
        app.processEvents()
        target = screenshots / f"{name}.png"
        if not window.grab().save(str(target)):
            raise RuntimeError(f"could not save {target}")
        records.append({
            "screen": name, "path": target.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256(target), "bytes": target.stat().st_size,
            "viewport": {
                "width": window.width(),
                "height": window.height(),
            },
        })

    window.navigate("HOME")
    for name, width, height in (
        ("home_1920x1080", 1920, 1080),
        ("home_1500x900", 1500, 900),
        ("home_1200x750", 1200, 750),
        ("home_minimum_1100x700", 1100, 700),
    ):
        window.resize(width, height)
        window.main_splitter.setSizes([245, max(640, width - 245)])
        app.processEvents()
        app.processEvents()
        save(name)
    window.resize(1500, 900)
    window.main_splitter.setSizes([245, 1255])
    window.activateWindow()
    window.navigation.setFocus(Qt.FocusReason.OtherFocusReason)
    app.processEvents()
    save("focus_sidebar_1500x900")
    window.global_buttons["Refresh All"].setFocus(
        Qt.FocusReason.OtherFocusReason
    )
    app.processEvents()
    save("focus_global_toolbar_1500x900")
    window.navigate("HOME")
    window.home_view.class_cards[0].setFocus(
        Qt.FocusReason.OtherFocusReason
    )
    app.processEvents()
    save("focus_artifact_card_1500x900")

    window.open_class("PUBLISHED_PRESENTATION_PDF")
    for name, width, height in (
        ("published_pdfs_empty_1500x900", 1500, 900),
        ("published_pdfs_empty_1200x750", 1200, 750),
        ("published_pdfs_empty_1100x700", 1100, 700),
    ):
        window.resize(width, height)
        window.main_splitter.setSizes([245, max(640, width - 245)])
        app.processEvents()
        app.processEvents()
        save(name)
    window.resize(1100, 700)
    window.main_splitter.setSizes([245, 855])
    window.class_workspaces[
        "PUBLISHED_PRESENTATION_PDF"
    ].configure_path_button.setFocus(Qt.FocusReason.OtherFocusReason)
    app.processEvents()
    save("focus_empty_state_action_1100x700")

    window.artifact_service.register(ArtifactRegistration(
        "PUBLISHED_PRESENTATION_PDF", "Synthetic selected published lecture",
        physical_path=published_file,
        symbolic_locator=(
            "PUBLISHED_PRESENTATION_PDF://fixtures/published-lecture.pdf"
        ),
        provenance="Synthetic acceptance fixture",
    ))
    window.refresh_all()
    window.open_class("PUBLISHED_PRESENTATION_PDF")
    published_workspace = window.class_workspaces["PUBLISHED_PRESENTATION_PDF"]
    published_workspace.table.selectRow(0)
    for name, width, height in (
        ("published_pdfs_selected_1500x900", 1500, 900),
        ("published_pdfs_selected_1200x750", 1200, 750),
        ("published_pdfs_selected_1100x700", 1100, 700),
    ):
        window.resize(width, height)
        window.main_splitter.setSizes([245, max(640, width - 245)])
        app.processEvents()
        app.processEvents()
        save(name)
    window.resize(1500, 900)
    window.main_splitter.setSizes([245, 1255])
    published_workspace.table.setFocus(Qt.FocusReason.OtherFocusReason)
    app.processEvents()
    save("focus_artifact_table_1500x900")
    window.resize(1100, 700)
    window.main_splitter.setSizes([245, 855])
    published_workspace.action_buttons["Open"].setFocus(
        Qt.FocusReason.OtherFocusReason
    )
    app.processEvents()
    save("focus_record_action_1100x700")

    window.resize(1500, 900)
    window.main_splitter.setSizes([245, 1255])
    app.processEvents()
    for artifact_class in window.class_repository.list(active_only=True):
        window.open_class(artifact_class["code"])
        app.processEvents()
        save(f'class_{artifact_class["code"].lower()}')
    visual_workspace = window.class_workspaces["INSTRUCTOR_DEFINED_CLASS_5"]
    visual_workspace.visualization_service.create_mind_map(
        "South Asia Regional Concepts"
    )
    window.refresh_all()
    window.open_class("INSTRUCTOR_DEFINED_CLASS_5")
    visual_workspace.table.selectRow(0)
    for name, width, height in (
        ("knowledge_maps_selected_1500x900", 1500, 900),
        ("knowledge_maps_selected_1100x700", 1100, 700),
    ):
        window.resize(width, height)
        window.main_splitter.setSizes([245, max(640, width - 245)])
        app.processEvents()
        app.processEvents()
        save(name)
    window.navigate("DECISIONS")
    app.processEvents()
    save("instructor_decision_queue")
    window.navigate("PATHS")
    app.processEvents()
    save("artifact_repository_paths")
    window.open_repository_paths_for("PRESENTATION_WORKBENCH")
    app.processEvents()
    save("repository_path_presentation_workbench_1500x900")
    window.scan_service.scan("FOUNDATIONAL_RESOURCE")
    window.scan_view.set_class("FOUNDATIONAL_RESOURCE")
    window.scan_view.reload()
    window.navigate("SCAN")
    for name, width, height in (
        ("scan_candidate_columns_1500x900", 1500, 900),
        ("scan_candidate_columns_1200x750", 1200, 750),
        ("scan_candidate_columns_1100x700", 1100, 700),
    ):
        window.resize(width, height)
        window.main_splitter.setSizes([245, max(640, width - 245)])
        app.processEvents()
        app.processEvents()
        save(name)
    window.resize(1500, 900)
    window.main_splitter.setSizes([245, 1255])
    app.processEvents()
    save("lecture_raw_material_topic_folders_1500x900")
    window.scan_service.scan("PUBLISHED_PRESENTATION_PDF")
    window.scan_view.set_class("PUBLISHED_PRESENTATION_PDF")
    window.scan_view.reload()
    window.resize(1500, 900)
    window.main_splitter.setSizes([245, 1255])
    app.processEvents()
    app.processEvents()
    save("scan_category_published_pdfs_1500x900")
    window.scan_service.scan("PRESENTATION_WORKBENCH")
    window.scan_view.set_class("PRESENTATION_WORKBENCH")
    window.scan_view.reload()
    for name, width, height in (
        ("scan_workbench_odp_census_1500x900", 1500, 900),
        ("scan_workbench_odp_census_1100x700", 1100, 700),
    ):
        window.resize(width, height)
        window.main_splitter.setSizes([245, max(640, width - 245)])
        app.processEvents()
        app.processEvents()
        save(name)
    window.scan_service.scan("AI_GENERATED_ARTIFACT")
    window.scan_service.set_ai_revision_workbench(
        1, "lecture_01/lecture1a.odp"
    )
    window.scan_service.set_ai_revision_state(
        1, "IN_REVISION", "lecture_01/lecture1a.odp"
    )
    window.scan_view.set_class("AI_GENERATED_ARTIFACT")
    window.scan_view.reload()
    for name, width, height in (
        ("ai_presentation_revision_queue_1500x900", 1500, 900),
        ("ai_presentation_revision_queue_1100x700", 1100, 700),
    ):
        window.resize(width, height)
        window.main_splitter.setSizes([245, max(640, width - 245)])
        app.processEvents()
        app.processEvents()
        save(name)
    dialog = RelationshipDialog(
        window.relationship_service, window.artifact_repository, source, window
    )
    dialog.show()
    app.processEvents()
    target = screenshots / "create_relationship_dialog.png"
    if not dialog.grab().save(str(target)):
        raise RuntimeError(f"could not save {target}")
    records.append({
        "screen": "create_relationship_dialog",
        "path": target.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": sha256(target), "bytes": target.stat().st_size,
    })
    dialog.close()
    missing_config = CourseArtifactConfig(
        database_path=output / "fixture.sqlite3",
        class_config_path=DEFAULT_CLASS_CONFIG,
        relationship_config_path=DEFAULT_RELATIONSHIP_CONFIG,
        local_paths_path=output / "missing_paths_wizard_fixture.json",
    )
    wizard = FirstLaunchPathWizard(
        PathResolver(missing_config), window.class_repository, window
    )
    wizard.show()
    app.processEvents()
    target = screenshots / "first_launch_path_wizard.png"
    if not wizard.grab().save(str(target)):
        raise RuntimeError(f"could not save {target}")
    records.append({
        "screen": "first_launch_path_wizard",
        "path": target.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": sha256(target), "bytes": target.stat().st_size,
    })
    wizard.close()
    window.close()
    manifest = {
        "evidence_type": "LOCAL_SYNTHETIC_DESKTOP_ACCEPTANCE",
        "public_candidate": False,
        "source_repository_bytes_used": False,
        "screenshots": records,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    manifest = capture(arguments.output.resolve())
    print(json.dumps({"screenshots": len(manifest["screenshots"]), "status": "CAPTURED"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
