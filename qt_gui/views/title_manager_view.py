from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
)

from gui.title_registry import TitleRegistryError
from qt_gui.dialogs.title_sync_dialog import TitleSyncDialog
from qt_gui.services.title_registry_service import TitleRegistryService


class TitleManagerView(QWidget):
    status_message = Signal(str)

    def __init__(self, service: TitleRegistryService, parent=None):
        super().__init__(parent)
        self.service = service
        self.records = []
        root = QVBoxLayout(self)
        title = QLabel("Lecture Title Management")
        title.setObjectName("viewTitle")
        root.addWidget(title)
        root.addWidget(QLabel(
            "High-fidelity inherited titles are reference records, not routine decisions. "
            "Instructor action is reserved for missing, conflicting, mismatched, or explicitly revised titles."
        ))
        actions = QHBoxLayout()
        self.reload_button = QPushButton("Reload registries")
        self.preview_button = QPushButton("Preview changes")
        self.apply_button = self.preview_button
        self.save_button = QPushButton("Save selected lecture titles")
        self.export_button = QPushButton("Export confirmed titles")
        for button in (self.reload_button, self.preview_button, self.save_button, self.export_button):
            actions.addWidget(button)
        actions.addStretch()
        root.addLayout(actions)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["Lecture", "Weekly title", "Confirmed", "Tuesday Part A", "Confirmed",
             "Friday Part B", "Confirmed", "Evidence", "Status"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 3)
        evidence_title = QLabel("Historical source evidence")
        evidence_title.setObjectName("sectionTitle")
        root.addWidget(evidence_title)
        self.evidence = QTextBrowser()
        self.evidence.setMaximumHeight(180)
        root.addWidget(self.evidence)
        self.reload_button.clicked.connect(self.validate_registries)
        self.preview_button.clicked.connect(self.preview_changes)
        self.save_button.clicked.connect(self.save_selected_row)
        self.export_button.clicked.connect(self.export_confirmed)
        self.table.itemSelectionChanged.connect(self.update_evidence)
        self.refresh()

    @staticmethod
    def _check_item(checked: bool) -> QTableWidgetItem:
        item = QTableWidgetItem()
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        item.setData(Qt.ItemDataRole.UserRole, checked)
        return item

    def refresh(self):
        self.records = self.service.records()
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            pair = record["pair"]
            parts = {part["part"]: part for part in record["parts"]}
            identifier = pair["lecture_id"].replace("IS529N-", "")
            id_item = QTableWidgetItem(identifier)
            id_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 0, id_item)
            weekly = QTableWidgetItem(pair["weekly_title"]); weekly.setData(Qt.ItemDataRole.UserRole, pair["weekly_title"])
            part_a = QTableWidgetItem(parts["A"]["title"]); part_a.setData(Qt.ItemDataRole.UserRole, parts["A"]["title"])
            part_b = QTableWidgetItem(parts["B"]["title"]); part_b.setData(Qt.ItemDataRole.UserRole, parts["B"]["title"])
            self.table.setItem(row, 1, weekly)
            self.table.setItem(row, 2, self._check_item(bool(pair["title_confirmed"])))
            self.table.setItem(row, 3, part_a)
            self.table.setItem(row, 4, self._check_item(bool(parts["A"]["title_confirmed"])))
            self.table.setItem(row, 5, part_b)
            self.table.setItem(row, 6, self._check_item(bool(parts["B"]["title_confirmed"])))
            self.table.setItem(row, 7, QTableWidgetItem(str(len(record["evidence"]))))
            self.table.setItem(row, 8, QTableWidgetItem(pair["title_status"]))
        self.table.resizeColumnsToContents()
        if self.table.rowCount() and self.table.currentRow() < 0:
            self.table.selectRow(0)

    def validate_registries(self):
        try:
            weekly, parts = self.service.validate()
        except TitleRegistryError as exc:
            QMessageBox.warning(self, "Registry validation failed", "\n".join(exc.errors))
            return
        message = f"Validated {len(weekly)} weekly and {len(parts)} part-title records. No database changes made."
        self.status_message.emit(message)
        QMessageBox.information(self, "Registries valid", message)

    def build_preview_dialog(self) -> TitleSyncDialog:
        batch_id, proposals = self.service.preview()
        return TitleSyncDialog(batch_id, proposals, self)

    def preview_changes(self):
        try:
            dialog = self.build_preview_dialog()
        except TitleRegistryError as exc:
            QMessageBox.warning(self, "Registry validation failed", "\n".join(exc.errors))
            return
        if dialog.exec() == dialog.DialogCode.Accepted:
            changed = self.service.apply_selected(dialog.batch_id, dialog.selected_proposal_ids())
            self.refresh()
            self.status_message.emit(f"Applied {changed} selected, non-conflicting title changes.")

    def save_selected_row(self):
        row = self.table.currentRow()
        if row < 0:
            return
        record = self.records[row]
        identifier = self.table.item(row, 0).text()
        values = (
            ("LECTURE_PAIR", identifier, 1, 2, record["pair"]["title_confirmed"]),
            ("LECTURE_PART", identifier + "A", 3, 4, record["parts"][0]["title_confirmed"]),
            ("LECTURE_PART", identifier + "B", 5, 6, record["parts"][1]["title_confirmed"]),
        )
        for target_type, target, title_column, confirm_column, previously_confirmed in values:
            title_item = self.table.item(row, title_column)
            confirmed = self.table.item(row, confirm_column).checkState() == Qt.CheckState.Checked
            original = title_item.data(Qt.ItemDataRole.UserRole)
            if previously_confirmed and (title_item.text() != original or not confirmed):
                answer = QMessageBox.question(
                    self, "Override confirmed title?",
                    f"{target} is instructor-confirmed. Explicitly replace or demote it?",
                )
                if answer != QMessageBox.StandardButton.Yes:
                    continue
            self.service.save_title(target_type, target, title_item.text(), confirmed)
        self.refresh()
        self.status_message.emit(f"Saved controlled title edits for {identifier}.")

    def export_confirmed(self):
        backups = self.service.export_confirmed()
        self.status_message.emit("Confirmed titles exported atomically; ignored local backups created.")
        QMessageBox.information(self, "Titles exported", f"Backups: {backups[0].name}, {backups[1].name}")

    def update_evidence(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.records):
            self.evidence.clear()
            return
        records = self.records[row]["evidence"]
        if not records:
            self.evidence.setPlainText("No historical title evidence registered for this lecture.")
            return
        self.evidence.setPlainText("\n\n".join(
            f"{item['target_identifier']} · {item['extraction_confidence']} · {item['target_classification']}\n"
            f"{item['extracted_title']}\n{item['source_filename']} · SHA-256 {item['source_sha256'][:16]}…"
            for item in records
        ))
