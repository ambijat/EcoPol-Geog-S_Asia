from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from generate_public_file_manifests import ManifestError, generate


class PublicFileManifestTests(unittest.TestCase):
    def test_repository_manifests_are_current_and_safe(self) -> None:
        result = generate(PROJECT_ROOT, check=True)
        self.assertGreater(result["candidate_count"], 300)

    def test_machine_path_in_candidate_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            machine_path = str(PurePosixPath("/") / "media" / "private" / "source")
            (root / "docs/public.md").write_text(machine_path, encoding="utf-8")
            with self.assertRaises(ManifestError):
                generate(root, dry_run=True)

    def test_canonical_records_are_not_candidates(self) -> None:
        include = (PROJECT_ROOT / "reports/public_include_manifest.txt").read_text(encoding="utf-8")
        self.assertNotIn("SEMESTER2026_Course_Governance_Preamble.md\n", include)
        self.assertNotIn("course_ledger/ledger.jsonl\n", include)


if __name__ == "__main__":
    unittest.main()
