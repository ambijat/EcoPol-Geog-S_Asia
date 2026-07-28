from __future__ import annotations

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox,
    QPushButton, QSpinBox, QSplitter, QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from qt_gui.services.historical_deck_service import HistoricalDeckService


class HistoricalDeckView(QWidget):
    def __init__(self, service: HistoricalDeckService, parent=None):
        super().__init__(parent); self.service=service; self.number=1; self.decks=[]; self.slides=[]; self.current_deck=None; self.current_slide=None
        layout=QVBoxLayout(self); title=QLabel("Historical Deck Inspector"); title.setObjectName("viewTitle"); layout.addWidget(title)
        self.summary=QLabel("Six Lecture 1 candidates · confirmation required · originals immutable"); self.summary.setObjectName("viewSubtitle"); layout.addWidget(self.summary)
        filters=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText("Search deck or extracted title"); self.class_filter=QComboBox(); self.class_filter.addItems(["ALL","RETAIN","REVISE","REPLACE","MOVE_TO_PART_A","MOVE_TO_PART_B","MERGE","SPLIT","VERIFY","ARCHIVE","SUPPLEMENTARY_PART_C"]); filters.addWidget(self.search,1); filters.addWidget(QLabel("Slide classification")); filters.addWidget(self.class_filter); layout.addLayout(filters)
        split=QSplitter(); self.deck_list=QListWidget(); self.slide_list=QListWidget(); split.addWidget(self.deck_list); split.addWidget(self.slide_list)
        detail=QWidget(); form=QFormLayout(detail); self.preview=QLabel("No local thumbnail"); self.preview.setMinimumHeight(160); self.preview.setScaledContents(False)
        self.text=QTextBrowser(); self.text.setMinimumWidth(470)
        self.assignment=QComboBox(); self.assignment.addItems(sorted(service.ASSIGNMENTS)); confirm=QPushButton("Confirm/correct deck assignment"); confirm.clicked.connect(self.confirm)
        self.status=QComboBox(); self.status.addItems(["RETAIN","REVISE","REPLACE","MOVE_TO_PART_A","MOVE_TO_PART_B","MERGE","SPLIT","VERIFY","ARCHIVE","SUPPLEMENTARY_PART_C"])
        self.part=QComboBox(); self.part.addItems(["","A","B","SHARED","SUPPLEMENTARY"]); self.position=QSpinBox(); self.position.setRange(0,999)
        self.factual=QCheckBox(); self.visual=QCheckBox(); self.reason=QTextEdit(); self.reason.setMaximumHeight(60); self.confidence=QComboBox(); self.confidence.addItems(["UNASSESSED","LOW","MEDIUM","HIGH"])
        classify=QPushButton("Save slide classification"); classify.clicked.connect(self.classify); cancel=QPushButton("Cancel unsaved changes"); cancel.clicked.connect(lambda:self.select_slide(self.slide_list.currentRow())); inspect=QPushButton("Inspect selected source read-only"); inspect.clicked.connect(self.inspect)
        classification_actions=QHBoxLayout(); classification_actions.addWidget(classify); classification_actions.addWidget(cancel)
        for label,widget in (("Preview",self.preview),("Extracted text / metadata",self.text),("Deck assignment",self.assignment),("",confirm),("Classification",self.status),("Target part",self.part),("Target position",self.position),("Factual update required",self.factual),("Visual update required",self.visual),("Confidence",self.confidence),("Instructor reason",self.reason),("",classification_actions),("",inspect)): form.addRow(label,widget)
        split.addWidget(detail); split.setSizes([300,260,650]); layout.addWidget(split,1)
        self.deck_list.currentRowChanged.connect(self.select_deck); self.slide_list.currentRowChanged.connect(self.select_slide); self.search.textChanged.connect(self.apply_filters); self.class_filter.currentTextChanged.connect(self.apply_filters); self.load_lecture(1)

    def load_lecture(self, number:int):
        self.number=number; self.decks=self.service.list_for_lecture(number); self.deck_list.clear()
        for d in self.decks:
            warning=" ⚠" if d["instructor_confirmation_required"] else ""
            self.deck_list.addItem(f'{d["deck_id"]} · {d["extracted_title"] or d["title"]}\n{d["inferred_part"]} · {d["confidence"]}{warning}')
        self.summary.setText(f"{len(self.decks)} Lecture {number} historical candidates · title-slide evidence preferred · instructor confirmation required")
        if self.decks:self.deck_list.setCurrentRow(0)

    def apply_filters(self):
        needle=self.search.text().casefold(); classification=self.class_filter.currentText()
        for i,deck in enumerate(self.decks):
            matches=needle in f'{deck["title"]} {deck["extracted_title"]}'.casefold()
            if classification!="ALL": matches = matches and any(s["current_status"]==classification for s in self.service.slides(deck["id"]))
            self.deck_list.item(i).setHidden(not matches)

    def select_deck(self,row:int):
        self.current_deck=self.decks[row] if 0<=row<len(self.decks) else None; self.slide_list.clear(); self.slides=[]
        if not self.current_deck:return
        self.slides=self.service.slides(self.current_deck["id"])
        for s in self.slides:self.slide_list.addItem(f'{s["historical_slide_number"]:03d} · {s["title"] or s["page_status"]} · {s["current_status"]}')
        i=self.assignment.findText(self.current_deck["instructor_assignment"]); self.assignment.setCurrentIndex(max(i,0))
        self.text.setPlainText("\n".join((f'extracted_title: {self.current_deck["extracted_title"]}',f'inferred_lecture: {self.current_deck["inferred_lecture_number"]}',f'inferred_part: {self.current_deck["inferred_part"]}',f'source_evidence: {self.current_deck["source_evidence"]}',f'confidence: {self.current_deck["confidence"]}',f'checksum: {self.current_deck["content_sha256"]}',f'symbolic_location: {self.current_deck["source_locator"]}',f'sequence_warning: {self.current_deck["sequence_mismatch_warning"] or "NONE"}')))
        if self.slides:self.slide_list.setCurrentRow(0)

    def select_slide(self,row:int):
        self.current_slide=self.slides[row] if 0<=row<len(self.slides) else None
        if not self.current_slide:return
        s=self.current_slide; self.text.setPlainText(f'layout: {s["layout_name"]}\nimages: {s["image_count"]}\ncharts: {s["chart_count"]}\ntables: {s["table_count"]}\nspeaker_notes: {bool(s["speaker_note_available"])}\nstatus: {s["page_status"]}\n\n{s["text_extract"]}')
        if s["visual_preview"]:
            pix=QPixmap(str(self.service.database.project_root/s["visual_preview"])); self.preview.setPixmap(pix.scaled(440,280))
        else:self.preview.setText("No local thumbnail")
        for combo,value in ((self.status,s["current_status"]),(self.part,s["target_part"]),(self.confidence,s["confidence"])):
            i=combo.findText(value); combo.setCurrentIndex(max(i,0))
        self.position.setValue(s["target_sequence"] or 0); self.factual.setChecked(bool(s["factual_update_required"])); self.visual.setChecked(bool(s["visual_update_required"])); self.reason.setPlainText(s["reason"])

    def inspect(self):
        if not self.current_deck:return
        try:self.service.inspect(self.current_deck["id"]); self.load_lecture(self.number)
        except Exception as exc:QMessageBox.warning(self,"Inspection unavailable",str(exc))

    def confirm(self):
        if self.current_deck:self.service.confirm_assignment(self.current_deck["id"],self.assignment.currentText()); self.load_lecture(self.number)

    def classify(self):
        if not self.current_slide:return
        try:
            self.service.classify_slide(self.current_slide["id"],{"current_status":self.status.currentText(),"target_part":self.part.currentText(),"target_sequence":self.position.value() or None,"factual_update_required":self.factual.isChecked(),"visual_update_required":self.visual.isChecked(),"confidence":self.confidence.currentText(),"reason":self.reason.toPlainText()}); self.select_deck(self.deck_list.currentRow())
        except Exception as exc:QMessageBox.warning(self,"Validation error",str(exc))
