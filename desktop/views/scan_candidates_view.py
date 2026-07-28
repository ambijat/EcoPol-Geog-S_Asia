from __future__ import annotations

from collections import Counter
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QHBoxLayout, QHeaderView,
    QInputDialog, QLabel, QMessageBox, QPushButton, QTableView, QVBoxLayout,
    QWidget,
)

from course_artifacts.repositories.class_repository import ArtifactClassRepository
from course_artifacts.services.scan_service import ScanService
from desktop.models.table_model import DictTableModel


class ScanCandidatesView(QWidget):
    changed = Signal()
    FILE_COLUMNS = (
        ("relative_path", "Relative path"),
        ("published_pdf_match", "Published PDF match"),
        ("file_extension", "Format"), ("file_size", "Bytes"),
        ("candidate_status", "Review status"),
        ("candidate_id", "Candidate record"),
    )
    FILE_COLUMN_WIDTHS = (400, 240, 90, 110, 210, 190)
    TOPIC_COLUMNS = (
        ("topic_label", "Topic"), ("lecture_group", "Lecture group"),
        ("topic_path", "Folder"), ("file_count", "Files"),
        ("formats", "Formats"), ("review_summary", "Review status"),
    )
    TOPIC_COLUMN_WIDTHS = (260, 130, 360, 90, 220, 210)
    REVISION_COLUMNS = (
        ("lecture_label", "Lecture"), ("tex_display", "TeX notes"),
        ("pdf_note_display", "PDF notes"),
        ("workbench_display", "Workbench presentations"),
        ("published_display", "Published PDFs"),
        ("revision_status", "Revision status"),
    )
    REVISION_COLUMN_WIDTHS = (110, 250, 230, 320, 260, 220)

    def __init__(
        self, service: ScanService, classes: ArtifactClassRepository, parent=None,
    ):
        super().__init__(parent)
        self.service = service
        self.classes = classes
        self._operational = True
        self._topic_mode = False
        self._revision_mode = False
        self.setAccessibleName("Scan candidate review workspace")
        root = QVBoxLayout(self)
        self.context = QLabel("SCAN CANDIDATE REVIEW")
        self.context.setObjectName("eyebrow")
        root.addWidget(self.context)
        self.title = QLabel("Artifact class")
        self.title.setObjectName("viewTitle")
        self.title.setAccessibleName("Selected artifact class")
        root.addWidget(self.title)
        self.subtitle = QLabel(
            "Scanning is explicit and read-only. Results are candidates; "
            "no artifact is registered automatically."
        )
        self.subtitle.setObjectName("viewSubtitle")
        self.subtitle.setWordWrap(True)
        root.addWidget(self.subtitle)
        controls = QHBoxLayout()
        self.artifact_class = QComboBox()
        self.artifact_class.setAccessibleName("Artifact root to scan")
        for item in classes.list(active_only=True):
            self.artifact_class.addItem(item["label"], item["code"])
        self.scan_button = QPushButton("Refresh Current Census")
        self.scan_button.setAccessibleName("Refresh current census")
        self.scan_button.setAccessibleDescription(
            "Read the configured folder; an unchanged census is reused and no "
            "files are registered automatically"
        )
        self.scan_button.clicked.connect(self.scan_selected)
        self.artifact_root_label = QLabel("Artifact root")
        controls.addWidget(self.artifact_root_label)
        controls.addWidget(self.artifact_class)
        controls.addWidget(self.scan_button)
        controls.addStretch()
        root.addLayout(controls)
        self.model = DictTableModel(self.FILE_COLUMNS)
        self.table = QTableView()
        self.table.setAccessibleName("Scan candidates table")
        self.table.setAccessibleDescription(
            "Candidate files awaiting an explicit instructor decision"
        )
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.table.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setSectionsMovable(True)
        header.setSectionsClickable(True)
        header.setCascadingSectionResizes(False)
        header.setMinimumSectionSize(72)
        header.setToolTip(
            "Drag column dividers to resize. Double-click a divider to fit "
            "its contents. Drag headings to reorder columns."
        )
        self.default_column_widths = self.FILE_COLUMN_WIDTHS
        for column, width in enumerate(self.default_column_widths):
            header.resizeSection(column, width)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        self.result_summary = QLabel("No completed scan for this artifact class")
        self.result_summary.setObjectName("tableResultSummary")
        self.result_summary.setAccessibleName("Latest scan result summary")
        root.addWidget(self.result_summary)
        self.column_resize_hint = QLabel(
            "Drag column dividers to resize · double-click to fit · "
            "drag headings to reorder"
        )
        self.column_resize_hint.setObjectName("tableResizeHint")
        self.column_resize_hint.setAccessibleName("Column resizing instructions")
        self.column_resize_hint.setAccessibleDescription(
            "Every Scan Candidates column is manually resizable and movable"
        )
        root.addWidget(self.column_resize_hint)
        actions = QHBoxLayout()
        self.action_buttons: dict[str, QPushButton] = {}
        for label, action in (
            ("Register", "REGISTER"), ("Ignore", "IGNORED"), ("Defer", "DEFERRED"),
            ("Mark as Duplicate", "MARKED_DUPLICATE"),
            ("Relate to Existing Artifact", "RELATE_TO_EXISTING"),
        ):
            button = QPushButton(label)
            button.setAccessibleName(label)
            button.setAccessibleDescription(
                f"Apply {label.lower()} to the selected scan candidate"
            )
            button.clicked.connect(
                lambda checked=False, target=action: self.apply_action(target)
            )
            self.action_buttons[label] = button
            actions.addWidget(button)
        self.open_topic_button = QPushButton("Open Topic Folder")
        self.open_topic_button.setAccessibleName("Open selected topic folder")
        self.open_topic_button.setAccessibleDescription(
            "Open the selected Lecture Raw Material topic folder without "
            "registering or modifying its files"
        )
        self.open_topic_button.clicked.connect(self.open_topic)
        self.open_topic_button.hide()
        actions.addWidget(self.open_topic_button)
        self.revision_buttons: dict[str, QPushButton] = {}
        revision_actions = (
            ("Open LaTeX Notes", self.open_latex_notes),
            ("Link Workbench", self.link_workbench),
            ("Begin Revision", self.begin_revision),
            ("Mark Integrated", lambda: self.set_revision_status("INTEGRATED")),
            ("Defer", lambda: self.set_revision_status("DEFERRED")),
            ("Reject", lambda: self.set_revision_status("REJECTED")),
        )
        for label, callback in revision_actions:
            button = QPushButton(label)
            button.setAccessibleName(label)
            button.clicked.connect(callback)
            button.hide()
            self.revision_buttons[label] = button
            actions.addWidget(button)
        actions.addStretch()
        root.addLayout(actions)
        self.artifact_class.currentIndexChanged.connect(self._class_changed)
        self.table.selectionModel().selectionChanged.connect(
            lambda _selected, _deselected: self._update_action_state()
        )
        self.table.doubleClicked.connect(lambda _index: self._activate_current())
        self._update_class_context()
        self.reload()

    def current(self) -> dict | None:
        index = self.table.currentIndex()
        return self.model.row(index.row()) if index.isValid() else None

    def set_class(self, code: str):
        index = self.artifact_class.findData(code)
        self.artifact_class.setCurrentIndex(max(index, 0))
        self._update_class_context()

    def scan_selected(self):
        code = str(self.artifact_class.currentData())
        previous_text = self.scan_button.text()
        self.scan_button.setEnabled(False)
        self.scan_button.setText("Scanning…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            self.service.scan(code)
        except Exception as exc:
            QMessageBox.warning(self, "Scan blocked", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
            self.scan_button.setText(previous_text)
            self.scan_button.setEnabled(self._operational)
        self.reload()
        self.changed.emit()

    def set_operational(self, operational: bool) -> None:
        """Gate mutations without disabling candidate inspection or scrolling."""
        self._operational = operational
        self.scan_button.setEnabled(operational)
        self._update_action_state()

    def apply_action(self, action: str):
        if self._topic_mode:
            return
        candidate = self.current()
        if not candidate:
            return
        try:
            if action == "REGISTER":
                self.service.register_candidate(candidate["id"])
            elif action == "RELATE_TO_EXISTING":
                artifacts = self.service.artifacts.list()
                if not artifacts:
                    raise ValueError("No registered artifact is available")
                labels = [
                    f'{item["artifact_id"]} · {item["title"]}' for item in artifacts
                ]
                selected, accepted = QInputDialog.getItem(
                    self, "Relate candidate to existing artifact",
                    "Existing artifact", labels, 0, False,
                )
                if not accepted:
                    return
                target = artifacts[labels.index(selected)]
                self.service.decide(
                    candidate["id"], action, related_artifact_id=target["id"]
                )
            else:
                self.service.decide(candidate["id"], action)
        except Exception as exc:
            QMessageBox.warning(self, "Candidate action blocked", str(exc))
            return
        self.reload()
        self.changed.emit()

    def open_topic(self):
        if not self._topic_mode:
            return
        topic = self.current()
        if not topic:
            return
        try:
            path = self.service.resolver.resolve(
                f'FOUNDATIONAL_RESOURCE://{topic["topic_path"]}'
            )
            if not path.is_dir():
                raise FileNotFoundError(path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as exc:
            QMessageBox.warning(self, "Topic folder unavailable", str(exc))

    def open_latex_notes(self):
        if not self._revision_mode:
            return
        lecture = self.current()
        if not lecture:
            return
        try:
            path = self.service.resolver.resolve(
                f'AI_GENERATED_ARTIFACT://{lecture["ai_folder"]}'
            )
            if not path.is_dir():
                raise FileNotFoundError(path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as exc:
            QMessageBox.warning(self, "LaTeX notes folder unavailable", str(exc))

    def _choose_workbench(self, lecture: dict) -> str:
        paths = lecture["workbench_paths"]
        if not paths:
            raise ValueError(
                f'No Workbench presentation was found for {lecture["lecture_label"]}'
            )
        selected = lecture.get("selected_workbench", "")
        if selected in paths:
            return selected
        if len(paths) == 1:
            selected = paths[0]
        else:
            labels = [Path(path).name for path in paths]
            chosen, accepted = QInputDialog.getItem(
                self, "Link Workbench presentation",
                f'{lecture["lecture_label"]} presentation',
                labels, 0, False,
            )
            if not accepted:
                return ""
            selected = paths[labels.index(chosen)]
        self.service.set_ai_revision_workbench(
            lecture["lecture_number"], selected
        )
        return selected

    def link_workbench(self):
        if not self._revision_mode:
            return
        lecture = self.current()
        if not lecture:
            return
        try:
            selected = self._choose_workbench(lecture)
        except Exception as exc:
            QMessageBox.warning(self, "Workbench link unavailable", str(exc))
            return
        if selected:
            lecture_number = lecture["lecture_number"]
            self.reload()
            self.table.selectRow(lecture_number - 1)

    def begin_revision(self):
        if not self._revision_mode:
            return
        lecture = self.current()
        if not lecture:
            return
        try:
            selected = self._choose_workbench(lecture)
            if not selected:
                return
            physical = self.service.resolver.resolve(
                f"PRESENTATION_WORKBENCH://{selected}"
            )
            if not physical.is_file():
                raise FileNotFoundError(physical)
            self.service.set_ai_revision_state(
                lecture["lecture_number"], "IN_REVISION", selected
            )
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(physical)))
        except Exception as exc:
            QMessageBox.warning(self, "Revision could not begin", str(exc))
            return
        lecture_number = lecture["lecture_number"]
        self.reload()
        self.table.selectRow(lecture_number - 1)
        self.changed.emit()

    def set_revision_status(self, status: str):
        if not self._revision_mode:
            return
        lecture = self.current()
        if not lecture or lecture["ai_note_count"] == 0:
            return
        try:
            self.service.set_ai_revision_state(
                lecture["lecture_number"], status,
                lecture.get("selected_workbench", ""),
            )
        except Exception as exc:
            QMessageBox.warning(self, "Revision status unavailable", str(exc))
            return
        lecture_number = lecture["lecture_number"]
        self.reload()
        self.table.selectRow(lecture_number - 1)
        self.changed.emit()

    def reload(self):
        code = str(self.artifact_class.currentData()) if self.artifact_class.count() else None
        rows = self.service.repository.latest_candidates(code) if code else []
        if code:
            accepted_extensions = {
                str(extension).lower()
                for extension in self.classes.get(code)["accepted_extensions"]
            }
            if accepted_extensions:
                rows = [
                    row for row in rows
                    if row["file_extension"].lower() in accepted_extensions
                ]
        if code == "PRESENTATION_WORKBENCH":
            rows = self.service.with_published_pdf_matches(rows)
        self._topic_mode = code == "FOUNDATIONAL_RESOURCE"
        self._revision_mode = code == "AI_GENERATED_ARTIFACT"
        if self._topic_mode:
            topics, topic_stats = self.service.raw_material_topics(rows)
            self._replace_rows(
                self.TOPIC_COLUMNS, self.TOPIC_COLUMN_WIDTHS, topics
            )
            self.table.setAccessibleName("Lecture Raw Material topics table")
            self.table.setAccessibleDescription(
                "Topic folders grouped under their lecture containers; "
                "contained files are summarized rather than flattened"
            )
            self.table.setColumnHidden(1, False)
        elif self._revision_mode:
            revisions, revision_stats = self.service.ai_revision_queue(rows)
            self._replace_rows(
                self.REVISION_COLUMNS, self.REVISION_COLUMN_WIDTHS, revisions
            )
            self.table.setAccessibleName("AI presentation revision queue")
            self.table.setAccessibleDescription(
                "Fifteen lecture rows identifying LaTeX source notes and PDF "
                "reading copies, linked to Workbench presentations"
            )
            self.table.setColumnHidden(1, False)
        else:
            self._replace_rows(
                self.FILE_COLUMNS, self.FILE_COLUMN_WIDTHS, rows
            )
            self.table.setAccessibleName("Scan candidates table")
            self.table.setAccessibleDescription(
                "Candidate files awaiting an explicit instructor decision"
            )
            self.table.setColumnHidden(
                1, code != "PRESENTATION_WORKBENCH"
            )
        if self.model.rows:
            self.table.selectRow(0)
            if self._topic_mode:
                summary = (
                    f'Latest scan · {len(self.model.rows)} topic folders'
                    f' · {topic_stats["topic_files"]} files summarized'
                    f' · {topic_stats["loose_files"]} loose root files not shown'
                    f' · {topic_stats["system_files"]} system files not shown'
                )
            elif self._revision_mode:
                summary = (
                    f'{revision_stats["lectures"]} lectures'
                    f' · {revision_stats["tex_sources"]} TeX notes'
                    f' · {revision_stats["pdf_notes"]} PDF notes'
                    f' · {revision_stats["lectures_with_notes"]} lectures with notes'
                    f' · {revision_stats["workbench_presentations"]} Workbench presentations'
                    f' · {revision_stats["published_pdfs"]} published PDFs'
                    f' · {revision_stats["unassigned_notes"]} unassigned notes'
                )
            else:
                formats = Counter(
                    (row["file_extension"] or "no extension").upper()
                    for row in self.model.rows
                )
                format_summary = " · ".join(
                    f"{extension}: {count}"
                    for extension, count in sorted(formats.items())
                )
                noun = "candidate" if len(self.model.rows) == 1 else "candidates"
                summary = (
                    f"Latest scan · {len(self.model.rows)} {noun} · {format_summary}"
                )
            if code == "PRESENTATION_WORKBENCH":
                match_statuses = Counter(
                    row["published_pdf_match_status"] for row in self.model.rows
                )
                matched = (
                    match_statuses["MATCHED_REGISTERED"]
                    + match_statuses["MATCHED_CANDIDATE"]
                )
                summary += (
                    f" · PDF matches: {matched}"
                    f" · unmatched: {match_statuses['NO_MATCH']}"
                    f" · ambiguous: {match_statuses['AMBIGUOUS']}"
                    " · ordered by lecture filename"
                )
                if match_statuses["PUBLISHED_SCAN_REQUIRED"]:
                    summary += " · scan Published PDFs to match"
            self.result_summary.setText(summary)
        else:
            if self._topic_mode and topic_stats["candidate_files"]:
                self.result_summary.setText(
                    "No topic folders found · "
                    f'{topic_stats["loose_files"]} loose root files not shown'
                    f' · {topic_stats["system_files"]} system files not shown'
                )
            else:
                self.result_summary.setText(
                    "No candidates in the latest completed scan for this artifact class"
                )
        self.result_summary.setToolTip(self.result_summary.text())
        self._update_action_state()

    def _class_changed(self, _index: int):
        self._update_class_context()
        self.reload()

    def _update_class_context(self):
        class_label = self.artifact_class.currentText() or "Artifact class"
        self.title.setText(class_label)
        self.title.setAccessibleDescription(
            f"Candidate review for {class_label}"
        )
        code = self.artifact_class.currentData()
        self.scan_button.setText(
            "Refresh LaTeX Notes" if code == "AI_GENERATED_ARTIFACT"
            else "Refresh Current Census"
        )
        self.artifact_root_label.setText(
            "LaTeX notes root" if code == "AI_GENERATED_ARTIFACT"
            else "Artifact root"
        )
        if code == "FOUNDATIONAL_RESOURCE":
            self.context.setText("TOPIC FOLDER REVIEW")
            self.subtitle.setText(
                "Review topic folders for Lecture Raw Material. Contained "
                "files are summarized at folder level; scanning remains "
                "explicit and read-only."
            )
            self.column_resize_hint.setText(
                "Topic folders only · contained files remain summarized · "
                "drag column dividers to resize"
            )
        elif code == "AI_GENERATED_ARTIFACT":
            self.context.setText("PRESENTATION REVISION WORKFLOW")
            self.title.setText("AI-Assisted LaTeX Revision Queue")
            self.subtitle.setText(
                "Review TeX source notes and PDF reading copies by lecture, "
                "open the linked editable Workbench presentation, and record "
                "instructor-controlled revision progress. Build auxiliaries "
                "are ignored."
            )
            self.column_resize_hint.setText(
                "One row per lecture · only .tex and .pdf are listed · "
                "Workbench presentations are the editable target"
            )
        else:
            self.context.setText("SCAN CANDIDATE REVIEW")
            self.subtitle.setText(
                f"Review candidate files for {class_label}. Scanning is explicit "
                "and read-only; no artifact is registered automatically."
            )
            self.column_resize_hint.setText(
                "Drag column dividers to resize · double-click to fit · "
                "drag headings to reorder"
            )

    def _update_action_state(self) -> None:
        has_selection = self.current() is not None
        for button in self.action_buttons.values():
            button.setVisible(not self._topic_mode and not self._revision_mode)
            button.setEnabled(
                not self._topic_mode and not self._revision_mode
                and self._operational and has_selection
            )
        self.open_topic_button.setVisible(self._topic_mode)
        self.open_topic_button.setEnabled(self._topic_mode and has_selection)
        lecture = self.current() if self._revision_mode else None
        has_notes = bool(lecture and lecture["ai_note_count"])
        has_workbench = bool(lecture and lecture["workbench_paths"])
        for button in self.revision_buttons.values():
            button.setVisible(self._revision_mode)
        self.revision_buttons["Open LaTeX Notes"].setEnabled(
            self._revision_mode and has_selection
        )
        self.revision_buttons["Link Workbench"].setEnabled(
            self._revision_mode and has_workbench
        )
        self.revision_buttons["Begin Revision"].setEnabled(
            self._revision_mode and self._operational
            and has_notes and has_workbench
        )
        self.revision_buttons["Mark Integrated"].setEnabled(
            self._revision_mode and self._operational
            and has_notes and has_workbench
        )
        for label in ("Defer", "Reject"):
            self.revision_buttons[label].setEnabled(
                self._revision_mode and self._operational and has_notes
            )

    def _activate_current(self) -> None:
        if self._topic_mode:
            self.open_topic()
        elif self._revision_mode:
            self.open_latex_notes()

    def _replace_rows(
        self, columns: tuple[tuple[str, str], ...],
        widths: tuple[int, ...], rows: list[dict],
    ) -> None:
        columns_changed = self.model.columns != columns
        if columns_changed:
            self.model.reconfigure(columns, rows)
            self.default_column_widths = widths
            for column, width in enumerate(widths):
                self.table.horizontalHeader().resizeSection(column, width)
        else:
            self.model.replace(rows)
