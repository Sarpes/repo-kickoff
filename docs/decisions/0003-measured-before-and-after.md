# 0003 · The skill is kept only if it changes measured behaviour

Date: 2026-11-04 · Status: accepted

## Context
A skill that teaches agents what they already do costs context and adds nothing. Following superpowers:writing-skills, every rule in SKILL.md answers a failure seen in runs without it.

## Method
Fresh `claude -p` sessions with the owner's real global settings. Scenario A: build "kur-takip" (TCMB rates → SQLite) inside a throwaway folder, with an invalid `GH_TOKEN` so nothing reaches GitHub. Scenario B: audit a real repository read-only (`git status` checked afterwards: 0 changes). A scorer checks 17 criteria per sandbox; the audit script was cross-checked against a hand-built ground truth.

## Results
| Criterion (scenario A) | Without skill (3 runs) | With skill (3 runs) | After refactor (2 runs) |
|---|---|---|---|
| Dependencies pinned `==` | 0/3 | 3/3 | 2/2 |
| Python version stated | 1/3 | 3/3 | 2/2 |
| Secret gate as code | 0/3 | 3/3 | 2/2 |
| `main` before first branch | 2/3 | 3/3 | 2/2 |
| Commits with a body | 29/29 | 20/21 | 16/16 |
| Samples kept inside the project root | — | 2/3 | 2/2 |
| Audit high + medium | 1 per repo | 0 | 0 |
| Cost per run | $1.78–3.02 | $1.80–1.86 | $2.18–2.24 |

Scenario B: the stale README reference was caught 1/2 without the skill and 2/2 with it; cost did not drop ($2.04 / $2.52), the time saved on scanning went into checking every reference. Samples are small (2–3 runs per arm): read the cost row as a direction, not a result.

## Rejected alternatives
- **Judging the skill by reading it**: the first version shipped two defects that only runs exposed (a bodyless example commit was copied verbatim; samples were saved outside the project root), and the audit flagged the gate's own file as a secret.

## Consequences
Any change to SKILL.md is re-run against scenario A before it is merged. Test-rig traps to avoid: a prompt asking to "write every command and explain why" tripped a model safeguard; a sandbox under `~/.claude` makes every write a protected-file denial.
