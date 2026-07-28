from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PySide6.QtTest import QTest

from qt_gui.app import create_application
from qt_gui.config import PROJECT_ROOT


DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "qt_gui_acceptance"
SCREENS = (
    ("dashboard", "Semester Dashboard"),
    ("lecture_titles", "Lecture Titles"),
    ("lecture_01_pair", "Lecture Pair Workspace"),
    ("governance", "Governance and Git Readiness"),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(output: Path) -> dict[str, object]:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"acceptance directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    app, window = create_application(argv=[])
    window.resize(1500, 960)
    window.show()
    app.processEvents()
    QTest.qWait(75)
    records = []
    for filename, destination in SCREENS:
        if destination == "Lecture Pair Workspace":
            window.open_lecture(1)
        else:
            window.navigate(destination)
        app.processEvents()
        QTest.qWait(75)
        target = output / f"{filename}.png"
        if not window.grab().save(str(target), "PNG"):
            raise RuntimeError(f"failed to capture {filename}")
        records.append({
            "screen": destination,
            "relative_path": target.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256(target),
            "bytes": target.stat().st_size,
        })
    window.close()
    manifest = {
        "evidence_type": "LOCAL_QT_PHASE1_SCREENSHOTS",
        "public_candidate": False,
        "records": records,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    result = capture(arguments.output.resolve())
    print(f"Qt screenshots captured: {len(result['records'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
