# claude-slice

A Claude Code plugin that runs a unit of work through a multi-agent cycle — spec, implement,
review, rework, mutation-test QA, rework, final review, land — with judgement and implementation
deliberately done by different models.

```
claude plugin marketplace add HamadiSan/claude-slice
claude plugin install slice@claude-slice
```

Then just work. The skill surfaces itself when you start something substantial and **proposes**
the cycle rather than running it — seven agents is not a decision to make on your behalf. Or ask
for it: `/slice:cycle` for the full pass, `/slice:quick` for a small change.

## The cycle

| # | Step | Model |
|---|---|---|
| 1 | Write the spec | Fable 5 |
| 2 | Implement it | Sonnet 5 |
| 3 | Code review | Opus 5 |
| 4 | Address the review | Sonnet 5 |
| 5 | QA / mutation testing | Opus 5 |
| 6 | Address QA | Sonnet 5 |
| 7 | Final review | Opus 5 |
| 8 | Document, commit, push | — |

Two cycles maximum. Work that will not converge in two rounds usually has a problem in its
specification rather than its code, and a third round will not find it.

## Why two gates and not one

Review and QA find **different classes** of defect, consistently:

- **Review** finds claims that do not match code — a comment promising behaviour the code lacks,
  an invariant asserted in prose and nowhere else, validation placed where it can never fire.
- **QA** finds untested behaviour, by breaking the source and seeing what stays green. It
  repeatedly shows that a high coverage number overstates the real position, because a line
  counts as covered when a test merely reaches it.

A single combined "quality" gate would be worse than both.

## What this encodes

The agent prompts are the point of the plugin. They carry the things a real run cost real time to
learn:

**The spec makes the architectural decisions.** Written from the request alone, a spec invents
abstractions the tree already has under another name — so the spec agent reads the layout, the
nearest existing component and the recurring idioms first, and then names the pattern it follows
*with the path of the code it follows*. A decision left open in the spec still gets made: during
implementation, inside one file, differently in each.

**Reviewers get no write tools.** A reviewer that can edit what it is judging becomes a second
unsupervised author.

**QA works on a copy, never the real tree.** A QA agent that backs up, mutates and restores will
silently revert whatever landed while it ran, and the damage surfaces much later as an unrelated
build error.

**A build failure is not a caught mutation.** A harness that greps for test failures counts a
compile error as "the tests caught it", and quietly overstates the suite.

**The coder is licensed to disagree.** With the spec, with the findings, with the instruction.
In practice this catches specs describing designs that cannot work, findings whose symptom is
right and mechanism wrong, and fixes that trade one bug for a worse one.

**A fix's comment is the least trustworthy text in a diff.** The largest single class of real
defect found is code contradicted by its own comment — and the worst cases are comments on
fixes, where someone has just repaired something and is the least sceptical reader of their own
description.

**Order fixtures so a wrong implementation fails.** A test asserting "the higher-priority one
wins", with the entries listed so last-wins also passes, proves nothing.

**Look for multiplicity.** Rules get tested once, in the single-item shape, so any bug involving
*two* — a missing scope filter, an aggregate returning the last value instead of the sum — walks
straight through.

## Cost

The full cycle on a real package is measured in millions of tokens and hours of wall clock. That
is a good trade for a persistence layer, an auth path or anything that runs unattended, and an
absurd one for a typo. `/slice:quick` exists for the second case, and the skill will say so.

MIT.
