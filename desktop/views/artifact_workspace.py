from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QModelIndex, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QInputDialog, QPushButton, QSizePolicy, QSplitter, QTableView, QTextBrowser,
    QVBoxLayout, QWidget,
)

from course_artifacts.repositories.artifact_repository import ArtifactRepository
from course_artifacts.repositories.class_repository import ArtifactClassRepository
from course_artifacts.services.artifact_service import ArtifactService
from course_artifacts.services.path_resolver import PathResolver
from course_artifacts.services.visualization_service import VisualizationService
from desktop.dialogs.artifact_dialog import ArtifactRegistrationDialog
from desktop.models.table_model import DictTableModel


class ArtifactTableView(QTableView):
    defaultActivated = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.currentIndex().isValid():
                self.defaultActivated.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ArtifactClassWorkspace(QWidget):
    changed = Signal()
    relationship_requested = Signal(int)
    show_relationships_requested = Signal(int)
    configure_path_requested = Signal(str)
    scan_requested = Signal(str)

    LAYER_LABELS = {
        "PUBLISHED_PRESENTATION_PDF": "Published Artifact Layer",
        "PRESENTATION_WORKBENCH": "Editable Presentation Layer",
        "FOUNDATIONAL_RESOURCE": "Lecture Raw Material Layer",
        "AI_GENERATED_ARTIFACT": "AI-assisted Analysis Layer",
        "INSTRUCTOR_DEFINED_CLASS_5": "Concept Visualisation Layer",
        "SPATIAL_RESOURCE": "Spatial Raw Material Layer",
    }
    EMPTY_STATE_NAMES = {
        "PUBLISHED_PRESENTATION_PDF": "published presentation PDFs",
        "PRESENTATION_WORKBENCH": "presentation workbench artifacts",
        "FOUNDATIONAL_RESOURCE": "lecture raw-material artifacts",
        "AI_GENERATED_ARTIFACT": "AI-assisted LaTeX notes",
        "INSTRUCTOR_DEFINED_CLASS_5": "knowledge maps or visualisations",
        "SPATIAL_RESOURCE": "spatial raw-material artifacts",
    }

    NOT_YET_IMPLEMENTED = frozenset({
        "Preview", "Inspect", "Edit Metadata", "Show Provenance",
        "Send to AI Queue", "Locate Missing File",
    })

    def __init__(
        self, class_code: str, artifacts: ArtifactService,
        classes: ArtifactClassRepository, resolver: PathResolver | None = None, parent=None,
    ):
        super().__init__(parent)
        self.class_code = class_code
        self.is_visualization_workspace = (
            class_code == "INSTRUCTOR_DEFINED_CLASS_5"
        )
        self.artifact_service = artifacts
        self.repository = ArtifactRepository(artifacts.database)
        self.classes = classes
        self.resolver = resolver
        self.visualization_service = (
            VisualizationService(artifacts.database, resolver)
            if self.is_visualization_workspace and resolver else None
        )
        self.artifact_class = classes.get(class_code)
        self.operational = False
        self.setAccessibleName(f'{self.artifact_class["label"]} workspace')
        root = QVBoxLayout(self)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        self.layer_label = QLabel(self.LAYER_LABELS[class_code])
        self.layer_label.setObjectName("eyebrow")
        title = QLabel(self.artifact_class["label"])
        title.setObjectName("viewTitle")
        subtitle = QLabel(self.artifact_class["description"])
        subtitle.setObjectName("viewSubtitle")
        subtitle.setWordWrap(True)
        heading.addWidget(self.layer_label)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        header.addLayout(heading)
        header.addStretch()
        self.count_badge = QLabel("0 artifacts")
        self.count_badge.setObjectName("heroBoundary")
        header.addWidget(self.count_badge)
        root.addLayout(header)
        self.class_action_toolbar = QFrame()
        self.class_action_toolbar.setObjectName("classActionToolbar")
        self.class_action_toolbar.setAccessibleName("Artifact class actions")
        self.class_action_toolbar.setAccessibleDescription(
            f'Actions for {self.artifact_class["label"]}'
        )
        self.class_action_toolbar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.primary_actions_layout = QGridLayout(self.class_action_toolbar)
        self.primary_actions_layout.setHorizontalSpacing(6)
        self.primary_actions_layout.setVerticalSpacing(6)
        self.add_button = QPushButton(
            "Create Mind Map"
            if self.is_visualization_workspace else "Add Artifact"
        )
        self.add_button.clicked.connect(
            self.create_mind_map
            if self.is_visualization_workspace else self.register
        )
        self.register_button = QPushButton(
            "Import Visualization"
            if self.is_visualization_workspace else "Register File"
        )
        self.register_button.clicked.connect(self.register)
        self.scan_button = QPushButton(
            "Scan Visualizations"
            if self.is_visualization_workspace else "Refresh Current Census"
        )
        self.scan_button.clicked.connect(
            lambda: self.scan_requested.emit(self.class_code)
        )
        self.refresh_button = QPushButton("Refresh Census")
        self.refresh_button.clicked.connect(self.reload)
        self.relate_button = QPushButton(
            "Link Supporting Artifacts"
            if self.is_visualization_workspace else "Create Relationship"
        )
        self.relate_button.clicked.connect(self.relate)
        self.class_action_buttons = {
            button.text(): button for button in (
                self.add_button, self.register_button, self.scan_button,
                self.refresh_button, self.relate_button,
            )
        }
        for button in self.class_action_buttons.values():
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            button.setAccessibleName(button.text())
            button.setAccessibleDescription(
                f'{button.text()} for {self.artifact_class["label"]}'
            )
        self.primary_action_columns = 0
        self._reflow_primary_actions()
        root.addWidget(self.class_action_toolbar)

        self.empty_state = QFrame()
        self.empty_state.setObjectName("emptyState")
        self.empty_state.setAccessibleName(
            f'Empty {self.artifact_class["label"]} workspace'
        )
        self.empty_state.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        readable_name = self.EMPTY_STATE_NAMES[class_code]
        self.empty_title = QLabel(f"No {readable_name} registered")
        self.empty_title.setObjectName("emptyStateTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_guidance = QLabel(
            (
                "Configure a separate visualisation root, create or import a "
                "portable map, then link it to supporting course artifacts."
            )
            if self.is_visualization_workspace else
            (
                "Configure the repository path, scan the folder, review candidates, "
                "and register selected artifacts."
            )
        )
        self.empty_guidance.setObjectName("emptyStateGuidance")
        self.empty_guidance.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_guidance.setWordWrap(True)
        empty_buttons = QHBoxLayout()
        self.configure_path_button = QPushButton("Configure Path")
        self.configure_path_button.setProperty("secondary", True)
        self.configure_path_button.clicked.connect(
            lambda: self.configure_path_requested.emit(self.class_code)
        )
        self.empty_scan_button = QPushButton(
            "Scan Visualizations"
            if self.is_visualization_workspace else "Refresh Current Census"
        )
        self.empty_scan_button.clicked.connect(
            lambda: self.scan_requested.emit(self.class_code)
        )
        self.empty_register_button = QPushButton(
            "Import Visualization"
            if self.is_visualization_workspace else "Register File"
        )
        self.empty_register_button.clicked.connect(self.register)
        for button in (
            self.configure_path_button, self.empty_scan_button,
            self.empty_register_button,
        ):
            button.setAccessibleName(button.text())
            empty_buttons.addWidget(button)
        self.configure_path_button.setAccessibleDescription(
            f'Configure the local repository path for {self.artifact_class["label"]}'
        )
        self.empty_scan_button.setAccessibleDescription(
            "Scan the configured folder to create review candidates; "
            "scanning does not register files automatically."
        )
        self.empty_register_button.setAccessibleDescription(
            f'Register a selected file as {self.artifact_class["label"]}'
        )
        empty_layout.addStretch()
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_guidance)
        empty_layout.addLayout(empty_buttons)
        empty_layout.addStretch()
        root.addWidget(self.empty_state, 1)

        self.content_splitter = QSplitter()
        self.model = DictTableModel((
            ("artifact_id", "Artifact ID"), ("title", "Title"), ("file_name", "File"),
            ("symbolic_locator", "Symbolic locator"), ("inspection_status", "Inspection"),
            ("instructor_status", "Instructor status"), ("relationship_count", "Relations"),
        ))
        self.table = ArtifactTableView()
        self.table.setAccessibleName(
            f'{self.artifact_class["label"]} artifact table'
        )
        self.table.setAccessibleDescription(
            "Use arrow keys, Home, End, Page Up, or Page Down to select a row; "
            "press Enter to open the selected artifact."
        )
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.resizeSection(0, 145)
        header.resizeSection(1, 210)
        header.resizeSection(2, 155)
        header.resizeSection(4, 115)
        header.resizeSection(5, 150)
        header.resizeSection(6, 75)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.content_splitter.addWidget(self.table)
        provenance = QFrame()
        provenance.setObjectName("provenancePanel")
        provenance.setAccessibleName("Artifact provenance and details")
        provenance.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.provenance_panel = provenance
        provenance_layout = QVBoxLayout(provenance)
        provenance_title = QLabel("Persistent Provenance")
        provenance_title.setObjectName("sectionTitle")
        provenance_layout.addWidget(provenance_title)
        self.provenance = QTextBrowser()
        self.provenance.setAccessibleName("Selected artifact provenance")
        self.provenance.setAccessibleDescription(
            "Read-only provenance, locator, inspection, and instructor status"
        )
        provenance_layout.addWidget(self.provenance)
        self.content_splitter.addWidget(provenance)
        self.content_splitter.setSizes([900, 390])
        root.addWidget(self.content_splitter, 1)

        self.record_action_bar = QFrame()
        self.record_action_bar.setObjectName("recordActionBar")
        self.record_action_bar.setAccessibleName("Selected artifact actions")
        self.record_action_bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.record_actions_layout = QGridLayout(self.record_action_bar)
        self.record_actions_layout.setContentsMargins(8, 8, 8, 8)
        self.record_actions_layout.setSpacing(8)
        self.action_buttons: dict[str, QPushButton] = {}
        self.action_groups: list[QFrame] = []
        groups = (
            (
                (
                    ("Inspect", ("Open Visualization",)),
                    (
                        "Connections",
                        ("Link Supporting Artifacts", "Show Relationships"),
                    ),
                    ("Workflow", ("Mark Reviewed",)),
                    (
                        "Exchange and maintenance",
                        ("Export Neo4j Bundle", "Locate Missing File", "Archive"),
                    ),
                )
                if self.is_visualization_workspace else
                (
                    ("Inspect", ("Open", "Preview", "Inspect")),
                    (
                        "Metadata and provenance",
                        ("Edit Metadata", "Show Provenance", "Show Relationships"),
                    ),
                    ("Workflow", ("Relate", "Send to AI Queue", "Mark Reviewed")),
                    ("Maintenance", ("Locate Missing File", "Archive")),
                )
            )
        )
        for group_title, labels in groups:
            group = QFrame()
            group.setObjectName("actionGroup")
            group.setAccessibleName(f"{group_title} actions")
            group.setAccessibleDescription(
                f"Record-level {group_title.lower()} controls"
            )
            group.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            group_layout = QGridLayout(group)
            group_layout.setContentsMargins(6, 4, 6, 6)
            heading_label = QLabel(group_title)
            heading_label.setObjectName("actionGroupTitle")
            group_layout.addWidget(heading_label, 0, 0, 1, len(labels))
            for index, label in enumerate(labels):
                button = QPushButton(label)
                button.setProperty("secondary", True)
                button.setProperty("compact", True)
                button.setEnabled(False)
                button.setAccessibleName(label)
                if label in self.NOT_YET_IMPLEMENTED:
                    not_implemented_notice = (
                        "Not implemented in this release. Reserved for a future update."
                    )
                    button.setToolTip(not_implemented_notice)
                    button.setAccessibleDescription(not_implemented_notice)
                else:
                    button.setAccessibleDescription(
                        self._action_description(label)
                    )
                self.action_buttons[label] = button
                group_layout.addWidget(button, 1, index)
            self.action_groups.append(group)
        self.record_action_columns = 0
        self._reflow_record_actions()
        open_label = (
            "Open Visualization" if self.is_visualization_workspace else "Open"
        )
        relate_label = (
            "Link Supporting Artifacts"
            if self.is_visualization_workspace else "Relate"
        )
        self.action_buttons[open_label].clicked.connect(self.open_selected)
        self.action_buttons[relate_label].clicked.connect(self.relate)
        self.action_buttons["Show Relationships"].clicked.connect(
            self.show_relationships
        )
        self.action_buttons["Mark Reviewed"].clicked.connect(self.mark_reviewed)
        if self.is_visualization_workspace:
            self.action_buttons["Export Neo4j Bundle"].clicked.connect(
                self.export_neo4j_bundle
            )
        self.action_buttons["Archive"].clicked.connect(self.archive_selected)
        self.action_buttons["Archive"].setDefault(False)
        self.action_buttons["Archive"].setAutoDefault(False)
        root.addWidget(self.record_action_bar)
        self.table.selectionModel().currentRowChanged.connect(self.select_row)
        self.table.defaultActivated.connect(self.open_selected)
        self.reload()
        self._configure_tab_order()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow_primary_actions()
        self._reflow_record_actions()

    def current(self) -> dict | None:
        index = self.table.currentIndex()
        return self.model.row(index.row()) if index.isValid() else None

    def reload(self):
        rows = self.repository.list(self.class_code)
        self.model.replace(rows)
        noun = "artifact" if len(rows) == 1 else "artifacts"
        self.count_badge.setText(f"{len(rows)} {noun}")
        self.empty_state.setVisible(not rows)
        self.content_splitter.setVisible(bool(rows))
        self.record_action_bar.setVisible(bool(rows))
        self._set_record_actions_enabled(False)
        if rows:
            self.table.selectRow(0)
        else:
            self.table.setCurrentIndex(QModelIndex())
            self.provenance.setPlainText(
                "No artifacts registered in this class.\n\n"
                + (
                    "Create or import a portable visualisation. Live Obsidian "
                    "vaults and Neo4j databases remain external."
                    if self.is_visualization_workspace else
                    "Use Add Artifact or Register File. Source files remain read-only."
                )
            )

    def select_row(self, current, _previous):
        artifact = self.model.row(current.row())
        if not artifact:
            self._set_record_actions_enabled(False)
            return
        self._set_record_actions_enabled(True)
        self.provenance.setPlainText(
            "\n".join((
                f'Artifact: {artifact["artifact_id"]}',
                f'Class: {artifact["class_label"]}',
                f'Title: {artifact["title"]}',
                f'Symbolic locator: {artifact["symbolic_locator"] or "NOT SET"}',
                f'Source repository: {artifact["source_repository"] or "NOT SET"}',
                f'Provenance: {artifact["provenance"] or "AWAITING DESCRIPTION"}',
                f'Inspection: {artifact["inspection_status"]}',
                f'Instructor status: {artifact["instructor_status"]}',
            ))
        )

    def register(self):
        invoker = QApplication.focusWidget()
        dialog = ArtifactRegistrationDialog(
            self.artifact_service, self.classes, self.class_code, self, self.resolver
        )
        if dialog.exec():
            self.reload()
            self.changed.emit()
        if invoker is not None and invoker.isEnabled():
            QTimer.singleShot(
                0,
                lambda control=invoker: control.setFocus(
                    Qt.FocusReason.OtherFocusReason
                ),
            )

    def create_mind_map(self):
        if not self.visualization_service:
            return
        title, accepted = QInputDialog.getText(
            self, "Create Mind Map", "Mind-map title"
        )
        if not accepted:
            return
        try:
            self.visualization_service.create_mind_map(title)
        except Exception as exc:
            QMessageBox.warning(self, "Mind map not created", str(exc))
            return
        self.reload()
        self.changed.emit()

    def relate(self):
        artifact = self.current()
        self.relationship_requested.emit(artifact["id"] if artifact else 0)

    def show_relationships(self):
        artifact = self.current()
        self.show_relationships_requested.emit(artifact["id"] if artifact else 0)

    def open_selected(self):
        artifact = self.current()
        if not artifact:
            return
        try:
            path = (
                self.resolver.resolve(artifact["symbolic_locator"])
                if self.resolver and artifact["symbolic_locator"]
                else Path(artifact["physical_path"])
            )
        except Exception as exc:
            QMessageBox.information(self, "Local file unavailable", str(exc))
            return
        if not path.is_file():
            QMessageBox.information(self, "No local file", "This artifact has no available local physical file.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def archive_selected(self):
        artifact = self.current()
        if artifact:
            self.repository.archive(artifact["id"])
            self.reload()
            self.changed.emit()

    def mark_reviewed(self):
        artifact = self.current()
        if artifact:
            self.repository.mark_reviewed(artifact["id"])
            self.reload()
            self.changed.emit()

    def export_neo4j_bundle(self):
        artifact = self.current()
        if not artifact or not self.visualization_service:
            return
        try:
            nodes, relationships = (
                self.visualization_service.export_neo4j_bundle(artifact["id"])
            )
        except Exception as exc:
            QMessageBox.warning(self, "Neo4j export blocked", str(exc))
            return
        QMessageBox.information(
            self, "Neo4j export created",
            "Portable CSV import files were created in the visualisation root:\n"
            f"{nodes.name}\n{relationships.name}\n\n"
            "The live Neo4j database was not accessed.",
        )

    def set_operational(self, operational: bool):
        self.operational = operational
        for button in (
            self.add_button, self.register_button, self.scan_button,
            self.relate_button, self.empty_scan_button, self.empty_register_button,
        ):
            button.setEnabled(operational)
        self._set_record_actions_enabled(self.current() is not None)

    def _set_record_actions_enabled(self, has_selection: bool):
        for label, button in self.action_buttons.items():
            if label in self.NOT_YET_IMPLEMENTED:
                button.setEnabled(False)
                continue
            requires_operational = label in {
                "Relate", "Link Supporting Artifacts", "Export Neo4j Bundle",
            }
            button.setEnabled(
                has_selection and (self.operational or not requires_operational)
            )

    def _reflow_primary_actions(self):
        columns = 5 if self.width() >= 780 else 3
        if columns == self.primary_action_columns:
            return
        while self.primary_actions_layout.count():
            self.primary_actions_layout.takeAt(0)
        for index, button in enumerate(self.class_action_buttons.values()):
            self.primary_actions_layout.addWidget(
                button, index // columns, index % columns
            )
        self.primary_action_columns = columns
        self.primary_actions_layout.invalidate()
        self.updateGeometry()

    def _reflow_record_actions(self):
        columns = 4 if self.width() >= 980 else 2
        if columns == self.record_action_columns:
            return
        while self.record_actions_layout.count():
            self.record_actions_layout.takeAt(0)
        for index, group in enumerate(self.action_groups):
            self.record_actions_layout.addWidget(
                group, index // columns, index % columns
            )
        self.record_action_columns = columns
        self.record_actions_layout.invalidate()
        self.record_action_bar.updateGeometry()
        self.updateGeometry()

    def focus_chain(self) -> list[QWidget]:
        return [
            *self.class_action_buttons.values(),
            self.configure_path_button,
            self.empty_scan_button,
            self.empty_register_button,
            self.table,
            self.provenance,
            *self.action_buttons.values(),
        ]

    def _configure_tab_order(self):
        chain = self.focus_chain()
        for first, second in zip(chain, chain[1:]):
            QWidget.setTabOrder(first, second)

    @staticmethod
    def _action_description(label: str) -> str:
        descriptions = {
            "Open": "Open the selected artifact using its authorised local application",
            "Preview": "Preview the selected artifact without changing it",
            "Inspect": "Inspect the selected artifact",
            "Edit Metadata": "Edit descriptive metadata for the selected artifact",
            "Show Provenance": "Show provenance for the selected artifact",
            "Show Relationships": "Show relationships involving the selected artifact",
            "Relate": "Create a relationship involving the selected artifact",
            "Send to AI Queue": (
                "Queue the selected artifact for a separately governed AI workflow"
            ),
            "Mark Reviewed": "Mark the selected artifact as reviewed",
            "Locate Missing File": "Locate a missing local file without rewriting the artifact record",
            "Archive": (
                "Archive the selected artifact record; this removes it from normal views"
            ),
            "Open Visualization": (
                "Open the selected portable visualisation in its associated local application"
            ),
            "Link Supporting Artifacts": (
                "Relate the selected visualisation to its supporting course artifacts"
            ),
            "Export Neo4j Bundle": (
                "Create portable Neo4j node and relationship CSV files without accessing a live database"
            ),
        }
        return descriptions[label]
