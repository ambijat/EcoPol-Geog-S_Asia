from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QTableView, QTextEdit, QVBoxLayout, QWidget,
)

from course_artifacts.repositories.decision_repository import DecisionRepository
from desktop.models.table_model import DictTableModel


class DecisionQueueView(QWidget):
    def __init__(self, repository: DecisionRepository, parent=None):
        super().__init__(parent)
        self.repository = repository
        root = QVBoxLayout(self)
        title = QLabel("Instructor Decision Queue")
        title.setObjectName("viewTitle")
        root.addWidget(title)
        subtitle = QLabel("Nothing inferred becomes authoritative silently. Resolve, defer, or request evidence explicitly.")
        subtitle.setObjectName("viewSubtitle")
        root.addWidget(subtitle)
        self.model = DictTableModel((
            ("decision_id", "Decision"), ("decision_type", "Type"),
            ("summary", "Summary"), ("subject_id", "Subject"), ("state", "State"),
        ))
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        self.note = QTextEdit()
        self.note.setPlaceholderText("Instructor resolution note or evidence requirement")
        self.note.setMaximumHeight(85)
        root.addWidget(self.note)
        actions = QHBoxLayout()
        for label, state in (
            ("Accept", "ACCEPTED"), ("Reject", "REJECTED"), ("Defer", "DEFERRED"),
            ("Needs More Evidence", "NEEDS_MORE_EVIDENCE"),
            ("Edit and Accept", "EDITED_AND_ACCEPTED"),
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, target=state: self.resolve(target))
            actions.addWidget(button)
        actions.addStretch()
        root.addLayout(actions)
        self.reload()

    def current(self) -> dict | None:
        index = self.table.currentIndex()
        return self.model.row(index.row()) if index.isValid() else None

    def resolve(self, state: str):
        row = self.current()
        if row and row["state"] == "PENDING":
            self.repository.resolve(row["id"], state, self.note.toPlainText())
            self.note.clear()
            self.reload()

    def reload(self):
        self.model.replace(self.repository.list())
        if self.model.rows:
            self.table.selectRow(0)
