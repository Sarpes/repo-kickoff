# 0004 · Public under MIT

Date: 2026-11-04 · Status: accepted (owner's decision) · Supersedes: 0002

## Context
0002 kept the repository private with no license until the owner decided. After reviewing and merging PR #1, the owner decided the skill should be usable by others.

## Decision
License the project under MIT and make the GitHub repository public.

## Checks before publishing
- Secrets: 0 unmarked secret-looking lines among all 1,105 lines ever added in any commit (not only the current tree), using `audit_repo.SECRET_TEXT`.
- Personal absolute paths (`C:\Users\…`, `/c/Users/…`): none in history.
- Commit identities: seven commits carry the owner's personal e-mail. The same address is already public in the commits of another public repository of his, so publishing adds no new exposure. Rewriting history to hide it was rejected (see below).

## Rejected alternatives
- **Apache-2.0**: also permissive and adds a patent grant, but longer and less common for Claude Code skills; nothing here needs a patent clause.
- **Rewrite history to a noreply e-mail before publishing**: needs a force push to `main` and changes every commit hash, which breaks the hashes cited in PR #1 and in these records, for an address that is already public.

## Consequences
Anyone may use, modify and redistribute the skill if they keep the copyright notice. `/plugin marketplace add Sarpes/repo-kickoff` works for everyone.
