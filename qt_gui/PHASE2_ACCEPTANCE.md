# Qt Phase 2 Instructor Acceptance

Status: local instructor acceptance only. This sequence does not approve a lecture, generate a final deck, or append a canonical ledger event.

Before starting, record the checksums of the selected historical source, `SEMESTER2026_Course_Governance_Preamble.md`, `course_ledger/ledger.jsonl`, and `resource_registry/resources.jsonl`.

1. Launch the cockpit with `scripts/run_qt_cockpit.sh`.
2. Open Lecture 1 from Semester Dashboard.
3. Select **Open Resources**.
4. Select one historical resource, assign it to Part A, add an instructor comment, and save.
5. Open **Historical Decks**.
6. Select one Lecture 1A candidate and choose **Inspect selected source read-only**.
7. Select one extracted slide/page, choose `REVISE`, supply an instructor reason, and save.
8. Open **Revised Notes**.
9. Select one of the six seeded headings and complete it using instructor-supplied material.
10. Link the note to the selected resource and historical slide/page, then save it as a working note.
11. Open **Slide Plan**.
12. Select the corresponding provisional slide and link the note, resource, and historical slide/page.
13. Inspect the linked evidence in each workspace and confirm the chain `Resource ↔ Historical slide ↔ Revised note ↔ Slide-plan entry`.
14. Recalculate the historical source checksum and confirm it matches the starting checksum.
15. Confirm the canonical ledger checksum and nine-block count are unchanged and that no canonical ledger event was created.

Cancellation check: make an unsaved form change, navigate away or close without pressing its save button, reopen the record, and confirm the database value did not change.

Expected boundaries: no AI or network call, no absolute path shown, no original copied or modified, derivatives remain below `qt_gui/local_state/historical_derivatives/`, and no slide or lecture is marked approved.
