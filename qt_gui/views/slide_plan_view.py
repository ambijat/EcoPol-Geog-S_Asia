from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt, Signal
from PySide6.QtWidgets import QComboBox,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QPushButton,QSplitter,QTableView,QTextEdit,QVBoxLayout,QWidget

from gui.services import SLIDE_ACTIONS,VISUAL_TYPES
from qt_gui.models.table_model import DictTableModel
from qt_gui.services.slide_plan_service import SlidePlanService
from qt_gui.widgets.link_list import LinkList


class SlidePlanView(QWidget):
    navigate_requested = Signal(str)
    COLUMNS=(("sequence","#"),("slide_id","Slide"),("part","Part"),("title","Title"),("action","Action"),("visual_type","Visual"),("verification_status","Verification"),("approval_status","Approval"))
    def __init__(self,service:SlidePlanService,parent=None):
        super().__init__(parent); self.service=service; self.number=1; self.current=None
        layout=QVBoxLayout(self); title=QLabel("Slide Revision Plan"); title.setObjectName("viewTitle"); layout.addWidget(title); subtitle=QLabel("Working plan only · Move controls persist explicit sequence · no final deck generation or approval"); subtitle.setObjectName("viewSubtitle"); layout.addWidget(subtitle)
        top=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText("Search slide title"); self.part_filter=QComboBox(); self.part_filter.addItems(["ALL","A","B"]); up=QPushButton("Move up"); down=QPushButton("Move down"); top.addWidget(self.search,1); top.addWidget(self.part_filter); top.addWidget(up); top.addWidget(down); layout.addLayout(top)
        split=QSplitter(); self.model=DictTableModel(self.COLUMNS); self.proxy=QSortFilterProxyModel(self); self.proxy.setSourceModel(self.model); self.proxy.setFilterKeyColumn(3); self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive); self.table=QTableView(); self.table.setModel(self.proxy); self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows); split.addWidget(self.table)
        editor=QWidget(); form=QFormLayout(editor); self.part=QComboBox(); self.part.addItems(["A","B"]); self.title_edit=QLineEdit(); self.purpose=QTextEdit(); self.purpose.setMaximumHeight(55); self.action=QComboBox(); self.action.addItems(SLIDE_ACTIONS); self.visual=QComboBox(); self.visual.addItems(VISUAL_TYPES); self.speaker=QTextEdit(); self.speaker.setMaximumHeight(55); self.citation=QLineEdit(); self.verification=QComboBox(); self.verification.addItems(["NOT_YET_VERIFIED","VERIFICATION_REQUIRED","VERIFIED"]); self.approval=QComboBox(); self.approval.addItems(["WORKING_DRAFT","RETURNED_FOR_REVISION"])
        self.resources=LinkList(); self.notes=LinkList(); self.historical=LinkList()
        for w in (self.resources,self.notes,self.historical):w.setMaximumHeight(90)
        save=QPushButton("Save slide-plan entry"); save.clicked.connect(self.save); cancel=QPushButton("Cancel unsaved changes"); cancel.clicked.connect(lambda:self.select_row(self.table.currentIndex(),self.table.currentIndex()))
        actions=QHBoxLayout(); actions.addWidget(save); actions.addWidget(cancel); evidence_nav=QHBoxLayout()
        for text,target in (("Resources","Resources"),("Notes","Revised Notes"),("Historical slides","Historical Decks")):
            button=QPushButton(f"Inspect {text}"); button.clicked.connect(lambda checked=False,t=target:self.navigate_requested.emit(t)); evidence_nav.addWidget(button)
        for label,widget in (("Part",self.part),("Title",self.title_edit),("Purpose",self.purpose),("Action",self.action),("Visual type",self.visual),("Speaker note",self.speaker),("Citation footer",self.citation),("Verification",self.verification),("Approval",self.approval),("Linked resources",self.resources),("Linked notes",self.notes),("Historical slide evidence",self.historical),("Inspect supporting evidence",evidence_nav),("",actions)):form.addRow(label,widget)
        split.addWidget(editor); split.setSizes([680,620]); layout.addWidget(split,1)
        self.search.textChanged.connect(self.proxy.setFilterFixedString); self.part_filter.currentTextChanged.connect(self.filter_part); self.table.selectionModel().currentRowChanged.connect(self.select_row); up.clicked.connect(lambda:self.move(-1)); down.clicked.connect(lambda:self.move(1)); self.load_lecture(1)

    def load_lecture(self,number:int):
        self.number=number; self.model.replace(self.service.list_for_lecture(number)); self.options=self.service.link_options(number)
        if self.model.rows:self.table.selectRow(0)

    def filter_part(self,value:str):
        if value=="ALL":self.proxy.setFilterKeyColumn(3); self.proxy.setFilterFixedString(self.search.text())
        else:self.proxy.setFilterKeyColumn(2); self.proxy.setFilterFixedString(value)

    def select_row(self,current,_previous):
        source=self.proxy.mapToSource(current); self.current=self.model.row(source.row())
        if not self.current:return
        d=self.service.detail(self.current["id"]); s=d["slide"]
        for combo,value in ((self.part,s["part"]),(self.action,s["action"]),(self.visual,s["visual_type"]),(self.verification,s["verification_status"]),(self.approval,s["approval_status"])):
            i=combo.findText(value); combo.setCurrentIndex(max(i,0))
        self.title_edit.setText(s["title"]); self.purpose.setPlainText(s["purpose"]); self.speaker.setPlainText(s["speaker_note"]); self.citation.setText(s["citation_footer"])
        self.resources.set_options(self.options["resources"],"resource_id","title",{r["id"] for r in d["resources"]}); self.notes.set_options(self.options["notes"],"note_id","topic",{r["id"] for r in d["notes"]}); self.historical.set_options(self.options["historical_slides"],"historical_slide_id","title",{r["id"] for r in d["historical_slides"]})

    def save(self):
        if not self.current:return
        try:self.service.save(self.current["id"],{"part":self.part.currentText(),"title":self.title_edit.text(),"purpose":self.purpose.toPlainText(),"action":self.action.currentText(),"visual_type":self.visual.currentText(),"speaker_note":self.speaker.toPlainText(),"citation_footer":self.citation.text(),"verification_status":self.verification.currentText(),"approval_status":self.approval.currentText(),"resource_pks":self.resources.checked_ids(),"note_pks":self.notes.checked_ids(),"historical_slide_pks":self.historical.checked_ids()}); self.load_lecture(self.number)
        except Exception as exc:QMessageBox.warning(self,"Validation error",str(exc))

    def move(self,direction:int):
        if self.current:self.service.move(self.current["id"],direction); self.load_lecture(self.number)
