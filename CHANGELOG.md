# Changelog

## 0.1.3 · 2026-11-04
- Directory listing links in `plugin.json`: homepage, repository, documentation (`docs/GUIDE.md`), support (issues), privacy policy (`PRIVACY.md`, new), terms (`LICENSE`).
- The secret gate's self-test uses a neutral variable name (`$EXAMPLE_TOKEN`) as its example of an allowed reference, instead of the name of a real credential that the plugin never reads.

## 0.1.2 · 2026-11-04
- `audit_repo.py` reads every `requirements*.txt` in the repo, so a second environment (for example a Docker worker's `worker/requirements.txt`) is recognised.
- Import names map to package names even when the package is not installed (`docx` → `python-docx`, `fpdf` → `fpdf2`, `webview` → `pywebview`), and namespace packages map by module (`google.oauth2` → `google-auth`, not `protobuf`). `pin_requirements.py` now uses the same mapping.
- Plugin icon and README logo.

## 0.1.1 · 2026-11-04
- The test that keeps the secret gate and `audit_repo.py` on identical patterns now compares the compiled patterns; it used to compare truncated text and missed a change after an escaped quote (PR #3).
- User guide: `docs/GUIDE.md`.
- Internal working documents (status notes, decision records) moved out of this public repo.

## 0.1.0 · 2026-11-04
- First version: kickoff and audit modes, `audit_repo.py`, `pin_requirements.py`, `install_secret_gate.py` with tests (PR #1).
- MIT license; repository public (PR #2).
