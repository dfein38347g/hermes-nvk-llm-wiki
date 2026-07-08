# hermes-nvk-llm-wiki

A [Hermes](https://github.com/NousResearch/hermes-agent/tree/main) plugin adapter that syncs the
[nvk/llm-wiki](https://github.com/nvk/llm-wiki) skill bundle into Hermes'
managed-skill layout. Provides markdown adaptation, CLI management commands,
session capture hooks, and a full session state machine with checkpointing,
digest generation, and rehydration.

## Features

- **Bundle generation** — reads vendored upstream wiki files and generates 25
  Hermes-compatible `SKILL.md` files (1 root router skill + 24 command alias
  skills) under a `research/` category tree
- **Markdown adaptation** — rewrites Claude Code-specific paths, slash commands,
  and skill references to Hermes managed-skill conventions
- **CLI** — five management commands (`sync`, `doctor`, `status`, `activate`, `wiki`)
- **5 event hooks** — `system_prompt_block`, `prefetch`, `sync_turn`,
  `on_pre_compress`, `on_session_end`
- **Session state machine** — append-only event logging, checkpoint snapshots,
  ephemeral research-session state, markdown digest generation, full rehydration
- **Config management** — activates the plugin by registering its external skill
  directory and disabling the built-in llm-wiki skill
- **Health checks** — `doctor` command verifies lock file, vendor directory,
  skill root, all 24 alias files, and Hermes config wiring
- **Zero runtime dependencies** — std lib only (Python ≥ 3.11)

## Architecture

```
├── plugin.yaml                 — Hermes plugin manifest (5 hooks, 24 aliases)
├── upstream.lock.json          — pinned version + commit of nvk/llm-wiki
├── runtime.py                  — bundle sync, markdown adaptation, doctor, config, status
├── cli.py                      — argparse CLI with sync/doctor/status/activate/wiki
├── session.py                  — event log, checkpoint, state, digest, rehydration
├── hooks/
│   ├── system_prompt.py        — injects wiki hub stats into system prompt
│   ├── prefetch.py             — loads checkpoint for session rehydration
│   ├── sync_turn.py            — appends redacted turn data to session log
│   ├── on_session_end.py       — writes final checkpoint + markdown digest
│   └── __init__.py
├── __init__.py                 — plugin entry point: register() called by Hermes
├── tests/
│   ├── fixtures/golden-vendor/ — vendored upstream files for test sync
│   ├── test_adaptation.py      — markdown path/command rewrites
│   ├── test_aliases.py         — alias skill frontmatter + content
│   ├── test_bundle.py          — full bundle generation
│   ├── test_cli.py             — argparse + command routing
│   ├── test_config.py          — config management helpers
│   ├── test_doctor.py          — health check logic
│   ├── test_frontmatter.py     — YAML frontmatter parsing
│   ├── test_hooks.py           — all 5 hook implementations
│   ├── test_init.py            — plugin registration
│   ├── test_integration.py     — full sync → doctor → alias cycle
│   ├── test_plugin_yaml.py     — manifest validation
│   └── test_session.py         — event log, checkpoint, digest, rehydration
└── pyproject.toml
```

## CLI Usage

The plugin registers a `wiki` CLI command with Hermes. It can also run standalone:

```
python -m cli sync --vendor path/to/vendor --output path/to/output --lock upstream.lock.json
python -m cli doctor --lock upstream.lock.json --vendor path/to/vendor --skill-root path/to/skill-root --config config.json
python -m cli doctor --lock upstream.lock.json --vendor path/to/vendor --skill-root path/to/skill-root --config config.json --fix
python -m cli status --lock upstream.lock.json --skill-root path/to/skill-root --config config.json
python -m cli activate --config config.json --managed-root path/to/managed-root
python -m cli wiki <command> [args...]
```

The sync workflow reads vendored upstream files (from `tests/fixtures/golden-vendor/`
in this repo) and generates Hermes-compatible SKILL.md files under a
`research/` category tree:

- **Root skill** `research/wiki/` — router skill for the wiki hub, includes
  `.hub/commands/*.md` and `.hub/skills/wiki-manager/references/` assets
- **Alias skills** `research/wiki-{command}/` — one per upstream wiki command
  (24 total), each wrapping a vendored upstream `.md` with Hermes-native
  frontmatter, usage guidelines, and adapted paths

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v     # 89 tests
```

Requirements: Python ≥ 3.11 (no runtime dependencies; pytest for dev).

## License

MIT
