# repo-kickoff

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

In audit mode, one of two sessions without the skill sampled the README's 29 `file:line` references and missed the one stale reference; with the skill, both checked all 29 and caught it. Method and numbers: [docs/decisions/0003-measured-before-and-after.md](docs/decisions/0003-measured-before-and-after.md).

**Full documentation:** [docs/GUIDE.md](docs/GUIDE.md): how each step works, the scripts, the secret gate, installing on other computers, troubleshooting.

## Requirements

- Python **3.11+** (the scripts use `tomllib`); tested on 3.13.9. Standard library only, nothing to `pip install`.
- git. GitHub CLI `gh` for the GitHub step and for fetching `.gitignore` templates (optional).

## Install

As a plugin:

```
/plugin marketplace add Sarpes/repo-kickoff
/plugin install repo-kickoff@repo-kickoff
```

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
| `docs/decisions/` | Why things are the way they are, including rejected alternatives |
| `docs/HANDOVER_*.md` | Current status and next steps |

## License

[MIT](LICENSE) © 2026 Sarp Esenyel.
