"""Capture or inventory the principal local cockpit screens."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "gui_acceptance" / "screenshots"
SCREENS = (
    ("dashboard", "/"),
    ("lecture_titles", "/titles"),
    ("workspace", "/lectures/1"),
    ("resources", "/lectures/1/resources"),
    ("historical_decks", "/lectures/1/decks"),
    ("revised_notes", "/lectures/1/notes"),
    ("slide_plan", "/lectures/1/slide-plan"),
    ("deliverables", "/lectures/1/deliverables"),
    ("class_record", "/lectures/1/class-record"),
    ("governance", "/governance?lecture=1"),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(base_url: str, output: Path, *, record_existing: bool = False) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    browser = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not browser and not record_existing:
        raise RuntimeError("no supported headless browser is available")
    records = []
    for name, route in SCREENS:
        target = output / f"{name}.png"
        if record_existing:
            if not target.is_file():
                raise FileNotFoundError(target)
        else:
            if target.exists():
                raise FileExistsError(f"refusing to overwrite {target}")
            subprocess.run(
                [browser, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                 "--window-size=1440,1100", f"--screenshot={target}", base_url.rstrip("/") + route],
                check=True, capture_output=True,
            )
        records.append({
            "screen": name,
            "route": route,
            "relative_path": target.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256(target),
            "bytes": target.stat().st_size,
        })
    manifest = {
        "evidence_type": "LOCAL_BROWSER_SCREENSHOTS",
        "public_candidate": False,
        "machine_specific_absolute_paths_expected": False,
        "records": records,
    }
    manifest_path = output.parent / "screenshots_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8529")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--record-existing", action="store_true")
    arguments = parser.parse_args()
    result = capture(arguments.base_url, arguments.output.resolve(), record_existing=arguments.record_existing)
    print(f"screenshots recorded: {len(result['records'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
