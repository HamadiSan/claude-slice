# slice

See the [repository README](../../README.md) for what this is and why.

```
plugins/slice/
├── skills/cycle/SKILL.md   the full eight-step cycle
├── skills/quick/SKILL.md   the four-step version for small changes
└── agents/
    ├── slice-spec.md       Fable 5  — writes the spec, decisively
    ├── slice-coder.md      Sonnet 5 — implements and reworks, licensed to disagree
    ├── slice-reviewer.md   Opus 5   — read-only; hunts claims that do not match code
    └── slice-qa.md         Opus 5   — mutation-tests on a copy of the tree
```

Models are pinned by full id (`claude-opus-5`, not `opus`) so the tiering survives alias drift.
