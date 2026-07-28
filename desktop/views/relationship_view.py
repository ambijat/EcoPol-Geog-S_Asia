from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableView, QVBoxLayout, QWidget,
)

from course_artifacts.repositories.artifact_repository import ArtifactRepository
from course_artifacts.services.path_resolver import PathResolver
from course_artifacts.services.relationship_service import RelationshipService
from desktop.dialogs.relationship_dialog import RelationshipDialog
from desktop.models.table_model import DictTableModel


class RelationshipView(QWidget):
    changed = Signal()

    NOT_YET_IMPLEMENTED = frozenset({
        "Reverse Direction", "Change Relationship Type", "Add Evidence",
        "Add Instructor Note", "Remove Relationship",
    })

    def __init__(
        self, service: RelationshipService, artifacts: ArtifactRepository,
        resolver: PathResolver | None = None, parent=None,
    ):
        super().__init__(parent)
        self.service = service
        self.artifacts = artifacts
        self.resolver = resolver
        self.suggested_source: int | None = None
        self.filter_artifact_pk: int | None = None
        root = QVBoxLayout(self)
        title = QLabel("Artifact Relationships")
        title.setObjectName("viewTitle")
        root.addWidget(title)
        subtitle = QLabel("Relationships are first-class records. Only instructor-confirmed records are academically authoritative.")
        subtitle.setObjectName("viewSubtitle")
        root.addWidget(subtitle)
        self.filter_label = QLabel("")
        self.filter_label.setObjectName("viewSubtitle")
        self.filter_label.setVisible(False)
        root.addWidget(self.filter_label)
        actions = QHBoxLayout()
        self.buttons: dict[str, QPushButton] = {}
        for label in (
            "Create Relationship", "Confirm Relationship", "Reject Suggested Relationship",
            "Reverse Direction", "Change Relationship Type", "Add Evidence",
            "Add Instructor Note", "Remove Relationship", "Open Source Artifact",
            "Open Target Artifact", "Show All Relationships",
        ):
            button = QPushButton(label)
            if label in self.NOT_YET_IMPLEMENTED:
                button.setToolTip(
                    "Not implemented in this release. Reserved for a future update."
                )
            self.buttons[label] = button
            actions.addWidget(button)
        self.buttons["Create Relationship"].clicked.connect(self.create)
        self.buttons["Confirm Relationship"].clicked.connect(self.confirm)
        self.buttons["Reject Suggested Relationship"].clicked.connect(self.reject)
        self.buttons["Open Source Artifact"].clicked.connect(self.open_source)
        self.buttons["Open Target Artifact"].clicked.connect(self.open_target)
        self.buttons["Show All Relationships"].clicked.connect(self.clear_filter)
        root.addLayout(actions)
        self.model = DictTableModel((
            ("relationship_id", "Relationship"), ("source_title", "Source"),
            ("relationship_type", "Type"), ("target_title", "Target"),
            ("directionality", "Direction"), ("status", "Authority status"),
            ("confidence", "Confidence"),
        ))
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        self.operational = False
        self.reload()

    def current(self) -> dict | None:
        index = self.table.currentIndex()
        return self.model.row(index.row()) if index.isValid() else None

    def create(self):
        if len(self.artifacts.list()) < 2:
            QMessageBox.information(
                self, "Two artifacts required",
                "Register at least two artifacts before creating a relationship.",
            )
            return
        invoker = QApplication.focusWidget()
        dialog = RelationshipDialog(
            self.service, self.artifacts, self.suggested_source or None, self
        )
        if dialog.exec():
            self.reload()
            self.changed.emit()
        self.suggested_source = None
        if invoker is not None and invoker.isEnabled():
            QTimer.singleShot(0, invoker.setFocus)

    def confirm(self):
        row = self.current()
        if row:
            self.service.confirm(row["id"])
            self.reload()
            self.changed.emit()

    def reject(self):
        row = self.current()
        if row:
            self.service.reject(row["id"])
            self.reload()
            self.changed.emit()

    def show_for(self, artifact_pk: int | None):
        self.filter_artifact_pk = artifact_pk
        if artifact_pk:
            artifact = self.artifacts.get(artifact_pk)
            self.filter_label.setText(
                f'Showing relationships involving: {artifact["title"]}'
            )
            self.filter_label.setVisible(True)
        else:
            self.filter_label.setVisible(False)
        self.reload()

    def clear_filter(self):
        self.show_for(None)

    def _open_artifact(self, artifact_pk: int):
        try:
            artifact = self.artifacts.get(artifact_pk)
        except KeyError as exc:
            QMessageBox.information(self, "Artifact not found", str(exc))
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

    def open_source(self):
        row = self.current()
        if row:
            self._open_artifact(row["source_artifact_id"])

    def open_target(self):
        row = self.current()
        if row:
            self._open_artifact(row["target_artifact_id"])

    def reload(self):
        self.model.replace(self.service.repository.list(self.filter_artifact_pk))
        if self.model.rows:
            self.table.selectRow(0)

    ALWAYS_AVAILABLE = frozenset({
        "Open Source Artifact", "Open Target Artifact", "Show All Relationships",
    })

    def set_operational(self, operational: bool):
        self.operational = operational
        for label, button in self.buttons.items():
            if label in self.NOT_YET_IMPLEMENTED:
                button.setEnabled(False)
            elif label in self.ALWAYS_AVAILABLE:
                button.setEnabled(True)
            else:
                button.setEnabled(operational)
