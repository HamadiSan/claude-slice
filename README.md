# claude-slice

A Claude Code plugin that runs a unit of work through a multi-agent cycle — spec, implement,
review, one rework round, final review, land — with judgement and implementation
deliberately done by different models, and the outcome reported back to the ticket that asked
for it.

```
claude plugin marketplace add HamadiSan/claude-slice
claude plugin install slice@claude-slice
```

Then just work. The skill surfaces itself when you start something substantial and **proposes**
the cycle rather than running it — four agent runs is not a decision to make on your behalf. Or ask
for it: `/slice:cycle` for the full pass, `/slice:quick` for a small change.

## The cycle

| # | Step | Role | Model (default) |
|---|---|---|---|
| 0 | Pick up the ticket | — | — |
| 1 | Write the spec | `spec` | Fable 5 |
| 2 | Implement it | `coder` | Sonnet 5 |
| 3 | Code review, with up to five mutants on risky code | `reviewer` | Opus 5 |
| 4 | Address the review — the one rework round | `coder` | Sonnet 5 |
| 5 | Final review: were the findings fixed? | `final-review` | Opus 5 |
| 6 | Document, commit, push, file follow-ups, report to the ticket | — | — |

**One review, one rework round.** After it, a blocker gets one narrow fix that the orchestrator
verifies itself; everything else becomes a follow-up ticket or a line in the closing comment, not
another round. Comment wording blocks a merge only when it would mislead about security or data.

**Mutation testing runs once**, in the first review, on risky code only — security, persistence,
wire formats, concurrency, hardware or money — and at most five mutants. The coder runs none and
the final review runs none. A full QA sweep (`slice-qa`, 20 mutants) runs only when you ask for it
on a slice, with `--qa`.

**Tests pin behaviour, not implementation**: the contract and its boundaries; for UI, goldens plus
a few semantics tests, and no pixel-arithmetic tests unless a real bug needs one.

## Choosing the models

Those are defaults. To see what is in effect and change it:

```
/slice:models                 pick each role, then where to save it
/slice:models show            just print the table and where each value came from
/slice:models reviewer        change one role
```

It shows the model for every role **and where that value came from**, because the usual question
is not "what should this be" but "why is it that". Choices persist to one of two files, both the
same shape and both free to set any subset of roles:

```json
{ "models": { "spec": "fable", "coder": "sonnet", "reviewer": "opus", "qa": "sonnet" } }
```

- `.slice.json` at the repo root — this project, checked in, shared with the team
- `~/.claude/slice.json` — every project on your machine, yours alone

Or set one for a single run: `/slice:cycle OXN-13 --reviewer=opus --coder=haiku`.

A flag beats the project file, which beats the user file, which beats the frontmatter default.
Values are `opus`, `sonnet`, `haiku` and `fable`. `final-review` is optional and falls back to
`reviewer` — split it off when you want a cheap first pass and an expensive last word, since that
is the gate that says land or do not land. The resolved models are named back to you before a run
starts, and an unrecognised value is rejected rather than silently replaced by a default.

You can run every role on one model. It is a cheaper, weaker cycle — the gates earn their keep
largely by not sharing the coder's blind spots — so the skill will say so once and then do it.

## Why mutation testing lives inside the review

Review finds claims that do not match code — a comment promising behaviour the code lacks, an
invariant asserted in prose and nowhere else, validation placed where it can never fire. A few
mutants on the risky lines find something review alone does not: tests that pass for the wrong
reason, where a line counts as covered because a test merely reaches it. Running them once, by the
agent that has just read the code against the spec, gets most of that value. Running them again in
the coder, the final review and a separate QA step mostly paid for the same answer three times.

## What this encodes

The agent prompts are the point of the plugin. They carry the things a real run cost real time to
learn:

**The spec makes the architectural decisions.** Written from the request alone, a spec invents
abstractions the tree already has under another name — so the spec agent reads the layout, the
nearest existing component and the recurring idioms first, and then names the pattern it follows
*with the path of the code it follows*. A decision left open in the spec still gets made: during
implementation, inside one file, differently in each.

**A failed cycle reports itself.** The success comment on a ticket is a convenience — there is a
merged PR either way. The comment that matters is the one a cycle posts when it gives up, because
the alternative is a ticket reading "in progress" forever, a branch nobody knows about, and
someone finding out a week later. One comment, at the end, either way. Never a comment per step.

**A follow-up is not filed until it has a number.** A cycle turns up real work it should not do,
and the reflex is to write "filed as a follow-up" and move on. Said before the ticket exists, that
sentence is the whole record — it reads as done, so nobody checks, and the finding is gone. Open
the ticket, get the ID, then write the sentence. The judgement is which findings need scheduling
rather than remembering: a backlog of speculative entries stops being read, so the ones that would
only ever make sense beside this code stay in the ticket comment.

**Reviewers get no write tools.** A reviewer that can edit what it is judging becomes a second
unsupervised author.

**Mutants run on a copy, never the real tree.** An agent that backs up, mutates and restores will
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
