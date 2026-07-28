from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QLabel, QScrollArea, QSizePolicy, QTableView,
    QVBoxLayout, QWidget,
)

from course_artifacts.repositories.class_repository import ArtifactClassRepository
from course_artifacts.repositories.decision_repository import DecisionRepository
from course_artifacts.repositories.relationship_repository import RelationshipRepository
from course_artifacts.services.artifact_service import ArtifactService
from desktop.models.table_model import DictTableModel
from desktop.widgets.artifact_class_button import ArtifactClassButton


class HomeView(QWidget):
    class_opened = Signal(str)

    def __init__(
        self, artifacts: ArtifactService, classes: ArtifactClassRepository,
        relationships: RelationshipRepository, decisions: DecisionRepository, parent=None,
    ):
        super().__init__(parent)
        self.artifacts = artifacts
        self.classes = classes
        self.relationships = relationships
        self.decisions = decisions
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName("homeScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll_area = scroll
        content = QWidget()
        content.setObjectName("homeCanvas")
        self.scroll_content = content
        root = QVBoxLayout(content)
        root.setContentsMargins(8, 8, 8, 18)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        identity = QFrame()
        identity.setObjectName("identityHero")
        hero = QVBoxLayout(identity)
        eyebrow = QLabel("IS529N · SEMESTER 2026")
        eyebrow.setObjectName("eyebrow")
        self.course_title = QLabel(
            "Economic and Political Geography of South Asia"
        )
        self.course_title.setObjectName("courseIdentityTitle")
        self.course_title.setWordWrap(True)
        self.functional_title = QLabel("Course Artifact Cockpit")
        self.functional_title.setObjectName("functionalTitle")
        self.functional_title.setWordWrap(True)
        self.evidence_subtitle = QLabel(
            "Artifact evidence, provenance and relationship management"
        )
        self.evidence_subtitle.setObjectName("viewSubtitle")
        self.evidence_subtitle.setWordWrap(True)
        boundary = QLabel("LOCAL · OFFLINE · INSTRUCTOR GOVERNED")
        boundary.setObjectName("heroBoundary")
        boundary.setWordWrap(True)
        boundary.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )
        hero.addWidget(eyebrow)
        hero.addWidget(self.course_title)
        hero.addWidget(self.functional_title)
        hero.addWidget(self.evidence_subtitle)
        hero.addWidget(boundary, 0)
        root.addWidget(identity)
        self.class_grid = QGridLayout()
        self.class_grid.setSpacing(14)
        root.addLayout(self.class_grid)
        survey_title = QLabel("Artifact Overview")
        survey_title.setObjectName("sectionTitle")
        root.addWidget(survey_title)
        self.survey = QFrame()
        self.survey.setObjectName("surveyBar")
        self.survey_layout = QGridLayout(self.survey)
        root.addWidget(self.survey)
        self.panels_grid = QGridLayout()
        self.panels_grid.setSpacing(14)
        self.recent_model = DictTableModel((
            ("artifact_id", "Artifact"), ("title", "Recent artifact"),
            ("class_label", "Class"), ("instructor_status", "Status"),
        ))
        recent = self._table_panel("Recent Artifacts", self.recent_model)
        self.relationship_model = DictTableModel((
            ("relationship_id", "Relationship"), ("relationship_type", "Type"),
            ("source_title", "Source"), ("target_title", "Target"), ("status", "Status"),
        ))
        relationship = self._table_panel("Relationship Queue", self.relationship_model)
        self.decision_model = DictTableModel((
            ("decision_id", "Decision"), ("summary", "Instructor decision"),
            ("state", "State"),
        ))
        decision = self._table_panel("Instructor Decision Queue", self.decision_model)
        publication = QFrame()
        publication.setObjectName("panel")
        publication_layout = QVBoxLayout(publication)
        publication_title = QLabel("Publication Chain Status")
        publication_title.setObjectName("sectionTitle")
        publication_layout.addWidget(publication_title)
        publication_layout.addWidget(QLabel(
            "No authoritative publication chain registered.\n"
            "Artifacts must be related and instructor-confirmed before this status changes."
        ))
        publication_layout.addStretch()
        self.panel_widgets = [recent, relationship, decision, publication]
        root.addLayout(self.panels_grid, 1)
        self.class_cards: list[ArtifactClassButton] = []
        self.survey_metrics: list[QLabel] = []
        self.class_column_count = 0
        self.reload()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow()

    def focus_chain(self) -> list[QWidget]:
        return list(self.class_cards)

    def _table_panel(self, title: str, model: DictTableModel) -> QFrame:
        frame = QFrame()
        frame.setObjectName("panel")
        layout = QVBoxLayout(frame)
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        table = QTableView()
        table.setModel(model)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        layout.addWidget(table)
        return frame

    def reload(self):
        while self.class_grid.count():
            item = self.class_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        counts = self.artifacts.class_counts()
        classes = self.classes.list(active_only=True)
        self.class_cards = []
        for index, artifact_class in enumerate(classes):
            card = ArtifactClassButton(artifact_class, counts.get(artifact_class["code"], {}))
            card.opened.connect(self.class_opened)
            self.class_cards.append(card)
        while self.survey_layout.count():
            item = self.survey_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        all_counts = list(counts.values())
        metrics = (
            ("Registered", sum(item["total"] for item in all_counts)),
            ("Uninspected", sum(item["uninspected"] for item in all_counts)),
            ("Unrelated", sum(item["orphaned"] for item in all_counts)),
            ("Needs Decision", len(self.decisions.list(pending_only=True))),
        )
        self.survey_metrics = []
        for label, value in metrics:
            metric = QLabel(f"<b>{value}</b><br>{label}")
            metric.setObjectName("surveyMetric")
            self.survey_metrics.append(metric)
        self._reflow()
        self.recent_model.replace(self.artifacts.recent())
        self.relationship_model.replace(self.relationships.list()[:8])
        self.decision_model.replace(self.decisions.list(pending_only=True)[:8])

    def _reflow(self):
        width = max(self.width(), 1)
        columns = 2 if width >= 940 else 1
        self._clear_layout(self.class_grid)
        for index, card in enumerate(self.class_cards):
            self.class_grid.addWidget(card, index // columns, index % columns)
        for column in range(2):
            self.class_grid.setColumnStretch(column, 1 if column < columns else 0)
        self.class_column_count = columns

        survey_columns = 4 if width >= 900 else 2
        self._clear_layout(self.survey_layout)
        for index, metric in enumerate(self.survey_metrics):
            self.survey_layout.addWidget(
                metric, index // survey_columns, index % survey_columns
            )

        panel_columns = 2 if width >= 900 else 1
        self._clear_layout(self.panels_grid)
        for index, panel in enumerate(self.panel_widgets):
            self.panels_grid.addWidget(
                panel, index // panel_columns, index % panel_columns
            )
        for column in range(2):
            self.panels_grid.setColumnStretch(
                column, 1 if column < panel_columns else 0
            )

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            layout.takeAt(0)
