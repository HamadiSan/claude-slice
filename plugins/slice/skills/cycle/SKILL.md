---
name: cycle
description: Run a substantial piece of work through a full multi-agent cycle - spec, implement, review, rework, mutation-test QA, rework, final review, then land, then report the outcome back to the tracked ticket whether the cycle succeeded or failed. Use when implementing a new package, module, subsystem or feature of real size, or when the user asks for a thorough or high-assurance build. PROPOSE this before starting; do not run it unprompted, it is expensive.
argument-hint: [what to build] [--role=model ...]
---

# The slice cycle

A unit of work goes through eight steps, with judgement and implementation deliberately done by
different models, bracketed by the ticket that asked for it.

| # | Step | Agent | Role | Model (default) |
|---|---|---|---|---|
| 0 | Pick up the ticket | you | — | — |
| 1 | Write the spec | `slice-spec` | `spec` | Fable 5 |
| 2 | Implement it | `slice-coder` | `coder` | Sonnet 5 |
| 3 | Code review | `slice-reviewer` | `reviewer` | Opus 5 |
| 4 | Address the review | `slice-coder` | `coder` | Sonnet 5 |
| 5 | QA / mutation testing | `slice-qa` | `qa` | Opus 5 |
| 6 | Address QA | `slice-coder` | `coder` | Sonnet 5 |
| 7 | Final review | `slice-reviewer` | `final-review` | Opus 5 |
| 8 | Document, commit, push, report to the ticket | you | — | — |

## Choosing the model for each role

**The Model column is a default, not a fixture.** The `Agent` tool's `model` parameter overrides
whatever an agent definition declares, so every role is selectable per invocation or per project.

**Resolve each role's model in this order**, highest priority first:

1. **What the user asked for in the invocation** —
   `/slice:cycle OXN-13 --reviewer=opus --coder=haiku`.
2. **The project's `.slice.json`**, if one exists at the repo root:
   ```json
   { "models": { "spec": "fable", "coder": "sonnet", "reviewer": "opus", "qa": "opus" } }
   ```
   It is checked in, so a team shares one answer instead of each person remembering flags.
3. **The user's `~/.claude/slice.json`**, same shape — their standing preference across every
   project on this machine.
4. **The agent's own frontmatter** — the defaults in the table above.

Read the two files once, at the start of the run. Either may set any subset of roles, so resolve
role by role rather than taking the first file that exists whole. `/slice:models` is the
interactive way to set them; nothing here requires that they were written by it.

Then **pass the resolved model explicitly on every `Agent` call**, even when it matches the
default. Relying on the frontmatter makes a run you cannot describe afterwards; passing it means
you can say in the ticket comment which models actually ran.

**Roles and values.** Four roles — `spec`, `coder`, `reviewer`, `qa` — plus an optional
`final-review`, which falls back to `reviewer` when unset. One `coder` setting covers all three
of its steps. Splitting `final-review` off is worth it when someone wants a cheap first pass and
an expensive last word, since that is the gate that says land or do not land.

Values are the short aliases the `Agent` tool accepts: `opus`, `sonnet`, `haiku`, `fable`. The
agent files spell their defaults as full IDs (`claude-opus-5`) — translate to the alias rather
than passing the long form through, which the tool will reject.

**Name what you resolved before step 1**, in one line. Someone who set `coder=haiku` in
`.slice.json` three weeks ago and forgot deserves to learn that before spending a cycle, not
while reading the diff.

**Reject a value you do not recognise instead of falling back to the default.** A typo'd
`--reviewer=opus5` that silently runs something else is precisely the failure nobody catches
until a gate has already missed something.

**If asked to run every role on one model, do it — and say once what it costs.** This cycle's
premise is that judgement and implementation come from *different* models; the gates earn their
keep largely by not sharing the coder's blind spots. One model everywhere is a cheaper, weaker
cycle. That is the user's call to make: recommend against it once, then run what they asked for.

## Before you start: propose, do not assume

This is seven agents and, for a package of real size, a large amount of wall clock and tokens.
**Tell the user roughly what it will cost and ask whether they want it**, unless they have
already asked for the cycle by name.

If the work is small — a bug fix, one function, a config change — say so and offer `/slice:quick`
or just doing it directly. Running eight steps on a typo is a bad trade and reflects badly on the
tool.

## The ticket

Most cycles exist because something is tracked — a Linear issue, a Jira ticket, a GitHub issue.
When one does, it brackets the run: it is an input to the spec, and it gets the outcome.

**At the start.** Establish the ticket from what the user gave you, from the branch name, or by
asking — once. Read it *including its comments*; the discussion under a ticket routinely holds the
constraint that never made it into the description. Pass it to `slice-spec` alongside the request,
so the spec is written against what was actually asked for rather than a paraphrase of it. If
there is genuinely no ticket, say so and carry on. Do not open one just to have something to
update.

**At the end, exactly once, whichever way it went.** One comment, when the run is over — not a
comment per step. A ticket narrating eight agent handoffs is noise, and the next person to open it
learns to skim past anything you wrote.

On success the comment says what shipped, **what the gates found and why it mattered**, the commit
or PR link, and anything declined with the reason it was declined. On failure it says where the
run stopped, which gate blocked it and on which finding, what state the branch is in, and what a
human now has to decide.

**The failure comment is the one that matters.** A cycle that converges leaves a merged PR and a
green build; its ticket comment is a convenience. A cycle that gives up leaves a ticket still
reading "in progress", a branch nobody knows exists, and someone finding out a week later. Post it
*before* you report back to the user — by then the run feels finished, which is exactly why this
is the step that gets skipped.

Post it if the run ends **for any reason**: two cycles without convergence, a gate you could not
satisfy, the user calling it off, or an error that stopped the run.

**Comment; do not silently transition.** Moving a ticket to In Review or Done touches other
people's boards and fires automation you cannot see. Transition it when the user asked you to or
the project's convention is written down — otherwise name the transition you would make and let
them make it.

**How to post it**, in order of preference: the tracker's MCP server if one is connected (Linear
`save_comment`, Jira `addCommentToJiraIssue`), otherwise its CLI (`gh issue comment`). If neither
is reachable, put the comment verbatim in your report to the user and mark it as unposted so they
can paste it. Never report a ticket as updated when the write did not land.

Keep out of the comment: secrets, tokens, whole diffs, raw agent transcripts. A ticket is usually
readable by more people than the repository is.

## Running it

**Between every step, commit.** The tree must be committed before a gate agent starts. Gates must
never see uncommitted work, and a QA agent that mutates and restores can otherwise revert work
that landed while it ran. Commit messages at intermediate steps should say they are checkpoints.

**Verify each agent's claims yourself.** Do not take "all tests pass" on trust — run the build,
the tests and the linter after every step. An agent reporting success it did not achieve is rare
but not rare enough, and you are the one landing this.

**Pass findings through a file, not a prompt — and you are the one who writes it.** The gate
agents have no write tools, deliberately: a reviewer that can edit what it is judging becomes a
second unsupervised author. So a gate returns its findings in its final message and *you* write
them to a scratch file, then point the fixer at that file. Do not instruct a gate to write the
file itself; it will correctly refuse, and you will have spent a round trip on the refusal.
Long findings pasted into a prompt lose their structure, and a file gives the fixer something to
work through methodically.

**Two cycles maximum.** If the final review still says DO NOT LAND after a second full pass, stop
and bring it to the user. Work that will not converge in two rounds usually has a problem in its
specification, not its code, and a third round will not find it. Stopping is an outcome: comment
on the ticket before you hand it back.

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
durable record of why the code is shaped as it is, and it is worth more than the diff. Then post
the ticket comment, and only then tell the user you are done.

If the project keeps a workflow or decisions document, add anything the cycle taught you about
the process itself.
