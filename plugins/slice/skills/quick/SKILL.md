---
name: quick
description: Run a small change through a light version of the slice cycle - implement, one review, fix, land. No spec and no mutation-testing pass. Use for bug fixes, single functions, config changes and anything where the full cycle would cost more than the change is worth.
argument-hint: [what to change] [--role=model ...]
---

# The quick cycle

Four steps, for work that does not justify seven agents.

| # | Step | Agent | Role | Model (default) |
|---|---|---|---|---|
| 1 | Implement | `slice-coder` | `coder` | Sonnet 5 |
| 2 | Review | `slice-reviewer` | `reviewer` | Opus 5 |
| 3 | Address the review | `slice-coder` | `coder` | Sonnet 5 |
| 4 | Commit, push, report to the ticket | you | — | — |

No spec: for a change this size, the request is the spec. No mutation-testing pass: it costs more
than it returns on a small diff, though the reviewer still reports untested guarantees it notices.

**The models are defaults.** Both roles take the same overrides the full cycle uses — an
invocation flag (`--reviewer=opus`), else `.slice.json` at the repo root, else the agent's
frontmatter. Pass the resolved model explicitly on every `Agent` call, and name what you resolved
before you start. Full rules and accepted values:
[the full cycle](../cycle/SKILL.md#choosing-the-model-for-each-role).

## Use the full cycle instead when

- the change introduces a new module, package or subsystem
- it touches persistence, concurrency, authentication, or money
- getting it wrong would be discovered late — an unattended job, a nightly, anything whose failure
  is silent
- the user asks for thoroughness or high assurance

When in doubt, say which you think fits and let the user choose. Escalating a small change costs
them tokens; under-gating a risky one costs them a defect in production.

## Running it

Commit before the review so the gate sees a frozen tree. Verify the build, tests and linter
yourself after each step rather than trusting the report. If the review finds something that
changes the shape of the work — a design problem rather than a defect — stop and propose the full
cycle instead of patching around it.

## The ticket

If the change came from a tracked ticket, read it first and post one comment when the run ends —
on success and, more importantly, on failure or when you stop to propose the full cycle. Same
rules as [the full cycle](../cycle/SKILL.md): one comment, at the end, comment rather than
transition, and never claim you updated a tracker you could not reach. Small changes are the ones
whose tickets go stale, because nobody thinks a two-line fix needs reporting.
