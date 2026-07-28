from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSplitter, QTableView, QTextEdit, QVBoxLayout, QWidget,
)

from gui.services import NOTE_ORIGINS, TEACHING_FUNCTIONS
from qt_gui.models.table_model import DictTableModel
from qt_gui.services.note_service import NoteService
from qt_gui.widgets.link_list import LinkList


class RevisedNotesView(QWidget):
    navigate_requested = Signal(str)
    COLUMNS=(("note_id","Note"),("part","Part"),("topic","Topic"),("teaching_function","Teaching function"),("verification_status","Verification"),("instructor_status","Instructor status"))
    def __init__(self,service:NoteService,parent=None):
        super().__init__(parent); self.service=service; self.number=1; self.current=None
        layout=QVBoxLayout(self); title=QLabel("Revised Notes Workspace"); title.setObjectName("viewTitle"); layout.addWidget(title)
        subtitle=QLabel("No embedded AI · provenance is always visible · verification requires evidence or instructor-origin declaration"); subtitle.setObjectName("viewSubtitle"); layout.addWidget(subtitle)
        top=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText("Search note topic"); new=QPushButton("New note"); duplicate=QPushButton("Duplicate note"); top.addWidget(self.search,1); top.addWidget(new); top.addWidget(duplicate); layout.addLayout(top)
        split=QSplitter(); self.model=DictTableModel(self.COLUMNS); self.proxy=QSortFilterProxyModel(self); self.proxy.setSourceModel(self.model); self.proxy.setFilterKeyColumn(2); self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.table=QTableView(); self.table.setModel(self.proxy); self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows); split.addWidget(self.table)
        editor=QWidget(); form=QFormLayout(editor)
        self.part=QComboBox(); self.part.addItems(["A","B","SHARED"]); self.topic=QLineEdit(); self.claim=QTextEdit(); self.explanation=QTextEdit(); self.evidence=QTextEdit()
        for box in (self.claim,self.explanation,self.evidence):box.setMaximumHeight(65)
        self.date=QLineEdit(); self.confidence=QComboBox(); self.confidence.addItems(["UNVERIFIED","LOW","MEDIUM","HIGH"]); self.function=QComboBox(); self.function.addItems(TEACHING_FUNCTIONS); self.suggested=QLineEdit()
        self.origin=QComboBox(); self.origin.addItems(NOTE_ORIGINS); self.verification=QComboBox(); self.verification.addItems(["NOT_YET_VERIFIED","VERIFICATION_REQUIRED","VERIFIED"]); self.status=QComboBox(); self.status.addItems(["WORKING_DRAFT","APPROVED_WORKING_NOTE","RETURNED_FOR_REVISION","ARCHIVED"]); self.origin_declared=QCheckBox("Instructor explicitly declares this note originates from instructor knowledge")
        self.resources=LinkList(); self.resources.setMaximumHeight(105); self.historical=LinkList(); self.historical.setMaximumHeight(105); save=QPushButton("Save note"); save.clicked.connect(self.save); cancel=QPushButton("Cancel unsaved changes"); cancel.clicked.connect(lambda:self.select_row(self.table.currentIndex(),self.table.currentIndex()))
        actions=QHBoxLayout(); actions.addWidget(save); actions.addWidget(cancel); open_resources=QPushButton("Open Resources"); open_resources.clicked.connect(lambda:self.navigate_requested.emit("Resources")); open_history=QPushButton("Open Historical Decks"); open_history.clicked.connect(lambda:self.navigate_requested.emit("Historical Decks")); evidence_nav=QHBoxLayout(); evidence_nav.addWidget(open_resources); evidence_nav.addWidget(open_history)
        for label,widget in (("Part",self.part),("Topic",self.topic),("Claim",self.claim),("Explanation",self.explanation),("Evidence",self.evidence),("Date relevance",self.date),("Confidence",self.confidence),("Teaching function",self.function),("Suggested slide",self.suggested),("Provenance class",self.origin),("Verification",self.verification),("Instructor status",self.status),("Origin declaration",self.origin_declared),("Linked resources",self.resources),("Linked historical slides",self.historical),("Inspect linked evidence",evidence_nav),("",actions)):form.addRow(label,widget)
        split.addWidget(editor); split.setSizes([620,680]); layout.addWidget(split,1)
        self.search.textChanged.connect(self.proxy.setFilterFixedString); self.table.selectionModel().currentRowChanged.connect(self.select_row); new.clicked.connect(self.new_note); duplicate.clicked.connect(self.duplicate_note); self.load_lecture(1)

    def load_lecture(self,number:int):
        self.number=number; self.model.replace(self.service.list_for_lecture(number)); self.options=self.service.link_options(number)
        if self.model.rows:self.table.selectRow(0)

    def select_row(self,current,_previous):
        source=self.proxy.mapToSource(current); self.current=self.model.row(source.row())
        if not self.current:return
        d=self.service.detail(self.current["id"]); n=d["note"]
        for combo,value in ((self.part,n["part"]),(self.confidence,n["confidence"]),(self.function,n["teaching_function"]),(self.origin,n["note_origin"]),(self.verification,n["verification_status"]),(self.status,n["instructor_status"])):
            i=combo.findText(value); combo.setCurrentIndex(max(i,0))
        self.topic.setText(n["topic"]); self.claim.setPlainText(n["claim"]); self.explanation.setPlainText(n["explanation"]); self.evidence.setPlainText(n["evidence"]); self.date.setText(n["date_relevance"]); self.suggested.setText(n["suggested_slide"]); self.origin_declared.setChecked(bool(n["instructor_origin_declared"]))
        self.resources.set_options(self.options["resources"],"resource_id","title",{r["id"] for r in d["resources"]}); self.historical.set_options(self.options["historical_slides"],"historical_slide_id","title",{r["id"] for r in d["historical_slides"]})

    def new_note(self):
        try:self.service.create(self.number,{"part":"A","topic":"New working note","claim":"","teaching_function":"CONCEPT","created_by":"Instructor","note_origin":"INSTRUCTOR_AUTHORED","instructor_status":"WORKING_DRAFT"}); self.load_lecture(self.number); self.table.selectRow(self.model.rowCount()-1)
        except Exception as exc:QMessageBox.warning(self,"Validation error",str(exc))

    def duplicate_note(self):
        if self.current:self.service.duplicate(self.current["id"]); self.load_lecture(self.number)

    def save(self):
        if not self.current:return
        try:
            self.service.save(self.current["id"],{"part":self.part.currentText(),"topic":self.topic.text(),"claim":self.claim.toPlainText(),"explanation":self.explanation.toPlainText(),"evidence":self.evidence.toPlainText(),"date_relevance":self.date.text(),"confidence":self.confidence.currentText(),"teaching_function":self.function.currentText(),"suggested_slide":self.suggested.text(),"note_origin":self.origin.currentText(),"verification_status":self.verification.currentText(),"instructor_status":self.status.currentText(),"instructor_origin_declared":self.origin_declared.isChecked(),"resource_pks":self.resources.checked_ids(),"historical_slide_pks":self.historical.checked_ids()}); self.load_lecture(self.number)
        except Exception as exc:QMessageBox.warning(self,"Validation error",str(exc))
