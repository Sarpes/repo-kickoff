# Undo: pick the row, then follow SKILL.md › Undo

Every row assumes `repo_state.py --fetch` ran first. "Backup" means `git branch backup/<YYYYMMDD-HHMM>-<short-hash>` before the command; "stash" means offering `git stash push -u -m backup` immediately followed by `git stash apply` before it (the stash keeps a copy of all uncommitted and untracked work; the apply puts the working tree back, so the command below still acts on the files meant). Run nothing without the user's OK.

## Uncommitted work

| Situation | Command | What it discards |
|---|---|---|
| Throw away edits in one file | stash, then `git restore <file>` | The file's uncommitted edits |
| Unstage a file, keep the edits | `git restore --staged <file>` | Nothing |
| Edits made on the wrong branch, not committed | `git stash push -m move`, `git switch <right>`, `git stash pop` | Nothing; on a conflict, resolve it and the stash stays until `git stash drop` |
| Remove untracked files | stash, `git clean -n -d` to list them, then `git clean -f -d <path>` | Those files, permanently; git never had them |

## Commits that are NOT pushed

| Situation | Command | What it discards |
|---|---|---|
| Wrong message on the last commit | backup, `git commit --amend` | The old commit (reachable through the backup) |
| Forgot a file in the last commit | backup, `git add <file>`, `git commit --amend --no-edit` | The old commit (backup) |
| Undo the last commit, keep its changes staged | backup, `git reset --soft HEAD~1` | The commit (backup) |
| Undo the last commit, keep changes unstaged | backup, `git reset HEAD~1` | The commit (backup) |
| Committed on the default branch instead of a new branch | `git switch -c <new-branch>`, then backup, then `git branch -f <default> <upstream>` | Nothing; the commits now live on the new branch |

## Commits that ARE pushed

| Situation | Command | What it discards |
|---|---|---|
| Reverse one pushed commit | `git revert <hash>`, then push | Nothing; a new commit undoes the old one |
| Reverse a merged pull request | `git revert -m 1 <merge-hash>`, then push | Nothing |
| A secret was pushed | 1. Revoke or rotate the credential first. 2. Remove it from the current files in a new commit. 3. Rewriting history (`git filter-repo`) only with the user's OK, and it does not undo the leak: clones and forks keep it | Rewriting history changes every later hash and needs a force push |

## Interrupted operations and lost work

| Situation | Command | What it discards |
|---|---|---|
| Merge with conflicts, want out | `git merge --abort` | The merge attempt |
| Rebase gone wrong | `git rebase --abort` | The rebase attempt |
| Detached HEAD with commits made there | `git switch -c rescue/<name>` | Nothing |
| A commit or branch seems lost | `git reflog`, find the hash, `git switch -c rescue/<name> <hash>` | Nothing. The reflog is local and its entries expire (usually after weeks) |

## Never, without the user's explicit OK for that exact command

- `git reset --hard`, `git restore`, `git clean -f` with uncommitted work present and no stash offered.
- `git push --force` on a shared branch. On the user's own unshared branch, `--force-with-lease` only.
- Deleting a branch, a backup branch or a stash.
- `git filter-repo` or any history rewrite of pushed commits.
