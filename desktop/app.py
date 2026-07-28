from __future__ import annotations

if __name__ == "__main__" and __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
import sys
from pathlib import Path

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import qVersion
from PySide6.QtWidgets import QApplication

from course_artifacts.config import (
    CourseArtifactConfig, DEFAULT_CLASS_CONFIG, DEFAULT_LOCAL_PATHS,
    DEFAULT_RELATIONSHIP_CONFIG,
)
from desktop.config import DesktopConfig, STYLE_SHEET, WATERMARK
from desktop.main_window import MainWindow


def create_application(config: DesktopConfig | None = None, argv: list[str] | None = None):
    app = QApplication.instance() or QApplication(argv or [])
    app.setApplicationName(
        "IS529N Economic and Political Geography of South Asia"
    )
    app.setApplicationDisplayName(
        "IS529N — Economic and Political Geography of South Asia"
    )
    app.setOrganizationName("IS529N Semester 2026")
    resolved = (config or DesktopConfig()).resolved()
    if resolved.style_sheet_path.is_file():
        app.setStyleSheet(resolved.style_sheet_path.read_text(encoding="utf-8"))
    window = MainWindow(resolved)
    return app, window


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch the IS529N course artifact cockpit"
    )
    parser.add_argument("--database", type=Path)
    parser.add_argument("--class-config", type=Path, default=DEFAULT_CLASS_CONFIG)
    parser.add_argument("--relationship-config", type=Path, default=DEFAULT_RELATIONSHIP_CONFIG)
    parser.add_argument("--local-paths", type=Path, default=DEFAULT_LOCAL_PATHS)
    parser.add_argument("--smoke-test", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    course_artifacts = CourseArtifactConfig(
        database_path=arguments.database or CourseArtifactConfig().database_path,
        class_config_path=arguments.class_config,
        relationship_config_path=arguments.relationship_config,
        local_paths_path=arguments.local_paths,
    )
    config = DesktopConfig(course_artifacts, STYLE_SHEET, WATERMARK)
    app, window = create_application(config, [])
    window.show()
    if arguments.smoke_test:
        app.processEvents()
        print(json.dumps({
            "status": "LAUNCHED",
            "title": window.windowTitle(),
            "pyside6": pyside_version,
            "qt": qVersion(),
            "artifact_class_buttons": window.artifact_class_button_count,
            "current_screen": window.navigation.currentItem().text(),
            "browser_sidecar_started": False,
            "ai_network_calls": False,
            "server_required": False,
            "source_repository_writes": False,
            "path_setup_required": window.path_setup_required,
        }, sort_keys=True))
        window.close()
        return 0
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
