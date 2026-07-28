from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


class DictTableModel(QAbstractTableModel):
    def __init__(self, columns: tuple[tuple[str, str], ...], rows=None, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.rows: list[dict[str, Any]] = list(rows or [])

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        key = self.columns[index.column()][0]
        if role == Qt.ItemDataRole.ToolTipRole:
            value = self.rows[index.row()].get(
                f"{key}_tooltip",
                self.rows[index.row()].get(key, ""),
            )
            return str(value)
        if role == Qt.ItemDataRole.DisplayRole:
            value = self.rows[index.row()].get(key, "")
            return str(value)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.columns[section][1]
        return super().headerData(section, orientation, role)

    def replace(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self.rows = list(rows)
        self.endResetModel()

    def reconfigure(
        self, columns: tuple[tuple[str, str], ...], rows: list[dict]
    ) -> None:
        self.beginResetModel()
        self.columns = columns
        self.rows = list(rows)
        self.endResetModel()

    def row(self, index: int) -> dict | None:
        return self.rows[index] if 0 <= index < len(self.rows) else None
