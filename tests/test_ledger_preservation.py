from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from course_ledger import read_blocks, verify_blocks


class LedgerPreservationTests(unittest.TestCase):
    def test_existing_nine_block_chain_and_first_eight_history_are_preserved(self) -> None:
        ledger_path = PROJECT_ROOT / "course_ledger" / "ledger.jsonl"
        if not ledger_path.is_file():
            self.skipTest(
                "course_ledger/ledger.jsonl is intentionally excluded from "
                "sanitised public packages (see reports/public_exclude_manifest.txt); "
                "ledger chain integrity is authoritative only in the private repository."
            )
        before = ledger_path.read_bytes()
        with ledger_path.open("r", encoding="utf-8") as handle:
            blocks = read_blocks(handle)
        self.assertEqual(len(blocks), 9)
        self.assertEqual(verify_blocks(blocks), [])
        self.assertEqual(
            blocks[7]["content_hash"],
            "5984a485f8047f9713cca4a64d07bd9809fc135d8212e4cf85851dd011a5c25f",
        )
        self.assertEqual(blocks[8]["block_number"], 9)
        self.assertEqual(blocks[8]["block_type"], "GOVERNANCE_CORRECTION")
        self.assertEqual(blocks[8]["approved_by"], "Instructor")
        self.assertEqual(blocks[8]["approval_status"], "APPROVED")
        self.assertEqual(
            blocks[8]["previous_block_hash"],
            blocks[7]["content_hash"],
        )
        self.assertEqual(ledger_path.read_bytes(), before)
        first_eight_blocks = b"".join(before.splitlines(keepends=True)[:8])
        self.assertEqual(
            hashlib.sha256(first_eight_blocks).hexdigest(),
            "73c036692abd80b23b118f9b852dcdbe4e0a0e08803359ba913e96886fbcdeff",
        )


if __name__ == "__main__":
    unittest.main()
