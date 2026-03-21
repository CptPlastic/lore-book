# Lore

Lore is a local memory system for software projects.

It captures decisions, facts, and lessons in plain files so your AI coding tools can use shared context across sessions.

## Start Here

- [Install](install.md)
- [Core Concepts](concepts.md)
- [CLI Reference](cli.md)
- [FAQ](faq.md)

## How It Works

1. Add memory entries with `lore add`.
2. Search memory with `lore search`.
3. Export context files with `lore export`.

## Quick Example

```bash
lore onboard
lore add decisions "Use PostgreSQL for row-level locking"
lore search "why did we choose postgres"
lore export
```

## Notes

If you are migrating existing docs, place markdown files in `docs/` and update navigation in `mkdocs.yml`.
