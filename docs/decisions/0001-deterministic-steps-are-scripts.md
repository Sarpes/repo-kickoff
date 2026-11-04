# 0001 · Deterministic steps are scripts; SKILL.md holds only order and judgment

Date: 2026-11-04 · Status: accepted

## Context
Checking imports against requirements, matching README `file:line` references, scanning for secrets and pinning versions give the same answer every time they are done right. In baseline runs, each audit session rewrote its own scanners from scratch (28–31 turns, about $2.2–2.4 per run), and one sampled the references instead of checking all of them.

## Options
- A. Describe the checks in SKILL.md prose and let the agent implement them each time.
- B. Ship tested scripts for the deterministic part; SKILL.md says when to run them and what to judge by hand.

## Decision
B. Four scripts with their own tests (`test_audit_repo.py`, `test_secret_gate.py`). SKILL.md lists the order, the commands and the checks a regex cannot make (does the install path work, does a run leave `git status` clean, are env vars documented).

## Rejected alternatives
- **A, prose only**: results vary per run, and a check that is re-implemented each time is never tested.
- **An LLM-written `.gitignore`**: hand-written ignores in baseline runs matched GitHub's official template 4–9 %. The template is fetched (`gh api /gitignore/templates/<Lang>`) and a project block is appended.
- **Picking Python in the hook by exit code**: the Windows Store `python3` stub exits without running the script (measured: exit 49, "Python bulunamadı"), so a gate chosen that way would pass everything. The hook asks each candidate to print a marker and refuses the commit if none works.

## Consequences
The scripts need Python 3.11+. The gate and `audit_repo.py` carry the same secret patterns in two places; `test_secret_gate.py` fails if they drift.
