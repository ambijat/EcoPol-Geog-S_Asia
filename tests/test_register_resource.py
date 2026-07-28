from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from register_resource import RegistrationError, read_registry, register_resource


class RegisterResourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.registry = self.root / "resource_registry" / "resources.jsonl"
        self.first = self.root / "first.txt"
        self.first.write_text("first source\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_resource_id_assignment(self) -> None:
        first_record = register_resource(self.first, {}, self.registry)
        second = self.root / "second.txt"
        second.write_text("second source\n", encoding="utf-8")
        second_record = register_resource(second, {}, self.registry)
        self.assertEqual(first_record["resource_id"], "IS529N-RES-0001")
        self.assertEqual(second_record["resource_id"], "IS529N-RES-0002")
        self.assertEqual(first_record["local_path"], "first.txt")

    def test_checksum_duplicate_detection(self) -> None:
        register_resource(self.first, {}, self.registry)
        duplicate = self.root / "duplicate.txt"
        duplicate.write_bytes(self.first.read_bytes())
        with self.assertRaisesRegex(RegistrationError, "identical checksum"):
            register_resource(duplicate, {}, self.registry)
        self.assertEqual(len(read_registry(self.registry)), 1)

    def test_dry_run_does_not_create_registry_or_lock(self) -> None:
        record = register_resource(self.first, {}, self.registry, dry_run=True)
        self.assertEqual(record["resource_id"], "IS529N-RES-0001")
        self.assertFalse(self.registry.exists())
        self.assertFalse((self.registry.parent / ".resources.lock").exists())

    def test_invalid_metadata_is_rejected(self) -> None:
        with self.assertRaisesRegex(RegistrationError, "invalid metadata"):
            register_resource(
                self.first,
                {"publication_date": "20 July 2026"},
                self.registry,
            )
        self.assertFalse(self.registry.exists())

    def test_atomic_registry_append(self) -> None:
        self.registry.parent.mkdir(parents=True)
        self.registry.write_text("", encoding="utf-8")
        original_inode = self.registry.stat().st_ino
        register_resource(self.first, {}, self.registry)
        self.assertNotEqual(self.registry.stat().st_ino, original_inode)
        payload = [json.loads(line) for line in self.registry.read_text().splitlines()]
        self.assertEqual(len(payload), 1)
        self.assertFalse(list(self.registry.parent.glob(".resources.jsonl.*")))


if __name__ == "__main__":
    unittest.main()
