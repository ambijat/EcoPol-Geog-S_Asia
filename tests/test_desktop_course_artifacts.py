from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import (
    QAbstractButton, QApplication, QDialog, QHeaderView, QLabel,
)

from course_artifacts.config import CourseArtifactConfig, DEFAULT_CLASS_CONFIG, DEFAULT_RELATIONSHIP_CONFIG
from course_artifacts.domain.models import ArtifactRegistration
from course_artifacts.services.path_resolver import LocalPathStore
from desktop.app import create_application
from desktop.config import DesktopConfig, STYLE_SHEET, WATERMARK
from desktop.dialogs.artifact_dialog import ArtifactRegistrationDialog
from desktop.dialogs.relationship_dialog import RelationshipDialog
from desktop.dialogs.first_launch_wizard import FirstLaunchPathWizard
from desktop.main_window import MainWindow


class DesktopCourseArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project_root = self.root / "application"
        self.project_root.mkdir()
        course_artifacts = CourseArtifactConfig(
            project_root=self.project_root,
            database_path=self.root / "local_state/database/test.sqlite3",
            class_config_path=DEFAULT_CLASS_CONFIG,
            relationship_config_path=DEFAULT_RELATIONSHIP_CONFIG,
            local_paths_path=self.root / "config/local_paths.json",
        )
        self.config = DesktopConfig(course_artifacts, STYLE_SHEET, WATERMARK)
        self.window = MainWindow(self.config)

    def tearDown(self):
        self.window.close()
        self.application.processEvents()
        self.temporary.cleanup()

    def test_application_launches_with_six_class_buttons_and_no_server(self):
        self.window.show()
        self.application.processEvents()
        self.assertEqual(self.window.artifact_class_button_count, 6)
        self.assertEqual(self.window.navigation.currentItem().text(), "Cockpit Home")
        self.assertFalse(hasattr(self.window, "server_process"))
        self.assertEqual(
            self.window.windowTitle(),
            "IS529N — Economic and Political Geography of South Asia",
        )
        self.assertEqual(
            self.window.home_view.course_title.text(),
            "Economic and Political Geography of South Asia",
        )
        self.assertEqual(
            self.window.home_view.functional_title.text(),
            "Course Artifact Cockpit",
        )
        self.assertEqual(
            self.window.home_view.evidence_subtitle.text(),
            "Artifact evidence, provenance and relationship management",
        )
        self.assertIn(
            "Economic and Political Geography of South Asia",
            self.window.course_identity_label.text().replace("\n", " "),
        )
        self.assertEqual(
            self.window.methodology_label.text(),
            "Course Artifact Cockpit",
        )
        self.assertTrue(self.window.path_setup_required)
        published = self.window.class_workspaces["PUBLISHED_PRESENTATION_PDF"]
        self.assertFalse(published.scan_button.isEnabled())
        self.assertFalse(published.register_button.isEnabled())
        self.assertTrue(self.window.scan_view.isEnabled())
        self.assertTrue(self.window.scan_view.table.isEnabled())
        self.assertFalse(self.window.scan_view.scan_button.isEnabled())
        self.assertIsNotNone(self.window.path_wizard)
        self.assertTrue(self.window.path_wizard.isVisible())

    def test_visible_product_language_uses_course_artifact_terminology(self):
        self.window.show()
        self.application.processEvents()
        dialog = ArtifactRegistrationDialog(
            self.window.artifact_service, self.window.class_repository,
            "PUBLISHED_PRESENTATION_PDF", self.window,
            self.window.path_resolver,
        )
        visible_text = [
            self.window.accessibleName(),
            self.window.accessibleDescription(),
            self.window.status_label.text(),
            *(
                widget.text()
                for widget in self.window.findChildren(QLabel)
            ),
            *(
                widget.text()
                for widget in self.window.findChildren(QAbstractButton)
            ),
            *(
                widget.text()
                for widget in dialog.findChildren(QLabel)
            ),
        ]
        for item in visible_text:
            self.assertNotIn("archaeolog", item.casefold())
        self.assertEqual(
            self.window.methodology_label.text(), "Course Artifact Cockpit"
        )
        self.assertEqual(
            self.window.home_view.evidence_subtitle.text(),
            "Artifact evidence, provenance and relationship management",
        )
        dialog.close()

    def test_main_window_reflows_cleanly_at_narrow_and_wide_sizes(self):
        self.window.show()
        self.application.processEvents()
        if self.window.path_wizard is not None:
            self.window.path_wizard.close()
        self.window.navigate("HOME")

        self.assertNotEqual(self.window.minimumSize(), self.window.maximumSize())
        self.assertGreater(
            self.window.maximumWidth(), self.window.minimumWidth()
        )
        self.assertGreater(
            self.window.maximumHeight(), self.window.minimumHeight()
        )

        self.window.resize(1100, 700)
        self.application.processEvents()
        self.assertEqual(self.window.size().width(), 1100)
        self.assertEqual(self.window.size().height(), 700)
        self.assertEqual(self.window.home_view.class_column_count, 1)
        self.assertEqual(self.window.global_action_columns, 5)
        self.assertEqual(len(self.window.home_view.class_cards), 6)
        for card in self.window.home_view.class_cards:
            self.assertLessEqual(
                card.width(), self.window.home_view.scroll_area.viewport().width()
            )
            self.assertFalse(card.isHidden())
            self.assertFalse(card.open_button.isHidden())
        for label in (
            "Cockpit Home", "Refresh All", "Find Duplicates",
            "Relationship Map", "Processing Queue", "Instructor Decisions",
            "Settings",
        ):
            self.assertFalse(self.window.global_buttons[label].isHidden())
            self.assertGreater(self.window.global_buttons[label].width(), 0)

        self.window.resize(1500, 950)
        self.application.processEvents()
        self.assertEqual(self.window.size().width(), 1500)
        self.assertEqual(self.window.home_view.class_column_count, 2)
        self.assertEqual(self.window.global_action_columns, 7)

        self.window.main_splitter.setSizes([220, 1280])
        self.application.processEvents()
        self.assertGreaterEqual(self.window.navigation_frame.width(), 210)
        self.assertLessEqual(self.window.navigation_frame.width(), 330)

    def test_create_application_factory(self):
        app, second_window = create_application(self.config, [])
        self.assertIs(app, self.application)
        self.assertIsInstance(second_window, MainWindow)
        self.assertEqual(
            app.applicationName(),
            "IS529N Economic and Political Geography of South Asia",
        )
        self.assertEqual(
            app.applicationDisplayName(),
            "IS529N — Economic and Political Geography of South Asia",
        )
        self.assertEqual(app.organizationName(), "IS529N Semester 2026")
        second_window.close()

    def test_each_class_button_opens_correct_workspace(self):
        for artifact_class in self.window.class_repository.list(active_only=True):
            self.window.home_view.class_opened.emit(artifact_class["code"])
            self.assertEqual(
                self.window.stack_keys[self.window.stack.currentIndex()],
                f'CLASS:{artifact_class["code"]}',
            )

    def test_sidebar_uses_complete_concise_labels_without_elision(self):
        expected = [
            "Cockpit Home", "Published PDFs", "Presentation Workbench",
            "Lecture Raw Material", "AI-assisted LaTeX Notes",
            "Knowledge Maps", "Spatial Raw Material", "Artifact Relationships",
            "Scan Candidates", "Instructor Decisions", "Repository Paths",
            "Settings",
        ]
        self.window.show()
        self.window.resize(1100, 700)
        self.application.processEvents()
        actual = [
            self.window.navigation.item(row).text()
            for row in range(self.window.navigation.count())
        ]
        self.assertEqual(actual, expected)
        metrics = self.window.navigation.fontMetrics()
        for row, label in enumerate(expected):
            item = self.window.navigation.item(row)
            self.assertNotIn("…", item.text())
            self.assertNotIn("...", item.text())
            self.assertGreater(
                self.window.navigation.visualItemRect(item).width(),
                metrics.horizontalAdvance(label),
            )
        self.assertEqual(
            self.window.navigation.item(1).toolTip(),
            "Published Presentation PDFs",
        )

    def test_global_and_class_actions_have_distinct_ownership(self):
        self.assertEqual(
            list(self.window.global_buttons),
            [
                "Cockpit Home", "Refresh All", "Find Duplicates",
                "Relationship Map", "Processing Queue",
                "Instructor Decisions", "Settings",
            ],
        )
        workspace = self.window.class_workspaces["PUBLISHED_PRESENTATION_PDF"]
        self.assertEqual(
            list(workspace.class_action_buttons),
            [
                "Add Artifact", "Register File", "Refresh Current Census",
                "Refresh Census", "Create Relationship",
            ],
        )
        self.assertTrue(
            set(self.window.global_buttons).isdisjoint(
                workspace.class_action_buttons
            )
        )

    def test_zero_artifact_class_shows_adaptive_empty_state(self):
        workspace = self.window.class_workspaces["PUBLISHED_PRESENTATION_PDF"]
        self.window.open_class("PUBLISHED_PRESENTATION_PDF")
        self.window.show()
        self.application.processEvents()
        self.assertTrue(workspace.empty_state.isVisible())
        self.assertFalse(workspace.content_splitter.isVisible())
        self.assertEqual(
            workspace.empty_title.text(),
            "No published presentation PDFs registered",
        )
        self.assertEqual(
            workspace.empty_guidance.text(),
            "Configure the repository path, scan the folder, review candidates, "
            "and register selected artifacts.",
        )
        self.assertEqual(
            [
                workspace.configure_path_button.text(),
                workspace.empty_scan_button.text(),
                workspace.empty_register_button.text(),
            ],
            ["Configure Path", "Refresh Current Census", "Register File"],
        )

    def test_record_actions_follow_table_selection(self):
        self._configure_required_roots()
        workspace = self.window.class_workspaces["PUBLISHED_PRESENTATION_PDF"]
        self.window.artifact_service.register(ArtifactRegistration(
            "PUBLISHED_PRESENTATION_PDF", "Selected fixture artifact"
        ))
        workspace.reload()
        self.window.open_class("PUBLISHED_PRESENTATION_PDF")
        self.window.show()
        self.application.processEvents()

        workspace.table.clearSelection()
        workspace.table.setCurrentIndex(QModelIndex())
        self.application.processEvents()
        self.assertTrue(all(
            not button.isEnabled()
            for button in workspace.action_buttons.values()
        ))

        workspace.table.selectRow(0)
        self.application.processEvents()
        self.assertTrue(all(
            button.isEnabled()
            for label, button in workspace.action_buttons.items()
            if label not in workspace.NOT_YET_IMPLEMENTED
        ))
        self.assertTrue(all(
            not workspace.action_buttons[label].isEnabled()
            for label in workspace.NOT_YET_IMPLEMENTED
        ))

    def test_internal_class_codes_are_not_primary_workspace_labels(self):
        for code, workspace in self.window.class_workspaces.items():
            self.assertNotEqual(workspace.layer_label.text(), code)
            self.assertNotIn("_", workspace.layer_label.text())
            self.assertTrue(workspace.layer_label.text().endswith("Layer"))

    def test_status_and_workspace_actions_are_reachable_at_minimum_size(self):
        self._configure_required_roots()
        workspace = self.window.class_workspaces["PUBLISHED_PRESENTATION_PDF"]
        self.window.artifact_service.register(ArtifactRegistration(
            "PUBLISHED_PRESENTATION_PDF", "Minimum-size fixture"
        ))
        workspace.reload()
        self.window.open_class("PUBLISHED_PRESENTATION_PDF")
        self.window.show()
        self.window.resize(1100, 700)
        message = (
            "Configuration and provenance status remains visible while the "
            "artifact workspace is displayed at minimum supported width."
        )
        self.window._show_status(message)
        self.application.processEvents()

        self.assertGreaterEqual(self.window.statusBar().height(), 32)
        self.assertTrue(self.window.status_label.isVisible())
        self.assertGreaterEqual(self.window.status_label.height(), 28)
        self.assertEqual(self.window.status_label.toolTip(), message)
        self.assertTrue(self.window.status_label.text())
        self.assertLessEqual(
            self.window.status_label.geometry().right(),
            self.window.statusBar().contentsRect().right(),
        )
        self.assertLessEqual(
            self.window.statusBar().geometry().bottom(),
            self.window.rect().bottom(),
        )
        self.assertEqual(self.window.global_action_columns, 5)
        self.assertEqual(workspace.primary_action_columns, 5)
        self.assertEqual(workspace.record_action_columns, 2)
        for button in (
            list(self.window.global_buttons.values())
            + list(workspace.class_action_buttons.values())
            + list(workspace.action_buttons.values())
        ):
            self.assertFalse(button.isHidden())
            self.assertGreater(button.width(), 0)

    def test_class_count_updates_after_registration_dialog(self):
        dialog = ArtifactRegistrationDialog(
            self.window.artifact_service, self.window.class_repository,
            "FOUNDATIONAL_RESOURCE", self.window,
        )
        dialog.title.setText("Synthetic registered artifact")
        dialog.symbolic_locator.setText("<RESOURCE_REPOSITORY>/synthetic.txt")
        dialog.save()
        self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)
        self.window.refresh_all()
        counts = self.window.artifact_service.class_counts()
        self.assertEqual(counts["FOUNDATIONAL_RESOURCE"]["total"], 1)

    def test_relationship_dialog_creates_record(self):
        first = self.window.artifact_service.register(ArtifactRegistration(
            "FOUNDATIONAL_RESOURCE", "Synthetic source"
        ))
        second = self.window.artifact_service.register(ArtifactRegistration(
            "PRESENTATION_WORKBENCH", "Synthetic workbench"
        ))
        dialog = RelationshipDialog(
            self.window.relationship_service, self.window.artifact_repository,
            first, self.window,
        )
        dialog.target.setCurrentIndex(dialog.target.findData(second))
        dialog.relationship_type.setCurrentIndex(
            dialog.relationship_type.findData("CANDIDATE_INGREDIENT_FOR")
        )
        dialog.save()
        self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)
        self.assertEqual(len(self.window.relationship_repository.list()), 1)

    def test_show_relationships_displays_existing_relationships_without_opening_create_dialog(self):
        source = self.window.artifact_service.register(ArtifactRegistration(
            "FOUNDATIONAL_RESOURCE", "Synthetic source"
        ))
        target = self.window.artifact_service.register(ArtifactRegistration(
            "PRESENTATION_WORKBENCH", "Synthetic workbench"
        ))
        unrelated_a = self.window.artifact_service.register(ArtifactRegistration(
            "PRESENTATION_WORKBENCH", "Unrelated artifact A"
        ))
        unrelated_b = self.window.artifact_service.register(ArtifactRegistration(
            "PRESENTATION_WORKBENCH", "Unrelated artifact B"
        ))
        source_dialog = RelationshipDialog(
            self.window.relationship_service, self.window.artifact_repository,
            source, self.window,
        )
        source_dialog.target.setCurrentIndex(source_dialog.target.findData(target))
        source_dialog.relationship_type.setCurrentIndex(
            source_dialog.relationship_type.findData("CANDIDATE_INGREDIENT_FOR")
        )
        source_dialog.save()
        self.assertEqual(source_dialog.result(), source_dialog.DialogCode.Accepted)

        unrelated_dialog = RelationshipDialog(
            self.window.relationship_service, self.window.artifact_repository,
            unrelated_a, self.window,
        )
        unrelated_dialog.target.setCurrentIndex(unrelated_dialog.target.findData(unrelated_b))
        unrelated_dialog.relationship_type.setCurrentIndex(
            unrelated_dialog.relationship_type.findData("CANDIDATE_INGREDIENT_FOR")
        )
        unrelated_dialog.save()
        self.assertEqual(unrelated_dialog.result(), unrelated_dialog.DialogCode.Accepted)
        self.assertEqual(len(self.window.relationship_repository.list()), 2)

        workspace = self.window.class_workspaces["FOUNDATIONAL_RESOURCE"]
        workspace.reload()
        row = next(
            index for index in range(workspace.model.rowCount())
            if workspace.model.row(index)["artifact_id"]
            == self.window.artifact_repository.get(source)["artifact_id"]
        )
        workspace.table.selectRow(row)

        with patch.object(RelationshipDialog, "exec", side_effect=AssertionError(
            "Show Relationships must not open the create-relationship dialog"
        )):
            workspace.action_buttons["Show Relationships"].click()

        self.assertEqual(self.window.stack.currentWidget(), self.window.relationship_view)
        self.assertEqual(self.window.relationship_view.filter_artifact_pk, source)
        shown_ids = {row["id"] for row in self.window.relationship_view.model.rows}
        self.assertEqual(len(shown_ids), 1)
        full_ids = {row["id"] for row in self.window.relationship_repository.list()}
        self.assertEqual(len(full_ids), 2)
        self.assertTrue(shown_ids.issubset(full_ids))

        self.window.relationship_view.buttons["Show All Relationships"].click()
        self.assertIsNone(self.window.relationship_view.filter_artifact_pk)
        self.assertFalse(self.window.relationship_view.filter_label.isVisible())
        self.assertEqual(len(self.window.relationship_view.model.rows), 2)

    def test_decision_queue_opens_with_fifth_class_decision(self):
        self.window.navigate("DECISIONS")
        self.assertEqual(self.window.stack.currentWidget(), self.window.decision_view)
        self.assertTrue(any(
            row["decision_type"] == "FIFTH_CLASS_DEFINITION"
            for row in self.window.decision_view.model.rows
        ))
        definition = next(
            row for row in self.window.decision_view.model.rows
            if row["decision_type"] == "FIFTH_CLASS_DEFINITION"
        )
        self.assertEqual(definition["state"], "ACCEPTED")

    def test_fifth_class_remains_editable_without_migration(self):
        fifth = self.window.class_repository.get("INSTRUCTOR_DEFINED_CLASS_5")
        self.window.class_repository.update(fifth["code"], {
            **fifth, "label": "Instructor Test Class", "status": "ACTIVE",
        })
        self.window.refresh_all()
        self.assertEqual(
            self.window.class_repository.get(fifth["code"])["label"],
            "Instructor Test Class",
        )

    def test_knowledge_maps_workspace_has_visualisation_specific_actions(self):
        workspace = self.window.class_workspaces["INSTRUCTOR_DEFINED_CLASS_5"]
        self.assertEqual(
            workspace.artifact_class["label"],
            "Knowledge Maps and Visualisations",
        )
        self.assertEqual(
            list(workspace.class_action_buttons),
            [
                "Create Mind Map", "Import Visualization",
                "Scan Visualizations", "Refresh Census",
                "Link Supporting Artifacts",
            ],
        )
        self.assertEqual(
            list(workspace.action_buttons),
            [
                "Open Visualization",
                "Link Supporting Artifacts", "Show Relationships",
                "Mark Reviewed", "Export Neo4j Bundle",
                "Locate Missing File", "Archive",
            ],
        )
        self.assertEqual(
            workspace.empty_title.text(),
            "No knowledge maps or visualisations registered",
        )
        self.assertIn(
            "separate visualisation root", workspace.empty_guidance.text()
        )

    def test_create_mind_map_review_and_neo4j_export_are_functional(self):
        self._configure_required_roots()
        root = self.root / "repositories/knowledge_maps"
        root.mkdir(parents=True)
        self.window.path_resolver.store.update(
            "INSTRUCTOR_DEFINED_CLASS_5",
            path=str(root), access_mode="read_write",
        )
        self.window.refresh_path_gate()
        workspace = self.window.class_workspaces["INSTRUCTOR_DEFINED_CLASS_5"]
        with patch(
            "desktop.views.artifact_workspace.QInputDialog.getText",
            return_value=("Regional Concepts", True),
        ):
            workspace.create_mind_map()
        self.assertTrue((root / "Regional_Concepts.mm").is_file())
        self.assertEqual(len(workspace.model.rows), 1)
        workspace.table.selectRow(0)
        workspace.mark_reviewed()
        self.assertEqual(
            workspace.model.rows[0]["instructor_status"], "REVIEWED"
        )
        with patch(
            "desktop.views.artifact_workspace.QMessageBox.information"
        ) as notice:
            workspace.export_neo4j_bundle()
        notice.assert_called_once()
        exports = root / "neo4j_exports"
        self.assertEqual(len(list(exports.glob("*_nodes.csv"))), 1)
        self.assertEqual(len(list(exports.glob("*_relationships.csv"))), 1)

    def test_first_launch_wizard_has_six_rows_and_native_folder_selection(self):
        wizard = FirstLaunchPathWizard(
            self.window.path_resolver, self.window.class_repository, self.window
        )
        self.assertEqual(len(wizard.rows), 6)
        selected = self.root / "published"
        selected.mkdir()
        with patch(
            "desktop.dialogs.first_launch_wizard.QFileDialog.getExistingDirectory",
            return_value=str(selected),
        ) as dialog:
            wizard.browse("PUBLISHED_PRESENTATION_PDF")
        dialog.assert_called_once()
        self.assertEqual(
            self.window.path_resolver.store.load()["artifact_roots"]
            ["PUBLISHED_PRESENTATION_PDF"]["path"],
            str(selected),
        )
        wizard.close()

    def test_repository_path_screen_displays_six_categories_without_scanning(self):
        self.window.navigate("PATHS")
        self.assertEqual(self.window.repository_paths_view.table.rowCount(), 6)
        with self.window.database.connection() as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM scan_sessions").fetchone()[0],
                0,
            )

    def test_repository_paths_follow_originating_workbench_context(self):
        self._configure_required_roots()
        view = self.window.repository_paths_view

        self.window.open_class("PRESENTATION_WORKBENCH")
        self.window.class_workspaces[
            "PRESENTATION_WORKBENCH"
        ].configure_path_requested.emit("PRESENTATION_WORKBENCH")

        self.assertIs(self.window.stack.currentWidget(), view)
        self.assertEqual(view.selected_code(), "PRESENTATION_WORKBENCH")
        self.assertEqual(view.title.text(), "Presentation Workbench")
        self.assertIn("Presentation Workbench", view.subtitle.text())

        view.reload()
        self.assertEqual(view.selected_code(), "PRESENTATION_WORKBENCH")
        self.assertEqual(view.title.text(), "Presentation Workbench")

        with patch(
            "desktop.views.repository_paths_view.QDesktopServices.openUrl",
            return_value=True,
        ) as opened:
            view.open_folder()
        opened.assert_called_once()
        opened_url = opened.call_args.args[0]
        self.assertEqual(
            Path(opened_url.toLocalFile()),
            self.root / "repositories" / "presentation_workbench",
        )

        view.set_class("FOUNDATIONAL_RESOURCE")
        self.assertEqual(view.title.text(), "Lecture Raw Material")

    def test_scan_candidate_columns_are_user_resizable_and_survive_reload(self):
        header = self.window.scan_view.table.horizontalHeader()
        self.assertEqual(
            [
                self.window.scan_view.model.headerData(
                    column, Qt.Orientation.Horizontal
                )
                for column in range(self.window.scan_view.model.columnCount())
            ],
            [
                "Relative path", "Published PDF match", "Format", "Bytes",
                "Review status", "Candidate record",
            ],
        )
        self.assertNotIn(
            "checksum_sha256",
            [key for key, _label in self.window.scan_view.model.columns],
        )
        self.assertFalse(header.stretchLastSection())
        self.assertTrue(header.sectionsMovable())
        self.assertTrue(header.sectionsClickable())
        self.assertGreaterEqual(header.minimumSectionSize(), 72)
        for column in range(self.window.scan_view.model.columnCount()):
            self.assertEqual(
                header.sectionResizeMode(column),
                QHeaderView.ResizeMode.Interactive,
            )

        original = header.sectionSize(0)
        requested = original + 83
        header.resizeSection(0, requested)
        self.application.processEvents()
        self.assertEqual(header.sectionSize(0), requested)
        self.window.scan_view.reload()
        self.application.processEvents()
        self.assertEqual(header.sectionSize(0), requested)
        self.assertIn("Drag column dividers", header.toolTip())
        self.assertIn(
            "double-click to fit",
            self.window.scan_view.column_resize_hint.text(),
        )

    def test_scan_candidate_heading_follows_selected_artifact_class(self):
        self.window.scan_view.set_class("PUBLISHED_PRESENTATION_PDF")
        self.assertEqual(
            self.window.scan_view.title.text(), "Published Presentation PDFs"
        )
        self.assertNotEqual(
            "Scan Candidates", self.window.scan_view.title.text()
        )
        self.assertIn(
            "Published Presentation PDFs",
            self.window.scan_view.subtitle.text(),
        )

        self.window.scan_view.set_class("FOUNDATIONAL_RESOURCE")
        self.assertEqual(
            self.window.scan_view.title.text(), "Lecture Raw Material"
        )
        self.assertIn(
            "Lecture Raw Material", self.window.scan_view.subtitle.text()
        )

    def test_workbench_latest_odp_census_remains_scrollable_in_configuration_mode(self):
        workbench_root = (
            self.root / "repositories" / "presentation_workbench"
        )
        published_root = (
            self.root / "repositories" / "published_presentation_pdf"
        )
        workbench_root.mkdir(parents=True)
        published_root.mkdir(parents=True)
        self.window.path_resolver.store.update(
            "PRESENTATION_WORKBENCH", path=str(workbench_root)
        )
        self.window.path_resolver.store.update(
            "PUBLISHED_PRESENTATION_PDF", path=str(published_root)
        )
        for number in range(40):
            (workbench_root / f"lecture-{number:02}.odp").write_bytes(
                f"fixture {number}".encode()
            )
            (published_root / f"LECTURE-{number:02}.pdf").write_bytes(
                f"published fixture {number}".encode()
            )
        (workbench_root / "irrelevant.pdf").write_bytes(b"not a workbench format")
        self.window.scan_service.scan("PUBLISHED_PRESENTATION_PDF")
        session_pk = self.window.scan_service.scan("PRESENTATION_WORKBENCH")
        self.window.scan_service.repository.add_candidate({
            "scan_session_id": session_pk,
            "candidate_id": "CAND-LEGACY-PDF",
            "relative_path": "irrelevant.pdf",
            "file_extension": ".pdf",
            "checksum_sha256": "legacy-polluted-session",
            "file_size": 22,
            "candidate_status": "AWAITING_REVIEW",
            "proposed_class_code": "PRESENTATION_WORKBENCH",
        })
        self.window.scan_view.set_class("PRESENTATION_WORKBENCH")
        self.window.navigate("SCAN")
        self.window.show()
        self.window.resize(1100, 700)
        self.application.processEvents()

        self.assertTrue(self.window.path_setup_required)
        self.assertEqual(self.window.scan_view.model.rowCount(), 40)
        self.assertEqual(
            {
                row["file_extension"]
                for row in self.window.scan_view.model.rows
            },
            {".odp"},
        )
        self.assertIn("40 candidates", self.window.scan_view.result_summary.text())
        self.assertIn(".ODP: 40", self.window.scan_view.result_summary.text())
        self.assertIn("PDF matches: 40", self.window.scan_view.result_summary.text())
        self.assertTrue(all(
            row["published_pdf_match_status"] == "MATCHED_CANDIDATE"
            for row in self.window.scan_view.model.rows
        ))
        self.assertFalse(self.window.scan_view.table.isColumnHidden(1))
        self.assertTrue(self.window.scan_view.table.isEnabled())
        scroll_bar = self.window.scan_view.table.verticalScrollBar()
        self.assertEqual(
            self.window.scan_view.table.verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn,
        )
        self.assertGreater(scroll_bar.maximum(), 0)
        self.window.scan_view.table.setFocus()
        QTest.keyClick(
            self.window.scan_view.table,
            Qt.Key.Key_End,
            Qt.KeyboardModifier.ControlModifier,
        )
        self.application.processEvents()
        self.assertEqual(self.window.scan_view.table.currentIndex().row(), 39)
        self.assertGreater(scroll_bar.value(), 0)
        self.assertFalse(self.window.scan_view.scan_button.isEnabled())
        self.assertTrue(all(
            not button.isEnabled()
            for button in self.window.scan_view.action_buttons.values()
        ))

    def test_lecture_raw_material_scan_displays_topic_folders_only(self):
        self._configure_required_roots()
        root = self.root / "repositories" / "foundational_resource"
        region = root / "LEC_RES_1" / "region_concept"
        region.mkdir(parents=True)
        (region / "concept.pdf").write_bytes(b"concept")
        (region / "maps").mkdir()
        (region / "maps" / "region.png").write_bytes(b"map")
        agriculture = root / "LEC_RES_2" / "agriculture"
        agriculture.mkdir(parents=True)
        (agriculture / "policy.docx").write_bytes(b"policy")
        (root / "LEC_RES_2" / "loose.pdf").write_bytes(b"loose")
        self.window.scan_service.scan("FOUNDATIONAL_RESOURCE")
        view = self.window.scan_view
        view.set_class("FOUNDATIONAL_RESOURCE")
        self.window.navigate("SCAN")
        self.application.processEvents()

        self.assertEqual(view.title.text(), "Lecture Raw Material")
        self.assertEqual(
            [
                view.model.headerData(column, Qt.Orientation.Horizontal)
                for column in range(view.model.columnCount())
            ],
            [
                "Topic", "Lecture group", "Folder", "Files",
                "Formats", "Review status",
            ],
        )
        self.assertEqual(view.model.rowCount(), 2)
        self.assertEqual(
            [row["topic_path"] for row in view.model.rows],
            ["LEC_RES_1/region_concept", "LEC_RES_2/agriculture"],
        )
        self.assertEqual(view.model.rows[0]["file_count"], 2)
        self.assertTrue(all(
            "relative_path" not in row for row in view.model.rows
        ))
        self.assertIn("2 topic folders", view.result_summary.text())
        self.assertIn("1 loose root files not shown", view.result_summary.text())
        self.assertTrue(all(
            button.isHidden() for button in view.action_buttons.values()
        ))
        self.assertFalse(view.open_topic_button.isHidden())
        self.assertTrue(view.open_topic_button.isEnabled())

        with patch(
            "desktop.views.scan_candidates_view.QDesktopServices.openUrl",
            return_value=True,
        ) as opened:
            view.open_topic()
        opened.assert_called_once()
        self.assertEqual(
            Path(opened.call_args.args[0].toLocalFile()), region
        )

    def test_ai_artifacts_use_fifteen_lecture_presentation_revision_queue(self):
        self._configure_required_roots()
        ai_root = self.root / "repositories" / "ai_generated_artifact"
        for number in range(1, 16):
            (ai_root / f"LEC_{number}").mkdir()
        (ai_root / "LEC_1/revision-note.tex").write_text(
            "\\section{AI-assisted revision note}", encoding="utf-8"
        )
        (ai_root / "LEC_1/revision-note.pdf").write_bytes(b"PDF reading copy")
        (ai_root / "LEC_1/revision-note.aux").write_text(
            "ignored build state", encoding="utf-8"
        )
        (ai_root / "LEC_1/revision-note.log").write_text(
            "ignored build log", encoding="utf-8"
        )
        workbench = self.root / "repositories" / "presentation_workbench"
        presentation = workbench / "LECTURE1" / "lecture1a.odp"
        presentation.parent.mkdir()
        presentation.write_bytes(b"editable presentation")
        published = self.root / "repositories" / "published_presentation_pdf"
        (published / "lecture1a.pdf").write_bytes(b"published presentation")
        self.window.scan_service.scan("PRESENTATION_WORKBENCH")
        self.window.scan_service.scan("PUBLISHED_PRESENTATION_PDF")
        self.window.scan_service.scan("AI_GENERATED_ARTIFACT")
        view = self.window.scan_view
        view.set_class("AI_GENERATED_ARTIFACT")
        self.window.navigate("SCAN")
        self.application.processEvents()

        self.assertEqual(view.title.text(), "AI-Assisted LaTeX Revision Queue")
        self.assertEqual(view.scan_button.text(), "Refresh LaTeX Notes")
        self.assertEqual(view.model.rowCount(), 15)
        self.assertEqual(
            [
                view.model.headerData(column, Qt.Orientation.Horizontal)
                for column in range(view.model.columnCount())
            ],
            [
                "Lecture", "TeX notes", "PDF notes",
                "Workbench presentations", "Published PDFs", "Revision status",
            ],
        )
        lecture_one = view.model.rows[0]
        self.assertEqual(lecture_one["lecture_label"], "Lecture 1")
        self.assertEqual(lecture_one["ai_note_count"], 2)
        self.assertEqual(lecture_one["tex_display"], "revision-note.tex")
        self.assertEqual(
            lecture_one["pdf_note_display"], "revision-note.pdf"
        )
        self.assertEqual(
            lecture_one["workbench_display"], "lecture1a.odp"
        )
        self.assertEqual(
            lecture_one["published_display"], "lecture1a.pdf"
        )
        self.assertTrue(all(
            button.isHidden() for button in view.action_buttons.values()
        ))
        self.assertTrue(all(
            not button.isHidden() for button in view.revision_buttons.values()
        ))

        with patch(
            "desktop.views.scan_candidates_view.QDesktopServices.openUrl",
            return_value=True,
        ) as opened:
            view.open_latex_notes()
        self.assertEqual(
            Path(opened.call_args.args[0].toLocalFile()), ai_root / "LEC_1"
        )

        view.link_workbench()
        self.assertEqual(
            view.model.rows[0]["selected_workbench"],
            "LECTURE1/lecture1a.odp",
        )
        with patch(
            "desktop.views.scan_candidates_view.QDesktopServices.openUrl",
            return_value=True,
        ) as opened:
            view.begin_revision()
        self.assertEqual(
            Path(opened.call_args.args[0].toLocalFile()), presentation
        )
        self.assertEqual(
            view.model.rows[0]["revision_status"], "Revision in progress"
        )

        view.set_revision_status("INTEGRATED")
        self.assertEqual(
            view.model.rows[0]["revision_status"],
            "Integrated into presentation",
        )
        self.assertTrue(view.model.rows[0]["updated_at"])
        view.table.selectRow(1)
        self.application.processEvents()
        self.assertFalse(view.revision_buttons["Begin Revision"].isEnabled())
        self.assertFalse(view.revision_buttons["Mark Integrated"].isEnabled())
        self.assertIn("15 lectures", view.result_summary.text())

    def test_four_configured_roots_enable_operational_controls(self):
        self._configure_required_roots()
        self.assertFalse(self.window.path_setup_required)
        for workspace in self.window.class_workspaces.values():
            self.assertTrue(workspace.scan_button.isEnabled())
            self.assertTrue(workspace.register_button.isEnabled())
        self.assertEqual(
            self.window.path_resolver.validate_all()
            ["INSTRUCTOR_DEFINED_CLASS_5"].status,
            "MISSING",
        )

    def _configure_required_roots(self):
        for code in (
            "PUBLISHED_PRESENTATION_PDF", "PRESENTATION_WORKBENCH",
            "FOUNDATIONAL_RESOURCE", "AI_GENERATED_ARTIFACT",
        ):
            path = self.root / "repositories" / code.lower()
            path.mkdir(parents=True, exist_ok=True)
            self.window.path_resolver.store.update(code, path=str(path))
        self.window.refresh_path_gate()


class KeyboardAccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project_root = self.root / "application"
        self.project_root.mkdir()
        course_artifacts = CourseArtifactConfig(
            project_root=self.project_root,
            database_path=self.root / "local_state/database/test.sqlite3",
            class_config_path=DEFAULT_CLASS_CONFIG,
            relationship_config_path=DEFAULT_RELATIONSHIP_CONFIG,
            local_paths_path=self.root / "config/local_paths.json",
        )
        store = LocalPathStore(course_artifacts)
        for code in (
            "PUBLISHED_PRESENTATION_PDF", "PRESENTATION_WORKBENCH",
            "FOUNDATIONAL_RESOURCE", "AI_GENERATED_ARTIFACT",
        ):
            path = self.root / "repositories" / code.lower()
            path.mkdir(parents=True)
            store.update(code, path=str(path))
        self.config = DesktopConfig(course_artifacts, STYLE_SHEET, WATERMARK)
        self.window = MainWindow(self.config)
        self.window.show()
        self.application.processEvents()

    def tearDown(self):
        self.window.close()
        self.application.processEvents()
        self.temporary.cleanup()

    def test_keyboard_first_focus_and_complete_forward_reverse_home_chain(self):
        self.assertIs(self.application.focusWidget(), self.window.navigation)
        expected = [
            self.window.navigation,
            *self.window.global_buttons.values(),
            *self.window.home_view.class_cards,
        ]
        observed = []
        self.window.navigation.setFocus()
        for _widget in expected:
            focused = self.application.focusWidget()
            observed.append(focused)
            if focused is not expected[-1]:
                QTest.keyClick(focused, Qt.Key.Key_Tab)
                self.application.processEvents()
        self.assertEqual(observed, expected)

        reverse_expected = [
            *reversed(self.window.home_view.class_cards),
            *reversed(list(self.window.global_buttons.values())),
            self.window.navigation,
        ]
        reverse_observed = []
        self.window.home_view.class_cards[-1].setFocus()
        for _widget in reverse_expected:
            focused = self.application.focusWidget()
            reverse_observed.append(focused)
            if focused is not reverse_expected[-1]:
                QTest.keyClick(
                    focused, Qt.Key.Key_Tab, Qt.KeyboardModifier.ShiftModifier
                )
                self.application.processEvents()
        self.assertEqual(reverse_observed, reverse_expected)

    def test_sidebar_arrows_home_end_and_explicit_activation(self):
        self.window.navigate("HOME")
        self.window.navigation.setFocus()
        QTest.keyClick(self.window.navigation, Qt.Key.Key_Down)
        self.assertEqual(self.window.navigation.currentRow(), 1)
        self.assertEqual(self.window.stack.currentIndex(), 0)
        QTest.keyClick(self.window.navigation, Qt.Key.Key_Return)
        self.assertEqual(self.window.stack.currentIndex(), 1)

        QTest.keyClick(self.window.navigation, Qt.Key.Key_End)
        self.assertEqual(
            self.window.navigation.currentRow(),
            self.window.navigation.count() - 1,
        )
        QTest.keyClick(self.window.navigation, Qt.Key.Key_Space)
        self.assertEqual(
            self.window.stack.currentIndex(), self.window.stack.count() - 1
        )
        QTest.keyClick(self.window.navigation, Qt.Key.Key_Home)
        self.assertEqual(self.window.navigation.currentRow(), 0)

    def test_artifact_card_enter_and_space_activation(self):
        for key in (Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.window.navigate("HOME")
            card = self.window.home_view.class_cards[0]
            card.setFocus()
            self.assertEqual(
                card.accessibleName(), "Published Presentation PDFs"
            )
            self.assertTrue(card.accessibleDescription())
            QTest.keyClick(card, key)
            self.assertEqual(
                self.window.stack_keys[self.window.stack.currentIndex()],
                "CLASS:PUBLISHED_PRESENTATION_PDF",
            )

    def test_empty_state_actions_follow_class_actions_in_tab_order(self):
        workspace = self.window.class_workspaces["PUBLISHED_PRESENTATION_PDF"]
        self.window.open_class("PUBLISHED_PRESENTATION_PDF")
        self.application.processEvents()
        workspace.relate_button.setFocus()
        QTest.keyClick(workspace.relate_button, Qt.Key.Key_Tab)
        self.assertIs(
            self.application.focusWidget(), workspace.configure_path_button
        )
        QTest.keyClick(workspace.configure_path_button, Qt.Key.Key_Tab)
        self.assertIs(self.application.focusWidget(), workspace.empty_scan_button)
        QTest.keyClick(workspace.empty_scan_button, Qt.Key.Key_Tab)
        self.assertIs(
            self.application.focusWidget(), workspace.empty_register_button
        )
        self.assertIn(
            "does not register files automatically",
            workspace.empty_scan_button.accessibleDescription(),
        )

    def test_table_keyboard_selection_enables_actions_and_enter_activates(self):
        workspace = self.window.class_workspaces["PUBLISHED_PRESENTATION_PDF"]
        self.window.artifact_service.register(ArtifactRegistration(
            "PUBLISHED_PRESENTATION_PDF", "Keyboard fixture"
        ))
        workspace.reload()
        self.window.open_class("PUBLISHED_PRESENTATION_PDF")
        workspace.table.clearSelection()
        workspace.table.setCurrentIndex(QModelIndex())
        self.application.processEvents()
        self.assertTrue(all(
            not button.isEnabled()
            for button in workspace.action_buttons.values()
        ))

        workspace.table.setFocus()
        QTest.keyClick(workspace.table, Qt.Key.Key_Down)
        self.application.processEvents()
        self.assertTrue(all(
            button.isEnabled()
            for label, button in workspace.action_buttons.items()
            if label not in workspace.NOT_YET_IMPLEMENTED
        ))
        self.assertTrue(all(
            not workspace.action_buttons[label].isEnabled()
            for label in workspace.NOT_YET_IMPLEMENTED
        ))
        workspace.table.defaultActivated.disconnect()
        activated = QSignalSpy(workspace.table.defaultActivated)
        QTest.keyClick(workspace.table, Qt.Key.Key_Return)
        self.assertEqual(activated.count(), 1)

    def test_disabled_record_action_does_not_activate(self):
        workspace = self.window.class_workspaces["PUBLISHED_PRESENTATION_PDF"]
        archive = workspace.action_buttons["Archive"]
        self.assertFalse(archive.isEnabled())
        activated = QSignalSpy(archive.clicked)
        QTest.keyClick(archive, Qt.Key.Key_Space)
        self.assertEqual(activated.count(), 0)
        self.assertFalse(archive.isDefault())

    def test_enabled_buttons_activate_with_enter_and_space(self):
        for button in (
            self.window.global_buttons["Find Duplicates"],
            self.window.class_workspaces[
                "PUBLISHED_PRESENTATION_PDF"
            ].refresh_button,
        ):
            activated = QSignalSpy(button.clicked)
            button.setFocus()
            QTest.keyClick(button, Qt.Key.Key_Return)
            self.application.processEvents()
            self.assertEqual(activated.count(), 1)
            QTest.keyClick(button, Qt.Key.Key_Space)
            self.application.processEvents()
            self.assertEqual(activated.count(), 2)

    def test_dialog_escape_invalid_enter_and_focus_return(self):
        dialog = ArtifactRegistrationDialog(
            self.window.artifact_service, self.window.class_repository,
            "PUBLISHED_PRESENTATION_PDF", self.window, self.window.path_resolver,
        )
        dialog.show()
        self.application.processEvents()
        self.assertIs(self.application.focusWidget(), dialog.title)
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)

        invalid = ArtifactRegistrationDialog(
            self.window.artifact_service, self.window.class_repository,
            "PUBLISHED_PRESENTATION_PDF", self.window, self.window.path_resolver,
        )
        with patch(
            "desktop.dialogs.artifact_dialog.QMessageBox.warning"
        ) as warning:
            invalid.show()
            self.application.processEvents()
            invalid.title.setFocus()
            QTest.keyClick(invalid.title, Qt.Key.Key_Return)
            self.application.processEvents()
        warning.assert_called_once()
        self.assertTrue(invalid.isVisible())
        self.assertIsNone(invalid.created_artifact_pk)
        invalid.reject()
        self.application.processEvents()

        workspace = self.window.class_workspaces["PUBLISHED_PRESENTATION_PDF"]
        self.window.open_class("PUBLISHED_PRESENTATION_PDF")
        self.window.activateWindow()
        workspace.add_button.setFocus()
        self.application.processEvents()
        self.assertIs(self.application.focusWidget(), workspace.add_button)
        with patch(
            "desktop.views.artifact_workspace.ArtifactRegistrationDialog.exec",
            return_value=0,
        ):
            workspace.register()
        self.application.processEvents()
        self.assertIs(self.application.focusWidget(), workspace.add_button)

    def test_accessible_metadata_decorative_focus_and_focus_styles(self):
        self.assertTrue(self.window.accessibleName())
        self.assertTrue(self.window.navigation.accessibleName())
        self.assertTrue(self.window.global_actions.accessibleName())
        self.assertTrue(self.window.status_label.accessibleName())
        self.assertEqual(
            self.window.status_label.focusPolicy(), Qt.FocusPolicy.NoFocus
        )
        for button in self.window.global_buttons.values():
            self.assertTrue(button.accessibleName())
        for card in self.window.home_view.class_cards:
            self.assertTrue(card.accessibleName())
            self.assertTrue(card.accessibleDescription())
            self.assertEqual(card.focusPolicy(), Qt.FocusPolicy.StrongFocus)

        workspace = self.window.class_workspaces["PUBLISHED_PRESENTATION_PDF"]
        for widget in (
            workspace.class_action_toolbar, workspace.table,
            workspace.provenance, workspace.record_action_bar,
        ):
            self.assertTrue(widget.accessibleName())
        for button in (
            *workspace.class_action_buttons.values(),
            *workspace.action_buttons.values(),
            workspace.configure_path_button,
            workspace.empty_scan_button,
            workspace.empty_register_button,
        ):
            self.assertTrue(button.accessibleName())
        for label in workspace.findChildren(QLabel):
            self.assertEqual(label.focusPolicy(), Qt.FocusPolicy.NoFocus)

        style = STYLE_SHEET.read_text(encoding="utf-8")
        for selector in (
            "QPushButton:focus", "QListWidget:focus",
            "QFrame#artifactClassCard:focus", "QTableView:focus",
            "QLineEdit:focus", "QComboBox:focus", "QCheckBox:focus",
        ):
            self.assertIn(selector, style)


if __name__ == "__main__":
    unittest.main()
