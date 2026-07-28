from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INCLUDE_MANIFEST = PROJECT_ROOT / "reports" / "public_include_manifest.txt"

AUDIT_README = """# IS529N Sanitized Audit Package

This is a non-authoritative, public-candidate snapshot prepared for external
technical and UX audit.

It excludes machine-local configuration, databases, private ledger authority
records, student and assessment data, credentials, original teaching binaries,
source repositories, caches, logs, and earlier archives.

Checksums in `SANITIZATION_MANIFEST.json` apply only to this explicit audit
package. The desktop cockpit does not hash files during routine scanning or
registration.
"""


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def build(output: Path) -> dict[str, object]:
    relative_paths = [
        Path(line.strip())
        for line in INCLUDE_MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    with tempfile.TemporaryDirectory(prefix="is529n-audit-") as directory:
        package = Path(directory) / "IS529N_SANITIZED_AUDIT"
        package.mkdir()
        for relative in relative_paths:
            source = (PROJECT_ROOT / relative).resolve()
            if not source.is_relative_to(PROJECT_ROOT) or not source.is_file():
                raise ValueError(f"Invalid public manifest entry: {relative}")
            destination = package / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        (package / "README_AUDIT.md").write_text(
            AUDIT_README, encoding="utf-8"
        )
        files = sorted(path for path in package.rglob("*") if path.is_file())
        manifest = {
            "authoritative": False,
            "course": "IS529N — Economic and Political Geography of South Asia",
            "document_type": "SANITIZED_AUDIT_PACKAGE_MANIFEST",
            "routine_cockpit_hashing": False,
            "file_count_before_manifest": len(files),
            "files": [
                {
                    "path": path.relative_to(package).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": digest(path),
                }
                for path in files
            ],
        }
        (package / "SANITIZATION_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".zip.tmp")
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for path in sorted(package.rglob("*")):
                if path.is_file():
                    archive.write(
                        path,
                        Path(package.name) / path.relative_to(package),
                    )
        temporary.replace(output)
    return {"output": str(output), "public_files": len(relative_paths)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports"
        / f"IS529N_SANITIZED_AUDIT_{date.today().isoformat()}.zip",
    )
    arguments = parser.parse_args()
    print(json.dumps(build(arguments.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
