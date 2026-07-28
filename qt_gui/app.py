from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import qVersion
from PySide6.QtWidgets import QApplication

from qt_gui.config import AppConfig, DEFAULT_DATABASE, PROJECT_ROOT, STYLE_SHEET, WATERMARK
from qt_gui.main_window import MainWindow


def create_application(config: AppConfig | None = None, argv: list[str] | None = None):
    app = QApplication.instance() or QApplication(argv or [])
    app.setApplicationName("IS529N Course Production Cockpit")
    app.setOrganizationName("IS529N Semester 2026")
    resolved = (config or AppConfig()).resolved()
    if resolved.style_sheet_path.is_file():
        app.setStyleSheet(resolved.style_sheet_path.read_text(encoding="utf-8"))
    window = MainWindow(resolved)
    return app, window


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the native IS529N Qt cockpit")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--smoke-test", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    config = AppConfig(
        project_root=arguments.project_root,
        database_path=arguments.database,
        watermark_path=WATERMARK,
        style_sheet_path=STYLE_SHEET,
    )
    app, window = create_application(config, [])
    window.show()
    if arguments.smoke_test:
        app.processEvents()
        print(json.dumps({
            "status": "LAUNCHED", "pyside6": pyside_version, "qt": qVersion(),
            "lecture_cards": window.dashboard_view.lecture_card_count,
            "current_screen": window.navigation.currentItem().text(),
            "ai_calls": "DISABLED", "git_writes": "DISABLED",
            "canonical_ledger_writes": "DISABLED",
            "lecture_1a_draft_generation": "ENABLED" if window.deliverables_view.generate_button.isEnabled() else "BLOCKED_BY_EVIDENCE_GATE",
        }, sort_keys=True))
        window.close()
        return 0
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
