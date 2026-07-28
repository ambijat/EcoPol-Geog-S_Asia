from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog,QHBoxLayout,QLabel,QListWidget,QPushButton,QSlider,QSplitter,QTextBrowser,QVBoxLayout,QWidget


class DeliverablePreviewDialog(QDialog):
    def __init__(self,project_root:Path,bundle:dict,parent=None):
        super().__init__(parent); self.project_root=project_root; self.bundle=bundle; self.paths=[]; self.zoom=100
        self.setWindowTitle(f'Deliverable preview · {bundle["version"]} {bundle["status"]}'); self.resize(1250,820)
        layout=QVBoxLayout(self); header=QLabel("Thumbnail preview — rendered PDF evidence, not pixel-perfect PowerPoint editing"); header.setObjectName("viewSubtitle");layout.addWidget(header)
        controls=QHBoxLayout(); self.previous=QPushButton("Previous");self.next=QPushButton("Next");self.slider=QSlider(Qt.Orientation.Horizontal);self.slider.setRange(50,200);self.slider.setValue(100);self.zoom_label=QLabel("100%");controls.addWidget(self.previous);controls.addWidget(self.next);controls.addWidget(QLabel("Zoom"));controls.addWidget(self.slider,1);controls.addWidget(self.zoom_label);layout.addLayout(controls)
        split=QSplitter();self.list=QListWidget();self.image=QLabel("No thumbnails generated");self.image.setAlignment(Qt.AlignmentFlag.AlignCenter);self.image.setMinimumWidth(650);self.metadata=QTextBrowser();split.addWidget(self.list);split.addWidget(self.image);split.addWidget(self.metadata);split.setSizes([220,720,340]);layout.addWidget(split,1)
        directory=bundle.get("thumbnail_directory","")
        if directory:
            self.paths=sorted((project_root/directory).glob("slide-*.png"))
            for i,path in enumerate(self.paths,1):self.list.addItem(f"Page {i} · {path.name}")
        sidecar={};validation={}
        if bundle.get("sidecar_path") and (project_root/bundle["sidecar_path"]).is_file():sidecar=json.loads((project_root/bundle["sidecar_path"]).read_text())
        if bundle.get("validation_report"):validation=json.loads(bundle["validation_report"])
        self.slide_metadata=sidecar.get("slides",[]);self.validation=validation.get("findings",[])
        self.list.currentRowChanged.connect(self.show_page);self.previous.clicked.connect(lambda:self.list.setCurrentRow(max(0,self.list.currentRow()-1)));self.next.clicked.connect(lambda:self.list.setCurrentRow(min(len(self.paths)-1,self.list.currentRow()+1)));self.slider.valueChanged.connect(self.set_zoom)
        if self.paths:self.list.setCurrentRow(0)

    def set_zoom(self,value:int):self.zoom=value;self.zoom_label.setText(f"{value}%");self.show_page(self.list.currentRow())

    def show_page(self,row:int):
        if not 0<=row<len(self.paths):return
        pix=QPixmap(str(self.paths[row]));size=pix.size()*self.zoom/100;self.image.setPixmap(pix.scaled(size,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        plan_index=row-1
        if 0<=plan_index<len(self.slide_metadata):
            item=self.slide_metadata[plan_index];sid=item.get("slide_id","");findings=[f for f in self.validation if f.get("slide_id")==sid]
            lines=[f'slide_id: {sid}',f'purpose: {item.get("purpose","")}',f'notes: {item.get("note_ids",[])}',f'resources: {item.get("resource_ids",[])}',f'historical evidence: {item.get("historical_slide_ids",[])}',f'verification: {item.get("verification_status","")}',f'approval: {item.get("approval_status","")}',f'deck decision: {self.bundle.get("deck_decision","")}',"","Validation warnings:"]
            lines.extend(f'- {finding["code"]}: {finding["message"]}' for finding in findings)
            self.metadata.setPlainText("\n".join(lines))
        else:self.metadata.setPlainText("Generated title page · instructor review required")
