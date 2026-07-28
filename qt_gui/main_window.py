from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QStackedWidget, QVBoxLayout, QWidget,
)

from qt_gui.config import COURSE_SCHEDULE, COURSE_SUBTITLE, COURSE_TITLE, WATERMARK_DISCLAIMER, AppConfig
from qt_gui.database.connection import DatabaseManager
from qt_gui.database.repositories.lecture_repository import LectureRepository
from qt_gui.database.repositories.title_repository import TitleRepository
from qt_gui.services.git_readiness_service import GitReadinessService
from qt_gui.services.class_record_service import ClassRecordService
from qt_gui.services.deliverable_service import DeliverableService
from qt_gui.services.historical_deck_service import HistoricalDeckService
from qt_gui.services.lecture_service import LectureService
from qt_gui.services.ledger_draft_service import LedgerDraftService
from qt_gui.services.note_service import NoteService
from qt_gui.services.resource_service import ResourceService
from qt_gui.services.slide_plan_service import SlidePlanService
from qt_gui.services.title_registry_service import TitleRegistryService
from qt_gui.services.triangulation_service import TriangulationService
from qt_gui.views.dashboard_view import DashboardView
from qt_gui.views.class_record_view import ClassRecordView
from qt_gui.views.deliverables_view import DeliverablesView
from qt_gui.views.governance_view import GovernanceView
from qt_gui.views.historical_deck_view import HistoricalDeckView
from qt_gui.views.lecture_pair_view import LecturePairView
from qt_gui.views.placeholder_view import PlaceholderView
from qt_gui.views.resource_cluster_view import ResourceClusterView
from qt_gui.views.revised_notes_view import RevisedNotesView
from qt_gui.views.slide_plan_view import SlidePlanView
from qt_gui.views.title_manager_view import TitleManagerView
from qt_gui.views.triangulation_view import TriangulationView
from qt_gui.widgets.watermark_container import WatermarkContainer


NAVIGATION = (
    "Semester Dashboard", "Lecture Titles", "Lecture Pair Workspace", "Resources",
    "Historical Decks", "Revised Notes", "Slide Plan", "Lecture Triangulation", "Deliverables",
    "Class Record", "Governance and Git Readiness", "Settings",
)


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config.resolved()
        self.setWindowTitle(f"{COURSE_TITLE} · {COURSE_SUBTITLE}")
        self.resize(1500, 960)
        database = DatabaseManager(self.config.database_path, self.config.project_root)
        database.initialise()
        lecture_service = LectureService(LectureRepository(database))
        title_service = TitleRegistryService(TitleRepository(database))
        governance_service = GitReadinessService(database)
        resource_service = ResourceService(database)
        historical_service = HistoricalDeckService(
            database, self.config.historical_repository_path, self.config.derivative_root
        )
        note_service = NoteService(database)
        slide_service = SlidePlanService(database)
        triangulation_service = TriangulationService(database)
        deliverable_service = DeliverableService(database)
        class_record_service = ClassRecordService(database)
        ledger_draft_service = LedgerDraftService(database)

        central = WatermarkContainer(self.config.watermark_path)
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        navigation_frame = QFrame(); navigation_frame.setObjectName("navigationRail")
        navigation_layout = QVBoxLayout(navigation_frame)
        brand = QLabel("IS529N\nCourse Production Cockpit")
        brand.setObjectName("navigationBrand")
        brand.setWordWrap(True)
        navigation_layout.addWidget(brand)
        self.navigation = QListWidget()
        self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for name in NAVIGATION:
            self.navigation.addItem(QListWidgetItem(name))
        navigation_layout.addWidget(self.navigation)
        boundary = QLabel("LOCAL · OFFLINE\nNo AI · No Git writes\nNo ledger appends")
        boundary.setObjectName("boundaryLabel")
        navigation_layout.addWidget(boundary)
        central_layout.addWidget(navigation_frame)

        workspace = QWidget(); workspace_layout = QVBoxLayout(workspace)
        header = QFrame(); header.setObjectName("courseHeader")
        header_layout = QVBoxLayout(header)
        course = QLabel(COURSE_TITLE); course.setObjectName("courseTitle")
        header_layout.addWidget(course)
        header_layout.addWidget(QLabel(f"{COURSE_SUBTITLE}  ·  {COURSE_SCHEDULE}"))
        workspace_layout.addWidget(header)
        self.stack = QStackedWidget()
        self.dashboard_view = DashboardView(lecture_service)
        self.title_manager_view = TitleManagerView(title_service)
        self.lecture_pair_view = LecturePairView(lecture_service)
        self.resource_view = ResourceClusterView(resource_service)
        self.historical_deck_view = HistoricalDeckView(historical_service)
        self.revised_notes_view = RevisedNotesView(note_service)
        self.slide_plan_view = SlidePlanView(slide_service)
        self.triangulation_view = TriangulationView(triangulation_service)
        self.deliverables_view = DeliverablesView(deliverable_service)
        self.class_record_view = ClassRecordView(class_record_service, ledger_draft_service)
        self.governance_view = GovernanceView(governance_service)
        phase_note = "Settings remain a bounded local placeholder. The browser cockpit is preserved as the reference implementation."
        views = (
            self.dashboard_view,
            self.title_manager_view,
            self.lecture_pair_view,
            self.resource_view,
            self.historical_deck_view,
            self.revised_notes_view,
            self.slide_plan_view,
            self.triangulation_view,
            self.deliverables_view,
            self.class_record_view,
            self.governance_view,
            PlaceholderView("Settings", f"{phase_note}\n\n{WATERMARK_DISCLAIMER}"),
        )
        for view in views:
            self.stack.addWidget(view)
        workspace_layout.addWidget(self.stack)
        central_layout.addWidget(workspace, 1)
        self.setCentralWidget(central)
        self.navigation.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.dashboard_view.lecture_selected.connect(self.open_lecture)
        self.lecture_pair_view.workspace_requested.connect(self.open_workspace)
        self.resource_view.navigate_requested.connect(lambda name: self.open_workspace(name, self.resource_view.number))
        self.revised_notes_view.navigate_requested.connect(lambda name: self.open_workspace(name, self.revised_notes_view.number))
        self.slide_plan_view.navigate_requested.connect(lambda name: self.open_workspace(name, self.slide_plan_view.number))
        self.title_manager_view.status_message.connect(self.statusBar().showMessage)
        self.navigation.setCurrentRow(0)
        self.statusBar().showMessage("Qt Phase 4 · three-way scholarly triangulation · historical originals read-only · no AI, Git, website, or canonical writes")

    def open_lecture(self, number: int):
        self.lecture_pair_view.load_lecture(number)
        self.navigation.setCurrentRow(2)

    def navigate(self, name: str):
        row = NAVIGATION.index(name)
        self.navigation.setCurrentRow(row)

    def open_workspace(self, name: str, number: int):
        target = {
            "Resources": self.resource_view,
            "Historical Decks": self.historical_deck_view,
            "Revised Notes": self.revised_notes_view,
            "Slide Plan": self.slide_plan_view,
            "Lecture Triangulation": self.triangulation_view,
            "Deliverables": self.deliverables_view,
            "Class Record": self.class_record_view,
        }.get(name)
        if target is not None:
            target.load_lecture(number)
        self.navigate(name)
