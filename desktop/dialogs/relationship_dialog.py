from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QMessageBox,
    QTextEdit, QVBoxLayout,
)

from course_artifacts.domain.models import RelationshipRegistration
from course_artifacts.repositories.artifact_repository import ArtifactRepository
from course_artifacts.services.relationship_service import RelationshipService


class RelationshipDialog(QDialog):
    def __init__(
        self, service: RelationshipService, artifacts: ArtifactRepository,
        source_artifact_pk: int | None = None, parent=None,
    ):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Create Artifact Relationship")
        self.setAccessibleName("Create artifact relationship dialog")
        self.setAccessibleDescription(
            "Create a proposed relationship between two registered artifacts"
        )
        self.setMinimumWidth(650)
        root = QVBoxLayout(self)
        title = QLabel("Create relationship")
        title.setObjectName("dialogTitle")
        root.addWidget(title)
        authority = QLabel("Suggested and imported relationships remain non-authoritative until the instructor confirms them.")
        authority.setObjectName("boundaryNotice")
        authority.setWordWrap(True)
        root.addWidget(authority)
        form = QFormLayout()
        self.source = QComboBox()
        self.source.setAccessibleName("Source artifact")
        self.target = QComboBox()
        self.target.setAccessibleName("Target artifact")
        for artifact in artifacts.list():
            label = f'{artifact["artifact_id"]} · {artifact["title"]}'
            self.source.addItem(label, artifact["id"])
            self.target.addItem(label, artifact["id"])
        if source_artifact_pk is not None:
            self.source.setCurrentIndex(max(self.source.findData(source_artifact_pk), 0))
        if self.target.count() > 1 and self.target.currentData() == self.source.currentData():
            self.target.setCurrentIndex(1)
        self.relationship_type = QComboBox()
        self.relationship_type.setAccessibleName("Relationship type")
        for item in service.repository.types():
            self.relationship_type.addItem(item["label"], item["code"])
        self.directionality = QComboBox()
        self.directionality.setAccessibleName("Directionality")
        self.directionality.addItems(["DIRECTED", "UNDIRECTED"])
        self.status = QComboBox()
        self.status.setAccessibleName("Initial authority status")
        self.status.addItems([
            "SYSTEM_SUGGESTED", "IMPORTED", "AI_PROPOSED", "INSTRUCTOR_CONFIRMED",
        ])
        self.confidence = QComboBox()
        self.confidence.setAccessibleName("Confidence")
        self.confidence.addItems(["UNASSESSED", "LOW", "MEDIUM", "HIGH"])
        self.evidence = QTextEdit()
        self.evidence.setAccessibleName("Relationship evidence")
        self.evidence.setMaximumHeight(80)
        self.note = QTextEdit()
        self.note.setAccessibleName("Instructor note")
        self.note.setMaximumHeight(80)
        form.addRow("Source artifact", self.source)
        form.addRow("Relationship type", self.relationship_type)
        form.addRow("Target artifact", self.target)
        form.addRow("Directionality", self.directionality)
        form.addRow("Initial status", self.status)
        form.addRow("Confidence", self.confidence)
        form.addRow("Evidence", self.evidence)
        form.addRow("Instructor note", self.note)
        root.addLayout(form)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.save)
        self.buttons.rejected.connect(self.reject)
        self.save_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.cancel_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button.setDefault(True)
        self.save_button.setAccessibleName("Save relationship")
        self.save_button.setAccessibleDescription(
            "Validate and create the proposed relationship"
        )
        self.cancel_button.setAccessibleName("Cancel relationship creation")
        self.cancel_button.setAutoDefault(False)
        root.addWidget(self.buttons)
        self.created_relationship_pk: int | None = None

    def showEvent(self, event):
        super().showEvent(event)
        self.source.setFocus()

    def save(self):
        try:
            self.created_relationship_pk = self.service.create(RelationshipRegistration(
                source_artifact_id=int(self.source.currentData()),
                target_artifact_id=int(self.target.currentData()),
                relationship_type_code=str(self.relationship_type.currentData()),
                directionality=self.directionality.currentText(),
                status=self.status.currentText(),
                confidence=self.confidence.currentText(),
                evidence=self.evidence.toPlainText(),
                instructor_note=self.note.toPlainText(),
            ))
        except Exception as exc:
            QMessageBox.warning(self, "Relationship blocked", str(exc))
            return
        self.accept()
