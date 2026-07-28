# Packaging Assessment

No standalone package is built in Phase 1.

Runtime dependencies are Python, PySide6 6.8.3, SQLite, `python-pptx`, external LibreOffice, and external `pdftoppm`. LibreOffice must not be bundled.

- **PyInstaller:** preferred first experiment because its Qt hooks are mature; verify QtSvg and future QtPdf plugins.
- **Nuitka:** a viable optimized alternative with greater toolchain complexity.
- **Native launcher and `.desktop` entry:** appropriate after executable path and icon approval.

Before packaging, add an approved icon, dependency probes, local-state policy, and reproducible build script. Exclude databases, historical bytes, drafts, canonical governance, instructor notes, student records, and logs.
