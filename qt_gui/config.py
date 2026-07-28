from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = PROJECT_ROOT / "gui" / "database" / "is529n_cockpit.sqlite3"
WATERMARK = PROJECT_ROOT / "gui" / "static" / "images" / "south_asia_watermark.svg"
STYLE_SHEET = Path(__file__).resolve().parent / "resources" / "styles" / "application.qss"

COURSE_TITLE = "Economic and Political Geography of South Asia"
COURSE_SUBTITLE = "IS529N Semester 2026"
COURSE_SCHEDULE = "Tuesday and Friday, 9:00 am–11:00 am"
WATERMARK_DISCLAIMER = "Decorative geographical motif; not for boundary interpretation."


@dataclass(frozen=True)
class AppConfig:
    project_root: Path = PROJECT_ROOT
    database_path: Path = DEFAULT_DATABASE
    watermark_path: Path = WATERMARK
    style_sheet_path: Path = STYLE_SHEET
    historical_repository_path: Path | None = None
    derivative_root: Path | None = None

    def resolved(self) -> "AppConfig":
        historical = self.historical_repository_path or _historical_repository(self.project_root)
        return AppConfig(
            project_root=self.project_root.resolve(),
            database_path=self.database_path.resolve(),
            watermark_path=self.watermark_path.resolve(),
            style_sheet_path=self.style_sheet_path.resolve(),
            historical_repository_path=historical.resolve() if historical else None,
            derivative_root=(self.derivative_root or self.project_root / "qt_gui/local_state/historical_derivatives").resolve(),
        )


def _historical_repository(project_root: Path) -> Path | None:
    configured = os.environ.get("IS529N_HISTORICAL_RESOURCE_REPOSITORY")
    if configured:
        return Path(configured)
    local = project_root / "config/public_projection_paths.local.json"
    if local.is_file():
        payload = json.loads(local.read_text(encoding="utf-8"))
        for item in payload.get("redactions", []):
            if item.get("category") == "HISTORICAL_RESOURCE_REPOSITORY":
                return Path(item["source"])
    return None
