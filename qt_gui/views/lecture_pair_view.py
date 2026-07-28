from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QScrollArea, QTextEdit, QVBoxLayout, QWidget,
)

from qt_gui.services.lecture_service import LectureService


FIELDS = (
    ("weekly_central_question", "Weekly central question"),
    ("weekly_argument", "Weekly argument"),
    ("relationship_between_parts", "Relationship between parts"),
    ("concepts_introduced_in_a", "Concepts introduced in Part A"),
    ("applications_developed_in_b", "Applications developed in Part B"),
    ("shared_resources", "Shared resources"),
    ("duplication_warnings", "Duplication warnings"),
    ("unresolved_gaps", "Unresolved gaps"),
    ("assessment_alignment", "Assessment alignment"),
)


class LecturePairView(QWidget):
    workspace_requested = Signal(str, int)
    def __init__(self, service: LectureService, parent=None):
        super().__init__(parent)
        self.service = service
        self.number = 1
        outer = QVBoxLayout(self)
        self.heading = QLabel()
        self.heading.setObjectName("viewTitle")
        self.identity = QLabel()
        self.identity.setObjectName("viewSubtitle")
        outer.addWidget(self.heading)
        outer.addWidget(self.identity)
        self.part_layout = QHBoxLayout()
        self.part_a = QGroupBox("Tuesday Part A")
        self.part_b = QGroupBox("Friday Part B")
        self.part_a.setMinimumHeight(145)
        self.part_b.setMinimumHeight(145)
        self.part_a_content = QVBoxLayout(self.part_a)
        self.part_b_content = QVBoxLayout(self.part_b)
        self.part_layout.addWidget(self.part_a)
        self.part_layout.addWidget(self.part_b)
        outer.addLayout(self.part_layout)
        self.metrics = QLabel(); self.metrics.setWordWrap(True); self.metrics.setObjectName("workspaceMetrics")
        outer.addWidget(self.metrics)
        shortcuts = QHBoxLayout()
        for label, target in (("Resources", "Resources"), ("Historical Decks", "Historical Decks"),
                              ("Revised Notes", "Revised Notes"), ("Slide Plan", "Slide Plan"),
                              ("Triangulation", "Lecture Triangulation"),
                              ("Deliverables", "Deliverables"), ("Class Record", "Class Record")):
            button = QPushButton(f"Open {label}")
            button.clicked.connect(lambda checked=False, name=target: self.workspace_requested.emit(name, self.number))
            shortcuts.addWidget(button)
        outer.addLayout(shortcuts)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        form_widget = QWidget(); form_widget.setObjectName("lectureForm"); self.form = QFormLayout(form_widget)
        self.editors = {}
        for field, label in FIELDS:
            editor = QTextEdit(); editor.setMaximumHeight(82)
            self.editors[field] = editor
            self.form.addRow(label, editor)
        scroll.setWidget(form_widget)
        outer.addWidget(scroll)
        save = QPushButton("Save lecture architecture")
        save.clicked.connect(self.save)
        outer.addWidget(save)
        self.load_lecture(1)

    @staticmethod
    def _replace_group_content(layout: QVBoxLayout, part: dict):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        title = QLabel(part["title"]); title.setObjectName("partTitle"); title.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(QLabel(f"{part['scheduled_day']} · {part['scheduled_time']}"))
        layout.addWidget(QLabel(part["identifier"]))
        layout.addWidget(QLabel(f"{part['lifecycle_status']} · {part['fidelity_status']} · {part['approval_status']}"))

    def load_lecture(self, number: int):
        self.number = number
        context = self.service.load_pair(number)
        pair = context["pair"]
        self.heading.setText(f"Lecture {number:02d} · {pair['weekly_title']}")
        self.identity.setText(f"{pair['lecture_id']} · Week {pair['week']} · Tuesday and Friday as one intellectual arc")
        parts = {part["part"]: part for part in context["parts"]}
        self._replace_group_content(self.part_a_content, parts["A"])
        self._replace_group_content(self.part_b_content, parts["B"])
        for field, _ in FIELDS:
            self.editors[field].setPlainText(pair[field])
        resource_counts = {key: sum(r["assignment"] == key for r in context["resources"])
                           for key in ("A", "B", "SHARED")}
        unresolved = sum(r["verification_status"] not in {"VERIFIED", "NOT_APPLICABLE"} for r in context["resources"])
        unresolved += sum(n.get("verification_status", "NOT_YET_VERIFIED") != "VERIFIED" for n in context["notes"])
        unresolved += sum(s["verification_status"] != "VERIFIED" for s in context["slide_plan"])
        total_slides = len(context["slide_plan"]); ready = sum(s["verification_status"] == "VERIFIED" for s in context["slide_plan"])
        self.metrics.setText(
            f"Resources — Part A: {resource_counts['A']} · Part B: {resource_counts['B']} · Shared: {resource_counts['SHARED']}    "
            f"Historical decks: {len(context['decks'])} · inspected slides/pages: {len(context['slides'])}    "
            f"Revised notes: {len(context['notes'])}    Slide plan: {ready}/{total_slides} verified    "
            f"Unresolved verification items: {unresolved}\nDuplication warnings: {pair['duplication_warnings'] or 'None recorded'}"
        )

    def save(self):
        values = {field: editor.toPlainText() for field, editor in self.editors.items()}
        values["instructor_status"] = "NOT_REVIEWED"
        self.service.save_architecture(self.number, values)
        QMessageBox.information(self, "Lecture saved", "Lecture architecture saved to the local database.")
