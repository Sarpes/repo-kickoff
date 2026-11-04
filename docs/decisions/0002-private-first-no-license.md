# 0002 · Private first, no license until the owner decides

Date: 2026-11-04 · Status: superseded by [0004](0004-public-under-mit.md) the same day (owner's decision)

## Context
The skill is meant to be shareable as a Claude Code plugin. Installing a plugin from GitHub needs a public repository; reuse by others needs a license.

## Options
- Visibility: public now · private first, public after review · always private.
- License: MIT · Apache-2.0 · none.

## Decision
Private first; the repository becomes public only after the owner has reviewed it and says so. No license: all rights reserved until the owner states otherwise.

## Rejected alternatives
- **Public from the first push**: a secret or personal path in an early commit would be published before anyone reviewed it.
- **MIT now** (the most common choice for skills and plugins): the owner chose to keep all rights for now. Without a license, others may view the code on GitHub but may not legally reuse it.

## Consequences
`/plugin marketplace add Sarpes/repo-kickoff` works only for the owner until the repo is public. `plugin.json` has no `license` field on purpose.
