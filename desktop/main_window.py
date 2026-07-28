from __future__ import annotations

from PySide6.QtCore import QEvent, Signal, Qt, QTimer
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QPushButton, QSizePolicy, QSplitter,
    QStackedWidget, QVBoxLayout, QWidget,
)

from course_artifacts.database.connection import CourseArtifactDatabase
from course_artifacts.repositories.artifact_repository import ArtifactRepository
from course_artifacts.repositories.class_repository import ArtifactClassRepository
from course_artifacts.repositories.decision_repository import DecisionRepository
from course_artifacts.repositories.relationship_repository import RelationshipRepository
from course_artifacts.services.artifact_service import ArtifactService
from course_artifacts.services.decision_service import DecisionService
from course_artifacts.services.relationship_service import RelationshipService
from course_artifacts.services.path_resolver import PathResolver
from course_artifacts.services.scan_service import ScanService
from desktop.config import DesktopConfig
from desktop.dialogs.artifact_dialog import ArtifactRegistrationDialog
from desktop.dialogs.first_launch_wizard import FirstLaunchPathWizard
from desktop.views.artifact_workspace import ArtifactClassWorkspace
from desktop.views.decision_queue_view import DecisionQueueView
from desktop.views.home_view import HomeView
from desktop.views.relationship_view import RelationshipView
from desktop.views.settings_view import SettingsView
from desktop.views.repository_paths_view import RepositoryPathsView
from desktop.views.scan_candidates_view import ScanCandidatesView
from desktop.widgets.watermark_container import WatermarkContainer


class ElidingLabel(QLabel):
    """A single-line label that preserves its complete text in a tooltip."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = ""
        self.set_full_text(text)

    @property
    def full_text(self) -> str:
        return self._full_text

    def set_full_text(self, text: str) -> None:
        self._full_text = text
        self.setToolTip(text)
        self._update_elision()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elision()

    def _update_elision(self) -> None:
        margins = self.contentsMargins()
        available = max(0, self.width() - margins.left() - margins.right())
        visible = self.fontMetrics().elidedText(
            self._full_text, Qt.TextElideMode.ElideRight, available
        )
        super().setText(visible)


class AccessibleNavigationList(QListWidget):
    destinationActivated = Signal(int)

    def keyPressEvent(self, event):
        if event.key() in (
            Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space,
        ):
            if self.currentRow() >= 0:
                self.destinationActivated.emit(self.currentRow())
            event.accept()
            return
        super().keyPressEvent(event)


NAVIGATION_LABELS = {
    "PUBLISHED_PRESENTATION_PDF": "Published PDFs",
    "PRESENTATION_WORKBENCH": "Presentation Workbench",
    "FOUNDATIONAL_RESOURCE": "Lecture Raw Material",
    "AI_GENERATED_ARTIFACT": "AI-assisted LaTeX Notes",
    "INSTRUCTOR_DEFINED_CLASS_5": "Knowledge Maps",
    "SPATIAL_RESOURCE": "Spatial Raw Material",
}


class MainWindow(QMainWindow):
    def __init__(self, config: DesktopConfig | None = None, parent=None):
        super().__init__(parent)
        self.config = (config or DesktopConfig()).resolved()
        QApplication.instance().installEventFilter(self)
        self.setWindowTitle("IS529N — Economic and Political Geography of South Asia")
        self.setAccessibleName(
            "IS529N Economic and Political Geography of South Asia artifact cockpit"
        )
        self.setAccessibleDescription(
            "Local instructor-governed course artifact management application"
        )
        self.setMinimumSize(1100, 700)
        self.resize(1500, 900)
        self.database = CourseArtifactDatabase(self.config.course_artifacts)
        self.database.initialise()
        self.class_repository = ArtifactClassRepository(self.database)
        self.artifact_repository = ArtifactRepository(self.database)
        self.relationship_repository = RelationshipRepository(self.database)
        self.decision_repository = DecisionRepository(self.database)
        self.artifact_service = ArtifactService(self.database)
        self.relationship_service = RelationshipService(self.database)
        self.decision_service = DecisionService(self.database)
        self.path_resolver = PathResolver(self.config.course_artifacts)
        self.scan_service = ScanService(self.database, self.path_resolver)
        self.decision_service.ensure_fifth_class_decision()
        self.class_workspaces: dict[str, ArtifactClassWorkspace] = {}
        self.stack_keys: list[str] = []

        tools_menu = self.menuBar().addMenu("Tools")
        browser_action = QAction("Start Browser Sidecar…", self)
        browser_action.triggered.connect(
            lambda: self._show_status(
                "Browser sidecar remains manual and disabled during the "
                "initial course artifact cycle.",
                7000,
            )
        )
        tools_menu.addAction(browser_action)
        settings_menu = self.menuBar().addMenu("Settings")
        paths_action = QAction("Artifact Repository Paths", self)
        paths_action.triggered.connect(lambda: self.navigate("PATHS"))
        settings_menu.addAction(paths_action)

        central = WatermarkContainer(self.config.watermark_path)
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        navigation_frame = QFrame()
        navigation_frame.setObjectName("navigationRail")
        navigation_frame.setMinimumWidth(210)
        navigation_frame.setMaximumWidth(330)
        self.navigation_frame = navigation_frame
        navigation_layout = QVBoxLayout(navigation_frame)
        self.course_identity_label = QLabel(
            "IS529N\nEconomic and Political\nGeography of South Asia"
        )
        self.course_identity_label.setObjectName("navigationBrand")
        self.course_identity_label.setWordWrap(True)
        navigation_layout.addWidget(self.course_identity_label)
        self.methodology_label = QLabel("Course Artifact Cockpit")
        self.methodology_label.setObjectName("navigationSubtitle")
        self.methodology_label.setWordWrap(True)
        navigation_layout.addWidget(self.methodology_label)
        nav_label = QLabel("ARTIFACT CONTROL")
        nav_label.setObjectName("navSection")
        navigation_layout.addWidget(nav_label)
        self.navigation = AccessibleNavigationList()
        self.navigation.setAccessibleName("Cockpit destinations")
        self.navigation.setAccessibleDescription(
            "Use Up, Down, Home, or End to choose a destination; "
            "press Enter or Space to open it."
        )
        self.navigation.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.navigation.setTextElideMode(Qt.TextElideMode.ElideNone)
        navigation_layout.addWidget(self.navigation, 1)
        boundary = QLabel(
            "LOCAL · OFFLINE · INSTRUCTOR GOVERNED\n\n"
            "NO AI EXECUTION · NO SERVER REQUIRED\n"
            "SOURCE REPOSITORIES READ-ONLY"
        )
        boundary.setObjectName("boundaryLabel")
        boundary.setWordWrap(True)
        navigation_layout.addWidget(boundary)
        workspace = QWidget()
        workspace.setMinimumWidth(0)
        workspace.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(18, 14, 18, 12)
        global_actions = QFrame()
        global_actions.setObjectName("globalActions")
        global_actions.setAccessibleName("Global cockpit actions")
        global_actions.setAccessibleDescription(
            "Actions that apply to the complete artifact cockpit"
        )
        global_actions.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.global_actions = global_actions
        self.global_actions_layout = QGridLayout(global_actions)
        self.global_actions_layout.setContentsMargins(8, 8, 8, 8)
        self.global_actions_layout.setHorizontalSpacing(6)
        self.global_actions_layout.setVerticalSpacing(6)
        self.global_buttons: dict[str, QPushButton] = {}
        for label in (
            "Cockpit Home", "Refresh All", "Find Duplicates", "Relationship Map",
            "Processing Queue", "Instructor Decisions", "Settings",
        ):
            button = QPushButton(label)
            button.setProperty("compact", True)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            button.setAccessibleName(label)
            button.setAccessibleDescription(
                f"Global action: {label}"
            )
            self.global_buttons[label] = button
        self.global_action_columns = 0
        self._reflow_global_actions()
        workspace_layout.addWidget(global_actions)
        self.stack = QStackedWidget()
        workspace_layout.addWidget(self.stack, 1)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(navigation_frame)
        self.main_splitter.addWidget(workspace)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([245, max(640, self.width() - 245)])
        central_layout.addWidget(self.main_splitter)
        self.setCentralWidget(central)

        self.home_view = HomeView(
            self.artifact_service, self.class_repository,
            self.relationship_repository, self.decision_repository,
        )
        self._add_view("HOME", "Cockpit Home", self.home_view)
        for artifact_class in self.class_repository.list(active_only=True):
            view = ArtifactClassWorkspace(
                artifact_class["code"], self.artifact_service, self.class_repository,
                self.path_resolver,
            )
            view.changed.connect(self.refresh_all)
            view.relationship_requested.connect(self.open_relationship_for)
            view.show_relationships_requested.connect(self.show_relationships_for)
            view.configure_path_requested.connect(self.open_repository_paths_for)
            view.scan_requested.connect(self.run_scan)
            self.class_workspaces[artifact_class["code"]] = view
            self._add_view(
                f'CLASS:{artifact_class["code"]}',
                NAVIGATION_LABELS[artifact_class["code"]],
                view,
                artifact_class["label"],
            )
        self.relationship_view = RelationshipView(
            self.relationship_service, self.artifact_repository, self.path_resolver
        )
        self.relationship_view.changed.connect(self.refresh_all)
        self._add_view("RELATIONSHIPS", "Artifact Relationships", self.relationship_view)
        self.scan_view = ScanCandidatesView(self.scan_service, self.class_repository)
        self.scan_view.changed.connect(self.refresh_all)
        self._add_view("SCAN", "Scan Candidates", self.scan_view)
        self.decision_view = DecisionQueueView(self.decision_repository)
        self._add_view("DECISIONS", "Instructor Decisions", self.decision_view)
        self.repository_paths_view = RepositoryPathsView(
            self.path_resolver, self.class_repository, self.artifact_repository
        )
        self.repository_paths_view.changed.connect(self.refresh_path_gate)
        self.repository_paths_view.scan_requested.connect(self.run_scan)
        self._add_view(
            "PATHS", "Repository Paths", self.repository_paths_view,
            "Artifact Repository Paths",
        )
        self.settings_view = SettingsView(self.class_repository)
        self.settings_view.changed.connect(self.refresh_all)
        self._add_view("SETTINGS", "Settings", self.settings_view)

        self.navigation.destinationActivated.connect(self._activate_navigation)
        self.navigation.itemClicked.connect(
            lambda item: self._activate_navigation(self.navigation.row(item))
        )
        self.stack.currentChanged.connect(
            lambda _index: self._configure_active_tab_order()
        )
        self.home_view.class_opened.connect(self.open_class)
        self.global_buttons["Cockpit Home"].clicked.connect(lambda: self.navigate("HOME"))
        self.global_buttons["Refresh All"].clicked.connect(self.refresh_all)
        self.global_buttons["Instructor Decisions"].clicked.connect(
            lambda: self.navigate("DECISIONS")
        )
        self.global_buttons["Settings"].clicked.connect(lambda: self.navigate("SETTINGS"))
        self.global_buttons["Find Duplicates"].clicked.connect(
            lambda: self._bounded_notice(
                "Duplicate decisions are manual. Open Scan Candidates, select "
                "a row, and use Mark as Duplicate."
            )
        )
        self.global_buttons["Relationship Map"].clicked.connect(
            lambda: self._bounded_notice("The native relationship map is reserved for Stage 5.")
        )
        self.global_buttons["Processing Queue"].clicked.connect(
            lambda: self._bounded_notice("AI packet processing is reserved for Stage 6; no API execution is present.")
        )
        self.navigation.setCurrentRow(0)
        self._activate_navigation(0)
        self.path_wizard: FirstLaunchPathWizard | None = None
        self.refresh_path_gate()
        if not self.path_resolver.operational():
            QTimer.singleShot(0, self.ensure_path_setup)
        self.status_label = ElidingLabel()
        self.status_label.setObjectName("statusMessage")
        self.status_label.setAccessibleName("Cockpit status")
        self.status_label.setAccessibleDescription(
            "Current local application and repository status"
        )
        self.status_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.status_label.setMinimumHeight(28)
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.statusBar().setMinimumHeight(32)
        self.statusBar().addWidget(self.status_label, 1)
        self._show_status(
            "Artifact foundation v0.1 · local SQLite · source repositories read-only · no server or AI execution"
        )
        self._configure_active_tab_order()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._focus_initial_control)

    def closeEvent(self, event):
        application = QApplication.instance()
        if application is not None:
            application.removeEventFilter(self)
        super().closeEvent(event)

    def eventFilter(self, watched, event):
        if (
            event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and isinstance(watched, QPushButton)
            and self.isAncestorOf(watched)
        ):
            if watched.isEnabled():
                watched.click()
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "global_buttons"):
            self._reflow_global_actions()

    def _reflow_global_actions(self):
        usable = max(1, self.width() - 240)
        if usable >= 1220:
            columns = 7
        elif usable >= 820:
            columns = 5
        elif usable >= 560:
            columns = 3
        else:
            columns = 2
        if columns == self.global_action_columns:
            return
        while self.global_actions_layout.count():
            self.global_actions_layout.takeAt(0)
        for index, button in enumerate(self.global_buttons.values()):
            self.global_actions_layout.addWidget(
                button, index // columns, index % columns
            )
        self.global_action_columns = columns

    def _add_view(
        self, key: str, label: str, view: QWidget, tooltip: str = ""
    ):
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, key)
        item.setToolTip(tooltip or label)
        self.navigation.addItem(item)
        self.stack.addWidget(view)
        self.stack_keys.append(key)

    def navigate(self, key: str):
        if key not in self.stack_keys:
            raise KeyError(key)
        row = self.stack_keys.index(key)
        self.navigation.setCurrentRow(row)
        self._activate_navigation(row)

    def _activate_navigation(self, row: int):
        if not 0 <= row < self.stack.count():
            return
        self.stack.setCurrentIndex(row)
        self.active_navigation_row = row
        for index in range(self.navigation.count()):
            item = self.navigation.item(index)
            font = QFont(item.font())
            font.setBold(index == row)
            item.setFont(font)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, item.text())
            item.setData(
                Qt.ItemDataRole.AccessibleDescriptionRole,
                item.toolTip(),
            )
        self._configure_active_tab_order()

    def _focus_initial_control(self):
        if self.path_wizard is not None and self.path_wizard.isVisible():
            return
        self.navigation.setFocus(Qt.FocusReason.TabFocusReason)

    def _configure_active_tab_order(self):
        if not hasattr(self, "navigation") or not hasattr(self, "stack"):
            return
        active = self.stack.currentWidget()
        chain: list[QWidget] = [
            self.navigation, *self.global_buttons.values()
        ]
        if hasattr(active, "focus_chain"):
            chain.extend(active.focus_chain())
        for first, second in zip(chain, chain[1:]):
            QWidget.setTabOrder(first, second)

    def open_class(self, class_code: str):
        self.navigate(f"CLASS:{class_code}")

    def open_repository_paths_for(self, class_code: str):
        self.repository_paths_view.set_class(class_code)
        self.navigate("PATHS")

    def open_relationship_for(self, artifact_pk: int):
        self.relationship_view.suggested_source = artifact_pk or None
        self.navigate("RELATIONSHIPS")
        if artifact_pk:
            self.relationship_view.create()

    def show_relationships_for(self, artifact_pk: int):
        self.relationship_view.show_for(artifact_pk or None)
        self.navigate("RELATIONSHIPS")

    def register_artifact(self):
        current_key = self.stack_keys[self.stack.currentIndex()]
        default_code = current_key.removeprefix("CLASS:") if current_key.startswith("CLASS:") else ""
        dialog = ArtifactRegistrationDialog(
            self.artifact_service, self.class_repository, default_code,
            self, self.path_resolver,
        )
        if dialog.exec():
            self.refresh_all()

    def refresh_all(self):
        self.home_view.reload()
        for workspace in self.class_workspaces.values():
            workspace.reload()
        self.relationship_view.reload()
        self.decision_view.reload()
        self.settings_view.reload()
        self.repository_paths_view.reload()
        self.scan_view.reload()
        for row in range(self.navigation.count()):
            item = self.navigation.item(row)
            key = item.data(Qt.ItemDataRole.UserRole)
            if str(key).startswith("CLASS:"):
                class_code = str(key).split(":", 1)[1]
                artifact_class = self.class_repository.get(class_code)
                item.setText(NAVIGATION_LABELS[class_code])
                item.setToolTip(artifact_class["label"])
        self.refresh_path_gate()
        self._configure_active_tab_order()

    def _bounded_notice(self, message: str):
        self._show_status(message, 9000)

    def _show_status(self, message: str, timeout: int = 0):
        if not hasattr(self, "status_label"):
            return
        self.status_label.set_full_text(message)
        if timeout:
            QTimer.singleShot(
                timeout,
                lambda expected=message: (
                    self.status_label.set_full_text("")
                    if self.status_label.full_text == expected else None
                ),
            )

    def ensure_path_setup(self):
        if self.path_resolver.operational() or (
            self.path_wizard is not None and self.path_wizard.isVisible()
        ):
            return
        self.path_wizard = FirstLaunchPathWizard(
            self.path_resolver, self.class_repository, self
        )
        self.path_wizard.configuration_changed.connect(self.refresh_path_gate)
        self.path_wizard.finished.connect(lambda _result: self.refresh_path_gate())
        self.path_wizard.show()

    def refresh_path_gate(self):
        operational = self.path_resolver.operational()
        for workspace in self.class_workspaces.values():
            workspace.set_operational(operational)
        self.relationship_view.set_operational(operational)
        self.scan_view.set_operational(operational)
        if operational:
            self._show_status(
                "Artifact roots available · operational cockpit enabled · no automatic scanning"
            )
        else:
            self._show_status(
                "Configuration mode · four required artifact roots must validate before operational actions"
            )

    def run_scan(self, class_code: str):
        self.navigate("SCAN")
        self.scan_view.set_class(class_code)
        self.scan_view.scan_selected()

    @property
    def path_setup_required(self) -> bool:
        return not self.path_resolver.operational()

    @property
    def artifact_class_button_count(self) -> int:
        return self.home_view.class_grid.count()
