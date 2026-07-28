from __future__ import annotations


from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
)

from course_artifacts.repositories.artifact_repository import ArtifactRepository
from course_artifacts.repositories.class_repository import ArtifactClassRepository
from course_artifacts.services.path_resolver import LocalPathStore, PathResolver


class RepositoryPathsView(QWidget):
    changed = Signal()
    scan_requested = Signal(str)

    def __init__(
        self, resolver: PathResolver, classes: ArtifactClassRepository,
        artifacts: ArtifactRepository, parent=None,
    ):
        super().__init__(parent)
        self.resolver = resolver
        self.store = LocalPathStore(resolver.config)
        self.classes = classes
        self.artifacts = artifacts
        self.setAccessibleName("Artifact repository paths workspace")
        root = QVBoxLayout(self)
        context = QLabel("ARTIFACT REPOSITORY PATH")
        context.setObjectName("eyebrow")
        root.addWidget(context)
        self.title = QLabel("Artifact Repository Paths")
        self.title.setObjectName("viewTitle")
        root.addWidget(self.title)
        self.subtitle = QLabel(
            "Machine-local roots resolve symbolic locators. Selecting a folder never scans or registers it."
        )
        self.subtitle.setObjectName("viewSubtitle")
        root.addWidget(self.subtitle)
        self.table = QTableWidget(0, 5)
        self.table.setAccessibleName("Artifact repository path validation table")
        self.table.setAccessibleDescription(
            "Machine-local path, validation status, access mode, and enabled state for each artifact class"
        )
        self.table.setHorizontalHeaderLabels([
            "Artifact class", "Configured local path", "Status", "Access mode", "Enabled",
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.currentCellChanged.connect(self._selection_changed)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        actions = QHBoxLayout()
        self.buttons: dict[str, QPushButton] = {}
        for label in (
            "Browse", "Validate", "Open Folder", "Rescan", "Clear",
            "Enable or Disable", "Change Access Mode", "Accept Conflict",
        ):
            button = QPushButton(label)
            button.setAccessibleName(label)
            if label == "Clear":
                button.setAccessibleDescription(
                    "Clear the selected machine-local root without changing artifact records"
                )
            elif label == "Rescan":
                button.setAccessibleDescription(
                    "Explicitly scan the selected root to create candidates only"
                )
            self.buttons[label] = button
            actions.addWidget(button)
        actions.addStretch()
        root.addLayout(actions)
        self.report = QTextBrowser()
        self.report.setAccessibleName("Symbolic re-resolution report")
        self.report.setMaximumHeight(150)
        root.addWidget(self.report)
        self.buttons["Browse"].clicked.connect(self.browse)
        self.buttons["Validate"].clicked.connect(self.reload)
        self.buttons["Open Folder"].clicked.connect(self.open_folder)
        self.buttons["Rescan"].clicked.connect(self.rescan)
        self.buttons["Clear"].clicked.connect(self.clear)
        self.buttons["Enable or Disable"].clicked.connect(self.toggle_enabled)
        self.buttons["Change Access Mode"].clicked.connect(self.change_access)
        self.buttons["Accept Conflict"].clicked.connect(self.accept_conflict)
        self.reload()

    def selected_code(self) -> str | None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def set_class(self, code: str) -> None:
        """Select the repository row that belongs to the originating workspace."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == code:
                self.table.setCurrentCell(row, 0)
                self.table.selectRow(row)
                self.table.scrollToItem(item)
                self._update_context()
                return
        raise KeyError(code)

    def browse(self):
        code = self.selected_code()
        if not code:
            return
        current = self.store.load()["artifact_roots"][code]["path"]
        selected = QFileDialog.getExistingDirectory(
            self, f"Select root for {code}", current
        )
        if selected:
            self.store.update(code, path=selected, enabled=True)
            self._after_change()

    def reload(self):
        selected_before_reload = self.selected_code()
        classes = {item["code"]: item for item in self.classes.list()}
        payload = self.store.load()["artifact_roots"]
        results = self.resolver.validate_all()
        self.table.setRowCount(0)
        for row, code in enumerate(classes):
            self.table.insertRow(row)
            values = (
                classes[code]["label"], payload[code]["path"], results[code].status,
                payload[code]["access_mode"], "YES" if payload[code]["enabled"] else "NO",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, code)
                if column == 2:
                    item.setToolTip(results[code].detail)
                    item.setData(
                        12,
                        f'{classes[code]["label"]} path status: '
                        f'{results[code].status}. {results[code].detail}',
                    )
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        target_code = (
            selected_before_reload
            if selected_before_reload in classes
            else next(iter(classes), None)
        )
        if target_code is not None:
            self.set_class(target_code)
        else:
            self._update_context()
        self._update_report()

    def open_folder(self):
        code = self.selected_code()
        if not code:
            return
        result = self.resolver.validate_all()[code]
        if result.operational:
            QDesktopServices.openUrl(QUrl.fromLocalFile(result.path))
        else:
            QMessageBox.information(self, "Folder unavailable", result.status)

    def rescan(self):
        code = self.selected_code()
        if code:
            self.scan_requested.emit(code)

    def clear(self):
        code = self.selected_code()
        if code:
            self.store.update(code, path="", allow_inside_project=False, allow_shared_root=False)
            self._after_change()

    def toggle_enabled(self):
        code = self.selected_code()
        if code:
            item = self.store.load()["artifact_roots"][code]
            self.store.update(code, enabled=not bool(item["enabled"]))
            self._after_change()

    def change_access(self):
        code = self.selected_code()
        if code:
            current = self.store.load()["artifact_roots"][code]["access_mode"]
            options = ["read_only", "read_write", "configurable"]
            selected, accepted = QInputDialog.getItem(
                self, "Change access mode", "Expected access mode",
                options, options.index(current), False,
            )
            if accepted:
                self.store.update(code, access_mode=selected)
                self._after_change()

    def accept_conflict(self):
        code = self.selected_code()
        if not code:
            return
        result = self.resolver.validate_all()[code]
        if result.status != "CONFLICTING_ROOT":
            return
        answer = QMessageBox.question(
            self, "Accept conflicting root",
            f"{result.detail}\n\nExplicitly accept this root?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.store.update(
                code,
                allow_inside_project="source tree" in result.detail,
                allow_shared_root="Same root" in result.detail,
            )
            self._after_change()

    def _after_change(self):
        self.reload()
        self.changed.emit()

    def _selection_changed(
        self, _row: int, _column: int, _old_row: int, _old_column: int
    ) -> None:
        self._update_context()

    def _update_context(self) -> None:
        code = self.selected_code()
        if not code:
            self.title.setText("Artifact Repository Paths")
            self.subtitle.setText(
                "Machine-local roots resolve symbolic locators. "
                "Selecting a folder never scans or registers it."
            )
            return
        artifact_class = self.classes.get(code)
        label = artifact_class["label"]
        self.title.setText(label)
        self.title.setAccessibleName(f"{label} repository path")
        self.subtitle.setText(
            f"Machine-local repository path for {label}. "
            "Selecting a folder never scans or registers it."
        )

    def _update_report(self):
        report = self.resolver.reresolution_report(self.artifacts.list())
        if not report:
            self.report.setPlainText(
                "No artifact records require re-resolution. Changing a root never rewrites records."
            )
            return
        totals = {key: 0 for key in ("resolved", "missing", "ambiguous")}
        for item in report:
            totals[item["outcome"]] += 1
        self.report.setPlainText(
            "Re-resolution report · records were not rewritten\n\n"
            + " · ".join(f"{key}: {value}" for key, value in totals.items())
        )
