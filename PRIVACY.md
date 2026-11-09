# Privacy policy

repo-kickoff is a Claude Code plugin: instructions plus Python scripts that run on your own machine. Its author runs no server and receives nothing from it.

## What it collects

Nothing. The plugin has no telemetry, no analytics and no server of its own. It stores nothing outside the repository you work on.

## What it reads

- The files of the repository you point it at and, in audit mode, their earlier versions in its git history (to find secrets that were committed and later deleted).
- For `pin_requirements.py`: the list of packages installed in the Python you run it with.

It does not read your environment variables or credential files. It looks for credential-shaped file names and lines inside your repository only to warn you about them, and it prints file names and line numbers, never the values.

## What leaves your machine, and only when you ask

| When | What | To |
|---|---|---|
| Kickoff step 2 | A request for GitHub's official `.gitignore` template (`gh api gitignore/templates/<Language>`, with your own `gh` login; if `gh` is missing or not signed in, a plain download of the same public file from `raw.githubusercontent.com/github/gitignore`) | GitHub |
| Kickoff step 8, through commands Claude Code shows for your permission unless you allowed them in advance; say "no GitHub" in your request to skip it | `gh repo create` makes a private repository under your GitHub account; `git push` uploads your project to it, with your own credentials | GitHub |
| Only if you or Claude run `repo_state.py --fetch` (Daily and Undo modes do, to learn what is already pushed) | `git fetch --all --prune --quiet`, which contacts the remotes already configured in that repository, with your own credentials, and updates its remote-tracking branches (with `--prune` it also removes remote-tracking branches whose branch was deleted on the remote). Without `--fetch` the script reads only the local repository | The repository's own remotes (usually GitHub) |

In Daily and Undo modes, Claude may also push commits or open a pull request (`git push`, `gh pr create`), through commands Claude Code shows for your permission unless you allowed them in advance, with your own credentials, to the repository's own remote. Audit mode sends nothing. Apart from the `--fetch` option above, `repo_state.py` sends nothing either. GitHub's handling of those requests is governed by [GitHub's privacy statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement).

Claude Code itself, which runs the plugin, is covered by [Anthropic's privacy policy](https://www.anthropic.com/legal/privacy).

## Contact

Questions or concerns: open an issue at https://github.com/Sarpes/repo-kickoff/issues.
