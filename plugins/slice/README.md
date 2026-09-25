# slice

See the [repository README](../../README.md) for what this is and why.

```
plugins/slice/
├── skills/cycle/SKILL.md   the full eight-step cycle, bracketed by the ticket
├── skills/quick/SKILL.md   the four-step version for small changes
├── skills/models/SKILL.md  interactive picker: which model each role runs on
└── agents/
    ├── slice-spec.md       Fable 5.1 — reads the codebase, then decides, decisively
    ├── slice-coder.md      Sonnet 5  — implements and reworks, licensed to disagree
    ├── slice-reviewer.md   Opus 5.5  — read-only; hunts claims that do not match code
    └── slice-qa.md         Opus 5.5  — mutation-tests on a copy of the tree
```

Those models are **defaults**. `/slice:models` shows what is in effect, where each value came
from, and writes a change to `.slice.json` (this project) or `~/.claude/slice.json` (all
projects); `--reviewer=opus` overrides either for one run. See
[Choosing the models](../../README.md#choosing-the-models).

A role takes **either** a short alias (`opus`, `sonnet`, `haiku`, `fable`) **or** a full model id
(`claude-opus-5-5`). They travel by different routes, and that is a property of the tooling rather
than a preference: the `Agent` tool's `model` parameter accepts only the four aliases and rejects a
full id outright, while agent frontmatter accepts only a full id. So an alias is passed on the
call, and a full id is delivered by leaving the frontmatter alone — which means config and
frontmatter must agree, and the cycle stops when they do not.

Pick an alias to track a family's current best, and a full id to pin one model. The pin has a
sharp edge worth knowing: **a full id the account cannot use does not error — the subagent falls
back to the inherited model and runs.** The cycle therefore probes each full id once before step 1
and reports the model that actually ran, never the one that was configured.

Effort is a Claude Code setting (`effortLevel`, `modelSettings.<id>.effortLevel`), not something
this plugin can set. The optional `effort` block records intent; the cycle resolves it, compares it
against settings, and says which won. Effort attaches to a model, so roles sharing a model share
its effort.
