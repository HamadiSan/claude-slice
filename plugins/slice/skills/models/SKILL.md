---
name: models
description: Pick and persist which model each slice role runs on - spec, coder, reviewer, qa, final-review. Shows what is currently in effect and where it came from, then writes the choice to this project or to all projects. Use ONLY when the user asks to see or change slice models; never run it as part of a cycle.
argument-hint: [show | <role>]
---

# Choosing the models

An interactive picker for the model behind each role, and where that choice is stored.

**Do not run this from inside a cycle.** A cycle resolves models silently and reports what it
resolved; stopping mid-run to ask is not the same thing. This skill runs only when the user asks
for it by name.

## What is stored where

Four sources, most specific wins:

| Precedence | Source | Scope |
|---|---|---|
| 1 | invocation flag — `/slice:cycle X --reviewer=opus` | one run |
| 2 | `.slice.json` at the repo root | this project, checked in, shared with the team |
| 3 | `~/.claude/slice.json` | every project, this machine, yours alone |
| 4 | agent frontmatter | the shipped defaults |

Both files use the same shape, and both may set any subset of roles:

```json
{ "models": { "spec": "fable", "coder": "sonnet", "reviewer": "opus", "qa": "opus" } }
```

Roles are `spec`, `coder`, `reviewer`, `qa`, and the optional `final-review`, which falls back to
`reviewer` when unset. Values are `opus`, `sonnet`, `haiku`, `fable`.

## Running it

**First, always: read all four sources and show what is in effect.** One table, one row per role,
naming the model *and where it came from* — "opus (project)", "sonnet (default)". A user cannot
sensibly change a setting they cannot currently see, and the most common real question here is
not "what should this be" but "why is it that".

If the argument is `show`, stop there. That is the whole command.

**Then ask.** Use `AskUserQuestion`, which renders the selectable UI. It caps at four questions
per call and four options per question, so the walk is two round trips:

- **Call 1 — four questions**, one per core role: `spec`, `coder`, `reviewer`, `qa`. Options are
  the four models. **List the current value first and mark it `(current)`** in its label, so
  keeping a setting is the first thing under the cursor and changing one is deliberate. Put the
  trade in each option's description — what that model is good and bad at for *that role*, not a
  generic blurb.
- **Call 2 — one question**: where to persist. `This project (.slice.json)` versus
  `All projects (~/.claude/slice.json)`. Ask it *after* the models, not before: the answer only
  matters once something is actually being changed, and asking first makes the user commit to a
  scope before knowing what they are scoping.

`final-review` is deliberately not in the walk. It falls back to `reviewer`, most people never
set it, and a fifth question to say "same as the one above" for the fourth time is a worse
default than leaving it out. It is reachable directly: `/slice:models final-review`.

**A single role as the argument** — `/slice:models reviewer` — is one round trip: that role's
question plus the scope question, in one call. Use this shape whenever the user names a role,
and offer `Same as reviewer` as the first option when the role is `final-review`.

## Writing it

**Merge; never overwrite the file.** Read the existing JSON, change only the roles the user just
answered, write it back. Someone may have keys in there this skill did not put there, and a
picker that silently drops a neighbouring setting is a bad trade for saving a read.

**Write only what changed from the shipped default.** A file pinning all five roles to the values
they already have is noise that will drift out of date and then quietly contradict a future
change to the defaults. If a role ends up back at its default, remove its key rather than writing
the default in explicitly.

**Create the parent directory if it is missing**, and if the JSON on disk is malformed, say so and
stop — do not repair it by overwriting, because the file may hold something the user wants back.

**If there is no repo** — no git root, or the user is somewhere transient — the project option is
meaningless. Say so and offer only the user-level file rather than writing `.slice.json` into
whatever directory happens to be current.

## Afterwards

**Print the effective table again**, the same shape as the one at the start, plus one line naming
the file that was written. The point of the second table is that the user sees the *result* of
the cascade, not just their answer — a project file can be shadowed by a flag, and a user-level
change can be invisible because the project already pins that role. That is exactly the confusion
this skill exists to end, and showing it costs one table.

Mention `.slice.json` is checked in when that is where the write went. It changes how a team's
cycles run, which is usually the intent, and occasionally a surprise.
