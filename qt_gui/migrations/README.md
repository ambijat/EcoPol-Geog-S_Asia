# Qt Migration Boundary

The Qt application reuses the public-safe, versioned SQLite migrations under `gui/migrations/` through `qt_gui.database.migrations`. It does not maintain a divergent schema copy.

Future Qt schema changes must be additive shared migrations compatible with the browser reference implementation until browser retirement is approved.
