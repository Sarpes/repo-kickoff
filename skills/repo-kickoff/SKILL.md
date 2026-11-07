---
name: repo-kickoff
description: Use when starting a new code project or repository, or when asked to write or check a repo's README, requirements, .gitignore, Python version or other setup files, or to audit whether a repo's docs match its code. Triggers include "new project", "set up the repo", "yeni proje", "repo kur", "README yaz", "requirements", "gitignore", "repoyu denetle". Not for routine commits in an established repo.
---

# repo-kickoff

Two modes. **Kickoff** builds a new repo whose setup can be reproduced and checked. **Audit** checks an existing repo, read-only. Deterministic steps are scripts in `scripts/` (run with `python <path>`); this file holds the order and the judgment.

## Kickoff

Confirm the project name (lowercase kebab-case ASCII) and root folder with the user before creating anything, and ask whether commits carry a `Co-Authored-By: Claude` trailer (`co_author`: `claude` is the default, `none` omits it). Do not assume the answer. Then, in this order:

| # | Step | Command / output |
|---|---|---|
| 1 | Repo with `main` that exists BEFORE any branch | `git init -b main`, `git commit --allow-empty -m "Initialize repository" -m "Empty root commit so main exists as the target of the first pull request."`, then `git switch -c chore/scaffold`. A branch opened before the first commit leaves no `main` for the PR to target. Every commit, this one included, has a body saying why. |
| 2 | `.gitignore` | Start from GitHub's template: `gh api gitignore/templates/Python --jq .source` (no leading `/`: Git Bash turns it into a Windows path). If `gh` fails: `curl -sSf https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore`. Never write the template from memory. Append a commented project block: `.env`, `.env.*`, `!.env.example`, data/output folders, local DBs. |
| 2b | Skeleton and registry entry | `python scripts/scaffold_project.py <repo> --id <id> --co-author claude\|none`: creates `docs/handovers`, `docs/architecture`, `docs/guides`, `docs/artifacts`, `docs/archive` (each with `.gitkeep`) and appends one entry (`id`, `path`, `status: active`, `co_author`) to the registry file named by the environment variable `CLAUDE_REGISTRY` (default `C:\Projects\workbench\registry\projects.yaml`). It never overwrites a file and refuses a duplicate id. Use `--no-registry` when there is no registry. Then write the root files it lists: `CLAUDE.md` (or `.claude/CLAUDE.md`), `README.md`, and, for repos whose root commit is 2026-11-06 or later, `DECISIONS.md` and `AI-Agents.md`. |
| 3 | Code and tests, in a venv | Fetch one real sample of any external input before writing parsers. Save samples inside the project root: `tests/fixtures/` if tests use them, otherwise a git-ignored `scratch/`. Never create folders next to the root. |
| 4 | Pinned dependencies | With the venv's interpreter, after tests pass: `python scripts/pin_requirements.py <repo> --write` → `requirements.txt` (`==`), `requirements-dev.txt`, `.python-version`. Ranges (`>=`) are for libraries others install; an app records what it ran with. |
| 5 | Secret gate in code, not a promise | `python scripts/install_secret_gate.py <repo>`; it proves itself on a throwaway repo before installing. Commit `.githooks/`. |
| 6 | README | What · Why · Requirements (Python version, services, env vars) · Install · Run · Test · Layout · Decisions (`DECISIONS.md`) · Status (`docs/handovers/HANDOVER_YYYY-MM-DD_HHMM.md`, header lines `Status: OPEN|COMPLETE`, `Started:`, `Completed:`; only the newest may be OPEN). In a public repo, keep decisions and status in a private companion repo and do not link it. |
| 7 | Gate before the first push | `python scripts/audit_repo.py <repo>` → 0 high, 0 medium. Open every `verify` line. |
| 8 | GitHub | `gh repo create <owner>/<name> --private --source . --remote origin`, push `main`, push the branch, open a PR. If `gh` fails, say so and list the commands. Commit messages end with the `Co-Authored-By` trailer only if `co_author` is `claude`. |

## Audit

1. `python scripts/audit_repo.py <repo>` first. It covers imports vs requirements, Python version, README file/line references, ignored-but-tracked files and secrets, including secrets that are only in the git history, in seconds. Do not rewrite these scans.
2. Check **every** `verify` line: open the referenced lines and compare them to the README sentence. Never sample. One stale range among 29 correct ones is the typical defect.
3. Judgment checks the script cannot make:
   - Does the README's install → run path work from a clean clone, and does it produce the README's numbers?
   - Run the main entry point or tests, then `git status`: generated outputs must be ignored.
   - Every env var the code reads (`os.environ`, `getenv`, `process.env`) is documented, with its default.
   - Behaviour the README claims has code behind it (grep for it); absolute paths are documented.
4. Report findings ordered by severity, each with `file:line` or command output. State what you did not check. Change nothing.

## Common mistakes

| Mistake | Fix |
|---|---|
| Branch before first commit → no `main` | Step 1 order |
| `>=` ranges in an app's requirements | `pin_requirements.py` from the tested venv |
| "I scanned for secrets" with no hook | `install_secret_gate.py` |
| Hook trusts `python3`; on Windows it can be the Store stub, which runs nothing (exit 49) | The installed hook checks a printed marker and fails closed |
| Sampling README references | Check all `verify` lines |
| Flagging documented absences as bugs | A README "not in this repo" note makes a missing file intentional |
