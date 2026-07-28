from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem


class LinkList(QListWidget):
    def set_options(self, rows: list[dict], id_key: str, label_key: str, selected: set[int] | None = None):
        selected = selected or set()
        self.clear()
        for row in rows:
            item = QListWidgetItem(f'{row.get(id_key, "")} · {row.get(label_key, "")}')
            item.setData(Qt.ItemDataRole.UserRole, int(row["id"]))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if int(row["id"]) in selected else Qt.CheckState.Unchecked)
            self.addItem(item)

    def checked_ids(self) -> list[int]:
        return [int(self.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.count())
                if self.item(i).checkState() == Qt.CheckState.Checked]
