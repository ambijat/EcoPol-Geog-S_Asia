from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QSpinBox,
    QMessageBox, QTextEdit, QVBoxLayout,
)

from course_artifacts.repositories.class_repository import ArtifactClassRepository


class ArtifactClassEditorDialog(QDialog):
    def __init__(self, repository: ArtifactClassRepository, artifact_class: dict, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.artifact_class = artifact_class
        self.setWindowTitle("Edit Artifact Class")
        self.setAccessibleName("Edit artifact class dialog")
        self.setMinimumWidth(600)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.label = QLineEdit(artifact_class["label"])
        self.label.setAccessibleName("Artifact class label")
        self.label.setAccessibleDescription("Required user-facing class name")
        self.description = QTextEdit(artifact_class["description"])
        self.description.setAccessibleName("Artifact class description")
        self.description.setMaximumHeight(90)
        self.icon = QLineEdit(artifact_class["icon"])
        self.icon.setAccessibleName("Artifact class icon text")
        self.order = QSpinBox()
        self.order.setAccessibleName("Display order")
        self.order.setRange(1, 99)
        self.order.setValue(artifact_class["display_order"])
        self.active = QCheckBox("Visible in the artifact cockpit")
        self.active.setAccessibleName("Artifact class active")
        self.active.setChecked(artifact_class["active"])
        self.extensions = QLineEdit(", ".join(artifact_class["accepted_extensions"]))
        self.extensions.setAccessibleName("Accepted extensions")
        self.suggestions = QLineEdit(
            ", ".join(artifact_class["default_relationship_suggestions"])
        )
        self.suggestions.setAccessibleName("Relationship suggestions")
        code = QLineEdit(artifact_class["code"])
        code.setAccessibleName("Fixed internal class code")
        code.setReadOnly(True)
        form.addRow("Class code (fixed)", code)
        form.addRow("Label", self.label)
        form.addRow("Description", self.description)
        form.addRow("Icon text", self.icon)
        form.addRow("Display order", self.order)
        form.addRow("Active", self.active)
        form.addRow("Accepted extensions", self.extensions)
        form.addRow("Relationship suggestions", self.suggestions)
        root.addLayout(form)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.save)
        self.buttons.rejected.connect(self.reject)
        self.save_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.cancel_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        self.save_button.setDefault(True)
        self.save_button.setAccessibleName("Save artifact class")
        self.cancel_button.setAccessibleName("Cancel artifact class editing")
        self.cancel_button.setAutoDefault(False)
        root.addWidget(self.buttons)

    def showEvent(self, event):
        super().showEvent(event)
        self.label.setFocus()

    def save(self):
        if not self.label.text().strip():
            QMessageBox.warning(
                self, "Artifact class not saved",
                "A user-facing artifact class label is required.",
            )
            self.label.setFocus()
            return
        self.repository.update(self.artifact_class["code"], {
            "label": self.label.text(),
            "description": self.description.toPlainText(),
            "icon": self.icon.text(),
            "display_order": self.order.value(),
            "active": self.active.isChecked(),
            "accepted_extensions": self._csv(self.extensions.text()),
            "default_relationship_suggestions": self._csv(self.suggestions.text()),
            "status": (
                "DEFINITION_PENDING"
                if self.artifact_class["code"] == "INSTRUCTOR_DEFINED_CLASS_5"
                and self.label.text().strip() == "Fifth Artifact Class"
                else "ACTIVE"
            ),
        })
        self.accept()

    @staticmethod
    def _csv(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]
