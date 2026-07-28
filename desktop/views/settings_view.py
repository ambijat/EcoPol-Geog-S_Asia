from __future__ import annotations

from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout, QLabel, QPushButton, QTableView, QVBoxLayout, QWidget,
)

from course_artifacts.repositories.class_repository import ArtifactClassRepository
from desktop.dialogs.class_editor_dialog import ArtifactClassEditorDialog
from desktop.models.table_model import DictTableModel


class SettingsView(QWidget):
    changed = Signal()

    def __init__(self, classes: ArtifactClassRepository, parent=None):
        super().__init__(parent)
        self.classes = classes
        root = QVBoxLayout(self)
        title = QLabel("Artifact Class Settings")
        title.setObjectName("viewTitle")
        root.addWidget(title)
        subtitle = QLabel(
            "Class definitions are configuration-driven. Knowledge Maps and "
            "Visualisations stores portable exports; live Obsidian vaults and "
            "Neo4j databases remain outside the managed artifact root."
        )
        subtitle.setObjectName("viewSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)
        self.model = DictTableModel((
            ("display_order", "Order"), ("code", "Code"), ("label", "Label"),
            ("icon", "Icon"), ("status", "Status"), ("active", "Active"),
        ))
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        actions = QHBoxLayout()
        self.edit_button = QPushButton("Edit Selected Artifact Class")
        self.edit_button.clicked.connect(self.edit)
        actions.addWidget(self.edit_button)
        actions.addStretch()
        root.addLayout(actions)
        self.reload()

    def current(self) -> dict | None:
        index = self.table.currentIndex()
        return self.model.row(index.row()) if index.isValid() else None

    def edit(self):
        artifact_class = self.current()
        if artifact_class:
            invoker = QApplication.focusWidget()
            dialog = ArtifactClassEditorDialog(self.classes, artifact_class, self)
            if dialog.exec():
                self.reload()
                self.changed.emit()
            if invoker is not None and invoker.isEnabled():
                QTimer.singleShot(0, invoker.setFocus)

    def reload(self):
        self.model.replace(self.classes.list())
        if self.model.rows:
            self.table.selectRow(0)
