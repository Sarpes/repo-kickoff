# repo-kickoff

![repo-kickoff](assets/logo.png)

A Claude Code skill with two modes:

- **Kickoff**: start a new repository whose setup can be reproduced and checked.
- **Audit**: check an existing repository's README, requirements and `.gitignore` against its code, without changing anything.

## Why

Measured on a small Python project ("kur-takip": TCMB daily exchange rates → SQLite), three fresh Claude Code sessions each. Without the skill, agents wrote good code and tests but:

| Criterion | Without skill | With skill |
|---|---|---|
| Dependencies pinned to the versions the tests ran with | 0/3 | 3/3 |
| Python version stated | 1/3 | 3/3 |
| Secret gate that exists as code (not "I scanned") | 0/3 | 3/3 |
| `main` exists before the first branch | 2/3 | 3/3 |
| Audit findings (high + medium) | 1 per repo | 0 |

In audit mode, one of two sessions without the skill sampled the README's 29 `file:line` references and missed the one stale reference; with the skill, both checked all 29 and caught it. Details: [docs/GUIDE.md](docs/GUIDE.md).

**Full documentation:** [docs/GUIDE.md](docs/GUIDE.md): how each step works, the scripts, the secret gate, installing on other computers, troubleshooting.

## Requirements

- Python **3.11+** (the scripts use `tomllib`); tested on 3.13.9. Standard library only, nothing to `pip install`. On macOS and Linux the command is often `python3` rather than `python`; on Windows, `python --version` must print a real version, not open the Microsoft Store.
- git. GitHub CLI `gh` for the GitHub step and for fetching `.gitignore` templates (optional).
- Built for Claude Code: the steps need a local git repository and Python. On claude.ai or in Cowork, without a local repository, the skill can only explain the steps.

## What it runs, fetches and sends

Everything below happens on your machine, with your own tools and credentials, and only when you ask for a kickoff or an audit.

| | What | Where |
|---|---|---|
| **Runs** | `git` (init, commit, branch, push) and the Python scripts in `skills/repo-kickoff/scripts/`. The scripts use only Python's standard library, call no program but `git`, and contain no network code. | your machine |
| **Reads** | The files of the repository you point it at, and (for `pin_requirements.py`) the installed-package list of the Python you run it with. It does not read your environment variables or credential files; it looks for credential-shaped file names and lines only to warn about them, and prints file names and line numbers, never values. | your machine |
| **Fetches** | GitHub's official `.gitignore` template, through `gh api /gitignore/templates/<Language>` with your own `gh` login (kickoff step 2). | GitHub |
| **Sends** | Only in kickoff step 8, and only when you go ahead: `gh repo create` makes a **private** repository under the owner you choose, and `git push` uploads your project to it, with your own credentials. Audit mode sends nothing. | GitHub |
| **Installs** | Into the new repository only: `.githooks/pre-commit` and `.githooks/secret_gate.py`, `git config core.hooksPath .githooks`, one `.gitattributes` line, and `.githooks/pre-commit` staged as executable so the hook also runs on macOS and Linux. The gate runs locally on each commit and reads only the staged files. | the repository |

No telemetry, no other services, nothing stored outside the repository you work on. Privacy policy: [PRIVACY.md](PRIVACY.md).

## Install

As a plugin, from a terminal:

```
claude plugin marketplace add Sarpes/repo-kickoff
claude plugin install repo-kickoff@repo-kickoff
```

Start a new Claude Code session afterwards. Inside a session, `/plugin` opens the plugin manager, where you can add the marketplace `Sarpes/repo-kickoff` and install from it.

Or as a personal skill: copy `skills/repo-kickoff/` to `~/.claude/skills/repo-kickoff/`.

## Use

Ask Claude Code to start a project or to check a repo; the skill triggers on phrases like "new project", "set up the repo", "audit this repo", "yeni proje", "repoyu denetle". The scripts also run on their own:

| Script | What it does |
|---|---|
| `skills/repo-kickoff/scripts/audit_repo.py <repo>` | Read-only audit: imports vs requirements, Python version, README `file:line` references, ignored-but-tracked files, secrets. Exit 1 on high/medium findings. |
| `skills/repo-kickoff/scripts/pin_requirements.py <repo> [--write]` | Run with the project's venv interpreter: writes `requirements.txt` / `requirements-dev.txt` with `==` pins and `.python-version`. |
| `skills/repo-kickoff/scripts/install_secret_gate.py <repo>` | Proves the pre-commit secret gate on a throwaway repo, then installs it (`.githooks/`, `core.hooksPath`, LF line endings via `.gitattributes`). |

## Test

```
python skills/repo-kickoff/scripts/test_audit_repo.py
python skills/repo-kickoff/scripts/test_secret_gate.py
```

Both build throwaway repos with planted defects and check each one is caught, and that a clean variant raises nothing. `test_secret_gate.py` also checks that the gate and `audit_repo.py` use identical secret patterns.

## Layout

| Path | What |
|---|---|
| `skills/repo-kickoff/SKILL.md` | The skill: order of steps and the judgment calls |
| `skills/repo-kickoff/scripts/` | Deterministic steps and their tests |
| `.claude-plugin/` | Plugin and marketplace manifests |
| `.githooks/` | This repo's own secret gate, installed by its own script |
| `docs/GUIDE.md` | User guide |
| `CHANGELOG.md` | What changed in each version |

## License

[MIT](LICENSE) © 2026 Sarp Esenyel.
