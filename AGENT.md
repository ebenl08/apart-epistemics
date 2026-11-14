# AGENT.md

Standing rules for agents working in this repo.

## Commits

- After every experiment or change, ask the user whether to commit before committing. Never commit or push unprompted.
- This directory may not itself be a git repo (subprojects like `context-language-models` may be). Check before offering.
- Subject: Conventional Commits, `type(scope): imperative summary` (feat, fix, refactor, docs, test, chore, perf), 50 chars max, no trailing period.
- Body: blank line after subject, wrapped at 72 columns, explains why, not what.
- Atomic: one logical change per commit, no unrelated files. Stage files explicitly (no `git add -A`) and review `git diff --staged` first.
- Do not commit secrets, data dumps or large result artifacts. Check `.gitignore`.
- Run relevant tests and checks before committing.
- End the message with the Co-Authored-By attribution line.

## Experiments

Before running an experiment, list its configuration as bullets:

- Mark each setting **control** (held fixed) or **vary**.
- Highlight the key changes against the baseline or previous run.
- Cover at least: model, benchmark, seeds, context budget, nudges, edit gate, serving engine, metric parameters (e.g. `--n-body-params`).

## Session workflow

- Log every major decision in `.agent/decisions.md` with date, time (from `date`), header and description. If unsure a decision is major, ask the user.
- After a decision, suggest updating `.agent/handoff/handoff-<session-name>.md`.
- Compact context at 250k tokens, then update that session's handoff file.
- Every plan defines milestones. After each milestone, stop and ask the user before continuing, unless the user said otherwise for that plan.

## References

- Give a valid, clickable link for every paper, repo, doc or file you cite.
- Use only URLs seen in the repo or verified. Never invent a URL. If none is verified, say so.
- Link local files by relative path, with a line number where useful.
