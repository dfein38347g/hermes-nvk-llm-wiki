# hermes-nvk-llm-wiki

A [Hermes](https://github.com/anomalyco/opencode) plugin adapter that syncs the
[nvk/llm-wiki](https://github.com/nvk/llm-wiki) skill bundle into Hermes'
managed-skill layout.

## Architecture

```
upstream.lock.json         — pinned version + commit of nvk/llm-wiki
runtime.py                 — sync, doctor, config helpers
cli.py                     — Hermes hook handlers
session.py                 — Hermes hook handlers
hooks/                     — Hermes event hooks
```

The sync workflow reads vendored upstream files from `tests/fixtures/golden-vendor/`
and generates Hermes-compatible SKILL.md files under a `research/` category tree.

- **Root skill** `research/wiki/` — router skill for the wiki hub
- **Alias skills** `research/wiki-{command}/` — one per upstream wiki command (24 total)

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
