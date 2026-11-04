# repo-kickoff

A Claude Code skill (plugin) for starting and auditing repositories. Source of truth for `~/.claude/skills/repo-kickoff`, which is a junction to `skills/repo-kickoff/` here: an edit here is live immediately.

## Layout
| Path | What |
|---|---|
| `skills/repo-kickoff/SKILL.md` | Order of steps + judgment calls. Keep it short; deterministic work belongs in scripts. |
| `skills/repo-kickoff/scripts/*.py` | Standard library only, Python 3.11+. Each has a test file. |
| `.claude-plugin/` | `plugin.json` + `marketplace.json`. License MIT (decision 0004). |
| `docs/decisions/` | Decision records with rejected alternatives. |
| `docs/HANDOVER_<date>.md` | Status. Newest date wins. |

## Commands
- Tests: `python skills/repo-kickoff/scripts/test_audit_repo.py` and `python skills/repo-kickoff/scripts/test_secret_gate.py`. Both must print ALL PASS.
- Audit this repo: `python skills/repo-kickoff/scripts/audit_repo.py .` → 0 high, 0 medium.
- After a clone: `git config core.hooksPath .githooks` (the secret gate).

## Never
- Never edit SKILL.md without re-running scenario A (decision 0003). The test rig lives outside this repo: `~/.claude/tools/agent-infra/skilltest/` (`run_A.ps1 -Label <x>`, `score_A.py <x>`).
- Never change the secret patterns in only one of `install_secret_gate.py` / `audit_repo.py`; `test_secret_gate.py` fails if they differ.
- Never put a real secret in a test. Planted test values end their line with `secret-gate: allow`.
- The repo is PUBLIC (decision 0004): every commit is published on push. Run the secret gate and `audit_repo.py .` before pushing; never commit personal paths, data or notes.
