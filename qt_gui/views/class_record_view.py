from __future__ import annotations

from PySide6.QtWidgets import QComboBox,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QPushButton,QScrollArea,QTextBrowser,QTextEdit,QVBoxLayout,QWidget

from qt_gui.services.class_record_service import ClassRecordService
from qt_gui.services.ledger_draft_service import LedgerDraftService


class ClassRecordView(QWidget):
    TEXT_FIELDS=("oral_material_added","student_questions","conceptual_difficulties","time_management","topics_deferred","follow_up_actions","impact_on_next_session","retrospective_entry_explanation")
    def __init__(self,service:ClassRecordService,ledger:LedgerDraftService,parent=None):
        super().__init__(parent);self.service=service;self.ledger=ledger;self.number=1;self.part="A";self.editors={}
        layout=QVBoxLayout(self);title=QLabel("Class Record");title.setObjectName("viewTitle");layout.addWidget(title);warning=QLabel("Local instructor record only. Do not enter student names, roll numbers, email addresses, or other identifying information.");warning.setObjectName("viewSubtitle");layout.addWidget(warning)
        top=QHBoxLayout();self.lecture=QComboBox();self.lecture.addItems([f"Lecture {n:02d}" for n in range(1,16)]);self.part_combo=QComboBox();self.part_combo.addItems(["A — Tuesday","B — Friday"]);top.addWidget(self.lecture);top.addWidget(self.part_combo);top.addStretch();layout.addLayout(top)
        scroll=QScrollArea();scroll.setWidgetResizable(True);form_widget=QWidget();form=QFormLayout(form_widget)
        for field,label in (("scheduled_date","Scheduled date (YYYY-MM-DD)"),("actual_date","Actual date (YYYY-MM-DD)"),("slides_planned","Slides planned"),("slides_covered","Slides covered"),("slides_omitted","Slides omitted")):
            editor=QLineEdit();self.editors[field]=editor;form.addRow(label,editor)
        for field in self.TEXT_FIELDS:
            editor=QTextEdit();editor.setMaximumHeight(70);self.editors[field]=editor;form.addRow(field.replace("_"," ").title(),editor)
        self.status=QComboBox();self.status.addItems(["NOT_REVIEWED","WORKING_DRAFT","INSTRUCTOR_VALIDATED"]);form.addRow("Instructor validation status",self.status);save=QPushButton("Save class record");cancel=QPushButton("Cancel unsaved changes");actions=QHBoxLayout();actions.addWidget(save);actions.addWidget(cancel);form.addRow(actions);scroll.setWidget(form_widget);layout.addWidget(scroll,1)
        draft=QHBoxLayout();self.event_type=QComboBox();self.event_type.addItems(sorted(self.ledger.TYPES));create=QPushButton("Generate isolated draft event");draft.addWidget(self.event_type);draft.addWidget(create);layout.addLayout(draft);self.preview=QTextBrowser();self.preview.setMaximumHeight(180);layout.addWidget(self.preview)
        self.lecture.currentIndexChanged.connect(lambda i:self.load(i+1,self.part));self.part_combo.currentIndexChanged.connect(lambda i:self.load(self.number,"A" if i==0 else "B"));save.clicked.connect(self.save);cancel.clicked.connect(lambda:self.load(self.number,self.part));create.clicked.connect(self.create_draft);self.load(1,"A")

    def load(self,number:int,part:str):
        self.number=number;self.part=part;row=self.service.load(number,part)
        for field,editor in self.editors.items():
            value=row.get(field,"") or "";editor.setPlainText(value) if isinstance(editor,QTextEdit) else editor.setText(value)
        i=self.status.findText(row.get("instructor_validation_status","") or "NOT_REVIEWED");self.status.setCurrentIndex(max(i,0));drafts=self.ledger.list_for_lecture(number);self.preview.setPlainText("\n".join(f'{d["event_id"]} · {d["approval_status"]} · {d["relative_path"]}' for d in drafts) or "No isolated Qt draft events.")

    def load_lecture(self,number:int):
        self.lecture.setCurrentIndex(number-1);self.load(number,self.part)

    def save(self):
        values={f:(e.toPlainText() if isinstance(e,QTextEdit) else e.text()) for f,e in self.editors.items()};values["instructor_validation_status"]=self.status.currentText()
        try:self.service.save(self.number,self.part,values);self.load(self.number,self.part)
        except Exception as exc:QMessageBox.warning(self,"Class-record safeguard",str(exc))

    def create_draft(self):
        try:path=self.ledger.prepare(self.number,self.event_type.currentText());self.preview.setPlainText(path.read_text(encoding="utf-8"))
        except Exception as exc:QMessageBox.warning(self,"Draft event blocked",str(exc))
