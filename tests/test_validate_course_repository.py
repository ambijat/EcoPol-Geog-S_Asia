from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from register_resource import register_resource
from validate_course_repository import REQUIRED_DIRECTORIES, validate_repository


class ValidateRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for directory in REQUIRED_DIRECTORIES:
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        registry = self.root / "resource_registry" / "resources.jsonl"
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text("", encoding="utf-8")
        ledger_dir = self.root / "course_ledger"
        ledger_dir.mkdir()
        shutil.copy2(PROJECT_ROOT / "course_ledger" / "ledger.jsonl", ledger_dir / "ledger.jsonl")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_repository_validation_accepts_controlled_empty_scaffold(self) -> None:
        result = validate_repository(self.root)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["summary"]["ledger_block_count"], 10)
        self.assertEqual(
            result["summary"]["ledger_chain_tip"],
            "b400eee7a9895a1b70ffc70d78c8877ce62b4c80fd504320f0cb09127cdedad3",
        )
        self.assertEqual(result["summary"]["resource_record_count"], 0)

    def test_original_generated_separation_violation_is_rejected(self) -> None:
        generated = self.root / "course" / "modules" / "source.txt"
        generated.write_text("incorrectly placed original\n", encoding="utf-8")
        register_resource(
            generated,
            {"source_class": "HISTORICAL_RESOURCE"},
            self.root / "resource_registry" / "resources.jsonl",
        )
        result = validate_repository(self.root)
        self.assertFalse(result["valid"])
        self.assertTrue(any("original source class" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
