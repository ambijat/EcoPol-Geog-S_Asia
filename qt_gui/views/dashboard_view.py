from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from qt_gui.services.lecture_service import LectureService
from qt_gui.widgets.lecture_card import LectureCard


class DashboardView(QWidget):
    lecture_selected = Signal(int)

    def __init__(self, service: LectureService, parent=None):
        super().__init__(parent)
        self.service = service
        root = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("Semester Dashboard")
        title.setObjectName("viewTitle")
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.reload)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(refresh)
        root.addLayout(header)
        subtitle = QLabel(
            "Supervisor Home · Historical presentations + raw scholarly resources + Wikidot learning layer "
            "→ triangulation → revised notes and slides → student learning package\n"
            "Fixed teaching allocation: Tuesday Part A, 9:00–11:00 · Friday Part B, 9:00–11:00"
        )
        subtitle.setObjectName("viewSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(14)
        for column in range(3):
            self.grid.setColumnStretch(column, 1)
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll)
        self.reload()

    def reload(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        cards = self.service.dashboard_cards()
        for index, data in enumerate(cards):
            card = LectureCard(data)
            card.opened.connect(self.lecture_selected)
            self.grid.addWidget(card, index // 3, index % 3)
        self.grid.setRowStretch((len(cards) + 2) // 3, 1)

    @property
    def lecture_card_count(self) -> int:
        return self.grid.count()
