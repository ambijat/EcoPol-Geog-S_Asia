from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt


class DictTableModel(QAbstractTableModel):
    """Small read-only model for service dictionaries; edits use validated detail forms."""

    def __init__(self, columns: tuple[tuple[str, str], ...], rows=None, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.rows: list[dict[str, Any]] = list(rows or [])

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return None
        value = self.rows[index.row()].get(self.columns[index.column()][0], "")
        if isinstance(value, bool):
            return "Yes" if value else "No"
        return str(value if value is not None else "")

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.columns[section][1]
        return str(section + 1)

    def replace(self, rows) -> None:
        self.beginResetModel()
        self.rows = list(rows)
        self.endResetModel()

    def row(self, index: int) -> dict[str, Any] | None:
        return self.rows[index] if 0 <= index < len(self.rows) else None


class MultiFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, search_column: int, parent=None):
        super().__init__(parent); self.search_column=search_column; self.search_text=""; self.exact:dict[int,str]={}

    def set_search(self, text: str): self.search_text=text.casefold(); self.invalidateFilter()
    def set_exact(self, column: int, value: str):
        if value == "ALL": self.exact.pop(column,None)
        else: self.exact[column]=value
        self.invalidateFilter()

    def filterAcceptsRow(self, row: int, parent: QModelIndex) -> bool:
        model=self.sourceModel()
        search=str(model.data(model.index(row,self.search_column,parent)) or "").casefold()
        if self.search_text not in search:return False
        return all(str(model.data(model.index(row,col,parent)) or "")==value for col,value in self.exact.items())
