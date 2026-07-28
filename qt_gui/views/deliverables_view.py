from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QComboBox,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QListWidget,QMessageBox,QPushButton,QSplitter,QTableWidget,QTableWidgetItem,QTextBrowser,QVBoxLayout,QWidget

from qt_gui.dialogs.deliverable_preview_dialog import DeliverablePreviewDialog
from qt_gui.services.deliverable_service import DECK_DECISIONS,SLIDE_DECISIONS,DeliverableService


class DeliverablesView(QWidget):
    def __init__(self,service:DeliverableService,parent=None):
        super().__init__(parent);self.service=service;self.number=1;self.part="A";self.bundles=[];self.current=None
        layout=QVBoxLayout(self);title=QLabel("Draft Deliverables");title.setObjectName("viewTitle");layout.addWidget(title);sub=QLabel("Governed local draft production · no Git controls · no automatic approval");sub.setObjectName("viewSubtitle");layout.addWidget(sub)
        controls=QHBoxLayout();self.lecture=QComboBox();self.lecture.addItems([f"Lecture {n:02d}" for n in range(1,16)]);self.part_combo=QComboBox();self.part_combo.addItems(["A — Tuesday","B — Friday"]);self.status=QComboBox();self.status.addItems(["DRAFT","REVISED"]);self.gate_label=QLabel();self.generate_button=QPushButton("Generate draft PPTX");controls.addWidget(self.lecture);controls.addWidget(self.part_combo);controls.addWidget(self.status);controls.addWidget(self.generate_button);controls.addWidget(self.gate_label,1);layout.addLayout(controls)
        split=QSplitter();self.history=QListWidget();split.addWidget(self.history);right=QWidget();right_layout=QVBoxLayout(right);self.summary=QTextBrowser();right_layout.addWidget(self.summary)
        actions=QHBoxLayout();self.render=QPushButton("Render PDF");self.thumbnails=QPushButton("Generate thumbnails");self.preview=QPushButton("Open preview");self.validate=QPushButton("Run validation");self.folder=QPushButton("Open containing folder")
        for b in (self.render,self.thumbnails,self.preview,self.validate,self.folder):actions.addWidget(b)
        right_layout.addLayout(actions)
        self.plan=QTableWidget(0,8);self.plan.setHorizontalHeaderLabels(["Slide","Purpose","Resource","Historical","Note","Citation","Verification","Decision"]);self.plan.horizontalHeader().setStretchLastSection(True);right_layout.addWidget(self.plan)
        review=QHBoxLayout();self.slide_decision=QComboBox();self.slide_decision.addItems(SLIDE_DECISIONS);self.slide_note=QLineEdit();self.slide_note.setPlaceholderText("Instructor slide-review note");self.record_slide=QPushButton("Record slide decision");review.addWidget(self.slide_decision);review.addWidget(self.slide_note,1);review.addWidget(self.record_slide);right_layout.addLayout(review)
        deck=QHBoxLayout();self.deck_decision=QComboBox();self.deck_decision.addItems(DECK_DECISIONS);self.deck_note=QLineEdit();self.deck_note.setPlaceholderText("Required for warning override");self.record_deck=QPushButton("Record instructor decision");self.return_button=QPushButton("Return deck for revision");deck.addWidget(self.deck_decision);deck.addWidget(self.deck_note,1);deck.addWidget(self.record_deck);deck.addWidget(self.return_button);right_layout.addLayout(deck)
        split.addWidget(right);split.setSizes([300,1000]);layout.addWidget(split,1)
        self.lecture.currentIndexChanged.connect(lambda i:self.load_lecture(i+1));self.part_combo.currentIndexChanged.connect(lambda i:self.load_part("A" if i==0 else "B"));self.history.currentRowChanged.connect(self.select_bundle);self.generate_button.clicked.connect(self.generate);self.render.clicked.connect(self.render_pdf);self.thumbnails.clicked.connect(self.generate_thumbnails);self.preview.clicked.connect(self.open_preview);self.validate.clicked.connect(self.run_validation);self.folder.clicked.connect(self.open_folder);self.record_slide.clicked.connect(self.record_slide_decision);self.record_deck.clicked.connect(self.record_deck_decision);self.return_button.clicked.connect(self.return_for_revision);self.load_lecture(1)

    def load_lecture(self,number:int):self.number=number;self.load_part(self.part)
    def load_part(self,part:str):
        self.part=part;gate=self.service.gate(self.number,part,self.status.currentText());self.generate_button.setEnabled(gate["enabled"]);self.gate_label.setText(f'Evidence-complete slides: {gate["evidence_complete_count"]} · '+("Generation enabled" if gate["enabled"] else "Blocked: "+"; ".join(gate["errors"])))
        self.plan.setRowCount(len(gate["plans"]))
        for row,p in enumerate(gate["plans"]):
            values=(p["slide_id"],p["purpose"],p["resource_link_count"],p["historical_link_count"],p["note_link_count"],"YES" if p["citation_footer"] else "NO",p["verification_status"],p["approval_status"])
            for col,value in enumerate(values):self.plan.setItem(row,col,QTableWidgetItem(str(value)))
        self.plan.resizeColumnsToContents();self.bundles=self.service.list_bundles(self.number,part);self.history.clear()
        for b in self.bundles:self.history.addItem(f'{b["version"]} · {b["status"]}\n{b["validation_status"]} · {b["deck_decision"]}')
        if self.bundles:self.history.setCurrentRow(0)
        else:self.current=None;self.summary.setPlainText("No generated local draft bundle.")

    def select_bundle(self,row:int):
        self.current=self.service.bundle(self.bundles[row]["id"]) if 0<=row<len(self.bundles) else None
        if not self.current:return
        b=self.current;self.summary.setPlainText("\n".join((f'version: {b["version"]} {b["status"]}',f'PPTX: {b["pptx_path"]}',f'PPTX checksum: {b["pptx_sha256"]}',f'PDF: {b["pdf_path"] or "NOT_RENDERED"}',f'PDF checksum: {b["pdf_sha256"] or "N/A"}',f'pages: {b["page_count"]}',f'thumbnails: {b["thumbnail_count"]}',f'provenance sidecar: {b["sidecar_path"]}',f'teaching brief: {b["teaching_brief_path"]}',f'validation: {b["validation_status"]}',f'approval state: {b["deck_decision"]}',f'rendering warnings: {b["rendering_warnings"]}')))

    def _act(self,callback):
        try:callback();self.load_part(self.part)
        except Exception as exc:QMessageBox.warning(self,"Operation blocked or failed",str(exc))
    def generate(self):self._act(lambda:self.service.generate(self.number,self.part,self.status.currentText()))
    def render_pdf(self):
        if self.current:self._act(lambda:self.service.render_pdf(self.current["id"]))
    def generate_thumbnails(self):
        if self.current:self._act(lambda:self.service.generate_thumbnails(self.current["id"]))
    def run_validation(self):
        if self.current:self._act(lambda:self.service.validate(self.current["id"]))
    def open_preview(self):
        if self.current:DeliverablePreviewDialog(self.service.database.project_root,self.service.bundle(self.current["id"]),self).exec()
    def open_folder(self):
        if self.current:QDesktopServices.openUrl(QUrl.fromLocalFile(str((self.service.database.project_root/self.current["pptx_path"]).parent)))
    def record_slide_decision(self):
        if not self.current or self.plan.currentRow()<0:return
        gate=self.service.gate(self.number,self.part);slide=gate["plans"][self.plan.currentRow()];self._act(lambda:self.service.record_slide_decision(self.current["id"],slide["id"],self.slide_decision.currentText(),self.slide_note.text()))
    def record_deck_decision(self):
        if self.current:self._act(lambda:self.service.record_deck_decision(self.current["id"],self.deck_decision.currentText(),self.deck_note.text()))
    def return_for_revision(self):
        if self.current:self._act(lambda:self.service.record_deck_decision(self.current["id"],"RETURNED_FOR_REVISION",self.deck_note.text()))
