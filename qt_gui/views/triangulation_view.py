from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QListWidget, QMessageBox,
    QPushButton, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QTextBrowser,
    QLineEdit, QVBoxLayout, QWidget,
)

from qt_gui.services.triangulation_service import RECOMMENDED_ACTIONS, TriangulationService


class TriangulationView(QWidget):
    def __init__(self, service: TriangulationService, parent=None):
        super().__init__(parent)
        self.service = service
        self.number = 1
        self.topics: list[dict] = []
        self.current_topic: dict | None = None
        self.current_findings: list[dict] = []
        root = QVBoxLayout(self)
        title = QLabel("Lecture Triangulation")
        title.setObjectName("viewTitle")
        root.addWidget(title)
        subtitle = QLabel(
            "Topic-wise scholarly control · Historical PPT + raw resources + website learning layer · decisions remain advisory"
        )
        subtitle.setObjectName("viewSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        controls = QHBoxLayout()
        self.lecture = QComboBox()
        self.lecture.addItems([f"Lecture {number:02d}" for number in range(1, 16)])
        self.refresh_button = QPushButton("Refresh triangulation")
        controls.addWidget(self.lecture)
        controls.addStretch()
        controls.addWidget(self.refresh_button)
        root.addLayout(controls)

        split = QSplitter()
        self.topic_list = QListWidget()
        self.topic_list.setMinimumWidth(260)
        split.addWidget(self.topic_list)

        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        self.question = QLabel("Select a triangulation topic")
        self.question.setWordWrap(True)
        self.question.setObjectName("sectionTitle")
        workspace_layout.addWidget(self.question)

        evidence_split = QSplitter()
        self.historical = self._evidence_column("Historical PPT")
        self.raw = self._evidence_column("Raw resources")
        self.website = self._evidence_column("Website notes and links")
        for column in (self.historical, self.raw, self.website):
            evidence_split.addWidget(column["widget"])
        evidence_split.setSizes([400, 400, 400])
        workspace_layout.addWidget(evidence_split, 2)

        tabs = QTabWidget()
        findings_widget = QWidget()
        findings_layout = QVBoxLayout(findings_widget)
        self.findings = QTableWidget(0, 5)
        self.findings.setHorizontalHeaderLabels(
            ["Finding", "Evidence gap", "Recommended action", "Status", "Why it matters"]
        )
        self.findings.horizontalHeader().setStretchLastSection(True)
        findings_layout.addWidget(self.findings)
        decision_form = QFormLayout()
        self.recommendation = QComboBox()
        self.recommendation.addItems(sorted(RECOMMENDED_ACTIONS))
        self.instructor_decision = QComboBox()
        self.instructor_decision.addItem("NOT_YET_DECIDED")
        self.instructor_decision.addItems(sorted(RECOMMENDED_ACTIONS))
        self.decision_comment = QLineEdit()
        self.decision_comment.setPlaceholderText("Instructor comment")
        self.confirmed = QCheckBox("Explicit instructor confirmation")
        self.save_decision = QPushButton("Record local decision")
        decision_form.addRow("Advisory recommendation", self.recommendation)
        decision_form.addRow("Instructor decision", self.instructor_decision)
        decision_form.addRow("Comment", self.decision_comment)
        decision_form.addRow("Confirmation", self.confirmed)
        decision_form.addRow("", self.save_decision)
        findings_layout.addLayout(decision_form)
        tabs.addTab(findings_widget, "Findings and decisions")

        queue_widget = QWidget()
        queue_layout = QVBoxLayout(queue_widget)
        queue_layout.addWidget(QLabel(
            "Instructor Decision Queue — resource selection, alignment, verification, and integration only"
        ))
        self.queue = QTableWidget(0, 6)
        self.queue.setHorizontalHeaderLabels(
            ["Topic", "Lecture", "Evidence gap", "Why it matters", "Recommended action", "Navigate"]
        )
        self.queue.horizontalHeader().setStretchLastSection(True)
        queue_layout.addWidget(self.queue)
        tabs.addTab(queue_widget, "Resource-control queue")

        candidates_widget = QWidget()
        candidates_layout = QVBoxLayout(candidates_widget)
        candidates_layout.addWidget(QLabel(
            "Just-in-time registry candidates — preparation does not alter the canonical registry"
        ))
        self.candidates = QTableWidget(0, 5)
        self.candidates.setHorizontalHeaderLabels(
            ["Layer", "Candidate", "Title", "Admission state", "Canonical registration"]
        )
        candidates_layout.addWidget(self.candidates)
        tabs.addTab(candidates_widget, "Registry intake candidates")
        workspace_layout.addWidget(tabs, 1)

        split.addWidget(workspace)
        split.setSizes([280, 1250])
        root.addWidget(split, 1)

        self.lecture.currentIndexChanged.connect(lambda index: self.load_lecture(index + 1))
        self.refresh_button.clicked.connect(lambda: self.load_lecture(self.number))
        self.topic_list.currentRowChanged.connect(self.select_topic)
        self.findings.currentCellChanged.connect(self.select_finding)
        self.save_decision.clicked.connect(self.record_decision)
        self.load_lecture(1)

    @staticmethod
    def _evidence_column(title: str) -> dict:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        body = QTextBrowser()
        layout.addWidget(heading)
        layout.addWidget(body)
        return {"widget": widget, "body": body}

    def load_lecture(self, number: int):
        self.number = number
        self.topics = self.service.list_topics(number)
        self.topic_list.clear()
        for topic in self.topics:
            self.topic_list.addItem(
                f'{topic["part"]} · {topic["topic"]}\n{topic["status"]} · '
                f'{topic["evidence_count"]} evidence · {topic["finding_count"]} findings'
            )
        self._load_queue()
        if self.topics:
            self.topic_list.setCurrentRow(0)
        else:
            self.current_topic = None
            self.question.setText("No triangulation topic exists for this lecture.")
            for column in (self.historical, self.raw, self.website):
                column["body"].clear()

    def _load_queue(self):
        rows = self.service.decision_queue(self.number)
        self.queue.setRowCount(len(rows))
        for row, item in enumerate(rows):
            values = (item["topic"], f'{item["lecture_id"]}-{item["part"]}', item["evidence_gap"],
                      item["why_it_matters"], item["recommended_action"], item["navigation"])
            for column, value in enumerate(values):
                self.queue.setItem(row, column, QTableWidgetItem(str(value)))
        self.queue.resizeColumnsToContents()

    def select_topic(self, row: int):
        if not 0 <= row < len(self.topics):
            return
        detail = self.service.topic_detail(self.topics[row]["id"])
        self.current_topic = detail["topic"]
        self.question.setText(
            f'{self.current_topic["lecture_id"]}-{self.current_topic["part"]} · '
            f'{self.current_topic["topic"]}\n{self.current_topic["central_question"]}'
        )
        grouped = {layer: [] for layer in (
            "HISTORICAL_PPT_LAYER", "RAW_RESOURCE_LAYER", "WEBSITE_LEARNING_LAYER"
        )}
        for evidence in detail["evidence"]:
            grouped[evidence["evidence_layer"]].append(evidence)
        columns = (
            (self.historical, "HISTORICAL_PPT_LAYER"),
            (self.raw, "RAW_RESOURCE_LAYER"),
            (self.website, "WEBSITE_LEARNING_LAYER"),
        )
        for column, layer in columns:
            records = grouped[layer]
            if not records:
                message = "NOT_YET_IDENTIFIED\nNOT_YET_VERIFIED"
                if layer == "WEBSITE_LEARNING_LAYER":
                    message += "\nAuthorised References MA index metadata exists; no topic-specific note is linked."
                column["body"].setPlainText(message)
                continue
            column["body"].setPlainText("\n\n".join(self._format_evidence(record) for record in records))
        self.current_findings = detail["findings"]
        self.findings.setRowCount(len(self.current_findings))
        for finding_row, finding in enumerate(self.current_findings):
            values = (finding["finding_type"], finding["evidence_gap"], finding["recommended_action"],
                      finding["instructor_status"], finding["summary"])
            for column, value in enumerate(values):
                self.findings.setItem(finding_row, column, QTableWidgetItem(str(value)))
        self.findings.resizeColumnsToContents()
        if self.current_findings:
            self.findings.selectRow(0)
            index = self.recommendation.findText(self.current_findings[0]["recommended_action"])
            if index >= 0:
                self.recommendation.setCurrentIndex(index)
        self.candidates.setRowCount(len(detail["candidates"]))
        for candidate_row, candidate in enumerate(detail["candidates"]):
            values = (candidate["evidence_layer"], candidate["source_identifier"], candidate["title"],
                      candidate["admission_status"], "YES" if candidate["canonical_registration_performed"] else "NO")
            for column, value in enumerate(values):
                self.candidates.setItem(candidate_row, column, QTableWidgetItem(str(value)))
        self.candidates.resizeColumnsToContents()

    @staticmethod
    def _format_evidence(evidence: dict) -> str:
        levels = ("NOT_USED", "MARGINALLY_USED", "PARTIALLY_USED", "SUBSTANTIALLY_USED", "STRUCTURALLY_CENTRAL")
        return "\n".join((
            evidence["source_identifier"], evidence["source_title"],
            f'Type: {evidence["source_type"]}',
            f'Treatment: {evidence["treatment_level"]} — {levels[evidence["treatment_level"]]}',
            f'Alignment: {evidence["alignment_level"]}',
            f'Evidentiary value: {evidence["evidentiary_value"]}',
            f'Currency: {evidence["currency_status"]}',
            f'Verification: {evidence["verification_status"]}',
            f'Instructor state: {evidence["instructor_status"]}',
            evidence["notes"],
        ))

    def select_finding(self, row: int, _column: int, _previous_row: int, _previous_column: int):
        if not 0 <= row < len(self.current_findings):
            return
        finding = self.current_findings[row]
        index = self.recommendation.findText(finding["recommended_action"])
        if index >= 0:
            self.recommendation.setCurrentIndex(index)

    def record_decision(self):
        if not self.current_topic:
            return
        row = self.findings.currentRow()
        finding_pk = self.current_findings[row]["id"] if 0 <= row < len(self.current_findings) else None
        try:
            self.service.record_decision(self.current_topic["id"], finding_pk, {
                "recommended_action": self.recommendation.currentText(),
                "instructor_decision": self.instructor_decision.currentText(),
                "instructor_comment": self.decision_comment.text(),
                "confirmed": self.confirmed.isChecked(),
            })
            QMessageBox.information(self, "Decision recorded", "Local triangulation decision recorded.")
        except Exception as exc:
            QMessageBox.warning(self, "Decision blocked", str(exc))
