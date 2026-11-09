# repo-kickoff

A Claude Code skill (plugin) for starting and auditing repositories. Source of truth for `~/.claude/skills/repo-kickoff`, which is a junction to `skills/repo-kickoff/` here: an edit here is live immediately.

This repo is PUBLIC. Internal documents (status handovers, decision records with rejected alternatives) live in the private companion repo `C:\Projects\repo-kickoff-internal` (github.com/Sarpes/repo-kickoff-internal), never here.

## Layout
| Path | What |
|---|---|
| `skills/repo-kickoff/SKILL.md` | Order of steps + judgment calls. Keep it short; deterministic work belongs in scripts. |
| `skills/repo-kickoff/scripts/*.py` | Standard library only, Python 3.11+. Each has a test file. |
| `.claude-plugin/` | `plugin.json` + `marketplace.json`, license MIT. Bump `version` in both on every release, plus `CHANGELOG.md`. |
| `docs/GUIDE.md` | The user guide. |

## Commands
- Tests: `python skills/repo-kickoff/scripts/test_audit_repo.py`, `python skills/repo-kickoff/scripts/test_secret_gate.py`, `python skills/repo-kickoff/scripts/test_scaffold_project.py` and `python skills/repo-kickoff/scripts/test_repo_state.py`. All must print ALL PASS (the scaffold and repo_state tests only use temp dirs; the scaffold test also uses a temp `CLAUDE_REGISTRY`).
- Audit this repo: `python skills/repo-kickoff/scripts/audit_repo.py .` → 0 high, 0 medium.
- After a clone: `git config core.hooksPath .githooks` (the secret gate).

## Never
- Never edit SKILL.md without re-running scenario A (internal decision 0003). The test rig lives outside this repo: `~/.claude/tools/agent-infra/skilltest/` (`run_A.ps1 -Label <x>`, `score_A.py <x>`).
- Never change the secret patterns in only one of `install_secret_gate.py` / `audit_repo.py`; `test_secret_gate.py` fails if they differ.
- Never put a real secret in a test. Planted test values end their line with `secret-gate: allow`.
- Every push is published. Run the secret gate and `audit_repo.py .` before pushing; never commit personal paths, data, status notes or decision records here.
