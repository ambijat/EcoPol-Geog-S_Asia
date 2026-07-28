# Qt Phase 1 Acceptance

## Automated smoke test

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m qt_gui.app --smoke-test
```

Expected evidence includes `status: LAUNCHED`, PySide6/Qt versions, 15 lecture cards, and disabled AI, Git writes, and canonical-ledger writes.

## Instructor walkthrough

1. Launch `.venv/bin/python -m qt_gui.app`.
2. Confirm the full course title, semester, and Tuesday/Friday schedule.
3. Confirm the dashboard contains 15 weekly cards with paired titles.
4. Open Lecture 1 and inspect Tuesday Part A and Friday Part B together.
5. Open **Lecture Titles** and inspect 15 rows, confirmation states, and source evidence.
6. Use **Reload registries** to validate without changing the database.
7. Use **Preview changes** and apply only selected non-conflicting proposals.
8. Confirm that instructor-confirmed conflicts remain protected.
9. Open **Governance and Git Readiness** and verify the read-only controls and nine-block ledger.
10. Confirm the browser cockpit still responds at its existing local URL.

Phase 2 destinations are visibly marked as placeholders, not represented as complete.
