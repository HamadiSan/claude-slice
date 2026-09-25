---
name: models
description: Pick and persist which model each slice role runs on - spec, coder, reviewer, qa, final-review - as a short alias or a full model id. Shows what is currently in effect, where it came from and the effort that will apply, then writes the choice to this project or to all projects. Use ONLY when the user asks to see or change slice models; never run it as part of a cycle.
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
{
  "models": { "spec": "fable", "coder": "sonnet", "reviewer": "claude-opus-5-5", "qa": "claude-opus-5-5" },
  "effort": { "reviewer": "high", "qa": "high" }
}
```

Roles are `spec`, `coder`, `reviewer`, `qa`, and the optional `final-review`, which falls back to
`reviewer` when unset.

**A model value is either a short alias or a full model id.** The two are not interchangeable in
how they reach the agent, and the difference is worth stating here because it decides what this
skill is allowed to offer:

- **Aliases** — `opus`, `sonnet`, `haiku`, `fable` — ride the `Agent` tool's `model` parameter, and
  track whatever that family's current best is.
- **Full ids** — `claude-opus-5-5`, `claude-haiku-4-5` — are rejected by that parameter, so they
  can only be carried by the agent's own frontmatter. Offering a full id that the frontmatter does
  not already name would write a setting the cycle has to refuse. **Check the frontmatter before
  offering one**, and say plainly when a pin is not available rather than writing it and letting
  the cycle discover it.

A full id that the account cannot use does not error — the subagent quietly runs the inherited
model instead. That is why the cycle probes a full id before using it, and why this skill should
never present a pin as confirmed simply because it was written to a file.

**Effort is a Claude Code setting, not a slice one.** `effortLevel` globally,
`modelSettings.<full-model-id>.effortLevel` per model. The `effort` block here is a statement of
intent that the cycle resolves, compares against settings, and reports — **this plugin cannot
apply it**. Two more limits follow from that: effort attaches to a *model*, so two roles sharing
one model necessarily share its effort; and when the block and settings disagree, settings win.
Say so rather than showing the intent as though it were the result.

## Running it

**First, always: read all four sources and show what is in effect.** One table, one row per role,
naming the model, *where it came from*, and the effective effort — "claude-opus-5-5 (user) ·
high (modelSettings)", "sonnet (default) · xhigh (global)". A user cannot sensibly change a
setting they cannot currently see, and the most common real question here is not "what should this
be" but "why is it that". Read effort from Claude Code's settings, never from the `effort` block —
the block records what was asked for, and the two can disagree.

If the argument is `show`, stop there. That is the whole command.

**Then ask.** Use `AskUserQuestion`, which renders the selectable UI. It caps at four questions
per call and four options per question, so the walk is two round trips:

- **Call 1 — four questions**, one per core role: `spec`, `coder`, `reviewer`, `qa`. Options are
  the models available for that role — the aliases, plus any full id the agent's frontmatter
  actually pins. **List the current value first and mark it `(current)`** in its label, so
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
