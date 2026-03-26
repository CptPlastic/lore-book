# 📜 lore

> *The spellbook for your codebase — chronicle decisions, context, and lessons your AI companions can actually read.*

**Lore** is a local AI memory system for software projects. It stores what you know as plain YAML alongside your code — then publishes that knowledge as instruction files that GitHub Copilot, Claude, Cursor, Codex, and other AI tools read automatically.

No external database. No API keys. No cloud sync. Everything lives in `.lore/` next to your code.

By default, lore exports **CHRONICLE.md plus all agent adapter files** so security and instruction preambles are consistently written for every tool.

---

## How it works

AI coding tools are stateless — they don't remember why you chose PostgreSQL over SQLite, that the auth layer must never bypass JWT validation, or that the frontend team deprecated the v1 API six months ago. You end up re-explaining the same context in every session.

Lore fixes that. You capture knowledge once; every AI session inherits it automatically.

```
Your decisions, facts, and lessons
        ↓  lore add / lore relic
  .lore/ (plain YAML)
        ↓  lore export
  CHRONICLE.md  ←  full project memory (one source of truth)
        ↓ referenced by lean instruction files:
  copilot-instructions.md · AGENTS.md · CLAUDE.md · .cursor/rules/memory.md
        ↓ on-demand:
  /lore  →  reads CHRONICLE.md into AI context when you ask
        ↓
  Every AI tool reads your repo context — without you repeating yourself
```

---

## Core concepts

### Spell *(memory)*

A single piece of knowledge: a decision, a fact, a hard-won lesson. Short, specific, retrievable by semantic search.

```sh
lore add decisions "Use PostgreSQL — we need JSONB and row-level locking"
lore add facts     "Auth service is the sole issuer of JWTs — never bypass it"
lore add preferences "Prefer explicit over clever — this codebase has many contributors"
```

### Tome *(category)*

A named collection of spells. Default tomes: **decisions, facts, preferences, summaries**. You can add your own in `.lore/config.yaml`.

Tomes are just directory names — each spell is one YAML file filed under its tome.

### Relic

A raw artifact saved as-is for later processing. Use a relic when things are moving fast and you don't have time to curate.

> Capture a relic now → distill spells from it later.

A relic can be anything: a pasted session log, a git diff, a doc excerpt from Confluence, a long Slack thread. It lands in `.lore/relics/` untouched. When you have time, you open it with `lore relic distill` and choose exactly which parts become proper spells.

### Export *(the chronicle)*

`lore export` writes your spells into the files AI tools pick up automatically, using a **two-layer architecture**:

**`CHRONICLE.md`** — the single source of truth. Contains every spell grouped by tome. All lean instruction files reference it.

| Lean instruction file | Tool | On by default |
|---|---|:---:|
| `CHRONICLE.md` | All tools (full memory) | ✅ |
| `.github/copilot-instructions.md` | GitHub Copilot | ✅ |
| `AGENTS.md` | OpenAI Codex, agent frameworks | ✅ |
| `CLAUDE.md` | Anthropic Claude | ✅ |
| `.cursor/rules/memory.md` | Cursor | ✅ |
| `.github/prompts/lore.prompt.md` | `/lore` trigger in Copilot Chat | ✅ |
| `.windsurfrules` | Windsurf / Codeium | ✅ |
| `GEMINI.md` | Gemini CLI | ✅ |
| `.clinerules` | Cline | ✅ |
| `CONVENTIONS.md` | Aider | ✅ |

Lean instruction files are intentionally small — they contain your project description, security preamble, and a single line telling the AI to read `CHRONICLE.md` for full context. This keeps per-request token overhead minimal.

To disable targets after onboarding, set them in `.lore/config.yaml`:

```yaml
export_targets:
  windsurf: false
  gemini: false
  cline: false
  aider: false
```

Exports are atomic — a crash mid-write never leaves a partial file.

---

## Install

```sh
pip install lore-book
```

### Windows (recommended)

Use the Python launcher so the command works consistently across Windows setups:

```powershell
py -m pip install --upgrade lore-book
```

If you prefer isolated CLI installs, `pipx` is the smoothest option on Windows:

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
pipx install lore-book
```

If you are installing from this repository, use the bootstrap script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1
```

Optional modes:

```powershell
# Force plain pip install mode
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1 -Mode pip

# Install from local source path via pipx
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1 -SourcePath .
```

### Windows package managers

`pipx install lore-book` remains the easiest path for most users.

This repo now generates Windows packaging artifacts during release:

- Scoop manifest: `packaging/scoop/lore-book.json`
- winget submission helper: `packaging/winget/submission-<version>.md`

After each release, use these to publish:

1. Submit `packaging/scoop/lore-book.json` to your Scoop bucket repository.
2. Use `packaging/winget/submission-<version>.md` to open/update a PR in `microsoft/winget-pkgs`.

For local development:

```sh
pip install -e .
```

**Requirements:** Python 3.10+. Lore works out of the box with TF-IDF search. Dense vector search (sentence-transformers) is optional and can be enabled with the setup wizard below.

### Enable dense vector search (wizard)

Want dense vector search? Run:

```sh
lore setup semantic
```

The wizard will:

- check whether `sentence-transformers` is installed
- offer to install semantic dependencies if missing
- validate model loading with your configured `embedding_model`, `model_endpoint`, and SSL settings

If you prefer non-interactive setup:

```sh
lore setup semantic --install-now
```

Default endpoint for Hugging Face models is:

```text
https://huggingface.co
```

If dense model loading fails, lore automatically falls back to TF-IDF so search still works.

---

## Documentation site (GitHub Pages)

This repository now includes a plain static docs site in `docs/` for GitHub Pages.

Preview locally:

```sh
cd docs
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

Publishing is handled by `.github/workflows/docs.yml` on pushes to `main`/`master`.

To migrate existing docs pages into this repo, add or edit static files under `docs/`.

---

## Quick start

```sh
lore onboard
```

The onboarding command explains every concept, walks you through store setup, security policy, your first spell, and publishing — with an interactive step-by-step flow. It also prompts for a **project description** (auto-detected from `pyproject.toml` or README) that appears at the top of every lean instruction file. Start here if you're new.

Onboard/Init also add local adapter files to `.gitignore` by default, so only shared chronicle memory is committed unless you choose otherwise.

---

## Spells — adding and searching memories

```sh
# Interactive, step-by-step
lore add

# One-liner (scriptable, CI-friendly)
lore add decisions "Use FastAPI — async support + automatic OpenAPI docs"
lore add preferences "Always use type hints" --tags style,python
lore add facts "Minimum supported Python is 3.10"

# Semantic search — finds conceptually related spells, not just keyword matches
lore search "why did we choose FastAPI"
lore search "authentication strategy"

# List all spells
lore list

# List by tome
lore list decisions

# Delete a spell
lore remove <id>
```

Spell IDs are short UUID prefixes. `lore list` shows them.

---

## Relics — capture now, curate later

Use relics when you want to preserve raw information without slowing down to decide what matters.

```sh
# Paste session notes interactively (enter . to finish)
lore relic capture

# Pull in a file — meeting notes, spec doc, wiki export
lore relic capture --file session-notes.md --title "Auth redesign session"

# Snapshot the current working-tree + staged diff
lore relic capture --git-diff --title "Pre-deploy changes"

# Capture the last N commits (messages + diffs)
lore relic capture --git-log 5 --title "Sprint 12 wrap-up"

# Read from clipboard (Windows: PowerShell Get-Clipboard, macOS: pbpaste, Linux: xclip)
lore relic capture --clipboard --title "Slack thread on rate limiting"

# Pipe anything in
git log --oneline -20 | lore relic capture --stdin --title "Recent commit history"
cat confluence-export.txt | lore relic capture --stdin --title "Architecture decision"

# Browse relics (shows preview of content)
lore relic list

# Read one in full
lore relic view a3f1b2c4

# Distill the good parts into spells
lore relic distill a3f1b2c4

# Delete a relic
lore relic remove a3f1b2c4
```

### Distilling

`lore relic distill` shows you the relic content and walks you through extracting spells one at a time:

```
  ─── Spell #1 ────────────────────────────────────────────
  ✦ Inscription  the wisdom to enshrine  (. to seal the book): We chose CQRS to
    separate read and write models after hitting contention on the orders table
  ✦ Tome         which grimoire? [decisions]:
  ✓  Spell a1b2c3d4 sealed into decisions.

  ─── Spell #2 ────────────────────────────────────────────
  ...
```

Each spell links back to its source relic. The tome selection is sticky — after you choose `decisions` for spell #1, it defaults to `decisions` for spell #2. Enter `.` to finish.

---

## Exporting AI context files

```sh
# Write all enabled context files (default: CHRONICLE + all adapters)
lore export

# Write one target only
lore export --format chronicle
lore export --format copilot
lore export --format agents
lore export --format claude
lore export --format cursor
lore export --format prompt    # .github/prompts/lore.prompt.md
lore export --format windsurf  # requires: windsurf: true in .lore/config.yaml
lore export --format gemini
lore export --format cline
lore export --format aider
```

If no `project_description` is set, `lore export` will remind you to run `lore onboard` — lean instruction files are more useful with a one-line project summary at the top.

Exports are regenerated every run. Adapter files are gitignored by default, so teams can commit only `CHRONICLE.md` unless they opt into versioning adapter files.

### The `/lore` trigger

The `prompt` export target writes `.github/prompts/lore.prompt.md`. In GitHub Copilot Chat, type `/lore` to invoke it — the AI will read `CHRONICLE.md` and surface context relevant to your current task. No setup beyond running `lore export`.

## Trust model (how to use it as a user)

Treat lore memory as layered trust, even before advanced trust metadata exists:

1. **Shared trusted memory (commit this)**
- `CHRONICLE.md` is your canonical reviewed memory.
- Only include decisions/facts you want every collaborator and agent to inherit.

2. **Local working memory (do not commit)**
- Keep generated adapter files (`AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, etc.) local by default.
- Use them as personal tool wrappers around the same shared chronicle.

3. **Raw untrusted intake**
- Capture noisy inputs as relics first (`lore relic capture`).
- Distill only verified points into spells (`lore relic distill`).

4. **Practical review loop**
- Add candidate memory.
- Validate against code/tests/docs.
- Export chronicle.
- Commit `CHRONICLE.md` only when reviewed.

5. **Trust signals you can use today**
- Reserve `decisions` and `facts` for high-confidence entries.
- Use tags to mark confidence state (for example: `verified`, `needs-review`, `deprecated`).
- Move or remove stale entries quickly with `lore remove` + re-add in correct form.

### Automate trust scoring from git

You can auto-score existing memories from git metadata (author, source, activity, tags):

```sh
lore trust refresh
```

Preview only (no writes):

```sh
lore trust refresh --dry-run
```

Explain one memory's score:

```sh
lore trust explain <id>
lore trust explain <id> --recompute
```

Tune trust thresholds in `.lore/config.yaml`:

```yaml
trust:
  default_score: 50
  chronicle_min_score: 60
  trusted_authors:
    - "Your Name"
  author_weights:
    "Release Bot": 10
```

When `chronicle_min_score` is greater than `0`, `lore export` includes only entries at or above that score in `CHRONICLE.md`.

---

## Git integration

### Post-commit hook

`lore hook install` opens an interactive wizard that installs a `.git/hooks/post-commit` script:

```sh
lore hook install
```

The wizard asks whether you want:
- **Auto-extract** — scan each new commit message for decisions and facts, store them automatically
- **Auto-export** — regenerate all AI context files after every commit so they're always current

The generated hook is clearly marked `# Installed by lore`. Remove it safely with:

```sh
lore hook uninstall
```

### Post-merge CHRONICLE sync hook

Install a post-merge hook that syncs shared `CHRONICLE.md` updates into local `.lore/` whenever pull/merge changes the chronicle:

```sh
lore hook sync-install
```

Remove it safely with:

```sh
lore hook sync-uninstall
```

### Extracting from past commits

```sh
# Extract from the last 20 commits
lore extract --last 20
```

Lore scans commit messages for structured knowledge and adds it to your store.

### Syncing shared CHRONICLE updates

If a teammate updates `CHRONICLE.md` and you pull those changes, import them back into your local `.lore/` store with:

```sh
lore sync
```

Useful flags:

```sh
# Preview only
lore sync --dry-run

# Import from a different markdown file
lore sync --file ./path/to/CHRONICLE.md

# Import only (skip export pass)
lore sync --no-export
```

`lore sync` deduplicates by category/content (and scope tags for instructions), so re-running it is safe.

---

## Security guidelines

`lore security` configures a security preamble injected at the top of every export. This ensures every AI tool that reads your repo context also receives your security constraints before anything else.

```sh
lore security
```

The preamble can include:

- **OWASP Top 10** reference (prevents the classics: injection, broken auth, SSRF, etc.)
- **Security policy file** link (e.g. `SECURITY.md`)
- **CODEOWNERS** notice — warns that sensitive paths need human review
- **Custom rules** — any project-specific edicts ("Never disable SSL verification", "All secrets via env vars", etc.)

This is especially useful in GitHub Enterprise environments where Copilot should always be reminded of your security posture before providing suggestions.

---

## Store layout

```
.lore/
  config.yaml            ← store settings, categories, model config, security
  decisions/             ← why things were built a certain way
  facts/                 ← project context, constraints, team conventions
  preferences/           ← coding style, tooling choices
  summaries/             ← AI session summaries, sprint recaps
  relics/                ← raw captured artifacts (sessions, diffs, docs)
  embeddings/
    index.json           ← local semantic search index (no external DB)
```

Each spell and relic is a plain YAML file. No database engine, no lock files, no proprietary format. You can read, edit, and commit them directly.

`.lore/` is automatically added to `.gitignore` on `lore init`. Local adapter exports are also gitignored by default so teams can commit only `CHRONICLE.md` as shared memory.

---

## TUI

```sh
lore ui
```

A retro phosphor-green terminal browser for searching, reading, adding, and exporting memories. Live-reloads whenever `.lore/` files change on disk — open it in a split pane while you work.

---

## Background daemon

```sh
# Start watching — auto-exports on every .lore change
lore awaken

# Run in background
lore awaken --background

# Stop the daemon
lore slumber
```

The daemon watches `.lore/` with filesystem events and regenerates all export files the moment any spell or config changes. Zero-friction — add a spell, your AI tools get it immediately.

---

## Health check

```sh
lore doctor
```

Reports:
- Whether the `.lore/` store exists and is readable
- Which semantic search mode is active (embedding model or TF-IDF fallback)
- Whether the configured model endpoint is reachable
- Counts of spells by tome and relics

## Release smoke test

Run a clean, isolated CLI smoke test before publishing:

```sh
./smoke.sh
```

What it does:

- creates a temporary workspace + virtualenv
- installs the current project as a normal package (`pip install .`)
- runs `lore version`, `lore init`, `lore add`, `lore trust refresh --dry-run`, and `lore export --format chronicle`
- exits non-zero on failure

Optional environment variables:

```sh
PYTHON_BIN=python3.12 ./smoke.sh
KEEP_SMOKE=1 ./smoke.sh
```

## Automated releases

Use the GitHub Actions workflow `Prepare Release` to automate versioning and changelog updates.

What it does:

- bumps `src/lore/__init__.py` version (`patch`, `minor`, `major`, or explicit version)
- generates/updates `CHANGELOG.md` from commit subjects since the last tag
- commits and pushes the version + changelog update
- creates and pushes a git tag
- creates a GitHub Release with generated release notes
- triggers the existing PyPI publish workflow when the release is published

How to run it:

1. Open GitHub Actions for this repo.
2. Run `Prepare Release`.
3. Choose `bump` (`patch`/`minor`/`major`) or provide an explicit `version`.

After it completes, you should see a new tag, updated `CHANGELOG.md`, and a published release.

---

## Corporate proxy / Artifactory

By default Lore downloads models from `https://huggingface.co`. If you're behind a ZScaler proxy or using an internal HuggingFace mirror:

```sh
lore config model_endpoint https://artifactory.example.com/artifactory/api/huggingfaceml/huggingface
lore config model_ssl_verify false   # only if SSL inspection breaks certificate validation
```

Run `lore doctor` to confirm the model downloads and loads from your endpoint.

---

## Command reference

| Command | Args / Flags | What it does |
|---|---|---|
| `onboard` | | Guided setup — concepts, store, security, first spell, export |
| `init` | `[path]` | Create a `.lore/` store in a directory |
| `add` | `[category] [content]` | Store a spell (interactive if no args) |
| `list` | `[category]` | List spells, optionally filtered by tome |
| `search` | `<query>` | Semantic search across all spells |
| `remove` | `<id>` | Delete a spell |
| `extract` | `[--last N]` | Pull spells from git commit messages |
| `sync` | `[--file PATH] [--dry-run] [--no-export]` | Import shared `CHRONICLE.md` entries into local `.lore/` |
| `export` | `[--format F]` | Write AI context files (`chronicle`, `agents`, `copilot`, `cursor`, `claude`, `prompt`, `windsurf`, `gemini`, `cline`, `aider`, `all`) |
| `config` | `<key> <value>` | Set a config value |
| `security` | | Configure the security preamble for exports |
| `doctor` | | Store + model health report |
| `trust refresh` | `[--dry-run]` | Recompute trust scores/levels from git + memory metadata |
| `trust explain` | `<id> [--recompute]` | Show trust signals and scoring reasons for one memory |
| `hook install` | | Install git post-commit hook (wizard) |
| `hook uninstall` | | Safely remove the lore-managed git hook |
| `hook sync-install` | | Install git post-merge hook to sync `CHRONICLE.md` into `.lore/` |
| `hook sync-uninstall` | | Safely remove the lore-managed post-merge sync hook |
| `index rebuild` | | Rebuild the semantic search index from scratch |
| `ui` | | Open the interactive terminal browser |
| `awaken` | `[--background]` | Watch `.lore/` and auto-export on change |
| `slumber` | | Stop the background daemon |
| `relic capture` | `[--file F] [--git-diff] [--git-log N] [--clipboard] [--stdin] [--title T] [--tags T]` | Capture a raw artifact |
| `relic list` | | List relics with content preview |
| `relic distill` | `<id>` | Extract spells from a relic interactively |
| `relic view` | `<id>` | View full relic content |
| `relic remove` | `<id>` | Permanently delete a relic |

Run `lore <command> --help` for detailed options on any command.

---

## Dependencies

| Package | Purpose |
|---|---|
| `sentence-transformers` | Local semantic embeddings via `all-MiniLM-L6-v2` |

---

## CI/CD workflows

- `.github/workflows/release.yml` — prepares a release, bumps version, updates changelog, tags, and creates GitHub Release
- `.github/workflows/publish.yml` — publishes to PyPI on `release.published`
| `gitpython` | Git history extraction |
| `typer` + `rich` | CLI and terminal output |
| `textual` | Interactive TUI |
| `watchdog` | Live reload in TUI + background daemon |
| `pyyaml` + `numpy` | YAML storage and vector math |
