from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout


class TitleSyncDialog(QDialog):
    def __init__(self, batch_id: int, proposals: list[dict], parent=None):
        super().__init__(parent)
        self.batch_id = batch_id
        self.setWindowTitle("Preview lecture-title changes")
        self.resize(1000, 560)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select non-conflicting changes to apply. Instructor-confirmed conflicts remain protected."))
        self.table = QTableWidget(len(proposals), 5)
        self.table.setHorizontalHeaderLabels(["Apply", "Target", "Current", "Proposed", "Result"])
        for row, proposal in enumerate(proposals):
            apply_item = QTableWidgetItem()
            apply_item.setData(Qt.ItemDataRole.UserRole, proposal["id"])
            apply_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            apply_item.setCheckState(
                Qt.CheckState.Unchecked if proposal["conflict"] or proposal["reason"] == "UNCHANGED" else Qt.CheckState.Checked
            )
            self.table.setItem(row, 0, apply_item)
            for column, key in enumerate(("target_identifier", "current_title", "proposed_title", "reason"), start=1):
                self.table.setItem(row, column, QTableWidgetItem(str(proposal[key])))
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Apply).setText("Apply selected changes")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_proposal_ids(self) -> set[int]:
        selected = set()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item.checkState() == Qt.CheckState.Checked:
                selected.add(int(item.data(Qt.ItemDataRole.UserRole)))
        return selected
