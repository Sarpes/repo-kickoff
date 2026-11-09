# repo-kickoff · User guide

repo-kickoff is a **skill** for [Claude Code](https://code.claude.com): a set of instructions plus small scripts that Claude loads only when a task needs them. It has four modes:

| Mode | Use it when | Changes files? |
|---|---|---|
| **Kickoff** | starting a new project or repository | yes: creates the repo and its setup files |
| **Audit** | checking an existing repo's README, requirements and `.gitignore` against its code | no: read-only, produces a report |
| **Daily** | carrying one task from a branch to a merged pull request | yes: branches, commits, pushes; merges only after your OK |
| **Undo** | repairing a git mistake (a wrong commit, lost work, a pushed secret) | only after your OK for the exact command, with a backup first |

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

You do not call it by name. Claude Code shows Claude a one-line description of every installed skill (about 760 characters for this one) and loads the full text (about 9,700 characters) only when a request matches, for example:

- "new project", "set up the repo", "start a repository for …"
- "audit this repo", "does the README match the code", "check the requirements / .gitignore"
- "start a task", "open a PR", "undo my last commit", "I pushed a secret"
- Turkish: "yeni proje", "repo kur", "README yaz", "repoyu denetle", "PR aç", "geri al"

It is not meant for a single commit you did not ask to run through the routine.

---

## 3. Kickoff mode, step by step

Claude first confirms the project's **name and folder** with you, then follows this order. Each step exists because a measured run got it wrong without it.

| # | Step | What happens | Why |
|---|---|---|---|
| 1 | `main` before any branch | `git init -b main`, an empty first commit on `main` with a message body, then a work branch `chore/scaffold` | A branch opened before the first commit leaves no `main`; the first pull request then has no target. |
| 2 | `.gitignore` | Fetched from GitHub's official template (`gh api gitignore/templates/Python`; if `gh` is missing or not signed in, the same file from `raw.githubusercontent.com/github/gitignore` with `curl`), plus a commented project block: `.env`, `.env.*`, `!.env.example`, data/output folders, local databases | Hand-written ignore files matched the official template only 4–9 %. With only `gh` and no fallback, sessions without a working `gh` wrote it partly from memory (match 0.57–0.58); with the fallback, 1.0 in 5 of 5 runs. |
| 3 | Code and tests | In a virtual environment; one real sample of each external input is fetched first and kept in `tests/fixtures/` (or a git-ignored `scratch/`) inside the project | Parsers written against real data, not guesses; no stray folders. |
| 4 | Pinned dependencies | `pin_requirements.py` writes `requirements.txt` (exact `==` versions), `requirements-dev.txt` and `.python-version` from the interpreter the tests passed in | An application should record what it ran with; ranges (`>=`) are for libraries. |
| 5 | Secret gate | `install_secret_gate.py` proves the gate on a throwaway repo, then installs it as a git pre-commit hook | "I checked for secrets" is a promise; a hook is a check that runs on every commit. |
| 6 | README | What · Why · Requirements (Python version, services, environment variables) · Install · Run · Test · Layout · Decisions · Status. In a public repository, decision records and status notes go to a private companion repository instead | A reader can install and run the project from the README alone; internal notes stay private. |
| 7 | Gate before the first push | `audit_repo.py` must report 0 high and 0 medium findings; every `verify` line is opened and checked | Catches a missing dependency or a stale README before anything is public. |
| 8 | GitHub | `gh repo create <owner>/<name> --private`, push `main`, push the branch, open a pull request. Claude Code shows these commands for your permission unless you allowed them in advance; the skill itself does not stop to ask, so say *"no GitHub"* in your request if you do not want this step | Work reaches `main` through a reviewed pull request. If `gh` is not available, Claude lists the commands instead. |

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

## 4a. Daily mode

Daily mode carries one task from a branch to a merged pull request. If the project's own `CLAUDE.md` sets different rules (branch names, commit trailer), those win.

1. **Look at the state first.** Claude runs `repo_state.py <repo> --fetch` (see §5). If a merge or rebase is half done, or files are in conflict, it stops and tells you instead of starting a task on top.
2. **Branch from a fresh default branch.** It switches to the default branch (usually `main`), pulls with `--ff-only` (fast-forward only: it refuses rather than create a merge), and opens a branch named `feat/`, `fix/`, `docs/` or `chore/` plus a short name. Changes you already made carry over to the new branch; they are never committed on the default branch. One task per branch.
3. **Commit.** Files are staged by name, never with `git add -A`, and Claude reads the staged diff before committing. The subject says what changed (imperative, at most 72 characters); the body says why, which alternative was rejected and how it was verified. If a pre-commit hook refuses the commit, Claude fixes the cause and checks `git status`, because a refused commit leaves its files staged. It never uses `--no-verify`.
4. **Push and open the pull request.** `git push -u origin <branch>`, then `gh pr create` with four sections: Goal, Choices (with rejected alternatives), Measurements (before and after, with the source) and How to check.
5. **Merge only on your OK.** Claude shows you what changed, why and how it was verified, and waits. It then merges with a merge commit, which keeps commit hashes quoted in documents valid.
6. **Sync.** It switches back to the default branch, pulls, and runs `repo_state.py` again. It then offers to delete the merged branch, locally and on the remote; it deletes nothing unless you say yes. If the repository has a second remote (a mirror), Claude tells you that copy needs its own push.

Example: you say *"fix the typo in the README"*. Claude runs the state report (clean, on `main`, up to date), creates `docs/readme-typo`, changes the one word, stages `README.md`, reads the diff and commits with the subject `Fix typo in README install section` and a body explaining why. It pushes, opens a pull request, and shows you the four sections. After your OK it merges, returns to `main`, pulls, and asks whether to delete `docs/readme-typo`.

---

## 4b. Undo mode

Undo mode repairs a git mistake. Which repair is right depends on a fact only the repository can tell, so Claude measures first and changes nothing until you agree.

1. **Diagnose.** `repo_state.py <repo> --fetch` reports, for each recent commit, whether it is **pushed** (contained in any remote-tracking branch). Claude never guesses this.
2. **Decide by that fact.** A commit that is not pushed exists only on your machine, so its history may be rewritten. A pushed commit may already be in someone else's clone, so history is not rewritten; a new commit that reverses it is added instead. The table of situations and commands is `skills/repo-kickoff/undo.md`.
3. **Explain, then ask.** Claude states in plain words what happened, the exact command, and what that command discards. It runs the command only after your explicit OK.
4. **Back up first.** Before a command that moves or rewrites history (`reset`, `commit --amend`, `rebase`, `branch -f`, deleting a branch), Claude saves the current point as a branch `backup/<YYYYMMDD-HHMM>-<short-hash>`. Before a command that discards uncommitted work (`restore`, `reset --hard`, `clean`), it offers a backup first: `git stash push -u -m backup` immediately followed by `git stash apply`, which keeps a copy of everything uncommitted in the stash and leaves your files as they were.
5. **Check.** It runs the state report again and shows that the result is what it promised. The backup branch stays until you delete it.

Example, the same mistake in two situations: you say *"undo my last commit"*.

- **Not pushed.** The report shows the commit with `pushed: false`. Claude proposes `git reset --soft HEAD~1`: the commit disappears, its changes stay staged, and the old commit remains reachable through the backup branch it creates first. After your OK it runs both commands and shows the new state.
- **Pushed.** The report shows `pushed: true`. Claude proposes `git revert <hash>` and then a push: history stays as it is, and a new commit undoes the old one. If what was pushed is a secret, Claude tells you first to revoke or rotate the credential, because a revert does not remove it from clones that already exist.

---

## 5. The scripts

All scripts are in `skills/repo-kickoff/scripts/`, use only Python's standard library and need Python 3.11+.

### `audit_repo.py <repo> [--json]`
Read-only. Exit code 1 if any **high** or **medium** finding exists, else 0.

| Check | Finds |
|---|---|
| REQ | Third-party imports (parsed from the code, not guessed) missing from every `requirements*.txt` in the repo (a container's `worker/requirements.txt` counts too) and `pyproject.toml`; listed packages never imported; unpinned versions (info); no stated Python version. Import names are mapped to package names even when the package is not installed (`docx` → `python-docx`, `google.oauth2` → `google-auth`). |
| DOC | README references to files that are not in the repo; `file:LINE` references beyond the end of the file; all in-range references as `verify` items |
| IGN | Files tracked although `.gitignore` ignores them; tracked files named like secrets (`.env`, any `*.env`, `secrets.toml`, `*_secrets.bat`, `client_secret*.json`, `credentials.json`, `.pem`, `.key`, …); lines that look like secrets (GitHub/Anthropic/AWS keys, private keys, `password = "…"`, unquoted `SOME_API_KEY=<16+ characters>`); tracked files over 5 MB |
| HIST | The same secret rules applied to the git history: file names that are no longer tracked, and lines in earlier versions or deleted files. A secret that was committed and later deleted is still readable by anyone who clones; the finding names the commit (never the value). The fix is to revoke the key; rewriting history alone does not help once it was pushed. A line still present in the current file is reported once, under IGN |

Severities: `high`, `medium` (fix before pushing), `verify` (open and compare by hand), `low`, `info` (often a deliberate choice: check the repo says so).

### `pin_requirements.py <repo> [--write]`
Run it **with the project's own interpreter** (the virtual environment the tests passed in). Scans every Python file git would track, splits imports into runtime and development (files under `tests/`, `test_*.py`, `conftest.py`), looks up the installed version of each and prints, or with `--write` writes, `requirements.txt`, `requirements-dev.txt` and `.python-version`. Exit code 1 if an imported package is not installed in that interpreter.

### `install_secret_gate.py <repo>`
Builds a throwaway repo, installs the gate there, and checks that a commit with a fake token is **refused** and a clean commit **accepted**. Only then does it install into your repo:

- `.githooks/pre-commit` and `.githooks/secret_gate.py`
- `git config core.hooksPath .githooks`
- `.gitattributes` line `.githooks/* text eol=lf`, so a Windows checkout does not break the hook

Commit `.githooks/` and `.gitattributes`. After cloning the repo anywhere else, run `git config core.hooksPath .githooks` once.

### `repo_state.py <repo> [--json] [--fetch] [--commits N]`
Reports facts about a git repository: current branch and default branch, upstream with ahead and behind counts, when it was last fetched, an interrupted merge or rebase, conflicted, staged, unstaged and untracked files, the stash count, the configured remotes (credentials stripped from their URLs), and the last N commits (default 10), each marked pushed or not. `--json` prints exact values; the text output escapes control characters in text taken from the repository. It never changes anything unless you pass `--fetch`, which runs `git fetch --all --prune --quiet` and so contacts the repository's own remotes and updates its remote-tracking branches (with `--prune` it also removes remote-tracking branches whose branch was deleted on the remote). Without `--fetch` it reads only the local repository and leaves `.git` byte-identical. Exit code 2 if the folder is not a git repository or an argument is bad.

### Tests
`test_audit_repo.py` and `test_secret_gate.py` build throwaway repositories with planted defects and check that each is caught and that a clean variant raises nothing. `test_secret_gate.py` also checks that the gate and `audit_repo.py` use identical secret patterns. `test_repo_state.py` checks the report against throwaway repositories (clean, dirty, conflicted, pushed and unpushed commits) and that `.git` is byte-identical before and after a run without `--fetch`.

---

## 6. The secret gate in daily use

- **What it blocks:** a commit whose staged files are named like secret files or contain lines that look like credentials. That includes unquoted `.env`-style lines (an upper-case name ending in `API_KEY`, `TOKEN`, `SECRET` or `PASSWORD`, followed by `=` and a value of 16 or more characters) and any file name ending in `.env`. The value itself is never printed.
- **What it allows:** references to a value kept elsewhere, such as `os.environ["MY_SETTING"]`, `"$MY_SETTING"`, `%MY_SETTING%`; an empty value such as `MY_SETTING=`; files ending in `.example`, `.sample`, `.template`.
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
- Update: `claude plugin marketplace update repo-kickoff` (fetches the latest catalog), then `claude plugin update repo-kickoff@repo-kickoff`, then restart Claude Code. A new version is offered only when the version number in `.claude-plugin/plugin.json` changes (see §9).
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
- **Checks before a release:** all four test files print ALL PASS; `claude plugin validate .` passes; `python skills/repo-kickoff/scripts/audit_repo.py .` reports 0 high and 0 medium.
- **Changing `SKILL.md`:** re-run the before/after scenarios (fresh sessions with and without the skill, scored on the criteria in §1); the skill is kept only for behaviour it measurably changes.
- **Secret patterns** live in two places (`install_secret_gate.py`, `audit_repo.py`); the test fails if they differ.
