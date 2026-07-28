from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout,
)


class ArtifactClassButton(QFrame):
    opened = Signal(str)

    def __init__(self, artifact_class: dict, counts: dict, parent=None):
        super().__init__(parent)
        self.artifact_class = artifact_class
        self.setObjectName("artifactClassCard")
        self.setProperty("classCode", artifact_class["code"])
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(artifact_class["label"])
        self.setAccessibleDescription(
            f'{artifact_class["status"].replace("_", " ")}. '
            f'{counts.get("total", 0)} registered; '
            f'{counts.get("uninspected", 0)} uninspected; '
            f'{counts.get("orphaned", 0)} unrelated; '
            f'{counts.get("awaiting_review", 0)} awaiting review.'
        )
        self.setMinimumWidth(0)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        icon = QLabel(artifact_class["icon"])
        icon.setObjectName("classIcon")
        state = QLabel(artifact_class["status"].replace("_", " "))
        state.setObjectName("statusBadge")
        state.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )
        top.addWidget(icon)
        top.addStretch()
        top.addWidget(state)
        layout.addLayout(top)
        title = QLabel(artifact_class["label"])
        title.setObjectName("classTitle")
        title.setWordWrap(True)
        layout.addWidget(title)
        description = QLabel(artifact_class["description"])
        description.setObjectName("classDescription")
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addStretch()
        metrics = QLabel(
            f'<b>{counts.get("total", 0)}</b> registered   ·   '
            f'{counts.get("uninspected", 0)} uninspected   ·   '
            f'{counts.get("orphaned", 0)} orphaned<br>'
            f'{counts.get("awaiting_classification", 0)} awaiting classification   ·   '
            f'{counts.get("awaiting_review", 0)} awaiting review   ·   '
            f'{counts.get("related", 0)} related   ·   '
            f'{counts.get("missing", 0)} missing'
        )
        metrics.setObjectName("classMetrics")
        metrics.setWordWrap(True)
        layout.addWidget(metrics)
        self.open_button = QPushButton("Open artifact class  →")
        self.open_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.open_button.setAccessibleName(
            f'Open {artifact_class["label"]}'
        )
        self.open_button.setObjectName(f"classButton_{artifact_class['code']}")
        self.open_button.clicked.connect(
            lambda: self.opened.emit(self.artifact_class["code"])
        )
        layout.addWidget(self.open_button)

    def keyPressEvent(self, event):
        if event.key() in (
            Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space,
        ):
            self.opened.emit(self.artifact_class["code"])
            event.accept()
            return
        super().keyPressEvent(event)
