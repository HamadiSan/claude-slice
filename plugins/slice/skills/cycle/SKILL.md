---
name: cycle
description: Run a substantial piece of work through a full multi-agent cycle - spec, implement, review (with a few targeted mutants on risky code), one rework round, final review, then land, then report the outcome back to the tracked ticket whether the cycle succeeded or failed. Use when implementing a new package, module, subsystem or feature of real size, or when the user asks for a thorough or high-assurance build. PROPOSE this before starting; do not run it unprompted, it is expensive.
argument-hint: [what to build] [--role=model ...] [--qa]
---

# The slice cycle

A unit of work goes through six steps, with judgement and implementation deliberately done by
different models, bracketed by the ticket that asked for it.

| # | Step | Agent | Role | Model (default) |
|---|---|---|---|---|
| 0 | Pick up the ticket | you | — | — |
| 1 | Write the spec | `slice-spec` | `spec` | Fable 5.1 |
| 2 | Implement it | `slice-coder` | `coder` | Sonnet 5 |
| 3 | Code review, with up to five mutants on risky code | `slice-reviewer` | `reviewer` | Opus 5.5 |
| 4 | Address the review — **the one rework round** | `slice-coder` | `coder` | Sonnet 5 |
| 5 | Final review: were the findings fixed? | `slice-reviewer` | `final-review` | Opus 5.5 |
| 6 | Document, commit, push, file follow-ups, report to the ticket | you | — | — |

A full mutation-testing QA pass (`slice-qa`) is **not** a step. It runs only when the user asks
for it on a specific slice — see **Full QA, on request only**.

## Choosing the model for each role

**The Model column is a default, not a fixture.** Every role is selectable per invocation or per
project.

**Resolve each role's model in this order**, highest priority first:

1. **What the user asked for in the invocation** —
   `/slice:cycle OXN-13 --reviewer=opus --coder=haiku`.
2. **The project's `.slice.json`**, if one exists at the repo root:
   ```json
   {
     "models": { "spec": "fable", "coder": "sonnet", "reviewer": "claude-opus-5-5" },
     "effort": { "reviewer": "high" }
   }
   ```
   It is checked in, so a team shares one answer instead of each person remembering flags.
3. **The user's `~/.claude/slice.json`**, same shape — their standing preference across every
   project on this machine.
4. **The agent's own frontmatter** — the defaults in the table above.

Read the two files once, at the start of the run. Either may set any subset of roles, so resolve
role by role rather than taking the first file that exists whole. `/slice:models` is the
interactive way to set them; nothing here requires that they were written by it.

**Roles.** Four — `spec`, `coder`, `reviewer`, `qa` — plus an optional `final-review`, which falls
back to `reviewer` when unset. `qa` only matters when a full QA pass was asked for. One `coder`
setting covers both of its steps. Splitting
`final-review` off is worth it when someone wants a cheap first pass and an expensive last word,
since that is the gate that says land or do not land.

### Two kinds of value, and two different routes

A role's model may be written either way, and **which one is written decides how it reaches the
agent**:

| Value | Example | How it is delivered |
|---|---|---|
| **Short alias** | `opus`, `sonnet`, `haiku`, `fable` | Pass it on the `Agent` call's `model` parameter. |
| **Full model id** | `claude-opus-5-5`, `claude-haiku-4-5` | **Omit the `model` parameter.** The id must already be that agent's frontmatter, and the frontmatter is what carries it. |

This split is not a style preference. **The `Agent` tool's `model` parameter accepts only the four
aliases and rejects anything else outright** — a full id passed there fails validation; it does not
degrade to something close. Agent frontmatter is the only place a full id is accepted. So a
full-id role runs by *not* overriding the frontmatter, which means the config and the frontmatter
have to agree.

**Check that they agree, and stop if they do not.** When a role resolves to a full id that is not
what that agent's frontmatter says, the id cannot be delivered. Say so and stop. Passing the
nearest alias instead is silently running a different model.

Prefer an **alias** when the intent is "the current best of this family", and let it drift upward
on purpose. Prefer a **full id** when the intent is one specific model — which makes the next rule
load-bearing.

### A full id fails silently. Probe it.

**When a full model id is unavailable to the account, the subagent does not error. It falls back to
the inherited model and runs.** Nothing announces the substitution. An entire cycle can therefore
be configured for one model, complete on another, and report the first.

So **probe each distinct full id once, before step 1**: spawn that agent with a throwaway prompt
asking only for the model id named in its own system prompt, and compare it against what was
resolved. Two or three short calls cost nothing beside a full cycle, and they turn a silent
substitution into a stated fact.

**Report the model each role actually ran on, not the one it was configured with.** An unverified
id in a ticket comment is a claim the run cannot support — the exact defect class these gates
exist to catch, committed by the cycle itself.

### Effort

Effort is **not** a parameter on the `Agent` tool, and there is no per-agent effort field. It comes
from Claude Code's own settings:

- `effortLevel` — the global default;
- `modelSettings.<full-model-id>.effortLevel` — per model, overriding the global;
- `maxEffortLevel` — a cap.

Two consequences follow. Both are real limits, not gaps to be worked around:

**Effort attaches to a model, not to a role.** Two roles on the same model necessarily get the same
effort. If the config asks for two different efforts on one model, that is unsatisfiable — say so
and stop, rather than honouring one of them quietly.

**This plugin cannot set effort. It resolves, checks and reports it.** The `effort` block is a
statement of intent, and settings are what decide. At resolve time read the effective
`effortLevel` for each role's model and **compare**. When they disagree, name both values and say
which won; do not restate the config as though it were the outcome.

**Name what you resolved before step 1**, one line per role: the model, whether it arrived as an
alias or a full id, where the value came from, and the effective effort. Someone who set
`coder=haiku` in `.slice.json` three weeks ago and forgot deserves to learn that before spending a
cycle, not while reading the diff.

**Reject a value you do not recognise instead of falling back to the default.** A typo'd
`--reviewer=opus5` that silently runs something else is precisely the failure nobody catches until
a gate has already missed something. Recognised means one of the four aliases, or a full id shaped
`claude-<family>-<version>`. Anything else is a typo, not a model.

## Before you start: propose, do not assume

This is four agent runs and, for a package of real size, a large amount of wall clock and tokens.
**Tell the user roughly what it will cost and ask whether they want it**, unless they have
already asked for the cycle by name.

If the work is small — a bug fix, one function, a config change — say so and offer `/slice:quick`
or just doing it directly. Running six steps on a typo is a bad trade and reflects badly on the
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
comment per step. A ticket narrating every agent handoff is noise, and the next person to open it
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

Post it if the run ends **for any reason**: a blocker left after the rework round, a gate you
could not satisfy, the user calling it off, or an error that stopped the run.

**Follow-ups get their own ticket, not a sentence.** A cycle generates work it should not do:
a finding that is real but out of scope, a defect in a neighbouring package, a design change too
large for this slice. Some of that belongs in the ticket comment; some of it needs to be
*scheduled*, and a comment on a closed ticket is never scheduled. Open a ticket when the finding
needs someone to plan it — it will be worked separately, it blocks or anticipates another ticket,
or it is a correctness, security or data-integrity property. Leave it in the comment when it is
context for whoever next touches this code, and would only ever be read next to it.

Do not open one per finding. Three tickets nobody triages are worse than three sentences someone
reads, and a backlog full of speculative entries stops being looked at. If you cannot say who
would pick it up and why it matters, it is a comment.

The ticket has to carry enough that a stranger can act on it: what the defect is, the measured
consequence rather than the theory, where it lives, and what "done" means. Link it back to the
cycle that found it, and link it from the originating ticket's comment. If it is blocked by the
work you just landed, say so in the tracker rather than in prose.

**A follow-up is not filed until it has an identifier.** Never tell the user, a ticket, or a
commit message that something is "filed as a follow-up" until the tracker has returned an ID —
saying it first and creating it later means it does not exist, and the sentence reads as though
it does. This is the same rule as *never report a ticket as updated when the write did not land*,
and it fails the same way: the work feels finished, so the bookkeeping gets narrated instead of
done. If the tracker is unreachable, say the follow-up is unfiled and give the user the text.

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
never see uncommitted work, and a gate that mutates and restores can otherwise revert work that
landed while it ran. Commit messages at intermediate steps should say they are checkpoints.

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

**One review, one rework round.** This is the rule that most decides what a cycle costs. Every
extra round re-reads the code, re-runs the suites and invites a new batch of findings about the
previous round's tests, and in practice the later rounds find little the first review did not.

- The first review's findings go to the coder **once**, as one batch.
- The final review checks that those findings were fixed and that the fix broke nothing. It does
  not open new lines of inquiry and it runs no mutants.
- What the final review still finds is sorted, not re-cycled:
  - **A blocker** (wrong behaviour, a security hole, data loss, a red build) gets one narrow fix.
    You verify that fix yourself — the build, the tests, the specific scenario — with no further
    review round.
  - **Everything else** — majors that are not blockers, minors, nits, test-coverage gaps — becomes
    a follow-up ticket or a line in the closing comment. It does not start another round.
- If the narrow fix does not resolve the blocker, stop and bring it to the user. Work that will
  not converge in one round usually has a problem in its specification, not its code. Stopping is
  an outcome: comment on the ticket before you hand it back.

**Comment wording blocks a merge only when it would mislead about security or data** — a comment
claiming a check, an isolation or a guarantee the code does not have. Any other comment that
claims more than the code does is a nit: list it for the coder's single round if it is cheap,
otherwise put it in the closing comment. It never earns a round of its own.

**CI failures are not review rounds.** A red CI on the PR is fixed directly and verified by CI. It
does not reopen the review.

**Write down every finding you decline.** A finding recorded in a comment, a test name, or a
spec's open-questions section survives being deprioritised. One that is only argued in a review and
then declined does not exist a week later — and the ones that come back are the ones nobody wrote
down. This costs a sentence and it is the cheapest insurance in the cycle. Where the declined
finding needs scheduling rather than remembering, it gets its own ticket — see **The ticket**.

## Mutation testing: once, in the first review, on risky code

Mutation testing answers a question review alone cannot: *would the tests notice if this broke?*
It finds tests that pass for the wrong reason — a check satisfied by a comment, a guard that does
nothing in a release build, an assertion that can never fire. It is also expensive: every mutant is
a rebuild and a test run, and every survivor tends to start another round of test writing.

So it runs **in one place**, the first review (step 3), and nowhere else:

- **The reviewer runs up to five mutants**, through the plugin's `scripts/mutate.py`, only on
  changed lines in these categories:
  - security, authorisation or tenant isolation, or anything that refuses a request;
  - persistence: SQL, migrations, ordering, idempotency, anything that writes;
  - a wire format, protocol or API contract another process depends on;
  - concurrency, timeouts, deadlines, retries or resource cleanup;
  - code that controls hardware or money.
- **A change with none of those** — documentation, presentational UI, glue — gets no mutants.
- **A surviving mutant is an ordinary finding.** It goes into the one rework round with the rest.
- **The coder runs no mutation table** and the final review runs no mutants. A coder proves a test
  works by seeing it fail before the fix, not with a separate mutation run.

Say in the ticket comment how many mutants ran and on what, or "no mutants: no risky code".

## Full QA, on request only

`slice-qa` runs a full sweep — a 20-mutant budget, ranked by consequence, on a copy of the tree.
It runs **only when the user asks for it** on a specific slice, with `--qa` or in words. Suggest it,
once, when a slice is mostly security or persistence code — an auth layer, RLS policies, a new
storage engine — and let the user decide. When it runs, it sits between steps 4 and 5, its
survivors go to the coder in the same single rework round where possible, and it runs on Sonnet by
default. Set `qa` to `opus` for a project where QA has to reason about subtle concurrency or
cryptography.

## What tests to ask for

Tokens spent on tests that pin implementation detail are spent twice: once to write them, and again
every time a later change has to update them. Ask for, and accept, tests of **behaviour**:

- **Test the contract and its boundaries**: inputs and outputs, error identities, permission
  refusals, persistence effects, the edge values of a limit. Not private helpers, call order or
  intermediate values.
- **UI**: goldens for appearance, plus a few semantics tests per component — label, role, enabled
  state, the one interaction that matters. No pixel-measurement or layout-arithmetic tests unless
  a real bug needs one to stay fixed.
- **No test per review comment.** A reviewer naming a gap is not an instruction to add a test for
  it; add one when the gap is behaviour a user or another system depends on.

The reviewer should hold the coder to this, and should not ask for tests that only pin how the code
happens to be written.

## What each gate is for

- **Review** finds claims that do not match code — a comment promising behaviour the
  implementation lacks, an invariant asserted in prose and nowhere else, validation that can never
  fire — and, through its few mutants, the tests on risky code that would not notice a regression.
- **The final review** confirms the findings were fixed and nothing regressed. It is a check, not a
  second review.

## Landing

Step 6 is yours. Write the commit message so it explains **what the gates found and why it
mattered** — the defects and their consequences, not a list of files. That message is the only
durable record of why the code is shaped as it is, and it is worth more than the diff. Then open
any follow-up tickets the run earned, so the closing comment can link them by ID rather than
promise them; then post that comment, and only then tell the user you are done.

If the project keeps a workflow or decisions document, add anything the cycle taught you about
the process itself.
