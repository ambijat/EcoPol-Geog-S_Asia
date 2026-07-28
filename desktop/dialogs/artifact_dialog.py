from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
)

from course_artifacts.domain.models import ArtifactRegistration
from course_artifacts.repositories.class_repository import ArtifactClassRepository
from course_artifacts.services.artifact_service import ArtifactService
from course_artifacts.services.path_resolver import PathResolver


class ArtifactRegistrationDialog(QDialog):
    def __init__(
        self, service: ArtifactService, classes: ArtifactClassRepository,
        default_class_code: str = "", parent=None, resolver: PathResolver | None = None,
    ):
        super().__init__(parent)
        self.service = service
        self.resolver = resolver
        self.setWindowTitle("Register Artifact")
        self.setAccessibleName("Register artifact dialog")
        self.setAccessibleDescription(
            "Register one artifact without modifying its source file"
        )
        self.setMinimumWidth(650)
        root = QVBoxLayout(self)
        heading = QLabel("Register a course artifact")
        heading.setObjectName("dialogTitle")
        root.addWidget(heading)
        note = QLabel(
            "Registration records the filename, format, size, timestamps, and "
            "symbolic location. It does not read or modify file contents."
        )
        note.setObjectName("boundaryNotice")
        note.setAccessibleName("Registration safety notice")
        note.setWordWrap(True)
        root.addWidget(note)
        form = QFormLayout()
        self.artifact_class = QComboBox()
        self.artifact_class.setAccessibleName("Artifact class")
        for item in classes.list(active_only=True):
            self.artifact_class.addItem(item["label"], item["code"])
        if default_class_code:
            index = self.artifact_class.findData(default_class_code)
            self.artifact_class.setCurrentIndex(max(index, 0))
        self.title = QLineEdit()
        self.title.setAccessibleName("Artifact title")
        self.title.setAccessibleDescription("Required title for the artifact")
        self.path = QLineEdit()
        self.path.setAccessibleName("Physical file")
        self.path.setAccessibleDescription(
            "Optional machine-local source file; the file remains unchanged"
        )
        self.browse_button = QPushButton("Choose file…")
        self.browse_button.setAccessibleName("Choose physical file")
        self.browse_button.setAutoDefault(False)
        self.browse_button.clicked.connect(self.choose_file)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path, 1)
        path_row.addWidget(self.browse_button)
        self.symbolic_locator = QLineEdit()
        self.symbolic_locator.setAccessibleName("Symbolic locator")
        self.symbolic_locator.setPlaceholderText("<RESOURCE_REPOSITORY>/relative/path")
        self.source_repository = QComboBox()
        self.source_repository.setAccessibleName("Source repository")
        self.source_repository.addItems([
            "", "RESOURCE_REPOSITORY", "PRESENTATION_WORKBENCH",
            "PUBLISHED_PRESENTATIONS", "AI_ARTIFACT_REPOSITORY",
            "KNOWLEDGE_MAP_REPOSITORY",
        ])
        self.creator = QLineEdit()
        self.creator.setAccessibleName("Creator or origin")
        self.provenance = QTextEdit()
        self.provenance.setAccessibleName("Provenance")
        self.provenance.setMaximumHeight(75)
        self.description = QTextEdit()
        self.description.setAccessibleName("Description")
        self.description.setMaximumHeight(75)
        form.addRow("Artifact class", self.artifact_class)
        form.addRow("Title", self.title)
        form.addRow("Physical file (local)", path_row)
        form.addRow("Symbolic locator", self.symbolic_locator)
        form.addRow("Source repository", self.source_repository)
        form.addRow("Creator or origin", self.creator)
        form.addRow("Provenance", self.provenance)
        form.addRow("Description", self.description)
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
        self.save_button.setAccessibleName("Save artifact")
        self.save_button.setAccessibleDescription(
            "Validate the form and register the artifact"
        )
        self.save_button.setDefault(True)
        self.cancel_button.setAccessibleName("Cancel artifact registration")
        self.cancel_button.setAutoDefault(False)
        root.addWidget(self.buttons)
        self.created_artifact_pk: int | None = None

    def showEvent(self, event):
        super().showEvent(event)
        self.title.setFocus()

    def choose_file(self):
        start = ""
        if self.resolver:
            code = str(self.artifact_class.currentData())
            result = self.resolver.validate_all()[code]
            start = result.path if result.operational else ""
        selected, _ = QFileDialog.getOpenFileName(self, "Register source file", start)
        if selected:
            try:
                locator = (
                    self.resolver.to_symbolic(
                        str(self.artifact_class.currentData()), Path(selected)
                    )
                    if self.resolver else self.symbolic_locator.text()
                )
            except Exception as exc:
                QMessageBox.warning(self, "File outside configured root", str(exc))
                return
            self.path.setText(selected)
            if locator:
                self.symbolic_locator.setText(locator)
            if not self.title.text():
                self.title.setText(Path(selected).stem)

    def save(self):
        try:
            physical = Path(self.path.text()) if self.path.text().strip() else None
            locator = self.symbolic_locator.text()
            if physical and self.resolver:
                locator = self.resolver.to_symbolic(
                    str(self.artifact_class.currentData()), physical
                )
            self.created_artifact_pk = self.service.register(ArtifactRegistration(
                artifact_class_code=str(self.artifact_class.currentData()),
                title=self.title.text(),
                physical_path=physical,
                symbolic_locator=locator,
                description=self.description.toPlainText(),
                provenance=self.provenance.toPlainText(),
                creator_or_origin=self.creator.text(),
                source_repository=self.source_repository.currentText(),
            ))
        except Exception as exc:
            QMessageBox.warning(self, "Registration blocked", str(exc))
            return
        self.accept()
