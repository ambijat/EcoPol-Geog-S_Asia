ALTER TABLE scan_candidates ADD COLUMN related_artifact_id INTEGER
    REFERENCES artifacts(id);

ALTER TABLE scan_candidates ADD COLUMN decision_note TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_scan_candidate_related_artifact
    ON scan_candidates(related_artifact_id);
