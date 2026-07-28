from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from qt_gui.services.git_readiness_service import GitReadinessService


class GovernanceView(QWidget):
    def __init__(self, service: GitReadinessService, parent=None):
        super().__init__(parent)
        self.service = service
        root = QVBoxLayout(self)
        title = QLabel("Governance and Git Readiness")
        title.setObjectName("viewTitle")
        root.addWidget(title)
        root.addWidget(QLabel("Read-only inspection. No stage, commit, push, release, or canonical-ledger controls exist."))
        self.form_widget = QWidget()
        self.form = QFormLayout(self.form_widget)
        self.values = {}
        for key, label in (
            ("branch", "Current branch"), ("latest_commit", "Last commit"),
            ("ledger_block_count", "Canonical ledger blocks"), ("ledger_chain_tip", "Canonical chain tip"),
            ("registry_record_count", "Registry records"),
            ("historical_preservation_status", "Historical sources"),
            ("latest_deliverable_version", "Latest deliverable version"),
            ("latest_deliverable_state", "Draft/approved state"),
            ("latest_validation_status", "Validation status"),
            ("latest_deliverable_classification", "Deliverable public/private class"),
            ("canonical_ledger_status", "Canonical ledger state"),
            ("draft_event_count", "Isolated draft-event count"),
        ):
            value = QLabel(); value.setTextInteractionFlags(value.textInteractionFlags() | value.textInteractionFlags().TextSelectableByMouse)
            self.values[key] = value
            self.form.addRow(label, value)
        root.addWidget(self.form_widget)
        self.files = QTableWidget(0, 2)
        self.files.setHorizontalHeaderLabels(["Proposed lecture file", "Public/private classification"])
        self.files.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.files)
        refresh = QPushButton("Refresh read-only status")
        refresh.clicked.connect(self.reload)
        root.addWidget(refresh)
        self.reload()

    def reload(self):
        report = self.service.governance_status(1)
        for key, label in self.values.items():
            label.setText(str(report[key]))
        selected = report["selected_lecture_files"]
        self.files.setRowCount(len(selected))
        for row, item in enumerate(selected):
            self.files.setItem(row, 0, QTableWidgetItem(item["path"]))
            self.files.setItem(row, 1, QTableWidgetItem(item["classification"]))
        self.files.resizeColumnsToContents()
