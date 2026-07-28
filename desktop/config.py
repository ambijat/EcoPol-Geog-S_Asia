from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from course_artifacts.config import CourseArtifactConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STYLE_SHEET = Path(__file__).resolve().parent / "resources" / "styles" / "application.qss"
WATERMARK = PROJECT_ROOT / "gui" / "static" / "images" / "south_asia_watermark.svg"


@dataclass(frozen=True)
class DesktopConfig:
    course_artifacts: CourseArtifactConfig = CourseArtifactConfig()
    style_sheet_path: Path = STYLE_SHEET
    watermark_path: Path = WATERMARK

    def resolved(self) -> "DesktopConfig":
        return DesktopConfig(
            course_artifacts=self.course_artifacts.resolved(),
            style_sheet_path=self.style_sheet_path.resolve(),
            watermark_path=self.watermark_path.resolve(),
        )
