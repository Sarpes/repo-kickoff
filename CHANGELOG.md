# Changelog

## 0.1.1 · 2026-11-04
- The test that keeps the secret gate and `audit_repo.py` on identical patterns now compares the compiled patterns; it used to compare truncated text and missed a change after an escaped quote (PR #3).
- User guide: `docs/GUIDE.md`.
- Internal working documents (status notes, decision records) moved out of this public repo.

## 0.1.0 · 2026-11-04
- First version: kickoff and audit modes, `audit_repo.py`, `pin_requirements.py`, `install_secret_gate.py` with tests (PR #1).
- MIT license; repository public (PR #2).
