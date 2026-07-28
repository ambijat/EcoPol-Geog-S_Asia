from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QFrame


class WatermarkContainer(QFrame):
    def __init__(self, svg_path: Path, parent=None):
        super().__init__(parent)
        self._renderer = QSvgRenderer(str(svg_path))
        self.setObjectName("watermarkContainer")

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._renderer.isValid():
            return
        painter = QPainter(self)
        painter.setOpacity(0.055)
        width = min(self.width() * 0.58, 720)
        height = width * 1.18
        target = QRectF(self.width() - width - 36, (self.height() - height) / 2, width, height)
        self._renderer.render(painter, target)
