# IS 529 N Course Ledger

`ledger.jsonl` is the authoritative project-local hash chain for material course and workflow events. Each line is one canonical JSON block. The chain is governance infrastructure; it is not a cryptocurrency or a public blockchain.

The historical resource repository is strictly read-only. Ledger files, event manifests, verification output, and all other generated artifacts remain inside the active project folder.

## Integrity model

- Block numbers begin at 1 and increase by one.
- The genesis block uses 64 zeroes as `previous_block_hash`.
- Every later block names the preceding block's `content_hash`.
- `content_hash` is SHA-256 over UTF-8 canonical JSON with sorted keys and compact separators, excluding only the `content_hash` field itself.
- Existing blocks are never edited. Corrections are appended as new superseding blocks.
- Retrospective blocks identify both the reconstructed event time and the later recording time.

## Verify

```bash
python3 scripts/course_ledger.py verify
```

## Append

Unapproved event proposals belong under `course_ledger/drafts/`, not in the canonical ledger. The normal lifecycle is:

```text
draft event
→ instructor review
→ explicit approval
→ append to canonical ledger
→ block number and hash assignment
```

Future `DRAFT` events must not normally be appended to `ledger.jsonl`. Existing legacy draft-status blocks remain unchanged as historical evidence and do not establish a precedent.

After explicit instructor approval, prepare the approved JSON event and run:

```bash
python3 scripts/course_ledger.py append path/to/events.json
```

The tool verifies the existing chain before appending, assigns the next block number and previous hash, fills explicit schema defaults, computes the new content hash, locks the ledger during the write, flushes it, and synchronises it to disk.

Do not manually edit `ledger.jsonl`. Do not mark an event `APPROVED` or `SEALED` without the instructor's explicit approval. A draft may be moved out of `course_ledger/drafts/` for canonical append only after that approval is recorded in the event metadata.

No append guard is implemented in the utility yet. Until a separately authorised, tested guard exists, the operator must verify `approval_status: APPROVED` and non-empty `approved_by` before invoking `append`.
