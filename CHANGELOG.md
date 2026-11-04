# Changelog

## 0.1.5 · 2026-11-04
- Secret gate and audit now also refuse unquoted env-style secrets (`SOME_API_KEY=` followed by 16 or more characters; names ending in `API_KEY`, `TOKEN`, `SECRET` or `PASSWORD`, upper case, optional `export`) and any file whose name ends in `.env` (for example `UsersName.env`), not only an exact `.env`. Before, both were accepted.
- Empty templates (`SOME_API_KEY=`) and code that reads the environment stay accepted.
- Tests cover both cases and the two must-accept cases; the gate/audit identity test now includes the new rule.

## 0.1.4 · 2026-11-04
- The pre-commit hook names each Python candidate (`python3`, `python`, `py`) on its own line instead of looping over a variable, so every command it can run is readable in the file. Behaviour is unchanged: the first candidate that prints the marker runs the gate; if none does, the commit is refused.
- `plugin.json` sets `icon`, so the directory listing uses the plugin's icon.
- Icon (512 × 512) and README logo (688 × 384) re-encoded smaller.
- The guide's example of an allowed reference uses a neutral name; this repo's `.gitignore` drops the web links from the template's comments.

## 0.1.3 · 2026-11-04
- Directory listing links in `plugin.json`: homepage, repository, documentation (`docs/GUIDE.md`), support (issues), privacy policy (`PRIVACY.md`, new), terms (`LICENSE`).
- The secret gate's self-test uses a neutral variable name (`$EXAMPLE_TOKEN`) as its example of an allowed reference, instead of the name of a real credential that the plugin never reads.
- Description and keywords name what the listing left implicit: the private GitHub repository and the gate that blocks API keys and passwords (keywords `github`, `git`, `api-keys`).

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
