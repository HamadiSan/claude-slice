# slice

See the [repository README](../../README.md) for what this is and why.

```
plugins/slice/
├── skills/cycle/SKILL.md   the full eight-step cycle, bracketed by the ticket
├── skills/quick/SKILL.md   the four-step version for small changes
└── agents/
    ├── slice-spec.md       Fable 5  — reads the codebase, then decides, decisively
    ├── slice-coder.md      Sonnet 5 — implements and reworks, licensed to disagree
    ├── slice-reviewer.md   Opus 5   — read-only; hunts claims that do not match code
    └── slice-qa.md         Opus 5   — mutation-tests on a copy of the tree
```

Those models are **defaults**. Each role is selectable per invocation (`--reviewer=opus`) or per
project (`.slice.json` at the repo root) — see
[Choosing the models](../../README.md#choosing-the-models).

The frontmatter pins a full id (`claude-opus-5`, not `opus`) so the default tiering survives alias
drift. The override takes the short alias instead, because that is what the `Agent` tool's `model`
parameter accepts — so a resolved model is translated, never passed through as a long id.
