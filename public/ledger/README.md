# Public Ledger Projection

The project-local `course_ledger/ledger.jsonl` is the canonical academic ledger. It remains private because its immutable history contains local infrastructure references.

`ledger_public.jsonl` is a redacted public projection. It preserves a limited pedagogical chronology and quotes canonical block numbers, previous-block references, and canonical content hashes as metadata. Those quoted values are provided for reference only.

The projection is explicitly `NON_CANONICAL`. Its records have been transformed, fields have been omitted, and local paths have been replaced or excluded. It therefore cannot independently reconstruct or verify the private canonical hash chain and must never be represented as the authoritative ledger.

`retrospective_events_2026-07-20_PUBLIC.json` applies the same boundary to the source retrospective event set. The manifest under `public/reports/` records source and output checksums. A checksum labelled `PUBLIC_PROJECTION_FILE_SHA256` verifies only the corresponding projection file; it does not confer canonical ledger status.

Regenerate and validate the projections with:

```bash
python3 scripts/generate_public_projection.py --dry-run
python3 scripts/generate_public_projection.py
```

The machine-local redaction mapping remains ignored and is never part of the public projection.
