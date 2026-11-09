---
name: repo-kickoff
description: Use when starting a new code project or repository, when asked to write or check a repo's README, requirements, .gitignore, Python version or other setup files, or to audit whether a repo's docs match its code; also when asked to run a task through the git routine (start a task branch, open a pull request, sync after a merge) or to undo a git mistake (undo a commit, unstage, recover lost work, a pushed secret). Triggers include "new project", "set up the repo", "yeni proje", "repo kur", "README yaz", "requirements", "gitignore", "repoyu denetle", "start a task", "open a PR", "PR aç", "undo a commit", "git undo", "geri al", "commit'i geri al", "I pushed a secret". Not for routine commits in an established repo unless the user asks for the task routine.
---

# repo-kickoff

Four modes. **Kickoff** builds a new repo whose setup can be reproduced and checked. **Audit** checks an existing repo, read-only. **Daily** carries one task from a branch to a merged pull request. **Undo** diagnoses a git mistake and repairs it after the user's OK. Deterministic steps are scripts in `scripts/` (run with `python <path>`); this file holds the order and the judgment.

## Kickoff

Confirm the project name (lowercase kebab-case ASCII) and root folder with the user before creating anything, and ask whether commits carry a `Co-Authored-By: Claude` trailer (`co_author`: `claude` is the default, `none` omits it). Do not assume the answer. Then, in this order:

| # | Step | Command / output |
|---|---|---|
| 1 | Repo with `main` that exists BEFORE any branch | `git init -b main`, `git commit --allow-empty -m "Initialize repository" -m "Empty root commit so main exists as the target of the first pull request."`, then `git switch -c chore/scaffold`. A branch opened before the first commit leaves no `main` for the PR to target. Every commit, this one included, has a body saying why. |
| 2 | `.gitignore` | Start from GitHub's template: `gh api gitignore/templates/Python --jq .source` (no leading `/`: Git Bash turns it into a Windows path). If `gh` fails: `curl -sSf https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore`. Never write the template from memory. Append a commented project block: `.env`, `.env.*`, `!.env.example`, data/output folders, local DBs. |
| 2b | Skeleton, private companion and registry entries | `python scripts/scaffold_project.py <repo> --id <id> --co-author claude\|none`: creates `docs/handovers`, `docs/architecture`, `docs/guides`, `docs/artifacts`, `docs/archive` (each with `.gitkeep`), the private companion `<id>-internal` next to the repo (with `ownership/`), and appends one entry for each (`id`, `path`, `status: active`, `co_author`) to the registry file named by the environment variable `CLAUDE_REGISTRY` (default `C:\Projects\workbench\registry\projects.yaml`). It never overwrites a file and refuses a duplicate id. Use `--no-registry` when there is no registry; `--internal-only` adds just the companion to an existing project. Then write the root files it lists: `CLAUDE.md` (or `.claude/CLAUDE.md`), `README.md`, and, for repos whose root commit is 2026-11-06 or later, `DECISIONS.md` and `AI-Agents.md`; and the companion's `README.md`. Private records (the owner's ownership answers) go only in the companion. |
| 3 | Code and tests, in a venv | Fetch one real sample of any external input before writing parsers. Save samples inside the project root: `tests/fixtures/` if tests use them, otherwise a git-ignored `scratch/`. Never create folders next to the root. |
| 4 | Pinned dependencies | With the venv's interpreter, after tests pass: `python scripts/pin_requirements.py <repo> --write` → `requirements.txt` (`==`), `requirements-dev.txt`, `.python-version`. Ranges (`>=`) are for libraries others install; an app records what it ran with. |
| 5 | Secret gate in code, not a promise | `python scripts/install_secret_gate.py <repo>`; it proves itself on a throwaway repo before installing. Commit `.githooks/`. |
| 6 | README | What · Why · Requirements (Python version, services, env vars) · Install · Run · Test · Layout · Decisions (`DECISIONS.md`) · Status (`docs/handovers/HANDOVER_YYYY-MM-DD_HHMM.md`, header lines `Status: OPEN|COMPLETE`, `Started:`, `Completed:`; only the newest may be OPEN). In a public repo, keep decisions and status in the private companion too. No repo links to its companion. |
| 7 | Gate before the first push | `python scripts/audit_repo.py <repo>` → 0 high, 0 medium. Open every `verify` line. |
| 8 | GitHub | `gh repo create <owner>/<name> --private --source . --remote origin`, push `main`, push the branch, open a PR. The companion gets its own repo, always private: `git init -b main` in it, a first commit with its README, `gh repo create <owner>/<name>-internal --private --source . --remote origin`, push. If `gh` fails, say so and list the commands. Commit messages end with the `Co-Authored-By` trailer only if `co_author` is `claude`. |

## Audit

1. `python scripts/audit_repo.py <repo>` first. It covers imports vs requirements, Python version, README file/line references, ignored-but-tracked files and secrets, including secrets that are only in the git history, and whether the private companion `<name>-internal` exists next to the repo, in seconds. Do not rewrite these scans.
2. Check **every** `verify` line: open the referenced lines and compare them to the README sentence. Never sample. One stale range among 29 correct ones is the typical defect.
3. Judgment checks the script cannot make:
   - Does the README's install → run path work from a clean clone, and does it produce the README's numbers?
   - Run the main entry point or tests, then `git status`: generated outputs must be ignored.
   - Every env var the code reads (`os.environ`, `getenv`, `process.env`) is documented, with its default.
   - Behaviour the README claims has code behind it (grep for it); absolute paths are documented.
4. Report findings ordered by severity, each with `file:line` or command output. State what you did not check. Change nothing.

## Daily

One task, from branch to merged pull request. The project's own rules (its `CLAUDE.md`) override these defaults.

| # | Step | Command / check |
|---|---|---|
| 1 | State first | `python scripts/repo_state.py <repo> --fetch`. If `operation` is set or `conflicted` is not empty, stop and report. Also stop and report if you are on the default branch with `ahead` greater than 0 (unpushed commits there); point to the `undo.md` row "Committed on the default branch instead of a new branch". |
| 2 | Branch from a fresh default branch | `git switch <default>`, `git pull --ff-only`, `git switch -c <prefix>/<short-name>` with `feat/`, `fix/`, `docs/` or `chore/`. Uncommitted changes come along to the new branch; never commit them on the default branch. One task per branch. |
| 3 | Commit | Stage by name (`git add <path>`, never `-A` or `.`), read `git diff --staged`, then commit. Subject: what changed, imperative, at most 72 characters. Body: why, the alternative rejected, how it was verified (command and number). Add a `Co-Authored-By` trailer only if the project records `co_author: claude`. If a hook refuses the commit, fix the cause (never `--no-verify`) and run `git status`: a refused commit leaves its files staged. |
| 4 | Push and open the pull request | `git push -u origin <branch>`, then `gh pr create` with the sections Goal · Choices (with rejected alternatives) · Measurements (before/after, source) · How to check. |
| 5 | Merge only on the user's OK | Show the pull request: what changed, why, how it was verified. Wait for the OK, then `gh pr merge <n> --merge` (a merge commit keeps hashes cited in docs valid). |
| 6 | Sync | `git switch <default>`, `git pull --ff-only`, `repo_state.py` again. Offer to delete the merged branch, locally and on the remote; delete nothing without the user's OK. If `remotes` lists a second copy of this repo, say that it needs its own push (`git push <remote> <default>`). |

## Undo

Diagnose before touching anything: the right fix depends on facts only the repo can tell.

1. `python scripts/repo_state.py <repo> --fetch`. The deciding fact is `pushed` for each commit involved. Never guess it. `pushed: false` means "not on any remote-tracking branch now"; if a remote branch was deleted, its commits may still exist in other people's clones, so ask before rewriting them.
2. Read `undo.md` and pick the matching row. Not pushed: history may be rewritten. Pushed: add a commit that reverses it; never rewrite shared history.
3. Tell the user in plain words what happened, the exact command, and what it will discard. Run it only after the user's explicit OK.
4. Before any command that moves or rewrites history (`reset`, `commit --amend`, `rebase`, `branch -f`, deleting a branch), save the current point: `git branch backup/<YYYYMMDD-HHMM>-<short-hash>`. Before a command that discards uncommitted work (`restore`, `reset --hard`, `clean`), offer a backup first: `git stash push -u -m backup` immediately followed by `git stash apply` (the stash keeps a copy, the working tree stays as it was, so the command then acts on the files you meant).
5. Run `repo_state.py` again and show that the result is what was promised. Keep the backup branch until the user deletes it.

## Common mistakes

| Mistake | Fix |
|---|---|
| Branch before first commit → no `main` | Step 1 order |
| `>=` ranges in an app's requirements | `pin_requirements.py` from the tested venv |
| "I scanned for secrets" with no hook | `install_secret_gate.py` |
| Hook trusts `python3`; on Windows it can be the Store stub, which runs nothing (exit 49) | The installed hook checks a printed marker and fails closed |
| Sampling README references | Check all `verify` lines |
| Flagging documented absences as bugs | A README "not in this repo" note makes a missing file intentional |
| Guessing whether a commit was pushed | `repo_state.py` reports `pushed` for each commit |
| `git push --force` to fix a pushed mistake | `git revert`; force only the user's own unshared branch, with `--force-with-lease`, after OK |
| Deleting a merged branch unasked | Offer it; delete only on OK |
