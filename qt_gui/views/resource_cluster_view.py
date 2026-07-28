from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSplitter, QTableView, QTextBrowser, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from qt_gui.models.table_model import DictTableModel, MultiFilterProxyModel
from qt_gui.services.resource_service import ResourceService


class ResourceClusterView(QWidget):
    navigate_requested = Signal(str)
    COLUMNS = (("resource_id", "Resource"), ("title", "Title"), ("file_type", "Type"),
               ("source_layer", "Source class"), ("assignment", "Part"),
               ("classification", "Intended use"), ("verification_status", "Verification"))

    def __init__(self, service: ResourceService, parent=None):
        super().__init__(parent); self.service = service; self.number = 1; self.current = None
        layout = QVBoxLayout(self)
        title = QLabel("Resource Cluster Browser"); title.setObjectName("viewTitle"); layout.addWidget(title)
        subtitle = QLabel("Symbolic locators only · originals remain read-only and in place"); subtitle.setObjectName("viewSubtitle"); layout.addWidget(subtitle)
        filters = QHBoxLayout(); self.lecture = QComboBox(); self.lecture.addItems([f"Lecture {n:02d}" for n in range(1,16)])
        self.search = QLineEdit(); self.search.setPlaceholderText("Search resource title")
        self.part_filter = QComboBox(); self.part_filter.addItems(["ALL","SHARED","A","B","SUPPLEMENTARY","UNCLASSIFIED","ARCHIVE_ONLY","EXCLUDED"])
        self.type_filter=QComboBox(); self.layer_filter=QComboBox(); self.use_filter=QComboBox(); self.verify_filter=QComboBox()
        for combo in (self.type_filter,self.layer_filter,self.use_filter,self.verify_filter):combo.addItem("ALL")
        filters.addWidget(self.lecture); filters.addWidget(self.search,1); filters.addWidget(QLabel("Part")); filters.addWidget(self.part_filter); filters.addWidget(QLabel("Type")); filters.addWidget(self.type_filter); filters.addWidget(QLabel("Source")); filters.addWidget(self.layer_filter); filters.addWidget(QLabel("Use")); filters.addWidget(self.use_filter); filters.addWidget(QLabel("Verify")); filters.addWidget(self.verify_filter); layout.addLayout(filters)
        split = QSplitter()
        self.clusters = QTreeWidget(); self.clusters.setHeaderLabel("Lecture resource clusters"); split.addWidget(self.clusters)
        self.model = DictTableModel(self.COLUMNS); self.proxy = MultiFilterProxyModel(1,self); self.proxy.setSourceModel(self.model)
        self.table = QTableView(); self.table.setModel(self.proxy); self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows); self.table.setSortingEnabled(True); split.addWidget(self.table)
        detail = QWidget(); form = QFormLayout(detail)
        self.metadata = QTextBrowser(); self.metadata.setMinimumWidth(390); self.metadata.setOpenExternalLinks(False)
        self.assignment = QComboBox(); self.assignment.addItems(["SHARED","A","B","SUPPLEMENTARY","UNCLASSIFIED","ARCHIVE_ONLY","EXCLUDED"])
        self.classification = QComboBox(); self.classification.addItems(["CENTRAL","SUPPORTING","CONCEPTUAL","MAP","DATA","CASE_STUDY","HISTORICAL_BACKGROUND","CLASSROOM_ILLUSTRATION","VERIFICATION_REQUIRED","ARCHIVE_ONLY","EXCLUDE"])
        self.centrality = QComboBox(); self.centrality.addItems(["CENTRAL","SUPPORTING"])
        self.comment = QTextEdit(); self.comment.setMaximumHeight(70)
        save = QPushButton("Save instructor classification"); save.clicked.connect(self.save); cancel=QPushButton("Cancel unsaved changes"); cancel.clicked.connect(lambda:self.select_row(self.table.currentIndex(),self.table.currentIndex()))
        actions=QHBoxLayout(); actions.addWidget(save); actions.addWidget(cancel)
        form.addRow(self.metadata); form.addRow("Lecture assignment",self.assignment); form.addRow("Intended use",self.classification); form.addRow("Centrality",self.centrality); form.addRow("Instructor comment",self.comment); form.addRow(actions)
        split.addWidget(detail); split.setSizes([220,650,430]); layout.addWidget(split,1)
        links = QHBoxLayout()
        for text,target in (("Open linked notes","Revised Notes"),("Open linked slides","Slide Plan"),("Open historical decks","Historical Decks")):
            button=QPushButton(text); button.clicked.connect(lambda checked=False,t=target:self.navigate_requested.emit(t)); links.addWidget(button)
        layout.addLayout(links)
        self.lecture.currentIndexChanged.connect(lambda i:self.load_lecture(i+1)); self.search.textChanged.connect(self.proxy.set_search)
        for combo,column in ((self.part_filter,4),(self.type_filter,2),(self.layer_filter,3),(self.use_filter,5),(self.verify_filter,6)):
            combo.currentTextChanged.connect(lambda value,c=column:self.proxy.set_exact(c,value))
        self.table.selectionModel().currentRowChanged.connect(self.select_row)
        self.load_lecture(1)

    def load_lecture(self, number: int):
        self.number=number; rows=self.service.list_for_lecture(number); self.model.replace(rows); self._clusters(rows)
        for combo,key in ((self.type_filter,"file_type"),(self.layer_filter,"source_layer"),(self.use_filter,"classification"),(self.verify_filter,"verification_status")):
            current=combo.currentText(); combo.blockSignals(True); combo.clear(); combo.addItem("ALL"); combo.addItems(sorted({str(r[key]) for r in rows if r[key]})); combo.setCurrentText(current if combo.findText(current)>=0 else "ALL"); combo.blockSignals(False)
        if rows: self.table.selectRow(0)

    def _clusters(self, rows):
        self.clusters.clear(); root=QTreeWidgetItem([f"Lecture {self.number:02d}"]); self.clusters.addTopLevelItem(root)
        labels=(("SHARED","Shared weekly resources"),("A","Tuesday Part A resources"),("B","Friday Part B resources"),("SUPPLEMENTARY","Supplementary Part C"),("UNCLASSIFIED","Unclassified resources"))
        for key,label in labels:
            QTreeWidgetItem(root,[f"{label} ({sum(r['assignment']==key for r in rows)})"])
        root.setExpanded(True)

    def select_row(self, current, _previous):
        source=self.proxy.mapToSource(current); self.current=self.model.row(source.row())
        if not self.current: return
        d=self.service.detail(self.current["id"]); r=d["resource"]
        fields=("resource_id","title","source_type","source_layer","source_locator","file_type","content_sha256","assignment","intended_use","source_quality","factual_currency_status","verification_status","copyright_status","classification_confidence","linked_note_count","linked_slide_count","instructor_status","extraction_status")
        self.metadata.setPlainText("\n".join(f"{k}: {self.current.get(k,r.get(k,''))}" for k in fields)+f"\n\nLinked notes: {len(d['notes'])}\nLinked slides: {len(d['slides'])}\nClassification history: {len(d['history'])}")
        for combo,value in ((self.assignment,r["assignment"]),(self.classification,r["classification"]),(self.centrality,r["centrality"])):
            i=combo.findText(value); combo.setCurrentIndex(max(i,0))
        self.comment.setPlainText(r["instructor_comment"])

    def save(self):
        if not self.current: return
        try:
            self.service.assign(self.number,self.current["id"],self.assignment.currentText(),self.classification.currentText(),self.centrality.currentText(),self.comment.toPlainText())
            self.load_lecture(self.number)
        except Exception as exc: QMessageBox.warning(self,"Validation error",str(exc))
