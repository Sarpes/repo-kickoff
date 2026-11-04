# repo-kickoff · User guide

repo-kickoff is a **skill** for [Claude Code](https://code.claude.com): a set of instructions plus small scripts that Claude loads only when a task needs them. It does two jobs:

| Mode | Use it when | Changes files? |
|---|---|---|
| **Kickoff** | starting a new project or repository | yes: creates the repo and its setup files |
| **Audit** | checking an existing repo's README, requirements and `.gitignore` against its code | no: read-only, produces a report |

It is written for Python projects; the git, `.gitignore`, secret-gate and README parts work for any language.

---

## 1. Why it exists

Measured in fresh Claude Code sessions (three runs per arm for kickoff, two for audit), agents without the skill wrote good code but skipped the parts that make a repository reproducible and safe:

| Criterion | Without the skill | With it |
|---|---|---|
| Dependencies pinned to the versions the tests ran with | 0 of 3 runs | 3 of 3 |
| Python version stated | 1 of 3 | 3 of 3 |
| Secret check that exists as code, not as "I scanned it" | 0 of 3 | 3 of 3 |
| `main` branch exists before the first work branch | 2 of 3 | 3 of 3 |
| Audit: stale `file:line` reference in a README caught | 1 of 2 | 2 of 2 |

The skill keeps the judgment in text and puts every repeatable check in a tested script, so the result does not depend on how carefully a session happens to work.

---

## 2. How Claude picks it up

You do not call it by name. Claude Code shows Claude a one-line description of every installed skill (~106 tokens for this one) and loads the full text (~950 tokens) only when a request matches, for example:

- "new project", "set up the repo", "start a repository for …"
- "audit this repo", "does the README match the code", "check the requirements / .gitignore"
- Turkish: "yeni proje", "repo kur", "README yaz", "repoyu denetle"

It is not meant for routine commits in a repository that is already set up.

---

## 3. Kickoff mode, step by step

Claude first confirms the project's **name and folder** with you, then follows this order. Each step exists because a measured run got it wrong without it.

| # | Step | What happens | Why |
|---|---|---|---|
| 1 | `main` before any branch | `git init -b main`, an empty first commit on `main` with a message body, then a work branch `chore/scaffold` | A branch opened before the first commit leaves no `main`; the first pull request then has no target. |
| 2 | `.gitignore` | Fetched from GitHub's official template (`gh api /gitignore/templates/Python`), plus a commented project block: `.env`, `.env.*`, `!.env.example`, data/output folders, local databases | Hand-written ignore files matched the official template only 4–9 %. |
| 3 | Code and tests | In a virtual environment; one real sample of each external input is fetched first and kept in `tests/fixtures/` (or a git-ignored `scratch/`) inside the project | Parsers written against real data, not guesses; no stray folders. |
| 4 | Pinned dependencies | `pin_requirements.py` writes `requirements.txt` (exact `==` versions), `requirements-dev.txt` and `.python-version` from the interpreter the tests passed in | An application should record what it ran with; ranges (`>=`) are for libraries. |
| 5 | Secret gate | `install_secret_gate.py` proves the gate on a throwaway repo, then installs it as a git pre-commit hook | "I checked for secrets" is a promise; a hook is a check that runs on every commit. |
| 6 | README | What · Why · Requirements (Python version, services, environment variables) · Install · Run · Test · Layout · Decisions · Status | A reader can install and run the project from the README alone. |
| 7 | Gate before the first push | `audit_repo.py` must report 0 high and 0 medium findings; every `verify` line is opened and checked | Catches a missing dependency or a stale README before anything is public. |
| 8 | GitHub | `gh repo create <owner>/<name> --private`, push `main`, push the branch, open a pull request | Work reaches `main` through a reviewed pull request. If `gh` is not available, Claude lists the commands instead. |

---

## 4. Audit mode

1. **Run the script first.** `audit_repo.py <repo>` checks, in seconds, what every manual audit would otherwise re-implement (see §5).
2. **Check every `verify` line.** The script finds README references such as `src/app.py:120-140` that point inside the file; Claude opens each one and compares the lines with what the README says about them. It never samples: in testing, one stale reference among 29 correct ones was the real defect, and sampling missed it.
3. **Judgment checks** a script cannot make:
   - Does the README's install → run path work from a clean clone, and does it reproduce the README's numbers?
   - After running the main entry point or the tests, is `git status` clean? (Generated output must be ignored.)
   - Is every environment variable the code reads documented, with its default?
   - Does every behaviour the README claims have code behind it?
4. **Report** findings by severity, each with `file:line` or command output, plus what was not checked. Nothing is changed.

---

## 5. The scripts

All scripts are in `skills/repo-kickoff/scripts/`, use only Python's standard library and need Python 3.11+.

### `audit_repo.py <repo> [--json]`
Read-only. Exit code 1 if any **high** or **medium** finding exists, else 0.

| Check | Finds |
|---|---|
| REQ | Third-party imports (parsed from the code, not guessed) missing from every `requirements*.txt` in the repo (a container's `worker/requirements.txt` counts too) and `pyproject.toml`; listed packages never imported; unpinned versions (info); no stated Python version. Import names are mapped to package names even when the package is not installed (`docx` → `python-docx`, `google.oauth2` → `google-auth`). |
| DOC | README references to files that are not in the repo; `file:LINE` references beyond the end of the file; all in-range references as `verify` items |
| IGN | Files tracked although `.gitignore` ignores them; tracked files named like secrets (`.env`, `secrets.toml`, `*_secrets.bat`, `client_secret*.json`, `credentials.json`, `.pem`, `.key`, …); lines that look like secrets (GitHub/Anthropic/AWS keys, private keys, `password = "…"`); tracked files over 5 MB |

Severities: `high`, `medium` (fix before pushing), `verify` (open and compare by hand), `low`, `info` (often a deliberate choice: check the repo says so).

### `pin_requirements.py <repo> [--write]`
Run it **with the project's own interpreter** (the virtual environment the tests passed in). Scans every Python file git would track, splits imports into runtime and development (files under `tests/`, `test_*.py`, `conftest.py`), looks up the installed version of each and prints, or with `--write` writes, `requirements.txt`, `requirements-dev.txt` and `.python-version`. Exit code 1 if an imported package is not installed in that interpreter.

### `install_secret_gate.py <repo>`
Builds a throwaway repo, installs the gate there, and checks that a commit with a fake token is **refused** and a clean commit **accepted**. Only then does it install into your repo:

- `.githooks/pre-commit` and `.githooks/secret_gate.py`
- `git config core.hooksPath .githooks`
- `.gitattributes` line `.githooks/* text eol=lf`, so a Windows checkout does not break the hook

Commit `.githooks/` and `.gitattributes`. After cloning the repo anywhere else, run `git config core.hooksPath .githooks` once.

### Tests
`test_audit_repo.py` and `test_secret_gate.py` build throwaway repositories with planted defects and check that each is caught and that a clean variant raises nothing. `test_secret_gate.py` also checks that the gate and `audit_repo.py` use identical secret patterns.

---

## 6. The secret gate in daily use

- **What it blocks:** a commit whose staged files are named like secret files or contain lines that look like credentials. The value itself is never printed.
- **What it allows:** references such as `os.environ["DB_PASSWORD"]`, `"$TOKEN"`, `%TOKEN%`; files ending in `.example`, `.sample`, `.template`.
- **A deliberate exception** (for example a fake value in a test): end that line with `secret-gate: allow`.
- **Python on Windows:** the hook does not trust the `python3` command, because the Windows Store placeholder answers to it without running anything. It asks each candidate (`python3`, `python`, `py`) to print a marker and uses the first that does. If none works, the commit is refused rather than let through.
- **Do not bypass it** with `git commit --no-verify`: fix the finding, or mark a genuine false positive as above.

---

## 7. Installing on another computer

### Requirements
- Claude Code (one-command install needs 2.1.292 or later)
- git; Python 3.11 or later on `PATH` as `python` (on Windows also check `python --version` prints a real version)
- Optional: GitHub CLI `gh`, signed in (`gh auth login`), for fetching `.gitignore` templates and creating repositories

### Option A · As a plugin (recommended)
In a terminal:

```
claude plugin install repo-kickoff --marketplace Sarpes/repo-kickoff
```

or in two steps, which also works on older versions:

```
claude plugin marketplace add Sarpes/repo-kickoff
claude plugin install repo-kickoff@repo-kickoff
```

Inside a Claude Code session the same works as `/plugin install repo-kickoff --marketplace Sarpes/repo-kickoff`. Check it with `claude plugin list` (shows `repo-kickoff@repo-kickoff`, enabled) and `claude plugin details repo-kickoff@repo-kickoff`. New sessions pick it up automatically.

### Option B · Several machines: one setup script
Writing the marketplace into `settings.json` alone did not install the plugin in testing (2026-11-04), so put the verified commands in your machine-setup script instead. PowerShell:

```powershell
claude plugin install repo-kickoff --marketplace Sarpes/repo-kickoff
python --version                      # must print a real version, not the Store placeholder
gh auth status                        # optional, for templates and repo creation
```

The same lines work in bash on macOS and Linux.

### Option C · As a personal skill, without the plugin system
Copy the folder `skills/repo-kickoff/` from this repository to `~/.claude/skills/repo-kickoff/`. This version does not update itself; copy again for a new release.

### Updating and removing
- Update: `claude plugin update repo-kickoff@repo-kickoff`. A new version is offered only when the version number in `.claude-plugin/plugin.json` changes (see §9).
- Remove: `claude plugin uninstall repo-kickoff@repo-kickoff`.

---

## 8. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Python bulunamadı` / "Python was not found" from a script or the hook | `python3` or `python` resolves to the Windows Store placeholder. Install Python and make sure `python --version` prints a version. |
| Commit refused: `no working Python found - commit refused (fail-closed)` | Same cause; the gate refuses rather than skip the check. |
| The gate does not run after cloning | Run `git config core.hooksPath .githooks` in the clone. |
| `\r: command not found` from the hook | The hook file was checked out with Windows line endings: make sure `.gitattributes` (`.githooks/* text eol=lf`) is committed, then re-checkout the file. |
| `.gitignore` step falls back to a hand-written file | `gh` is not installed or not signed in; run `gh auth login`. |
| `update` says "already at the latest version" after a fix was merged | The release did not bump `version` in `plugin.json`. |

---

## 9. For maintainers

- **Versions:** bump `version` in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` with every change users should receive, and add a line to `CHANGELOG.md`. Without a bump, `claude plugin update` keeps users on the old copy.
- **Checks before a release:** both test files print ALL PASS; `claude plugin validate .` passes; `python skills/repo-kickoff/scripts/audit_repo.py .` reports 0 high and 0 medium.
- **Changing `SKILL.md`:** re-run the before/after scenarios (fresh sessions with and without the skill, scored on the criteria in §1); the skill is kept only for behaviour it measurably changes.
- **Secret patterns** live in two places (`install_secret_gate.py`, `audit_repo.py`); the test fails if they differ.
