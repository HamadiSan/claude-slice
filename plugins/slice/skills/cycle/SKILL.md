---
name: cycle
description: Run a substantial piece of work through a full multi-agent cycle - spec, implement, review, rework, mutation-test QA, rework, final review, then land. Use when implementing a new package, module, subsystem or feature of real size, or when the user asks for a thorough or high-assurance build. PROPOSE this before starting; do not run it unprompted, it is expensive.
argument-hint: [what to build]
---

# The slice cycle

A unit of work goes through eight steps, with judgement and implementation deliberately done by
different models.

| # | Step | Agent | Model |
|---|---|---|---|
| 1 | Write the spec | `slice-spec` | Fable 5 |
| 2 | Implement it | `slice-coder` | Sonnet 5 |
| 3 | Code review | `slice-reviewer` | Opus 5 |
| 4 | Address the review | `slice-coder` | Sonnet 5 |
| 5 | QA / mutation testing | `slice-qa` | Opus 5 |
| 6 | Address QA | `slice-coder` | Sonnet 5 |
| 7 | Final review | `slice-reviewer` | Opus 5 |
| 8 | Document, commit, push | you | — |

## Before you start: propose, do not assume

This is seven agents and, for a package of real size, a large amount of wall clock and tokens.
**Tell the user roughly what it will cost and ask whether they want it**, unless they have
already asked for the cycle by name.

If the work is small — a bug fix, one function, a config change — say so and offer `/slice:quick`
or just doing it directly. Running eight steps on a typo is a bad trade and reflects badly on the
tool.

## Running it

**Between every step, commit.** The tree must be committed before a gate agent starts. Gates must
never see uncommitted work, and a QA agent that mutates and restores can otherwise revert work
that landed while it ran. Commit messages at intermediate steps should say they are checkpoints.

**Verify each agent's claims yourself.** Do not take "all tests pass" on trust — run the build,
the tests and the linter after every step. An agent reporting success it did not achieve is rare
but not rare enough, and you are the one landing this.

**Pass findings through a file, not a prompt.** Write the review or QA output to a scratch file
and point the next agent at it. Long findings pasted into a prompt lose structure, and a file
gives the fixer something to work through methodically.

**Two cycles maximum.** If the final review still says DO NOT LAND after a second full pass, stop
and bring it to the user. Work that will not converge in two rounds usually has a problem in its
specification, not its code, and a third round will not find it.

**Write down every finding you decline.** A finding recorded in a comment, a test name, or a
spec's open-questions section survives being deprioritised. One that is only argued in a review and
then declined does not exist a week later — and the ones that come back are the ones nobody wrote
down. This costs a sentence and it is the cheapest insurance in the cycle.

## What each gate is for

Review and QA reliably find **different classes** of defect, which is why both run:

- **Review** finds claims that do not match code — a comment promising behaviour the
  implementation lacks, an invariant asserted in prose and nowhere else. Also validation that can
  never fire.
- **QA** finds untested behaviour, by mutating the source and seeing what stays green. It
  repeatedly demonstrates that a high coverage number overstates the real position.

A single combined "quality" gate would be worse than both.

## Landing

Step 8 is yours. Write the commit message so it explains **what the gates found and why it
mattered** — the defects and their consequences, not a list of files. That message is the only
durable record of why the code is shaped as it is, and it is worth more than the diff.

If the project keeps a workflow or decisions document, add anything the cycle taught you about
the process itself.
