from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderView(QWidget):
    def __init__(self, title: str, phase_note: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        heading = QLabel(title); heading.setObjectName("viewTitle")
        note = QLabel(phase_note); note.setObjectName("placeholderNote"); note.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(note)
        layout.addStretch()
