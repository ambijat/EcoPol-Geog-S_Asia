from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QGridLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWizard, QWizardPage,
)

from course_artifacts.repositories.class_repository import ArtifactClassRepository
from course_artifacts.services.path_resolver import LocalPathStore, PathResolver, REQUIRED_ROOTS


class FirstLaunchPathWizard(QWizard):
    configuration_changed = Signal()

    def __init__(
        self, resolver: PathResolver, classes: ArtifactClassRepository, parent=None,
    ):
        super().__init__(parent)
        self.resolver = resolver
        self.store = LocalPathStore(resolver.config)
        self.classes = classes
        self.setWindowTitle("IS529N Artifact Repository Setup")
        self.setAccessibleName("Artifact repository path setup wizard")
        self.setAccessibleDescription(
            "Configure machine-local roots; folder selection does not scan or ingest files"
        )
        self.setMinimumSize(980, 520)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        page = QWizardPage()
        page.setTitle("Configure local artifact repository roots")
        page.setSubTitle(
            "Folder selection does not scan or ingest files. Optional classes may remain unconfigured."
        )
        root = QVBoxLayout(page)
        boundary = QLabel(
            "Four required roots must validate before registration, scanning, and relationships are enabled."
        )
        boundary.setObjectName("boundaryNotice")
        boundary.setWordWrap(True)
        root.addWidget(boundary)
        grid = QGridLayout()
        for column, heading in enumerate((
            "Artifact class", "Current local path", "Folder", "Validation status",
            "Expected access mode",
        )):
            label = QLabel(heading)
            label.setObjectName("tableHeading")
            grid.addWidget(label, 0, column)
        self.rows: dict[str, dict] = {}
        class_map = {item["code"]: item for item in classes.list()}
        payload = self.store.load()
        for row, code in enumerate(class_map, start=1):
            item = payload["artifact_roots"][code]
            label = QLabel(class_map[code]["label"])
            if code in REQUIRED_ROOTS:
                label.setText(label.text() + " *")
            path = QLineEdit(str(item.get("path", "")))
            path.setAccessibleName(f'{class_map[code]["label"]} local path')
            path.setReadOnly(True)
            browse = QPushButton("Browse…")
            browse.setAccessibleName(
                f'Browse for {class_map[code]["label"]} repository path'
            )
            status = QLabel("MISSING")
            status.setObjectName("pathStatus")
            status.setAccessibleName(
                f'{class_map[code]["label"]} validation status'
            )
            access = QComboBox()
            access.setAccessibleName(
                f'{class_map[code]["label"]} expected access mode'
            )
            access.addItems(["read_only", "read_write", "configurable"])
            access.setCurrentText(item.get("access_mode", "read_only"))
            browse.clicked.connect(lambda checked=False, target=code: self.browse(target))
            access.currentTextChanged.connect(
                lambda value, target=code: self.change_access(target, value)
            )
            grid.addWidget(label, row, 0)
            grid.addWidget(path, row, 1)
            grid.addWidget(browse, row, 2)
            grid.addWidget(status, row, 3)
            grid.addWidget(access, row, 4)
            self.rows[code] = {
                "path": path, "browse": browse, "status": status,
                "access": access,
            }
        root.addLayout(grid)
        root.addStretch()
        note = QLabel(
            "* Required for operational mode. You may close this wizard and continue in configuration mode."
        )
        note.setObjectName("viewSubtitle")
        root.addWidget(note)
        self.addPage(page)
        self.currentIdChanged.connect(lambda _page: self.refresh())
        self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        first = next(iter(self.rows.values()), None)
        if first:
            first["browse"].setFocus()

    def browse(self, code: str):
        current = self.rows[code]["path"].text()
        selected = QFileDialog.getExistingDirectory(
            self, f"Select root for {code}", current
        )
        if selected:
            self.store.update(code, path=selected, enabled=True)
            self.configuration_changed.emit()
            self.refresh()

    def change_access(self, code: str, access_mode: str):
        self.store.update(code, access_mode=access_mode)
        self.configuration_changed.emit()
        self.refresh()

    def refresh(self):
        payload = self.store.load()["artifact_roots"]
        results = self.resolver.validate_all()
        for code, widgets in self.rows.items():
            widgets["path"].setText(str(payload[code].get("path", "")))
            widgets["status"].setText(results[code].status)
            widgets["status"].setToolTip(results[code].detail)
            widgets["status"].setAccessibleDescription(results[code].detail)
