"""CLI entry point for lore."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich import box

from . import __version__
from .config import LOCAL_AGENT_FILES

# ---------------------------------------------------------------------------
# Palette (mirrors tui.py so help screen feels consistent)
# ---------------------------------------------------------------------------
_P  = "#39ff14"   # phosphor green
_PD = "#1a7a0a"   # dim green
_A  = "#ffaa00"   # amber
_AD = "#996600"   # dim amber
_BG = "#080c08"
_BD = "#1a6606"   # border
_LORE_GITIGNORE_ENTRY = ".lore/"

_BANNER_TEXT = f"[bold {_A}]L · O · R · E   -   AI  PROJECT  MEMORY   v{__version__}[/bold {_A}]"

# Force truecolor so VS Code's integrated terminal and other 256-color
# terminals don't degrade hex palette colors to ugly approximations.
# LORE_NO_COLOR=1 lets users opt out (e.g. for plain CI logs).
_force_color  = os.environ.get("LORE_NO_COLOR", "") == ""
_color_system = "truecolor" if _force_color else None
if _force_color and not os.environ.get("COLORTERM"):
    os.environ["COLORTERM"] = "truecolor"

app = typer.Typer(
    name="lore",
    help="AI memory manager for local repos and projects.",
    no_args_is_help=False,
    invoke_without_command=True,
)
hook_app  = typer.Typer(help="Manage git hooks.")
index_app = typer.Typer(help="Manage the embedding index.")
relic_app = typer.Typer(help="Capture and manage relics - rich session artifacts.")
setup_app = typer.Typer(help="Guided setup helpers.")
trust_app = typer.Typer(help="Trust scoring and trust metadata tools.")
app.add_typer(hook_app,  name="hook")
app.add_typer(index_app, name="index")
app.add_typer(relic_app, name="relic")
app.add_typer(setup_app, name="setup")
app.add_typer(trust_app, name="trust")


# ---------------------------------------------------------------------------
# lore version
# ---------------------------------------------------------------------------

@app.command()
def version(
    check: Annotated[
        bool,
        typer.Option("--check", help="Check PyPI for the latest available version"),
    ] = False,
) -> None:
    """Show the current lore version and optionally check for updates."""
    console.print(f"lore [bold]{__version__}[/bold]")
    if check:
        try:
            import urllib.request
            import json as _json
            url = "https://pypi.org/pypi/lore-book/json"
            with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310
                data = _json.loads(resp.read())
            latest = data["info"]["version"]
            if latest == __version__:
                console.print(f"[dim]You are up to date.[/dim]")
            else:
                console.print(
                    f"[bold {_A}]A new version is available:[/bold {_A}] [bold]{latest}[/bold]  "
                    f"[dim](you have {__version__})[/dim]\n"
                    f"  [dim]Run: [bold]python -m pip install --upgrade lore-book[/bold][/dim]"
                )
        except Exception:
            console.print(f"[dim]Could not reach PyPI to check for updates.[/dim]")

console     = Console(color_system=_color_system, force_terminal=_force_color)
err_console = Console(stderr=True, color_system=_color_system, force_terminal=_force_color)


_CORE_ROWS = [
    ("onboard",  "",                        "📜  new here? begin the chronicle setup"),
    ("add",      "\\[category] \\[content]",  "inscribe a new memory into the spellbook"),
    ("search",   "<query>",                 "seek knowledge across all memories"),
    ("export",   "\\[--format]",              "publish the chronicle to AI context files"),
    ("relic",    "capture|list|distill …",  "🏺  capture artifacts, distill into spells"),
    ("ui",       "",                        "open the interactive terminal grimoire"),
]

_MORE_ROWS = [
    ("list",          "\\[category]",             "list memories, optionally by tome"),
    ("lint",          "\\[--fail-on LEVELS]",      "check memory quality and metadata integrity"),
    ("associate",     "<id>",                   "suggest or apply related memory links"),
    ("remove",        "<id>",                   "delete a memory by its ID"),
    ("extract",       "\\[--last N]",             "pull memories from recent git commits"),
    ("sync",          "\\[--file PATH]",          "import shared CHRONICLE entries into .lore"),
    ("init",          "\\[path]",                 "create a .lore store in a directory"),
    ("doctor",        "",                        "check store, model, and search status"),
    ("setup",         "semantic",                "guided setup for dense vector search"),
    ("setup",         "extract-patterns",        "manage custom extraction patterns for commits"),
    ("trust",         "refresh",                 "recompute memory trust from git signals"),
    ("trust",         "explain <id>",            "show trust score inputs for one memory"),
    ("awaken",        "\\[--background]",         "👁  watch .lore and auto-export on change"),
    ("slumber",       "",                        "banish the background daemon"),
    ("config",        "<key> <value>",           "set a config value"),
    ("security",      "",                        "configure security guidelines for exports"),
    ("hook",          "install|uninstall",       "manage the post-commit git hook"),
    ("hook",          "sync-install|sync-uninstall", "manage CHRONICLE post-merge sync hook"),
    ("index",         "rebuild",                 "rebuild the semantic search index"),
    ("version",       "\\[--check]",              "show version; --check queries PyPI"),
]


def _build_table(rows: list[tuple[str, str, str]]) -> Table:
    t = Table(box=box.SIMPLE, show_header=True, header_style=f"bold {_A}",
              show_edge=False, padding=(0, 1), expand=False)
    t.add_column("SPELL",       style=f"bold {_P}", no_wrap=True, min_width=12)
    t.add_column("ARGS",        style=_PD,          no_wrap=True, min_width=20)
    t.add_column("EFFECT",      style=f"{_P}")
    for cmd, args, desc in rows:
        t.add_row(cmd, args, desc)
    return t


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    show_all: Annotated[
        bool,
        typer.Option("--all", help="Reveal the full grimoire of spells."),
    ] = False,
) -> None:
    """Show help when lore is run with no subcommand."""
    if ctx.invoked_subcommand is not None:
        return

    console.print()
    console.print(f"  {_BANNER_TEXT}")
    console.print()

    if show_all:
        console.print(f"  [{_AD}]── full grimoire ──────────────────────────────────[/{_AD}]")
        console.print()
        console.print(_build_table(_CORE_ROWS + _MORE_ROWS))
        console.print(f"  [{_AD}]Run [bold]lore <spell> --help[/bold] for detailed options.[/{_AD}]")
    else:
        console.print(_build_table(_CORE_ROWS))
        console.print(
            f"  [{_AD}]Run [bold]lore --all[/bold] to reveal the full grimoire · "
            f"[bold]lore <spell> --help[/bold] for details.[/{_AD}]"
        )

    console.print()

    # Background update check — non-blocking, silent on error or up-to-date.
    def _check_update() -> None:
        try:
            import urllib.request
            import json as _json
            with urllib.request.urlopen(  # noqa: S310
                "https://pypi.org/pypi/lore-book/json", timeout=3
            ) as resp:
                latest = _json.loads(resp.read())["info"]["version"]
            if latest != __version__:
                console.print(
                    f"  [{_A}]✦  Update available:[/{_A}] [bold]{latest}[/bold]"
                    f"  [dim](you have {__version__})[/dim]\n"
                    f"  [dim]  python -m pip install --upgrade lore-book[/dim]\n"
                )
        except Exception:
            pass

    import threading as _threading
    _threading.Thread(target=_check_update, daemon=True).start()


def _require_root() -> Path:
    from .config import find_memory_root
    root = find_memory_root()
    if root is None:
        err_console.print(
            "[red]No .lore directory found. Run `lore init` first.[/red]"
        )
        raise typer.Exit(code=1)
    from .store import ensure_identity
    repaired, identity = ensure_identity(root)
    if repaired:
        console.print(
            f"\n  [bold {_A}]▲[/bold {_A}]  Identity was missing or corrupt — regenerated: "
            f"[bold {_A}]{identity['name']}[/bold {_A}]  [dim]({identity['id']})[/dim]\n"
        )
    return root


def _parse_id_csv(value: str | None) -> list[str]:
    if not value:
        return []
    out: list[str] = []
    for raw in value.split(","):
        item = raw.strip()
        if item and item not in out:
            out.append(item)
    return out


def _normalize_review_date(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    from datetime import date

    date.fromisoformat(cleaned)
    return cleaned


def _resolve_memory_ref(memories: list[dict[str, Any]], ref: str) -> dict[str, Any] | None:
    if ref.isdigit():
        idx = int(ref) - 1
        if 0 <= idx < len(memories):
            return memories[idx]
        return None

    matches = [m for m in memories if str(m.get("id", "")).startswith(ref)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous ID prefix '{ref}' — matches {len(matches)} spells. Use more characters.")
    return None


def _print_association_table(suggestions: list[dict[str, Any]]) -> None:
    def _preview(text: str, limit: int = 96) -> str:
        compact = " ".join(text.split())
        return compact if len(compact) <= limit else compact[: limit - 1].rstrip() + "…"

    table = Table(show_header=True, header_style=f"bold {_A}", expand=True)
    table.add_column("Score", width=7, no_wrap=True)
    table.add_column("Semantic", width=9, no_wrap=True)
    table.add_column("ID", style="dim", width=10, no_wrap=True)
    table.add_column("Category", width=14, no_wrap=True)
    table.add_column("Shared Tags", width=18, no_wrap=True)
    table.add_column("Content", min_width=20, overflow="fold")
    for item in suggestions:
        table.add_row(
            f"{float(item.get('_score', 0.0)):.3f}",
            f"{float(item.get('_semantic_score', 0.0)):.3f}",
            str(item.get("id", "")),
            str(item.get("category", "")),
            ", ".join(item.get("_shared_tags", [])) or "-",
            _preview(str(item.get("content", ""))),
        )
    console.print(table)


def _apply_related_links(root: Path, source_id: str, target_ids: list[str]) -> int:
    from .store import list_memories, update_memory

    memories = list_memories(root)
    id_map = {str(m.get("id", "")): m for m in memories if m.get("id")}
    source = id_map.get(source_id)
    if source is None:
        return 0

    current_source = [str(v).strip() for v in (source.get("related_to") or []) if str(v).strip()]
    updated_source = current_source[:]
    applied = 0

    for target_id in target_ids:
        tid = str(target_id).strip()
        if not tid or tid == source_id or tid not in id_map:
            continue
        if tid not in updated_source:
            updated_source.append(tid)
            applied += 1

        target = id_map[tid]
        target_related = [str(v).strip() for v in (target.get("related_to") or []) if str(v).strip()]
        if source_id not in target_related:
            target_related.append(source_id)
            update_memory(root, tid, {"related_to": target_related})

    if updated_source != current_source:
        update_memory(root, source_id, {"related_to": updated_source})
    return applied


def _interactive_add_inputs(root: Path) -> tuple[str, str, str | None, str | None, str | None, bool, str | None]:
    from .config import load_config
    from rich.prompt import Prompt, Confirm

    cfg = load_config(root)
    valid_cats: list[str] = cfg.get("categories", [])

    console.print()
    console.print(Panel(
        f"[bold {_A}]New memory — let's walk through it step by step.[/bold {_A}]",
        border_style=_BD, padding=(0, 2), style=f"on {_BG}",
    ))
    console.print()

    console.print("  [bold]Step 1 of 5  —  Category[/bold]")
    console.print(f"  [dim]Available:[/dim] {', '.join(valid_cats)}")
    console.print("  [dim](type a new name to create a custom category)[/dim]")
    console.print()
    category = Prompt.ask(
        f"  [bold {_P}]Category[/bold {_P}]",
        default=valid_cats[0] if valid_cats else "facts",
    )
    console.print()

    console.print("  [bold]Step 2 of 5  —  Content[/bold]")
    console.print("  [dim]Describe the decision, fact, or thing you want to remember.[/dim]")
    console.print()
    content = Prompt.ask(f"  [bold {_P}]Memory[/bold {_P}]")
    while not content.strip():
        console.print("  [bold red]Content cannot be empty.[/bold red]")
        content = Prompt.ask(f"  [bold {_P}]Memory[/bold {_P}]")
    console.print()

    console.print("  [bold]Step 3 of 5  —  Tags[/bold]  [dim](optional)[/dim]")
    console.print("  [dim]Comma-separated keywords to make this easier to find later.[/dim]")
    console.print()
    tags_input = Prompt.ask(f"  [bold {_P}]Tags[/bold {_P}]", default="")
    tags = tags_input if tags_input.strip() else None
    console.print()

    console.print("  [bold]Step 4 of 5  —  Relationships[/bold]  [dim](optional)[/dim]")
    console.print("  [dim]Link this memory to other memory IDs if relevant.[/dim]")
    console.print()
    depends_on = Prompt.ask(
        f"  [bold {_P}]Depends on[/bold {_P}] [dim](comma-separated IDs)[/dim]",
        default="",
    )
    related_to = Prompt.ask(
        f"  [bold {_P}]Related to[/bold {_P}] [dim](comma-separated IDs)[/dim]",
        default="",
    )
    console.print()

    console.print("  [bold]Step 5 of 5  —  Lifecycle[/bold]  [dim](optional)[/dim]")
    deprecated = Confirm.ask(f"  [bold {_P}]Mark as deprecated?[/bold {_P}]", default=False)
    review_date_input = Prompt.ask(
        f"  [bold {_P}]Review date[/bold {_P}] [dim](YYYY-MM-DD, blank to skip)[/dim]",
        default="",
    )
    review_date = review_date_input if review_date_input.strip() else None
    console.print()

    console.print("  [dim]───────────────────────────────[/dim]")
    console.print(f"  [bold]Category :[/bold] {category}")
    console.print(f"  [bold]Memory   :[/bold] {content}")
    console.print(f"  [bold]Tags     :[/bold] {tags or '(none)'}")
    console.print(f"  [bold]Depends  :[/bold] {depends_on or '(none)'}")
    console.print(f"  [bold]Related  :[/bold] {related_to or '(none)'}")
    console.print(f"  [bold]Deprecated:[/bold] {'yes' if deprecated else 'no'}")
    console.print(f"  [bold]Review   :[/bold] {review_date or '(none)'}")
    console.print("  [dim]───────────────────────────────[/dim]")
    console.print()
    confirmed = Confirm.ask(f"  [bold {_P}]Save this memory?[/bold {_P}]", default=True)
    if not confirmed:
        console.print("\n  [dim]Cancelled — nothing was saved.[/dim]\n")
        raise typer.Exit()
    console.print()
    return category, content, tags, depends_on, related_to, deprecated, review_date


def _auto_associate_entry(
    root: Path,
    entry: dict[str, Any],
    *,
    interactive_mode: bool,
    associate_top: int,
    associate_min_score: float,
) -> None:
    from rich.prompt import Confirm
    from .search import suggest_associations

    suggestions = suggest_associations(
        root,
        mem_id=entry["id"],
        top_k=max(1, associate_top),
        min_score=max(0.0, min(1.0, associate_min_score)),
    )
    if not suggestions:
        console.print("  [dim]No strong related-memory suggestions found.[/dim]")
        return

    console.print()
    console.print(f"  [bold {_A}]Suggested associations[/bold {_A}] for [bold]{entry['id']}[/bold]")
    _print_association_table(suggestions)
    should_apply = True
    if interactive_mode:
        console.print()
        should_apply = Confirm.ask(
            f"  [bold {_P}]Apply these related links?[/bold {_P}]",
            default=True,
        )
    if should_apply:
        applied = _apply_related_links(root, entry["id"], [str(s.get("id", "")) for s in suggestions])
        console.print(f"  [bold {_P}]✓[/bold {_P}]  Linked [bold]{applied}[/bold] related memories")


def _ensure_gitignore_entries(root: Path, entries: list[str]) -> list[str]:
    """Ensure each entry exists in .gitignore; returns entries added this run."""
    gitignore = root / ".gitignore"
    if gitignore.exists():
        lines = gitignore.read_text().splitlines()
    else:
        lines = []

    existing = set(lines)
    added: list[str] = []
    for entry in entries:
        if entry not in existing:
            lines.append(entry)
            existing.add(entry)
            added.append(entry)

    if added:
        gitignore.write_text("\n".join(lines).rstrip() + "\n")
    return added


def _sync_existing_chronicle(root: Path) -> dict[str, object] | None:
    """Import an existing CHRONICLE into the local store during onboarding.

    This preserves previously logged spells before onboarding republishes the
    chronicle and adapter files.
    """
    from .chronicle import import_chronicle

    chronicle_path = root / "CHRONICLE.md"
    if not chronicle_path.exists():
        return None

    preview = import_chronicle(root, chronicle_path=chronicle_path, dry_run=True)
    if preview["recognized"] == 0:
        return None
    if preview["added"] == 0:
        preview["indexed_pairs"] = []
        return preview

    stats = import_chronicle(root, chronicle_path=chronicle_path, dry_run=False)
    if stats["indexed_pairs"]:
        from .search import batch_index_memories

        batch_index_memories(root, stats["indexed_pairs"])
    return stats


# ---------------------------------------------------------------------------
# mem init
# ---------------------------------------------------------------------------

@app.command()
def init(
    path: Annotated[
        Path,
        typer.Argument(help="Directory to initialize (default: current directory)"),
    ] = Path("."),
    extract: Annotated[
        bool,
        typer.Option("--extract", help="Also extract memories from recent git commits after init"),
    ] = False,
    last: Annotated[
        int,
        typer.Option("--last", "-n", help="Number of recent commits to scan when --extract is set"),
    ] = 20,
) -> None:
    """Initialize a .lore store in the given directory."""
    from .store import init_store
    from .extract import _is_git_repo
    from .config import load_config
    root = path.resolve()
    init_store(root)
    cfg = load_config(root)
    identity = cfg.get("identity", {})
    ident_name = identity.get("name", "")
    ident_id = identity.get("id", "")
    if ident_name and ident_id:
        console.print(
            f"  [bold {_P}]✦[/bold {_P}]  Lore identity: "
            f"[bold {_A}]{ident_name}[/bold {_A}]  [dim]({ident_id})[/dim]"
        )
        console.print()
    is_git = _is_git_repo(root)
    # Warn if not inside a git repo — extract/hook won't work
    if not is_git:
        console.print(
            f"  [bold {_A}]▲[/bold {_A}]  [bold]{root}[/bold] is not a git repository.\n"
            f"  [dim]lore add/search/export work fine here, but [bold]lore extract[/bold] and "
            f"[bold]lore hook[/bold] require git.\n"
            f"  Run [bold]git init[/bold] first if you need those features.[/dim]"
        )
        console.print()
    # Shared-chronicle mode: commit CHRONICLE.md, keep local adapter files uncommitted.
    added = _ensure_gitignore_entries(root, [_LORE_GITIGNORE_ENTRY, *LOCAL_AGENT_FILES])
    for entry in added:
        console.print(f"[dim]Added {entry} to .gitignore[/dim]")
    console.print(f"[green]Initialized lore store at[/green] {root / '.lore'}")
    console.print()

    # Bootstrap all agent files so AI tools pick up lore directives from day one.
    from .export import export_all
    with console.status("Bootstrapping agent files…"):
        written = export_all(root)
    for p in written:
        console.print(f"  [bold {_P}]✓[/bold {_P}]  {p.relative_to(root)}")
    console.print()

    # Optionally extract memories from recent git history.
    if extract and is_git:
        from .extract import extract_from_git
        from .store import add_memory
        from .search import batch_index_memories
        console.print(f"[dim]Scanning last {last} commit(s) for memory candidates…[/dim]")
        try:
            candidates = extract_from_git(root, n_commits=last)
        except RuntimeError as e:
            err_console.print(f"[red]{e}[/red]")
            candidates = []
        if candidates:
            to_index: list[tuple[str, str]] = []
            for c in candidates:
                entry = add_memory(root, c["category"], c["content"], source=c["source"])
                to_index.append((entry["id"], c["content"]))
            if to_index:
                with console.status("Indexing extracted memories…"):
                    batch_index_memories(root, to_index)
            console.print(
                f"  [bold {_P}]✓[/bold {_P}]  Extracted and saved [bold]{len(to_index)}[/bold] "
                f"memory(s) from git history."
            )
            # Re-export so chronicle reflects the newly extracted memories.
            with console.status("Updating chronicle…"):
                export_all(root)
            console.print(f"  [bold {_P}]✓[/bold {_P}]  Chronicle updated.")
            console.print()
        else:
            console.print(f"[dim]No memory candidates found in the last {last} commit(s).[/dim]")
            console.print()
    elif extract and not is_git:
        console.print(
            f"  [bold {_A}]▲[/bold {_A}]  [dim]--extract skipped: not a git repository.[/dim]"
        )
        console.print()

    console.print(
        Panel(
            f"[bold]The [bold {_P}].lore/[/bold {_P}] directory is your project memory.[/bold]\n"
            "Everything you [bold]add[/bold], [bold]extract[/bold], or [bold]import[/bold] lives here as plain YAML — "
            "readable, diffable, and fully yours.\n\n"
            f"[dim]Agent files have been bootstrapped. Run [bold]lore add[/bold] to store your first memory.[/dim]",
            border_style=_BD,
            padding=(0, 2),
            style=f"on {_BG}",
        )
    )
    console.print("  [dim]Want dense vector search? Run [bold]lore setup semantic[/bold].[/dim]")


def _detect_project_description(root: Path) -> str:
    """Auto-detect a one-line project description from pyproject.toml or README."""
    import re

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text()
            m = re.search(r'^description\s*=\s*["\'](.+?)["\']', text, re.MULTILINE)
            if m:
                return m.group(1).strip()
        except Exception:
            pass

    for readme in ("README.md", "README.rst", "README.txt", "README"):
        p = root / readme
        if p.exists():
            try:
                for line in p.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith(("#", "!", "<", "[", ">")) and len(line) >= 15:
                        return line[:140]
            except Exception:
                pass

    return ""


# ---------------------------------------------------------------------------
# lore onboard
# ---------------------------------------------------------------------------

_RPG_PAUSE = 0.6   # seconds between story beats (0 = instant, nice for CI)

@app.command()
def onboard() -> None:
    """Begin the lore onboarding quest — set up everything from scratch."""
    import time
    from pathlib import Path as _Path
    from rich.prompt import Prompt, Confirm
    from rich.rule import Rule
    from .config import find_memory_root, load_config, save_config

    def _beat(text: str, pause: float = _RPG_PAUSE) -> None:
        console.print(text)
        time.sleep(pause)

    def _chapter(n: int, title: str) -> None:
        console.print()
        console.print(Rule(f"  [bold {_A}]Chapter {n}  {title}[/bold {_A}]  ", style=_BD))
        console.print()
        time.sleep(_RPG_PAUSE * 0.5)

    # ── Prologue ─────────────────────────────────────────────────────────────
    console.print()
    console.print(Panel(
        f"[bold {_A}]📜  L · O · R · E[/bold {_A}]\n"
        f"[dim {_A}]An Onboarding Chronicle[/dim {_A}]",
        border_style=_BD, padding=(1, 4), style=f"on {_BG}",
    ))
    console.print()
    time.sleep(_RPG_PAUSE)

    _beat(f"  [bold {_P}]In every great project, knowledge is earned - and forgotten.[/bold {_P}]")
    _beat(f"  [dim]Decisions fade. Context is lost. The codebase grows opaque.[/dim]")
    console.print()
    _beat(f"  [bold {_A}]Lore[/bold {_A}] is your project's memory - a living chronicle that travels")
    _beat(f"  with your code and speaks directly to your AI tools.")
    console.print()
    _beat(f"  [dim]This onboarding will guide you through the four rites of initiation:[/dim]")
    _beat(f"  [dim]  I.   Forge the Store[/dim]", 0.2)
    _beat(f"  [dim]  II.  Inscribe a Law  (security)[/dim]", 0.2)
    _beat(f"  [dim]  III. Record a Memory[/dim]", 0.2)
    _beat(f"  [dim]  IV.  Publish the Chronicle[/dim]", 0.2)
    console.print()

    # ── Concept primer ────────────────────────────────────────────────────────
    time.sleep(_RPG_PAUSE * 0.5)
    console.print(Panel(
        f"[bold {_A}]  A Brief Lexicon[/bold {_A}]\n\n"
        f"[bold {_P}]Spell[/bold {_P}] [dim](memory)[/dim]\n"
        f"  A single piece of knowledge - a decision, a fact, a lesson learned.\n"
        f"  Spells are the atoms of your chronicle. Each gets its own YAML entry.\n\n"
        f"[bold {_P}]Tome[/bold {_P}] [dim](category)[/dim]\n"
        f"  A named collection of spells: facts, decisions, preferences, summaries.\n"
        f"  You choose the tomes; lore just files things into them.\n\n"
        f"[bold {_P}]Relic[/bold {_P}]\n"
        f"  A raw artifact - a session dump, a git diff, a pasted doc - saved\n"
        f"  as-is. Later you distill a relic into spells, keeping only what matters.\n\n"
        f"[bold {_P}]Export[/bold {_P}] [dim](the chronicle)[/dim]\n"
        f"  lore writes your spells into files your AI tools read automatically:\n"
        f"  [dim]copilot-instructions.md  AGENTS.md  CLAUDE.md  .cursor/rules/memory.md[/dim]\n"
        f"  Every tool that reads your repo now shares your context, always in sync.",
        border_style=_BD, padding=(0, 2), style=f"on {_BG}",
    ))
    console.print()
    time.sleep(_RPG_PAUSE * 0.5)

    if not Confirm.ask(f"  [bold {_P}]Are you ready to begin?[/bold {_P}]", default=True):
        console.print(f"\n  [dim]The scroll remains sealed. Return when you are ready.[/dim]\n")
        raise typer.Exit()

    # ── Chapter I — Forge the Store ──────────────────────────────────────────
    _chapter(1, "Forge the Store")
    _beat(f"  [dim]Before memories can be kept, a sanctum must be prepared.[/dim]")
    _beat(f"  [dim]The [bold {_P}].lore/[/bold {_P}] directory will hold every chronicle, decision,")
    _beat(f"  [dim]and fact - as plain YAML, committed alongside your code.[/dim]")
    console.print()

    root = find_memory_root()
    if root:
        _beat(f"  [bold {_P}]✓[/bold {_P}]  A store already exists at [bold]{root / '.lore'}[/bold]")
        _beat(f"  [dim]Your sanctum stands. We shall not disturb it.[/dim]")
    else:
        dest_str = Prompt.ask(
            f"  [bold {_P}]Where shall the store be forged?[/bold {_P}] [dim](path)[/dim]",
            default=".",
        )
        dest = _Path(dest_str).resolve()
        console.print()
        from .store import init_store
        init_store(dest)
        _ensure_gitignore_entries(dest, [_LORE_GITIGNORE_ENTRY, *LOCAL_AGENT_FILES])
        root = dest
        _beat(f"  [bold {_P}]✓[/bold {_P}]  The sanctum has been forged at [bold]{root / '.lore'}[/bold]")
        _beat(f"  [dim]The gates have been hidden from git's eye.[/dim]")

    added = _ensure_gitignore_entries(root, [_LORE_GITIGNORE_ENTRY, *LOCAL_AGENT_FILES])
    if added:
        _beat(f"  [bold {_P}]✓[/bold {_P}]  Local adapter files were added to .gitignore.")

    chronicle_stats = _sync_existing_chronicle(root)
    if chronicle_stats:
        if int(chronicle_stats["added"]) > 0:
            _beat(
                f"  [bold {_P}]✓[/bold {_P}]  Preserved [bold]{chronicle_stats['added']}[/bold] "
                f"entr{'y' if chronicle_stats['added'] == 1 else 'ies'} from the existing chronicle."
            )
            _beat(f"  [dim]Your old spells were merged into the store before publishing.[/dim]")
        else:
            _beat(f"  [bold {_P}]✓[/bold {_P}]  The existing chronicle is already reflected in the store.")

    cfg = load_config(root)

    # ── Project description ───────────────────────────────────────────────────
    existing_desc = cfg.get("project_description", "").strip()
    if not existing_desc:
        console.print()
        _beat(f"  [dim]A brief description helps AI tools understand this project at a glance.[/dim]")
        console.print()
        detected = _detect_project_description(root)
        proj_desc = Prompt.ask(
            f"  [bold {_P}]Project description[/bold {_P}] [dim](one line, optional)[/dim]",
            default=detected,
        )
        if proj_desc.strip():
            cfg["project_description"] = proj_desc.strip()
            save_config(root, cfg)
            _beat(f"  [bold {_P}]✓[/bold {_P}]  Inscribed: [dim]{proj_desc[:72]}[/dim]")
    else:
        _beat(f"  [bold {_P}]✓[/bold {_P}]  Project: [dim]{existing_desc[:72]}[/dim]")

    # ── Chapter II — Inscribe a Law ──────────────────────────────────────────
    _chapter(2, "Inscribe a Law")
    _beat(f"  [dim]Every chronicle must be bound by covenant:[/dim]")
    _beat(f"  [dim]rules that tell your AI what it must never do.[/dim]")
    console.print()

    sec = dict(cfg.get("security", {}))
    already_set = sec.get("enabled", False)
    if already_set:
        _beat(f"  [bold {_P}]✓[/bold {_P}]  A security covenant is already inscribed.")
        reconfigure = Confirm.ask(
            f"  [bold {_P}]Re-configure it now?[/bold {_P}]", default=False
        )
    else:
        reconfigure = True

    if reconfigure:
        _beat(f"  [dim]The standard covenant includes:[/dim]")
        _beat(f"  [dim]  · No hardcoded credentials or disabled SSL[/dim]", 0.15)
        _beat(f"  [dim]  · OWASP Top 10 prevention[/dim]", 0.15)
        _beat(f"  [dim]  · Reference to SECURITY.md and CODEOWNERS[/dim]", 0.15)
        console.print()

        sec["enabled"] = Confirm.ask(
            f"  [bold {_P}]Enable the security covenant?[/bold {_P}]", default=True
        )
        console.print()

        if sec["enabled"]:
            sec.setdefault("owasp_top10", True)
            sec.setdefault("security_policy", "SECURITY.md")
            sec.setdefault("codeowners", True)
            sec.setdefault("custom_rules", [])

            sec["owasp_top10"] = Confirm.ask(
                f"  [bold {_P}]Include OWASP Top 10 reference?[/bold {_P}]",
                default=sec["owasp_top10"],
            )
            policy = Prompt.ask(
                f"  [bold {_P}]Security policy file[/bold {_P}] [dim](blank to skip)[/dim]",
                default=sec["security_policy"] or "SECURITY.md",
            )
            sec["security_policy"] = policy.strip() or None
            sec["codeowners"] = Confirm.ask(
                f"  [bold {_P}]Reference CODEOWNERS?[/bold {_P}]",
                default=sec["codeowners"],
            )
            console.print()
            _beat(f"  [dim]Scribe any custom edicts (blank line to finish):[/dim]")
            rules: list[str] = list(sec["custom_rules"])
            while True:
                r = Prompt.ask(f"  [bold {_P}]Edict[/bold {_P}] [dim](blank to finish)[/dim]", default="")
                if not r.strip():
                    break
                rules.append(r.strip())
            sec["custom_rules"] = rules

        cfg["security"] = sec
        save_config(root, cfg)
        _beat(f"\n  [bold {_P}]✓[/bold {_P}]  The covenant has been inscribed in the config.")

    # ── Chapter III — Record a Memory ────────────────────────────────────────
    _chapter(3, "Record a Memory")
    _beat(f"  [dim]A spell is one discrete piece of knowledge: a decision your team made,[/dim]")
    _beat(f"  [dim]a gotcha you hit, a rule your AI should always follow.[/dim]")
    _beat(f"  [dim]Spells are short, specific, and retrievable by semantic search.[/dim]")
    _beat(f"  [dim](For long raw artifacts - session dumps, diffs, docs - use [bold {_P}]lore relic capture[/bold {_P}] instead.)[/dim]")
    console.print()

    from .store import add_memory, list_memories
    from .search import index_memory

    existing = list_memories(root)
    if existing:
        _beat(
            f"  [bold {_P}]✓[/bold {_P}]  Your tome already holds "
            f"[bold]{len(existing)}[/bold] entr{'y' if len(existing)==1 else 'ies'}."
        )
        add_one = Confirm.ask(
            f"  [bold {_P}]Add another memory now?[/bold {_P}]", default=False
        )
    else:
        add_one = True

    if add_one:
        valid_cats = cfg.get("categories", ["decisions", "facts", "preferences", "summaries"])
        console.print()
        console.print(f"  [dim]Available categories:[/dim] {', '.join(valid_cats)}")
        console.print()
        mem_cat = Prompt.ask(
            f"  [bold {_P}]Category[/bold {_P}]",
            default=valid_cats[0] if valid_cats else "facts",
        )
        console.print()
        mem_content = Prompt.ask(f"  [bold {_P}]Memory[/bold {_P}]")
        while not mem_content.strip():
            console.print(f"  [bold red]The tome refuses an empty entry.[/bold red]")
            mem_content = Prompt.ask(f"  [bold {_P}]Memory[/bold {_P}]")
        mem_tags_raw = Prompt.ask(
            f"  [bold {_P}]Tags[/bold {_P}] [dim](comma-separated, optional)[/dim]", default=""
        )
        mem_tags = [t.strip() for t in mem_tags_raw.split(",") if t.strip()]
        console.print()
        with console.status("  Indexing…"):
            entry = add_memory(root, mem_cat, mem_content, tags=mem_tags)
            index_memory(root, entry["id"], mem_content)
        _beat(f"  [bold {_P}]✓[/bold {_P}]  Memory [bold]{entry['id']}[/bold] has been sealed in the tome.")

    # ── Chapter IV — Publish the Chronicle ───────────────────────────────────
    _chapter(4, "Publish the Chronicle")
    _beat(f"  [dim]The final rite: transcribe the chronicle into the languages")
    _beat(f"  [dim]your AI companions can read.[/dim]")
    console.print()
    _beat(f"  [dim]By default, lore writes [bold]CHRONICLE.md[/bold] and all agent adapter files.[/dim]")
    _beat(f"  [dim]Adapter files are gitignored by default, so users can opt into committing them later.[/dim]")
    console.print()
    _beat(f"  [dim]Adapter files include:[/dim]")
    _beat(f"  [dim]  · [bold].github/copilot-instructions.md[/bold]  - GitHub Copilot[/dim]", 0.15)
    _beat(f"  [dim]  · [bold]AGENTS.md[/bold]                        - OpenAI Codex / agents[/dim]", 0.15)
    _beat(f"  [dim]  · [bold]CLAUDE.md[/bold]                        - Anthropic Claude[/dim]", 0.15)
    _beat(f"  [dim]  · [bold].cursor/rules/memory.md[/bold]          - Cursor[/dim]", 0.15)
    console.print()

    if Confirm.ask(f"  [bold {_P}]Publish the chronicle now?[/bold {_P}]", default=True):
        from .export import export_all
        console.print()
        with console.status("  Transcribing…"):
            paths = export_all(root)
        for p in paths:
            console.print(f"  [bold {_P}]✓[/bold {_P}]  {p.relative_to(root)}")

    # ── Epilogue ──────────────────────────────────────────────────────────────
    console.print()
    console.print(Rule(style=_BD))
    console.print()
    time.sleep(_RPG_PAUSE)
    _beat(f"  [bold {_P}]The chronicle is open. The rites are complete.[/bold {_P}]")
    console.print()
    _beat(f"  [dim]From this day forward, your memories travel with your code.[/dim]")
    _beat(f"  [dim]Every AI that reads your repo will know what you know.[/dim]")
    console.print()
    _beat(f"  A few commands to guide your journey:")
    console.print()
    _beat(f"    [bold {_P}]lore add[/bold {_P}]                  [dim]Record a spell (interactive)[/dim]", 0.1)
    _beat(f"    [bold {_P}]lore search <query>[/bold {_P}]       [dim]Find spells semantically[/dim]", 0.1)
    _beat(f"    [bold {_P}]lore setup semantic[/bold {_P}]     [dim]Enable dense vector search (guided)[/dim]", 0.1)
    _beat(f"    [bold {_P}]lore export[/bold {_P}]               [dim]Republish AI context files[/dim]", 0.1)
    _beat(f"    [bold {_P}]lore relic capture --git-diff[/bold {_P}] [dim]Capture a raw artifact[/dim]", 0.1)
    _beat(f"    [bold {_P}]lore relic distill <id>[/bold {_P}]  [dim]Extract spells from a relic[/dim]", 0.1)
    _beat(f"    [bold {_P}]lore ui[/bold {_P}]                   [dim]Open the visual memory browser[/dim]", 0.1)
    _beat(f"    [bold {_P}]lore doctor[/bold {_P}]               [dim]Diagnose the store and model[/dim]", 0.1)
    console.print()
    console.print(f"  [bold {_A}]May your context never be lost.[/bold {_A}]")
    console.print()


# ---------------------------------------------------------------------------
# mem add
# ---------------------------------------------------------------------------

@app.command()
def add(
    category: Annotated[
        Optional[str],
        typer.Argument(help="Category: decisions, facts, preferences, summaries"),
    ] = None,
    content: Annotated[
        Optional[str],
        typer.Argument(help="Memory content to store"),
    ] = None,
    tags: Annotated[
        Optional[str],
        typer.Option("--tags", "-t", help="Comma-separated tags"),
    ] = None,
    depends_on: Annotated[
        Optional[str],
        typer.Option("--depends-on", help="Comma-separated memory IDs this entry depends on"),
    ] = None,
    related_to: Annotated[
        Optional[str],
        typer.Option("--related-to", help="Comma-separated related memory IDs"),
    ] = None,
    deprecated: Annotated[
        bool,
        typer.Option("--deprecated/--not-deprecated", help="Mark this memory as deprecated"),
    ] = False,
    review_date: Annotated[
        Optional[str],
        typer.Option("--review-date", help="Optional review date in YYYY-MM-DD format"),
    ] = None,
    auto_associate: Annotated[
        bool,
        typer.Option("--auto-associate", help="Suggest and attach related memories automatically"),
    ] = False,
    associate_top: Annotated[
        int,
        typer.Option("--associate-top", help="Maximum number of related memories to attach"),
    ] = 3,
    associate_min_score: Annotated[
        float,
        typer.Option("--associate-min-score", help="Minimum association score to accept"),
    ] = 0.35,
) -> None:
    """Add a new memory entry (interactive walkthrough when called with no args)."""
    from .store import add_memory
    from .search import index_memory

    root = _require_root()

    interactive_mode = category is None and content is None

    if interactive_mode:
        category, content, tags, depends_on, related_to, deprecated, review_date = _interactive_add_inputs(root)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    depends_list = _parse_id_csv(depends_on)
    related_list = _parse_id_csv(related_to)
    try:
        normalized_review_date = _normalize_review_date(review_date)
    except ValueError:
        err_console.print("[red]Invalid --review-date. Use YYYY-MM-DD.[/red]")
        raise typer.Exit(code=1)

    with console.status("Indexing…"):
        entry = add_memory(
            root,
            category,
            content,
            tags=tag_list,
            depends_on=depends_list,
            related_to=related_list,
            deprecated=deprecated,
            review_date=normalized_review_date,
        )
        index_memory(root, entry["id"], content)

    if auto_associate:
        _auto_associate_entry(
            root,
            entry,
            interactive_mode=interactive_mode,
            associate_top=associate_top,
            associate_min_score=associate_min_score,
        )
    console.print(
        f"  [bold {_P}]✓[/bold {_P}]  Saved [bold]{entry['id']}[/bold] → [bold]{category}[/bold]"
    )
    from .export import export_all
    with console.status("Updating chronicle…"):
        export_all(root)
    console.print(f"  [bold {_P}]✓[/bold {_P}]  Chronicle updated")
    console.print()


# ---------------------------------------------------------------------------
# mem list
# ---------------------------------------------------------------------------

@app.command("list")
def list_cmd(
    category: Annotated[
        Optional[str],
        typer.Argument(help="Filter by category (omit to show all)"),
    ] = None,
) -> None:
    """List stored memories."""
    from .store import list_memories

    root = _require_root()
    memories = list_memories(root, category)
    if not memories:
        console.print("[yellow]No memories found.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("#", style="dim", width=4, no_wrap=True)
    table.add_column("ID", style="dim", width=10, no_wrap=True)
    table.add_column("Category", width=14, no_wrap=True)
    table.add_column("Content", min_width=20, overflow="fold")
    table.add_column("Tags", width=20, no_wrap=True)
    table.add_column("Created", width=19, no_wrap=True)

    for i, m in enumerate(memories, 1):
        table.add_row(
            str(i),
            m.get("id", ""),
            m.get("category", ""),
            m.get("content", ""),
            ", ".join(m.get("tags", [])),
            m.get("created_at", "")[:19],
        )
    console.print(table)
    console.print(f"  [dim]Use [bold]lore edit <#>[/bold] or [bold]lore edit <id>[/bold] to modify a spell.[/dim]")


@app.command("lint")
def lint_cmd(
    fail_on: Annotated[
        Optional[str],
        typer.Option(
            "--fail-on",
            help="Comma-separated severities that should cause non-zero exit (error,warning)",
        ),
    ] = None,
) -> None:
    """Check memory quality for duplicates, stale entries, and metadata integrity."""
    from datetime import date

    from .config import load_config
    from .store import list_memories

    root = _require_root()
    cfg = load_config(root)
    memories = list_memories(root)

    if not memories:
        console.print("[yellow]No memories found.[/yellow]")
        return

    valid_ids = {str(m.get("id", "")) for m in memories if m.get("id")}
    seen_content: dict[tuple[str, str], str] = {}
    findings: list[tuple[str, str, str]] = []

    def report(severity: str, mem_id: str, message: str) -> None:
        findings.append((severity, mem_id, message))

    for m in memories:
        mem_id = str(m.get("id", "?"))
        category = str(m.get("category", "")).strip()
        content = str(m.get("content", "")).strip()
        norm_key = (category.lower(), " ".join(content.lower().split()))

        if not content:
            report("error", mem_id, "content is empty")

        if norm_key in seen_content:
            report("warning", mem_id, f"possible duplicate of {seen_content[norm_key]}")
        else:
            seen_content[norm_key] = mem_id

        tags = [str(t).strip() for t in (m.get("tags") or []) if str(t).strip()]
        if category == "instructions":
            if not tags:
                report("warning", mem_id, "instruction has no scope tag (expected one of tool tags)")
            unknown_scopes = [t for t in tags if t not in _VALID_TOOLS]
            if unknown_scopes:
                report("error", mem_id, f"instruction has unknown scope tag(s): {', '.join(unknown_scopes)}")

        for field in ("depends_on", "related_to"):
            raw = m.get(field) or []
            if not isinstance(raw, list):
                report("error", mem_id, f"{field} must be a list")
                continue
            for ref_id in raw:
                ref = str(ref_id).strip()
                if not ref:
                    continue
                if ref == mem_id:
                    report("warning", mem_id, f"{field} contains self-reference")
                elif ref not in valid_ids:
                    report("warning", mem_id, f"{field} references unknown id: {ref}")

        review_date = m.get("review_date")
        if review_date:
            try:
                due = date.fromisoformat(str(review_date))
                if due < date.today():
                    report("warning", mem_id, f"review_date has passed: {review_date}")
            except ValueError:
                report("error", mem_id, f"review_date is not valid ISO date: {review_date}")

        deprecated = m.get("deprecated", False)
        if not isinstance(deprecated, bool):
            report("error", mem_id, "deprecated must be true or false")

        trust_score = m.get("trust_score")
        min_score = int(cfg.get("trust", {}).get("chronicle_min_score", 0) or 0)
        try:
            score_int = int(trust_score)
            if score_int < min_score:
                report("warning", mem_id, f"trust_score {score_int} is below chronicle_min_score {min_score}")
        except Exception:
            report("error", mem_id, "trust_score is not an integer")

    severity_style = {
        "error": "bold red",
        "warning": f"bold {_A}",
    }

    if findings:
        table = Table(show_header=True, header_style=f"bold {_A}", expand=True)
        table.add_column("Severity", width=10, no_wrap=True)
        table.add_column("ID", style="dim", width=10, no_wrap=True)
        table.add_column("Issue", min_width=30, overflow="fold")
        for severity, mem_id, message in findings:
            label = Text(severity)
            label.stylize(severity_style.get(severity, ""))
            table.add_row(label, mem_id, message)
        console.print(table)
    else:
        console.print(f"[bold {_P}]No lint issues found.[/bold {_P}]")

    counts = {
        "error": sum(1 for sev, _, _ in findings if sev == "error"),
        "warning": sum(1 for sev, _, _ in findings if sev == "warning"),
    }
    console.print(
        f"[dim]Lint summary:[/dim] errors={counts['error']} warnings={counts['warning']}"
    )

    fail_levels = {s.strip().lower() for s in (fail_on or "").split(",") if s.strip()}
    if any(sev in fail_levels for sev, _, _ in findings):
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# mem search
# ---------------------------------------------------------------------------

@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Natural language search query")],
    top: Annotated[
        int,
        typer.Option("--top", "-k", help="Number of results to return"),
    ] = 5,
) -> None:
    """Semantic search over stored memories."""
    from .search import search as do_search

    root = _require_root()
    with console.status("Searching…"):
        results = do_search(root, query, top_k=top)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold blue", expand=True)
    table.add_column("Score", width=7, no_wrap=True)
    table.add_column("ID", style="dim", width=10, no_wrap=True)
    table.add_column("Category", width=12, no_wrap=True)
    table.add_column("Content", min_width=20, overflow="fold")

    for r in results:
        table.add_row(
            f"{r.get('_score', 0):.3f}",
            r.get("id", ""),
            r.get("category", ""),
            r.get("content", ""),
        )
    console.print(table)


@app.command()
def associate(
    ref: Annotated[
        str,
        typer.Argument(help="Row number from `lore list` or memory ID prefix"),
    ],
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Write the suggested associations into related_to on both memories"),
    ] = False,
    top: Annotated[
        int,
        typer.Option("--top", "-k", help="Number of suggestions to show"),
    ] = 5,
    min_score: Annotated[
        float,
        typer.Option("--min-score", help="Minimum association score to include"),
    ] = 0.35,
) -> None:
    """Suggest related memories for an existing entry, optionally applying them."""
    from .export import export_all
    from .search import suggest_associations
    from .store import list_memories

    root = _require_root()
    memories = list_memories(root)
    if not memories:
        console.print("[yellow]No memories found.[/yellow]")
        return

    try:
        mem = _resolve_memory_ref(memories, ref.strip())
    except ValueError as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    if mem is None:
        err_console.print(f"[red]No spell found matching '{ref}'.[/red]")
        raise typer.Exit(code=1)

    with console.status("Finding associations…"):
        suggestions = suggest_associations(
            root,
            mem_id=str(mem.get("id", "")),
            top_k=max(1, top),
            min_score=max(0.0, min(1.0, min_score)),
        )

    if not suggestions:
        console.print(f"[yellow]No related memory suggestions found for[/yellow] [bold]{mem.get('id', '')}[/bold].")
        return

    console.print(f"[bold {_A}]Association suggestions[/bold {_A}] for [bold]{mem.get('id', '')}[/bold]")
    _print_association_table(suggestions)

    if apply:
        applied = _apply_related_links(root, str(mem.get("id", "")), [str(s.get("id", "")) for s in suggestions])
        with console.status("Updating chronicle…"):
            export_all(root)
        console.print(f"  [bold {_P}]✓[/bold {_P}]  Applied [bold]{applied}[/bold] related links and updated the chronicle")


# ---------------------------------------------------------------------------
# mem remove
# ---------------------------------------------------------------------------

@app.command()
def remove(
    mem_id: Annotated[str, typer.Argument(help="Memory ID to remove")],
) -> None:
    """Remove a memory entry by ID."""
    from .store import remove_memory
    from .search import remove_from_index

    root = _require_root()
    deleted = remove_memory(root, mem_id)
    if deleted:
        remove_from_index(root, mem_id)
        console.print(f"[green]Removed[/green] [bold]{mem_id}[/bold]")
    else:
        err_console.print(f"[red]Memory ID '{mem_id}' not found.[/red]")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# lore describe
# ---------------------------------------------------------------------------

@app.command()
def describe(
    text: Annotated[
        Optional[str],
        typer.Argument(help="One-line project description"),
    ] = None,
) -> None:
    """Set the project description shown at the top of all lean instruction files."""
    from .config import load_config, save_config
    from rich.prompt import Prompt

    root = _require_root()
    cfg = load_config(root)

    if text is None:
        current = cfg.get("project_description", "").strip()
        console.print()
        if current:
            console.print(f"  [dim]Current:[/dim] {current}")
            console.print()
        text = Prompt.ask(
            f"  [bold {_P}]Project description[/bold {_P}] [dim](one line)[/dim]",
            default=current or "",
        )

    text = text.strip()
    if not text:
        console.print("  [dim]No change.[/dim]")
        return

    cfg["project_description"] = text
    save_config(root, cfg)
    console.print(f"  [bold {_P}]✓[/bold {_P}]  Description set. Run [bold]lore export[/bold] to publish.")
    console.print()


# ---------------------------------------------------------------------------
# lore instructions
# ---------------------------------------------------------------------------

_VALID_TOOLS = ["all", "agents", "copilot", "cursor", "claude", "windsurf", "gemini", "cline", "aider"]

@app.command("instructions")
def instructions_cmd(
    content: Annotated[
        Optional[str],
        typer.Argument(help="Directive for the AI tool(s)"),
    ] = None,
    tool: Annotated[
        str,
        typer.Option("--tool", "-t", help=f"Target tool tag: {', '.join(_VALID_TOOLS)}"),
    ] = "all",
) -> None:
    """Add a tool-specific instruction spell (shortcut for `lore add instructions`)."""
    from .store import add_memory
    from .search import index_memory
    from rich.prompt import Prompt

    root = _require_root()

    if tool not in _VALID_TOOLS:
        err_console.print(f"[red]Unknown tool '{tool}'. Choose: {', '.join(_VALID_TOOLS)}[/red]")
        raise typer.Exit(code=1)

    if content is None:
        console.print()
        console.print(f"  [dim]This will add a directive to the [bold]instructions[/bold] tome, scoped to \"{tool}\".[/dim]")
        console.print(f"  [dim]Tools tagged \"all\" appear in every lean instruction file.[/dim]")
        console.print()
        content = Prompt.ask(f"  [bold {_P}]Instruction[/bold {_P}]")
        while not content.strip():
            console.print(f"  [bold red]Content cannot be empty.[/bold red]")
            content = Prompt.ask(f"  [bold {_P}]Instruction[/bold {_P}]")
        console.print()

    with console.status("Indexing…"):
        entry = add_memory(root, "instructions", content.strip(), tags=[tool])
        index_memory(root, entry["id"], content)

    console.print(
        f"  [bold {_P}]✓[/bold {_P}]  Saved [bold]{entry['id']}[/bold] "
        f"→ [bold]instructions[/bold] [dim](scope: {tool})[/dim]"
    )
    console.print(f"  [dim]Run [bold]lore export[/bold] to publish to your AI tool files.[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# lore edit
# ---------------------------------------------------------------------------

@app.command()
def edit(
    ref: Annotated[
        Optional[str],
        typer.Argument(help="Row number from `lore list` or memory ID prefix"),
    ] = None,
) -> None:
    """Edit a memory — pick by row number or ID (interactive picker if no arg)."""
    from .store import list_memories, update_memory
    from .search import index_memory
    from .config import load_config
    from rich.prompt import Prompt, Confirm

    root = _require_root()
    memories = list_memories(root)
    if not memories:
        console.print("[yellow]No memories found.[/yellow]")
        return

    mem: dict | None = None

    if ref is None:
        # Interactive numbered picker
        console.print()
        table = Table(show_header=True, header_style=f"bold {_A}", expand=True)
        table.add_column("#", style="dim", width=4, no_wrap=True)
        table.add_column("ID", style="dim", width=10, no_wrap=True)
        table.add_column("Category", width=14, no_wrap=True)
        table.add_column("Content", min_width=20, overflow="fold")
        table.add_column("Tags", width=20, no_wrap=True)
        for i, m in enumerate(memories, 1):
            table.add_row(
                str(i),
                m.get("id", ""),
                m.get("category", ""),
                m.get("content", ""),
                ", ".join(m.get("tags", [])),
            )
        console.print(table)
        console.print()
        choice = Prompt.ask(f"  [bold {_P}]Which spell to edit?[/bold {_P}] [dim](#  or  id)[/dim]")
        ref = choice.strip()

    # Resolve by row number first, then ID prefix
    if ref.isdigit():
        idx = int(ref) - 1
        if 0 <= idx < len(memories):
            mem = memories[idx]
        else:
            err_console.print(f"[red]No spell at row {ref}.[/red]")
            raise typer.Exit(code=1)
    else:
        matches = [m for m in memories if m.get("id", "").startswith(ref)]
        if len(matches) == 1:
            mem = matches[0]
        elif len(matches) > 1:
            err_console.print(f"[red]Ambiguous ID prefix '{ref}' — matches {len(matches)} spells. Use more characters.[/red]")
            raise typer.Exit(code=1)
        else:
            err_console.print(f"[red]No spell found matching '{ref}'.[/red]")
            raise typer.Exit(code=1)

    # Pre-populated edit form
    console.print()
    console.print(Panel(
        f"[bold {_A}]Editing spell [dim]{mem['id']}[/dim][/bold {_A}]",
        border_style=_A, padding=(0, 2), style=f"on {_BG}",
    ))
    console.print()

    cfg = load_config(root)
    valid_cats = cfg.get("categories", [])
    console.print(f"  [dim]Available categories:[/dim] {', '.join(valid_cats)}")
    console.print()

    new_category = Prompt.ask(
        f"  [bold {_P}]Category[/bold {_P}]",
        default=mem.get("category", "facts"),
    )
    console.print()
    new_content = Prompt.ask(
        f"  [bold {_P}]Content[/bold {_P}]",
        default=mem.get("content", ""),
    )
    while not new_content.strip():
        console.print(f"  [bold red]Content cannot be empty.[/bold red]")
        new_content = Prompt.ask(f"  [bold {_P}]Content[/bold {_P}]")
    console.print()
    current_tags = ", ".join(mem.get("tags", []))
    new_tags_input = Prompt.ask(
        f"  [bold {_P}]Tags[/bold {_P}]",
        default=current_tags,
    )
    new_tags = [t.strip() for t in new_tags_input.split(",") if t.strip()]
    console.print()

    current_depends = ", ".join(mem.get("depends_on", []))
    new_depends_input = Prompt.ask(
        f"  [bold {_P}]Depends on[/bold {_P}] [dim](comma-separated IDs)[/dim]",
        default=current_depends,
    )
    new_depends = _parse_id_csv(new_depends_input)
    console.print()

    current_related = ", ".join(mem.get("related_to", []))
    new_related_input = Prompt.ask(
        f"  [bold {_P}]Related to[/bold {_P}] [dim](comma-separated IDs)[/dim]",
        default=current_related,
    )
    new_related = _parse_id_csv(new_related_input)
    console.print()

    current_deprecated = bool(mem.get("deprecated", False))
    new_deprecated = Confirm.ask(
        f"  [bold {_P}]Deprecated?[/bold {_P}]",
        default=current_deprecated,
    )
    console.print()

    current_review = str(mem.get("review_date", "") or "")
    new_review_input = Prompt.ask(
        f"  [bold {_P}]Review date[/bold {_P}] [dim](YYYY-MM-DD, blank to clear)[/dim]",
        default=current_review,
    )
    try:
        new_review_date = _normalize_review_date(new_review_input)
    except ValueError:
        err_console.print("[red]Invalid review date. Use YYYY-MM-DD.[/red]")
        raise typer.Exit(code=1)
    console.print()

    confirmed = Confirm.ask(f"  [bold {_P}]Save changes?[/bold {_P}]", default=True)
    if not confirmed:
        console.print(f"  [dim]Cancelled — nothing was changed.[/dim]\n")
        raise typer.Exit()

    updates = {
        "category": new_category,
        "content": new_content,
        "tags": new_tags,
        "depends_on": new_depends,
        "related_to": new_related,
        "deprecated": new_deprecated,
        "review_date": new_review_date,
    }
    with console.status("Saving…"):
        updated = update_memory(root, mem["id"], updates)
        if updated:
            index_memory(root, updated["id"], new_content)

    if updated:
        console.print(f"  [bold {_P}]✓[/bold {_P}]  Saved [bold]{updated['id']}[/bold] → [bold]{new_category}[/bold]")
    else:
        err_console.print(f"[red]Update failed — spell not found.[/red]")
        raise typer.Exit(code=1)
    console.print()

@app.command()
def sync(
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Path to CHRONICLE markdown file (default: ./CHRONICLE.md)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview how many entries would be added without writing"),
    ] = False,
    do_export: Annotated[
        bool,
        typer.Option("--export/--no-export", help="Export AI context files after sync"),
    ] = True,
) -> None:
    """Import shared CHRONICLE.md entries into the local .lore store."""
    from .chronicle import import_chronicle
    from .search import batch_index_memories

    root = _require_root()
    chosen = file.resolve() if file else None

    with console.status("Syncing CHRONICLE into local lore store…"):
        try:
            stats = import_chronicle(root, chronicle_path=chosen, dry_run=dry_run)
        except RuntimeError as exc:
            err_console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1)

    if not dry_run and stats["indexed_pairs"]:
        with console.status("Indexing imported memories…"):
            batch_index_memories(root, stats["indexed_pairs"])

    mode = "(dry run) " if dry_run else ""
    console.print(
        f"[green]{mode}Sync complete.[/green] "
        f"Added [bold]{stats['added']}[/bold], "
        f"skipped duplicates [bold]{stats['skipped_duplicates']}[/bold], "
        f"recognized [bold]{stats['recognized']}[/bold] bullets."
    )

    if stats["skipped_unknown_section"]:
        console.print(
            f"[yellow]Skipped {stats['skipped_unknown_section']} bullet(s) outside recognized sections.[/yellow]"
        )

    source_path = stats["path"]
    rel = source_path.relative_to(root) if source_path.is_relative_to(root) else source_path
    console.print(f"[dim]Source:[/dim] {rel}")

    if do_export and not dry_run:
        from .export import export_all
        with console.status("Exporting updated context files…"):
            paths = export_all(root)
        for p in paths:
            console.print(f"[green]Wrote[/green] {p.relative_to(root)}")


@app.command()
def extract(
    last: Annotated[
        int,
        typer.Option("--last", "-n", help="Number of recent commits to scan"),
    ] = 20,
    auto: Annotated[
        bool,
        typer.Option("--auto", help="Save all candidates without prompting"),
    ] = False,
    do_export: Annotated[
        bool,
        typer.Option("--export", help="Also export AI context files after saving (avoids a second process startup)"),
    ] = False,
) -> None:
    """Extract memory candidates from git commit history."""
    from .extract import extract_from_git
    from .store import add_memory
    from .search import batch_index_memories

    root = _require_root()
    with console.status(f"Scanning last {last} commit(s)…"):
        try:
            candidates = extract_from_git(root, n_commits=last)
        except RuntimeError as e:
            err_console.print(f"[red]{e}[/red]")
            raise typer.Exit(code=1)

    if not candidates:
        console.print("[yellow]No memory candidates found in commit history.[/yellow]")
        if do_export:
            from .export import export_all
            export_all(root)
        return

    console.print(f"Found [bold]{len(candidates)}[/bold] candidate(s).\n")

    to_index: list[tuple[str, str]] = []
    saved = 0
    for i, c in enumerate(candidates, 1):
        console.print(
            f"[bold]\\[{i}/{len(candidates)}][/bold] "
            f"[cyan]\\[{c['category']}][/cyan] {c['content']}"
        )
        if not auto and not typer.confirm("  Save this memory?", default=True):
            continue
        entry = add_memory(root, c["category"], c["content"], source=c["source"])
        to_index.append((entry["id"], c["content"]))
        saved += 1

    if to_index:
        with console.status("Indexing…"):
            batch_index_memories(root, to_index)

    console.print(f"\n[green]Saved {saved} memory(s).[/green]")

    if do_export:
        from .export import export_all
        with console.status("Exporting…"):
            paths = export_all(root)
        for p in paths:
            console.print(f"[green]Exported[/green] {p.relative_to(root)}")


# ---------------------------------------------------------------------------
# mem export
# ---------------------------------------------------------------------------

@app.command()
def export(
    fmt: Annotated[
        str,
        typer.Option(
            "--format", "-f",
            help="Target format: agents | copilot | cursor | claude | all",
        ),
    ] = "all",
) -> None:
    """Export memories as AI context files."""
    from .export import EXPORT_TARGETS, export_all

    root = _require_root()
    if fmt == "all":
        paths = export_all(root)
    elif fmt in EXPORT_TARGETS:
        paths = [EXPORT_TARGETS[fmt](root)]
    else:
        valid = ", ".join(EXPORT_TARGETS) + ", all"
        err_console.print(f"[red]Unknown format '{fmt}'. Choose: {valid}[/red]")
        raise typer.Exit(code=1)

    for p in paths:
        rel = p.relative_to(root)
        console.print(f"[green]Wrote[/green] {rel}")

    from .config import load_config
    cfg = load_config(root)
    if not cfg.get("project_description", "").strip():
        console.print(
            f"\n[{_A}]Tip:[/{_A}] No project description set — "
            "lean instruction files will lack a project summary.\n"
            f"  Run [bold]lore onboard[/bold] or add "
            f"[bold]project_description[/bold] to [dim].lore/config.yaml[/dim]."
        )


# ---------------------------------------------------------------------------
# mem hook install
# ---------------------------------------------------------------------------

@hook_app.command("install")
def hook_install() -> None:
    """Interactive wizard to install the git post-commit hook."""
    from .extract import install_git_hook, _is_git_repo
    from rich.prompt import Confirm
    from rich.syntax import Syntax

    root = _require_root()

    console.print()
    console.print(f"  {_BANNER_TEXT}")
    console.print()
    console.print(f"  [bold]Git Hook Setup[/bold]")
    console.print(
        f"  [dim]A [bold {_P}]post-commit[/bold {_P}] hook runs automatically after every"
        f" [bold]git commit[/bold].\n"
        f"  Lore can use it to extract memories from your commit messages\n"
        f"  and optionally keep your AI context files up to date.[/dim]"
    )
    console.print()

    # Check git repo
    if not _is_git_repo(root):
        err_console.print(
            f"[red]  ✗  {root} is not a git repository. Run [bold]git init[/bold] first.[/red]"
        )
        raise typer.Exit(code=1)

    # Check for existing hook
    hook_path = root / ".git" / "hooks" / "post-commit"
    if hook_path.exists():
        existing = hook_path.read_text()
        console.print(f"  [bold {_A}]▲[/bold {_A}]  A post-commit hook already exists:")
        console.print()
        console.print(Syntax(existing, "sh", theme="ansi_dark", line_numbers=False))
        console.print()
        if not Confirm.ask(
            f"  [bold {_P}]Overwrite it?[/bold {_P}]", default=False
        ):
            console.print(f"  [dim]Cancelled — existing hook left in place.[/dim]\n")
            raise typer.Exit()
        console.print()

    # Step 1 — extract on commit
    console.print(f"  [bold]Step 1 of 2  —  Auto-extract memories from commits[/bold]")
    console.print(
        f"  [dim]After each commit, lore will scan the message for decisions,\n"
        f"  choices, and context and store them automatically.[/dim]"
    )
    console.print()
    do_extract = Confirm.ask(
        f"  [bold {_P}]Enable auto-extract on commit?[/bold {_P}]", default=True
    )
    console.print()

    if not do_extract:
        console.print(f"  [dim]Nothing to install — hook requires at least auto-extract.\n"
                      f"  You can always run [bold]lore extract[/bold] manually.[/dim]\n")
        raise typer.Exit()

    # Step 2 — auto-export
    console.print(f"  [bold]Step 2 of 2  —  Auto-export AI context files on commit[/bold]")
    console.print(
        f"  [dim]After extracting, lore can immediately re-write:\n"
        f"  [bold].github/copilot-instructions.md[/bold], [bold]AGENTS.md[/bold], "
        f"[bold]CLAUDE.md[/bold], [bold].cursor/rules/memory.md[/bold]\n"
        f"  so your AI tools always see the latest memories.[/dim]\n"
        f"  [bold {_A}]Note:[/bold {_A}] [dim]This adds the exported files to your working tree —\n"
        f"  you may want to stage and commit them in a follow-up commit.[/dim]"
    )
    console.print()
    do_export = Confirm.ask(
        f"  [bold {_P}]Also auto-export AI context files after each commit?[/bold {_P}]",
        default=True,
    )
    console.print()

    # Preview the hook script
    preview_lines = [
        "#!/bin/sh",
        "# Installed by lore",
        "lore extract --last 1 --auto",
    ]
    if do_export:
        preview_lines.append("lore export")
    preview_lines.append("")
    preview = "\n".join(preview_lines)

    console.print(f"  [dim]───────────────────────────────[/dim]")
    console.print(f"  [bold]Hook script preview:[/bold]")
    console.print()
    console.print(Syntax(preview, "sh", theme="ansi_dark", line_numbers=False))
    console.print(f"  [dim]Will be written to:[/dim] [bold]{hook_path}[/bold]")
    console.print(f"  [dim]───────────────────────────────[/dim]")
    console.print()

    if not Confirm.ask(f"  [bold {_P}]Install this hook?[/bold {_P}]", default=True):
        console.print(f"  [dim]Cancelled. Nothing was written.[/dim]\n")
        raise typer.Exit()

    try:
        path = install_git_hook(root, auto_export=do_export)
        console.print()
        console.print(f"  [bold {_P}]✓[/bold {_P}]  Hook installed at [bold]{path}[/bold]")
        console.print()
        console.print(f"  [dim]From now on, every [bold]git commit[/bold] will:[/dim]")
        console.print(f"  [dim]  · Extract memory candidates from the commit message[/dim]")
        if do_export:
            console.print(f"  [dim]  · Regenerate all AI context files immediately[/dim]")
        console.print(f"  [dim]Run [bold]lore list[/bold] after your next commit to see it in action.[/dim]")
    except RuntimeError as e:
        err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    console.print()


# ---------------------------------------------------------------------------
# lore hook uninstall
# ---------------------------------------------------------------------------

@hook_app.command("uninstall")
def hook_uninstall() -> None:
    """Remove the lore-managed post-commit git hook."""
    from .extract import uninstall_git_hook
    from rich.prompt import Confirm

    root = _require_root()
    hook_path = root / ".git" / "hooks" / "post-commit"

    if not hook_path.exists():
        console.print("[yellow]No post-commit hook found — nothing to remove.[/yellow]")
        raise typer.Exit()

    content = hook_path.read_text()
    if "# Installed by lore" not in content:
        err_console.print(
            f"[red]The hook at {hook_path} was not installed by lore.[/red]\n"
            "[dim]Remove it manually to avoid accidentally deleting someone else's hook.[/dim]"
        )
        raise typer.Exit(code=1)

    console.print(f"  [dim]Will remove:[/dim] [bold]{hook_path}[/bold]")
    if not Confirm.ask(f"  [bold #39ff14]Remove the hook?[/bold #39ff14]", default=False):
        console.print("  [dim]Cancelled — hook left in place.[/dim]")
        raise typer.Exit()

    try:
        uninstall_git_hook(root)
        console.print(f"  [bold #39ff14]✓[/bold #39ff14]  Hook removed.")
    except RuntimeError as e:
        err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)


@hook_app.command("sync-install")
def hook_sync_install() -> None:
    """Install a post-merge hook that syncs CHRONICLE.md changes into .lore."""
    from .extract import install_post_merge_sync_hook, _is_git_repo
    from rich.prompt import Confirm
    from rich.syntax import Syntax

    root = _require_root()

    if not _is_git_repo(root):
        err_console.print(
            f"[red]  ✗  {root} is not a git repository. Run [bold]git init[/bold] first.[/red]"
        )
        raise typer.Exit(code=1)

    hook_path = root / ".git" / "hooks" / "post-merge"
    if hook_path.exists():
        existing = hook_path.read_text()
        console.print(f"  [bold {_A}]▲[/bold {_A}]  A post-merge hook already exists:")
        console.print()
        console.print(Syntax(existing, "sh", theme="ansi_dark", line_numbers=False))
        console.print()
        if not Confirm.ask(
            f"  [bold {_P}]Overwrite it?[/bold {_P}]", default=False
        ):
            console.print(f"  [dim]Cancelled — existing hook left in place.[/dim]\n")
            raise typer.Exit()

    preview = "\n".join([
        "#!/bin/sh",
        "# Installed by lore -- chronicle sync",
        "if git diff --name-only ORIG_HEAD HEAD | grep -q '^CHRONICLE.md$'; then",
        "  lore sync --no-export >/dev/null 2>&1",
        "  lore export >/dev/null 2>&1",
        "fi",
        "",
    ])

    console.print(f"  [dim]───────────────────────────────[/dim]")
    console.print(f"  [bold]Hook script preview:[/bold]")
    console.print()
    console.print(Syntax(preview, "sh", theme="ansi_dark", line_numbers=False))
    console.print(f"  [dim]Will be written to:[/dim] [bold]{hook_path}[/bold]")
    console.print(f"  [dim]───────────────────────────────[/dim]")
    console.print()

    if not Confirm.ask(f"  [bold {_P}]Install this hook?[/bold {_P}]", default=True):
        console.print(f"  [dim]Cancelled. Nothing was written.[/dim]\n")
        raise typer.Exit()

    try:
        path = install_post_merge_sync_hook(root)
        console.print()
        console.print(f"  [bold {_P}]✓[/bold {_P}]  Sync hook installed at [bold]{path}[/bold]")
        console.print(
            "  [dim]After git merge/pull, lore will sync when CHRONICLE.md changes.[/dim]"
        )
    except RuntimeError as e:
        err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)


@hook_app.command("sync-uninstall")
def hook_sync_uninstall() -> None:
    """Remove the lore-managed post-merge CHRONICLE sync hook."""
    from .extract import uninstall_post_merge_sync_hook
    from rich.prompt import Confirm

    root = _require_root()
    hook_path = root / ".git" / "hooks" / "post-merge"

    if not hook_path.exists():
        console.print("[yellow]No post-merge hook found — nothing to remove.[/yellow]")
        raise typer.Exit()

    content = hook_path.read_text()
    if "# Installed by lore -- chronicle sync" not in content:
        err_console.print(
            f"[red]The hook at {hook_path} was not installed by lore.[/red]\n"
            "[dim]Remove it manually to avoid accidentally deleting someone else's hook.[/dim]"
        )
        raise typer.Exit(code=1)

    console.print(f"  [dim]Will remove:[/dim] [bold]{hook_path}[/bold]")
    if not Confirm.ask(f"  [bold #39ff14]Remove the hook?[/bold #39ff14]", default=False):
        console.print("  [dim]Cancelled — hook left in place.[/dim]")
        raise typer.Exit()

    try:
        uninstall_post_merge_sync_hook(root)
        console.print(f"  [bold #39ff14]✓[/bold #39ff14]  Sync hook removed.")
    except RuntimeError as e:
        err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# lore index rebuild
# ---------------------------------------------------------------------------

@index_app.command("rebuild")
def index_rebuild() -> None:
    """Rebuild the semantic embedding index from all stored memories."""
    from .search import rebuild_index

    root = _require_root()
    with console.status("Rebuilding index…"):
        count = rebuild_index(root)
    console.print(f"[green]Indexed {count} memory(s).[/green]")


# ---------------------------------------------------------------------------
# lore setup semantic
# ---------------------------------------------------------------------------

@setup_app.command("semantic")
def setup_semantic(
    install_now: Annotated[
        bool,
        typer.Option("--install-now", help="Install semantic dependencies without prompting"),
    ] = False,
) -> None:
    """Guided setup for dense vector search (sentence-transformers)."""
    import subprocess
    import sys
    from io import StringIO
    from rich.prompt import Confirm

    from .config import load_config

    root = _require_root()
    cfg = load_config(root)
    endpoint = cfg.get("model_endpoint") or "https://huggingface.co"
    ssl_verify = cfg.get("model_ssl_verify", True)
    model_name = cfg.get("embedding_model", "all-MiniLM-L6-v2")

    console.print()
    console.print(Panel(
        f"[bold {_A}]Dense Vector Search Setup[/bold {_A}]\n"
        f"[dim]Want dense vector search? This wizard enables and validates semantic embeddings.[/dim]",
        border_style=_BD, padding=(1, 2), style=f"on {_BG}",
    ))
    console.print(f"  [dim]Model   :[/dim] [bold]{model_name}[/bold]")
    console.print(f"  [dim]Endpoint:[/dim] [bold]{endpoint}[/bold]")
    console.print(f"  [dim]SSL     :[/dim] {'enabled' if ssl_verify else 'disabled'}")
    console.print()

    dep_ok = True
    try:
        import sentence_transformers  # noqa: F401
    except Exception:
        dep_ok = False

    install_cmd = f'"{sys.executable}" -m pip install "lore-book[semantic]"'
    if not dep_ok:
        console.print(f"  [bold {_A}]▲[/bold {_A}] [bold]sentence-transformers[/bold] is not installed.")
        console.print(f"  [dim]Install command:[/dim] {install_cmd}")
        console.print()
        should_install = install_now or Confirm.ask(
            f"  [bold {_P}]Install semantic dependencies now?[/bold {_P}]",
            default=True,
        )
        if not should_install:
            console.print(f"\n  [dim]Skipped install. Run [bold]lore setup semantic[/bold] any time to continue.[/dim]")
            raise typer.Exit(code=1)

        with console.status("Installing semantic dependencies…"):
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", "lore-book[semantic]"],
                capture_output=True,
                text=True,
            )

        if proc.returncode != 0:
            err_console.print("[red]Install failed.[/red]")
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()
            if tail:
                err_console.print(f"[dim]{tail[-1]}[/dim]")
            err_console.print(f"[dim]Try manually:[/dim] {install_cmd}")
            raise typer.Exit(code=1)

        console.print(f"  [bold {_P}]✓[/bold {_P}]  Dependencies installed.")
        console.print()

    console.print(f"  [{_A}]Checking model load…[/{_A}]", end=" ")
    try:
        import logging
        import warnings

        for logger_name in (
            "huggingface_hub", "huggingface_hub.file_download",
            "huggingface_hub.utils", "sentence_transformers",
            "urllib3", "tqdm",
        ):
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        warnings.filterwarnings("ignore")

        if endpoint:
            os.environ["HF_ENDPOINT"] = endpoint.rstrip("/")

        _orig_ssl_ctx = None
        if not ssl_verify:
            import ssl as _ssl_mod
            os.environ["CURL_CA_BUNDLE"] = ""
            os.environ["REQUESTS_CA_BUNDLE"] = ""
            _orig_ssl_ctx = _ssl_mod._create_default_https_context  # noqa: SLF001
            _ssl_mod._create_default_https_context = _ssl_mod._create_unverified_context  # noqa: SLF001

        from sentence_transformers import SentenceTransformer
        _old_out, _old_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = StringIO()
        try:
            SentenceTransformer(model_name)
        finally:
            sys.stdout, sys.stderr = _old_out, _old_err
            if _orig_ssl_ctx is not None:
                import ssl as _ssl_mod
                _ssl_mod._create_default_https_context = _orig_ssl_ctx  # noqa: SLF001

        console.print(f"[bold {_P}]ready ✓[/bold {_P}]")
        console.print(f"\n  [bold {_P}]Dense vector search is enabled.[/bold {_P}]")
        console.print(f"  [dim]Try:[/dim] [bold]lore search \"your query\"[/bold]")
    except Exception as exc:
        console.print(f"[bold {_A}]unavailable[/bold {_A}]")
        err_console.print(f"  [bold {_A}]▲[/bold {_A}] Could not load model: [dim]{exc}[/dim]")
        err_console.print(
            f"  [dim]Check endpoint/SSL settings with [bold]lore config[/bold], then re-run "
            f"[bold]lore setup semantic[/bold].[/dim]"
        )
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# lore setup extract-patterns
# ---------------------------------------------------------------------------

@setup_app.command("extract-patterns")
def setup_extraction_patterns() -> None:
    """Manage custom commit message extraction patterns for auto-categorizing memories."""
    from .config import load_config, save_config
    from rich.prompt import Prompt, Confirm
    from rich.table import Table

    root = _require_root()
    cfg = load_config(root)
    patterns = cfg.get("extraction_patterns", [])

    console.print()
    console.print(Panel(
        f"[bold {_A}]Extraction Patterns Setup[/bold {_A}]\n"
        f"[dim]Teach lore to auto-categorize memories from your commit messages.[/dim]",
        border_style=_BD, padding=(1, 2), style=f"on {_BG}",
    ))
    console.print(f"  [dim]Patterns override how lore categorizes extracted commits.[/dim]")
    console.print()

    # Show current patterns
    if patterns:
        console.print(f"  [bold]Current patterns ({len(patterns)}):[/bold]")
        table = Table(show_header=True, header_style=f"bold {_A}", box=box.SIMPLE)
        table.add_column("Name",     width=20, no_wrap=True)
        table.add_column("Type",     width=8,  no_wrap=True)
        table.add_column("Category", width=14, no_wrap=True)
        table.add_column("Pattern",  min_width=30, overflow="fold")
        table.add_column("Enabled",  width=8,  no_wrap=True)
        for p in patterns:
            enabled_str = "✓" if p.get("enabled", True) else "✗"
            table.add_row(
                p.get("name", "?"),
                p.get("type", "?"),
                p.get("category", "?"),
                p.get("pattern", "?"),
                enabled_str,
            )
        console.print(table)
        console.print()

    while True:
        console.print(f"  [bold]Actions:[/bold]")
        console.print(f"    [bold {_P}]a[/bold {_P}]  Add a new pattern")
        console.print(f"    [bold {_P}]e[/bold {_P}]  Edit existing pattern")
        console.print(f"    [bold {_P}]d[/bold {_P}]  Delete a pattern")
        console.print(f"    [bold {_P}]s[/bold {_P}]  Save and exit")
        console.print()
        action = Prompt.ask(
            f"  [bold {_P}]Choose[/bold {_P}]",
            choices=["a", "e", "d", "s"],
            default="s",
        ).lower()

        if action == "a":
            console.print()
            console.print(f"  [bold]Add pattern[/bold]")
            console.print(f"  [dim]Example: DECISION: comments get categorized as 'decisions'[/dim]")
            console.print()
            name = Prompt.ask(f"  [bold {_P}]Name[/bold {_P}]").strip()
            if not name:
                console.print("[yellow]Name cannot be empty.[/yellow]\n")
                continue

            pattern_type = Prompt.ask(
                f"  [bold {_P}]Type[/bold {_P}]",
                choices=["regex", "prefix"],
                default="prefix",
            ).lower()
            console.print(f"  [dim]Pattern is {pattern_type}. Matching is case-" +
                         ("insensitive regex." if pattern_type == "regex" else "insensitive prefix.") + "[/dim]")
            pattern_str = Prompt.ask(f"  [bold {_P}]Pattern[/bold {_P}]").strip()
            if not pattern_str:
                console.print("[yellow]Pattern cannot be empty.[/yellow]\n")
                continue

            if pattern_type == "regex":
                try:
                    import re
                    re.compile(pattern_str)
                except Exception as e:
                    console.print(f"[yellow]Invalid regex: {e}[/yellow]\n")
                    continue

            category = Prompt.ask(
                f"  [bold {_P}]Category[/bold {_P}]",
                default="facts",
            ).strip()

            enabled = Confirm.ask(
                f"  [bold {_P}]Enabled[/bold {_P}]",
                default=True,
            )

            patterns.append({
                "name": name,
                "type": pattern_type,
                "pattern": pattern_str,
                "category": category,
                "enabled": enabled,
            })
            console.print(f"\n  [bold {_P}]✓[/bold {_P}]  Pattern added.\n")

        elif action == "e":
            if not patterns:
                console.print("[yellow]No patterns to edit.[/yellow]\n")
                continue
            console.print()
            console.print(f"  [dim]Which pattern to edit?[/dim]")
            for i, p in enumerate(patterns):
                console.print(f"    {i+1}. {p['name']} ({p['type']})")
            idx_str = Prompt.ask(f"  [bold {_P}]Number[/bold {_P}]").strip()
            try:
                idx = int(idx_str) - 1
                if 0 <= idx < len(patterns):
                    pat = patterns[idx]
                    console.print()
                    console.print(f"  [bold]Editing: {pat['name']}[/bold]")
                    pat["name"] = Prompt.ask(f"  [bold {_P}]Name[/bold {_P}]", default=pat["name"]).strip()
                    pat["pattern"] = Prompt.ask(f"  [bold {_P}]Pattern[/bold {_P}]", default=pat["pattern"]).strip()
                    pat["category"] = Prompt.ask(f"  [bold {_P}]Category[/bold {_P}]", default=pat["category"]).strip()
                    pat["enabled"] = Confirm.ask(f"  [bold {_P}]Enabled[/bold {_P}]", default=pat.get("enabled", True))
                    console.print(f"\n  [bold {_P}]✓[/bold {_P}]  Pattern updated.\n")
                else:
                    console.print(f"[yellow]Invalid number.[/yellow]\n")
            except ValueError:
                console.print(f"[yellow]Invalid input.[/yellow]\n")

        elif action == "d":
            if not patterns:
                console.print("[yellow]No patterns to delete.[/yellow]\n")
                continue
            console.print()
            console.print(f"  [dim]Which pattern to delete?[/dim]")
            for i, p in enumerate(patterns):
                console.print(f"    {i+1}. {p['name']}")
            idx_str = Prompt.ask(f"  [bold {_P}]Number[/bold {_P}]").strip()
            try:
                idx = int(idx_str) - 1
                if 0 <= idx < len(patterns):
                    pat = patterns[idx]
                    if Confirm.ask(f"  [bold red]Delete '{pat['name']}'?[/bold red]", default=False):
                        patterns.pop(idx)
                        console.print(f"\n  [bold {_P}]✓[/bold {_P}]  Pattern deleted.\n")
                else:
                    console.print(f"[yellow]Invalid number.[/yellow]\n")
            except ValueError:
                console.print(f"[yellow]Invalid input.[/yellow]\n")

        elif action == "s":
            break

    cfg["extraction_patterns"] = patterns
    save_config(root, cfg)
    console.print(f"  [bold {_P}]✓[/bold {_P}]  Saved. Run [bold]lore extract[/bold] to test patterns.")
    console.print()


# ---------------------------------------------------------------------------
# lore trust refresh
# ---------------------------------------------------------------------------

@trust_app.command("refresh")
def trust_refresh(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would change without writing files"),
    ] = False,
) -> None:
    """Recompute trust score/level metadata for all stored memories."""
    from datetime import datetime, timezone

    from .config import load_config
    from .store import list_memories, update_memory
    from .trust import build_author_activity_bonus, score_memory, trust_level

    root = _require_root()
    cfg = load_config(root)
    memories = list_memories(root)

    if not memories:
        console.print("[yellow]No memories found. Add entries first with lore add.[/yellow]")
        return

    with console.status("Scoring trust from git and metadata signals…"):
        bonuses = build_author_activity_bonus(root, cfg)

        changed = 0
        level_counts = {"high": 0, "medium": 0, "low": 0}
        for entry in memories:
            score, reasons = score_memory(root, entry, cfg, author_activity_bonus=bonuses)
            level = trust_level(score)
            level_counts[level] += 1
            now_iso = datetime.now(timezone.utc).isoformat()

            source = (entry.get("source") or "")
            source_commit = entry.get("source_commit")
            if source.startswith("git:") and not source_commit:
                parts = source.split(":", 2)
                source_commit = parts[1] if len(parts) > 1 else None

            if (
                entry.get("trust_score") != score
                or entry.get("trust_level") != level
                or entry.get("trust_reasons") != reasons
                or (source_commit and entry.get("source_commit") != source_commit)
            ):
                changed += 1
                if not dry_run:
                    snapshots_raw = entry.get("trust_score_snapshots") or []
                    snapshots: list[dict[str, object]] = []
                    if isinstance(snapshots_raw, list):
                        for item in snapshots_raw:
                            if isinstance(item, dict):
                                snapshots.append(item)
                    snapshots.append(
                        {
                            "updated_at": now_iso,
                            "score": score,
                            "level": level,
                            "reasons": reasons,
                        }
                    )
                    snapshots = snapshots[-25:]

                    updates: dict[str, object] = {
                        "trust_score": score,
                        "trust_level": level,
                        "trust_reasons": reasons,
                        "trust_updated_at": now_iso,
                        "trust_score_snapshots": snapshots,
                    }
                    if source_commit:
                        updates["source_commit"] = source_commit
                    update_memory(root, entry["id"], updates)

    mode = "(dry run) " if dry_run else ""
    console.print(
        f"[green]{mode}Trust refresh complete.[/green] "
        f"Updated [bold]{changed}[/bold] of [bold]{len(memories)}[/bold] entries."
    )
    console.print(
        "Distribution: "
        f"high={level_counts['high']}  "
        f"medium={level_counts['medium']}  "
        f"low={level_counts['low']}"
    )


@trust_app.command("explain")
def trust_explain(
    mem_id: Annotated[str, typer.Argument(help="Memory ID (full or prefix)")],
    recompute: Annotated[
        bool,
        typer.Option("--recompute", help="Recompute score now instead of using stored reasons"),
    ] = False,
) -> None:
    """Show how a memory's trust score was derived."""
    from .config import load_config
    from .store import list_memories
    from .trust import (
        build_author_activity_bonus,
        memory_trust_score,
        score_memory,
        trust_level,
    )

    root = _require_root()
    cfg = load_config(root)
    memories = list_memories(root)

    matches = [m for m in memories if str(m.get("id", "")).startswith(mem_id)]
    if not matches:
        err_console.print(f"[red]No memory found for id/prefix '{mem_id}'.[/red]")
        raise typer.Exit(code=1)
    if len(matches) > 1:
        ids = ", ".join(m.get("id", "?") for m in matches[:8])
        err_console.print(
            "[red]ID prefix is ambiguous.[/red] "
            f"Matches: [dim]{ids}{'…' if len(matches) > 8 else ''}[/dim]"
        )
        raise typer.Exit(code=1)

    entry = matches[0]
    default_score = int(cfg.get("trust", {}).get("default_score", 50) or 50)

    stored_score = memory_trust_score(entry, default_score=default_score)
    stored_level = entry.get("trust_level") or trust_level(stored_score)
    stored_reasons = entry.get("trust_reasons") or []

    live_score = stored_score
    live_level = stored_level
    live_reasons = list(stored_reasons)

    if recompute or not live_reasons:
        bonuses = build_author_activity_bonus(root, cfg)
        live_score, live_reasons = score_memory(root, entry, cfg, author_activity_bonus=bonuses)
        live_level = trust_level(live_score)

    console.print()
    console.print(f"[bold]Memory[/bold] {entry.get('id', '?')}  [dim]({entry.get('category', 'facts')})[/dim]")
    console.print(f"[dim]{entry.get('content', '').strip()}[/dim]")
    console.print()

    console.print(
        f"Stored trust: [bold]{stored_level} {stored_score}[/bold]"
        + (" [dim](from last refresh)[/dim]" if stored_reasons else " [dim](default/no reasons stored)[/dim]")
    )
    console.print(f"Current trust: [bold]{live_level} {live_score}[/bold]")

    if live_reasons:
        console.print("\n[bold]Reasons[/bold]")
        for reason in live_reasons:
            console.print(f"- {reason}")

    snapshots = entry.get("trust_score_snapshots") or []
    if isinstance(snapshots, list) and snapshots:
        console.print("\n[bold]History[/bold]")
        for snap in snapshots[-5:]:
            if not isinstance(snap, dict):
                continue
            when = snap.get("updated_at", "?")
            score = snap.get("score", "?")
            level = snap.get("level", "?")
            console.print(f"- {when}: {level} {score}")

    source = entry.get("source")
    author = entry.get("git_author")
    tags = entry.get("tags") or []
    if source or author or tags:
        console.print("\n[bold]Signals[/bold]")
        if source:
            console.print(f"- source: {source}")
        if author:
            console.print(f"- git_author: {author}")
        if tags:
            console.print(f"- tags: {', '.join(tags)}")


# ---------------------------------------------------------------------------
# lore config
# ---------------------------------------------------------------------------

@app.command("config")
def config_set(
    key: Annotated[str, typer.Argument(help="Config key to set")],
    value: Annotated[str, typer.Argument(help="Value to set")],
) -> None:
    """Set a config value in .lore/config.yaml.

    \b
    Examples:
      lore config model_endpoint https://artifactory.example.com/huggingface
      lore config model_ssl_verify false
      lore config embedding_model all-MiniLM-L6-v2
      lore config scope local
    """
    from .config import load_config, save_config
    root = _require_root()
    cfg = load_config(root)
    # coerce booleans
    coerced: object = value
    if value.lower() in ("true", "yes", "1"):
        coerced = True
    elif value.lower() in ("false", "no", "0", "none", "null", ""):
        coerced = False if value.lower() in ("false", "no", "0") else None
    cfg[key] = coerced
    save_config(root, cfg)
    console.print(f"[green]Set[/green] {key} = {coerced!r}")


# ---------------------------------------------------------------------------
# lore security
# ---------------------------------------------------------------------------

@app.command()
def security() -> None:
    """Configure the security preamble injected into all AI context file exports."""
    from .config import load_config, save_config
    from rich.prompt import Prompt, Confirm

    root = _require_root()
    cfg  = load_config(root)
    sec  = dict(cfg.get("security", {}))

    console.print()
    console.print(f"  {_BANNER_TEXT}")
    console.print()
    console.print(f"  [bold]Security preamble setup[/bold]")
    console.print(
        f"  [dim]When enabled, a security guidelines section is prepended to every\n"
        f"  AI context file written by [bold]lore export[/bold] "
        f"(.github/copilot-instructions.md, AGENTS.md, CLAUDE.md, .cursorrules).[/dim]"
    )
    console.print()

    # ── Step 1: enable/disable ───────────────────────────────────────────────
    currently = sec.get("enabled", False)
    console.print(f"  [bold]Step 1 of 5  —  Enable security preamble[/bold]")
    console.print(f"  [dim]Currently:[/dim] {'enabled' if currently else 'disabled'}")
    console.print()
    enabled = Confirm.ask(
        f"  [bold {_P}]Include security guidelines in exports?[/bold {_P}]",
        default=currently,
    )
    sec["enabled"] = enabled
    console.print()

    if not enabled:
        cfg["security"] = sec
        save_config(root, cfg)
        console.print(f"  [dim]Security preamble disabled. Run [bold]lore export[/bold] to update files.[/dim]")
        console.print()
        return

    # ── Step 2: OWASP Top 10 ────────────────────────────────────────────────
    console.print(f"  [bold]Step 2 of 5  —  OWASP Top 10[/bold]")
    console.print(
        f"  [dim]Adds a bullet referencing all 10 OWASP categories\n"
        f"  (injection, broken access control, cryptographic failures, etc.)[/dim]"
    )
    console.print()
    sec["owasp_top10"] = Confirm.ask(
        f"  [bold {_P}]Include OWASP Top 10 reference?[/bold {_P}]",
        default=sec.get("owasp_top10", True),
    )
    console.print()

    # ── Step 3: security policy file ────────────────────────────────────────
    console.print(f"  [bold]Step 3 of 5  —  Security policy file[/bold]")
    console.print(
        f"  [dim]Path to your SECURITY.md (relative to repo root).\n"
        f"  Leave blank to skip this reference.[/dim]"
    )
    console.print()
    policy_default = sec.get("security_policy", "SECURITY.md") or ""
    policy_input = Prompt.ask(
        f"  [bold {_P}]Security policy file[/bold {_P}]",
        default=policy_default,
    )
    sec["security_policy"] = policy_input.strip() or None
    console.print()

    # ── Step 4: CODEOWNERS ──────────────────────────────────────────────────
    console.print(f"  [bold]Step 4 of 5  —  CODEOWNERS[/bold]")
    console.print(
        f"  [dim]Adds a note that sensitive paths are governed by CODEOWNERS\n"
        f"  and require additional human review.[/dim]"
    )
    console.print()
    sec["codeowners"] = Confirm.ask(
        f"  [bold {_P}]Reference CODEOWNERS in guidelines?[/bold {_P}]",
        default=sec.get("codeowners", True),
    )
    console.print()

    # ── Step 5: custom rules ─────────────────────────────────────────────────
    existing_rules: list[str] = sec.get("custom_rules", [])
    console.print(f"  [bold]Step 5 of 5  —  Custom rules[/bold]")
    console.print(
        f"  [dim]Add project-specific security rules (e.g. \"Never call external APIs "
        f"without rate limiting.\").\n  Enter one rule per prompt. Leave blank and press Enter to finish.[/dim]"
    )
    if existing_rules:
        console.print(f"\n  [dim]Existing rules:[/dim]")
        for r in existing_rules:
            console.print(f"    [dim]·[/dim] {r}")
    console.print()
    keep_existing = True
    if existing_rules:
        keep_existing = Confirm.ask(
            f"  [bold {_P}]Keep existing custom rules?[/bold {_P}]",
            default=True,
        )
        console.print()
    new_rules: list[str] = list(existing_rules) if keep_existing else []
    while True:
        rule = Prompt.ask(f"  [bold {_P}]Rule[/bold {_P}] [dim](blank to finish)[/dim]", default="")
        if not rule.strip():
            break
        new_rules.append(rule.strip())
    sec["custom_rules"] = new_rules
    console.print()

    # ── Save ─────────────────────────────────────────────────────────────────
    console.print(f"  [dim]───────────────────────────────[/dim]")
    console.print(f"  [bold]OWASP Top 10 :[/bold] {'yes' if sec['owasp_top10'] else 'no'}")
    console.print(f"  [bold]Policy file  :[/bold] {sec['security_policy'] or '(none)'}")
    console.print(f"  [bold]CODEOWNERS   :[/bold] {'yes' if sec['codeowners'] else 'no'}")
    console.print(f"  [bold]Custom rules :[/bold] {len(sec['custom_rules'])}")
    console.print(f"  [dim]───────────────────────────────[/dim]")
    console.print()

    if Confirm.ask(f"  [bold {_P}]Save and export now?[/bold {_P}]", default=True):
        cfg["security"] = sec
        save_config(root, cfg)
        console.print()
        from .export import export_all
        paths = export_all(root)
        for p in paths:
            console.print(f"  [bold {_P}]✓[/bold {_P}]  Wrote {p.relative_to(root)}")
    else:
        cfg["security"] = sec
        save_config(root, cfg)
        console.print(f"  [dim]Saved. Run [bold]lore export[/bold] to apply to context files.[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# lore doctor
# ---------------------------------------------------------------------------

@app.command()
def doctor() -> None:
    """Check lore setup — model, store, config, and search mode."""
    from .config import find_memory_root, load_config, memory_dir

    console.print(Panel(_BANNER_TEXT, border_style=_BD, padding=(0, 2), style=f"on {_BG}"))
    console.print()

    ok  = f"[bold {_P}]✓[/bold {_P}]"
    warn = f"[bold {_A}]▲[/bold {_A}]"
    err  = f"[bold red]✗[/bold red]"

    # --- Store ---
    root = find_memory_root()
    if root:
        mdir = memory_dir(root)
        cfg  = load_config(root)
        console.print(f"  {ok}  Store found at [bold]{mdir}[/bold]")
        identity = cfg.get("identity", {})
        ident_name = identity.get("name", "")
        ident_id = identity.get("id", "")
        if ident_name and ident_id:
            console.print(
                f"  {ok}  Identity       : "
                f"[bold {_A}]{ident_name}[/bold {_A}]  [dim]({ident_id})[/dim]"
            )
    else:
        console.print(f"  {err}  No .lore store found.")
        console.print(f"       Run [bold]lore init[/bold] first, then re-run [bold]lore doctor[/bold].")
        console.print(f"\n       [{_AD}]Model and config checks are skipped until the store exists.[/{_AD}]")
        console.print()
        raise SystemExit(1)

    # --- Git ---
    from .extract import _is_git_repo, git_context
    console.print()
    if _is_git_repo(root):
        ctx = git_context(root)
        branch = ctx.get("branch", "unknown")
        author = ctx.get("author")
        remote = ctx.get("remote_name")
        last_sha = ctx.get("last_sha")
        last_msg = ctx.get("last_msg", "")
        repo_label = remote or root.name
        console.print(f"  {ok}  Git repo        : [bold]{repo_label}[/bold]")
        console.print(f"  {ok}  Branch          : [bold]{branch}[/bold]")
        if author:
            console.print(f"  {ok}  Author          : [bold]{author}[/bold]")
        if last_sha:
            short_msg = last_msg[:60] + ("…" if len(last_msg) > 60 else "")
            console.print(f"  {ok}  Last commit     : [dim]{last_sha}[/dim] {short_msg}")
        hook_path = root / ".git" / "hooks" / "post-commit"
        if hook_path.exists() and "# Installed by lore" in hook_path.read_text():
            console.print(f"  {ok}  Post-commit hook: [bold]installed[/bold]")
        else:
            console.print(f"  {warn}  Post-commit hook: [dim]not installed[/dim]  "
                          f"[{_AD}]→ run [bold {_P}]lore hook install[/bold {_P}][/{_AD}]")
    else:
        console.print(f"  {warn}  Git repo        : [bold {_A}]not a git repository[/bold {_A}]")
        console.print(f"       [{_AD}][bold]lore extract[/bold] and [bold]lore hook[/bold] require git.[/{_AD}]")

    # --- Config values ---
    endpoint   = cfg.get("model_endpoint") or "https://huggingface.co"
    ssl_verify = cfg.get("model_ssl_verify", True)
    model_name = cfg.get("embedding_model", "all-MiniLM-L6-v2")
    console.print(f"  {ok}  Embedding model : [bold]{model_name}[/bold]")
    console.print(f"  {ok}  Model endpoint  : [bold]{endpoint}[/bold]")
    console.print(f"       [{_AD}]→ If behind a proxy run:[/{_AD}] "
                  f"[bold {_P}]lore config model_endpoint <url>[/bold {_P}]")
    if not ssl_verify:
        console.print(f"  {warn}  SSL verify      : [bold red]disabled[/bold red]")
    else:
        console.print(f"  {ok}  SSL verify      : enabled")

    # --- Spell counts + instructions nudge ---
    console.print()
    from .store import list_memories
    all_mems = list_memories(root)
    by_cat: dict[str, int] = {}
    for m in all_mems:
        cat = m.get("category", "?")
        by_cat[cat] = by_cat.get(cat, 0) + 1
    total = sum(by_cat.values())
    if total:
        counts = "  ".join(f"[dim]{c}[/dim] {n}" for c, n in sorted(by_cat.items()))
        console.print(f"  {ok}  Spells ({total})    : {counts}")
    else:
        console.print(f"  {warn}  No spells stored yet. Run [bold]lore add[/bold] to capture your first memory.")
    if not by_cat.get("instructions"):
        console.print(
            f"  {warn}  No [bold]instructions[/bold] spells — "
            f"[{_AD}]these become per-tool directives in your AI files.[/{_AD}]\n"
            f"       [{_AD}]→ run [bold {_P}]lore instructions[/bold {_P}] to add one[/{_AD}]"
        )

    # --- Model availability ---
    console.print()
    console.print(f"  [{_A}]Checking model…[/{_A}]", end=" ")
    try:
        import logging, warnings, os, sys
        for n in ("huggingface_hub", "sentence_transformers", "urllib3", "tqdm"):
            logging.getLogger(n).setLevel(logging.CRITICAL)
        warnings.filterwarnings("ignore")
        os.environ.setdefault("TQDM_DISABLE", "1")
        if endpoint:
            os.environ["HF_ENDPOINT"] = endpoint.rstrip("/")
        if not ssl_verify:
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context  # noqa: SLF001
        # Redirect stdout+stderr briefly to swallow the BERT LOAD REPORT
        from io import StringIO
        _old_out, _old_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = StringIO()
        try:
            from sentence_transformers import SentenceTransformer
            SentenceTransformer(model_name)
        finally:
            sys.stdout, sys.stderr = _old_out, _old_err
        console.print(f"[bold {_P}]semantic search active ✓[/bold {_P}]")
        console.print(f"\n  {ok}  [bold]lore is fully operational.[/bold]")
    except Exception as exc:
        console.print(f"[bold {_A}]unavailable[/bold {_A}]")
        console.print(f"  {warn}  Falling back to TF-IDF search (no embeddings).")
        console.print(f"       [{_AD}]Reason: {exc}[/{_AD}]")
        if "No module named 'sentence_transformers'" in str(exc):
            console.print(f"\n       [{_A}]To fix:[/{_A}] install semantic dependencies:")
            console.print( "       [bold]pip install \"lore-book[semantic]\"[/bold]")
            console.print( "       [dim]or run [bold]lore setup semantic[/bold] for guided setup.[/dim]")
        else:
            console.print(f"\n       [{_A}]To fix:[/{_A}] set [bold]model_endpoint[/bold] to an "
                          "accessible HuggingFace mirror,")
            console.print( "       or set [bold]model_ssl_verify false[/bold] if SSL is the only blocker.")
    console.print()


# ---------------------------------------------------------------------------
# lore ui  (Textual TUI)
# ---------------------------------------------------------------------------

@app.command()
def ui() -> None:
    """Open the interactive TUI — browse, add, delete, export in real time."""
    try:
        from .tui import LoreApp
    except ImportError:
        err_console.print(
            "[red]textual is required for the TUI. Run: pip install textual[/red]"
        )
        raise typer.Exit(code=1)

    root = _require_root()
    LoreApp(root).run()


# ---------------------------------------------------------------------------
# lore awaken  (spellbook daemon)
# ---------------------------------------------------------------------------

@app.command()
def awaken(
    background: Annotated[
        bool,
        typer.Option("--background", "-b", help="Run as a detached background daemon"),
    ] = False,
    debounce: Annotated[
        float,
        typer.Option("--debounce", help="Seconds to wait after last change before re-exporting"),
    ] = 1.5,
) -> None:
    """Awaken the spellbook — watch .lore and auto-export AI context on every change."""
    import os
    import threading
    import time
    from datetime import datetime, timezone
    from rich.live import Live
    from .daemon import run_spellbook, SpellbookState, SpellbookStatus, daemonize, pid_file

    root = _require_root()
    pf = pid_file(root)

    # Guard: refuse if a daemon is already awake.
    if pf.exists():
        try:
            existing_pid = int(pf.read_text().strip())
            os.kill(existing_pid, 0)
            console.print(
                f"[yellow]The spellbook is already awake (PID {existing_pid}).[/yellow]\n"
                f"[dim]Run [bold]lore slumber[/bold] to put it to sleep first.[/dim]"
            )
            raise typer.Exit()
        except (ProcessLookupError, ValueError):
            pf.unlink(missing_ok=True)

    # ── Background mode ──────────────────────────────────────────────────────
    if background:
        if not hasattr(os, "fork"):
            err_console.print("[red]Background mode requires POSIX (macOS / Linux).[/red]")
            raise typer.Exit(code=1)
        daemonize(root, debounce=debounce)
        console.print(
            f"\n  [bold {_P}]✓[/bold {_P}]  The spellbook stirs in the shadows.\n"
            f"  [dim]Run [bold]lore slumber[/bold] to put it to rest.[/dim]\n"
        )
        return

    # ── Foreground mode — Rich Live display ──────────────────────────────────
    _STATUS_ICON = {
        SpellbookStatus.IDLE: "💤",
        SpellbookStatus.WATCHING: "👁 ",
        SpellbookStatus.CASTING: "✨",
    }
    _STATUS_COLOR = {
        SpellbookStatus.IDLE: _PD,
        SpellbookStatus.WATCHING: _P,
        SpellbookStatus.CASTING: _A,
    }

    state_ref: list[SpellbookState] = [SpellbookState()]

    def _on_state_change(s: SpellbookState) -> None:
        state_ref[0] = s

    def _make_panel(s: SpellbookState) -> Panel:
        icon = _STATUS_ICON[s.status]
        color = _STATUS_COLOR[s.status]
        last = s.last_cast.strftime("%H:%M:%S") if s.last_cast else "—"
        uptime = str(datetime.now(timezone.utc) - s.started_at).split(".")[0]
        lines = [
            f"  [bold {color}]{icon}  {s.status.value.upper()}[/bold {color}]",
            "",
            f"  [dim]Watching :[/dim]  [bold]{root / '.lore'}[/bold]",
            f"  [dim]Last cast:[/dim]  [bold]{last}[/bold]   [dim]({s.cast_count} total)[/dim]",
            f"  [dim]Uptime   :[/dim]  {uptime}",
        ]
        if s.last_scroll:
            lines.append(f"  [dim]Changed  :[/dim]  {s.last_scroll}")
        if s.errors:
            lines += ["", f"  [bold red]Errors:[/bold red]"]
            for e in s.errors[-3:]:
                lines.append(f"  [red]· {e}[/red]")
        lines += ["", f"  [dim]Ctrl+C to banish[/dim]"]
        return Panel(
            "\n".join(lines),
            title=f"[bold {_A}]📜  Spellbook[/bold {_A}]",
            border_style=_BD,
            style=f"on {_BG}",
        )

    stop_event = threading.Event()
    daemon_thread = threading.Thread(
        target=run_spellbook,
        args=(root, debounce),
        kwargs={"on_state_change": _on_state_change, "stop_event": stop_event},
        daemon=True,
    )
    daemon_thread.start()

    try:
        with Live(_make_panel(state_ref[0]), console=console, refresh_per_second=4) as live:
            while daemon_thread.is_alive():
                live.update(_make_panel(state_ref[0]))
                time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        daemon_thread.join(timeout=3)
        console.print(f"\n  [dim]The spellbook has been banished. Farewell.[/dim]\n")


# ---------------------------------------------------------------------------
# lore slumber  (stop background daemon)
# ---------------------------------------------------------------------------

@app.command()
def slumber() -> None:
    """Banish the background spellbook daemon."""
    import os
    import signal as _signal
    from .daemon import pid_file

    root = _require_root()
    pf = pid_file(root)

    if not pf.exists():
        console.print("[yellow]No spellbook is currently awake.[/yellow]")
        raise typer.Exit()

    try:
        pid = int(pf.read_text().strip())
        os.kill(pid, _signal.SIGTERM)
        pf.unlink(missing_ok=True)
        console.print(
            f"\n  [bold {_P}]✓[/bold {_P}]  The spellbook drifts into slumber. (PID {pid})\n"
        )
    except (ValueError, ProcessLookupError):
        pf.unlink(missing_ok=True)
        console.print("[yellow]Spellbook was not running. Cleaned up stale PID file.[/yellow]")
    except PermissionError:
        err_console.print("[red]Permission denied — cannot stop the daemon.[/red]")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# lore relic capture
# ---------------------------------------------------------------------------

@relic_app.command("capture")
def relic_capture(
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Read content from a file"),
    ] = None,
    git_diff: Annotated[
        bool,
        typer.Option("--git-diff", help="Capture working-tree + staged diff"),
    ] = False,
    git_log: Annotated[
        Optional[int],
        typer.Option("--git-log", help="Capture the last N commits (messages + diffs)"),
    ] = None,
    clipboard: Annotated[
        bool,
        typer.Option("--clipboard", "-c", help="Read from the system clipboard"),
    ] = False,
    stdin: Annotated[
        bool,
        typer.Option("--stdin", help="Read from stdin (e.g. cat notes.txt | lore relic capture --stdin)"),
    ] = False,
    title: Annotated[
        Optional[str],
        typer.Option("--title", "-t", help="Relic title (skips the prompt)"),
    ] = None,
    tags: Annotated[
        Optional[str],
        typer.Option("--tags", help="Comma-separated tags"),
    ] = None,
) -> None:
    """Capture a session, notes, or diff as a relic in the spellbook."""
    import subprocess
    import sys as _sys
    from rich.prompt import Prompt, Confirm
    from rich.rule import Rule as _Rule
    from .relics import save_relic

    root = _require_root()

    auto_sources = sum([bool(file), git_diff, bool(git_log is not None), clipboard, stdin])
    if auto_sources > 1:
        err_console.print("[red]Specify only one of: --file, --git-diff, --git-log, --clipboard, --stdin[/red]")
        raise typer.Exit(code=1)

    content = ""
    source_label = "manual"

    if stdin:
        content = _sys.stdin.read()
        source_label = "stdin"

    elif file:
        if not file.exists():
            err_console.print(f"[red]File not found: {file}[/red]")
            raise typer.Exit(code=1)
        content = file.read_text(encoding="utf-8", errors="replace")
        source_label = str(file)

    elif clipboard:
        clipboard_cmds = [
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-Clipboard -Raw"],
            ["pwsh", "-NoProfile", "-NonInteractive", "-Command", "Get-Clipboard -Raw"],
            ["pbpaste"],
            ["xclip", "-selection", "clipboard", "-o"],
        ]
        for cmd in clipboard_cmds:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True)
            except FileNotFoundError:
                continue
            if r.returncode == 0:
                content = r.stdout
                source_label = "clipboard"
                break
        else:
            err_console.print(
                "[red]Clipboard tool not found. Use PowerShell Get-Clipboard (Windows), "
                "pbpaste (macOS), or xclip (Linux).[/red]"
            )
            raise typer.Exit(code=1)

    elif git_diff:
        try:
            for _args in (["git", "diff"], ["git", "diff", "--cached"]):
                r = subprocess.run(_args, capture_output=True, text=True, cwd=root)
                if r.stdout.strip():
                    content = (content + "\n" + r.stdout).strip()
            if not content:
                err_console.print("[yellow]No unstaged or staged changes found.[/yellow]")
                raise typer.Exit()
            source_label = "git-diff"
        except FileNotFoundError:
            err_console.print("[red]git not found in PATH.[/red]")
            raise typer.Exit(code=1)

    elif git_log is not None:
        try:
            n = max(1, git_log)
            r1 = subprocess.run(
                ["git", "log", f"-{n}", "--stat", "--oneline"],
                capture_output=True, text=True, cwd=root,
            )
            r2 = subprocess.run(
                ["git", "log", f"-{n}", "-p", "--no-merges"],
                capture_output=True, text=True, cwd=root,
            )
            content = (r1.stdout.strip() + "\n\n" + r2.stdout.strip()).strip()
            if not content:
                err_console.print("[yellow]No commits found.[/yellow]")
                raise typer.Exit()
            source_label = f"git-log-{n}"
        except FileNotFoundError:
            err_console.print("[red]git not found in PATH.[/red]")
            raise typer.Exit(code=1)

    non_interactive = bool(auto_sources)

    console.print()
    console.print(Panel(
        f"[bold {_A}]🏺  Relic Capture[/bold {_A}]\n"
        f"[dim]Preserve a session, doc, or diff — then distill it into spells.[/dim]",
        border_style=_BD, padding=(0, 2), style=f"on {_BG}",
    ))
    console.print()

    if not non_interactive:
        console.print(f"  [bold]Content[/bold]  [dim]— paste notes, a doc excerpt, or anything worth keeping.[/dim]")
        console.print(f"  [dim]Enter [bold].[/bold] on its own line when done.  Ctrl-C to abort.[/dim]")
        console.print()
        lines_in: list[str] = []
        try:
            while True:
                try:
                    line = console.input(f"  [{_PD}]>[/{_PD}] ")
                except EOFError:
                    break
                if line.strip() == ".":
                    break
                lines_in.append(line)
        except KeyboardInterrupt:
            console.print("\n  [dim]Aborted.[/dim]\n")
            raise typer.Exit()
        content = "\n".join(lines_in).strip()
        if not content:
            console.print("[yellow]No content entered. Relic not saved.[/yellow]")
            raise typer.Exit()
    else:
        console.print(f"  [dim]Source:[/dim] {source_label}  [dim]({len(content):,} chars)[/dim]")
        console.print()

    # ── Title ─────────────────────────────────────────────────────────────────
    if title is None:
        default_title = ""
        if git_log is not None:
            default_title = f"git session — last {git_log} commits"
        elif git_diff:
            default_title = "git diff"
        elif file:
            default_title = file.stem.replace("_", " ").replace("-", " ")
        console.print()
        title = Prompt.ask(f"  [bold {_P}]Title[/bold {_P}]", default=default_title or "")
        while not title.strip():
            console.print(f"  [bold red]A relic must have a title.[/bold red]")
            title = Prompt.ask(f"  [bold {_P}]Title[/bold {_P}]")

    # ── Tags ──────────────────────────────────────────────────────────────────
    tag_list: list[str] = []
    if tags is not None:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    elif not non_interactive:
        tags_raw = Prompt.ask(
            f"  [bold {_P}]Tags[/bold {_P}] [dim](comma-separated, optional)[/dim]", default=""
        )
        tag_list = [t.strip() for t in tags_raw.split(",") if t.strip()]

    console.print()
    console.print(_Rule(f"  [bold {_A}]Preview[/bold {_A}]  ", style=_BD))
    console.print(f"  [bold]Title  :[/bold] {title}")
    console.print(f"  [bold]Tags   :[/bold] {', '.join(tag_list) or '(none)'}")
    console.print(f"  [bold]Content:[/bold] {len(content):,} chars")
    console.print()

    if not non_interactive:
        if not Confirm.ask(f"  [bold {_P}]Seal this relic?[/bold {_P}]", default=True):
            console.print("\n  [dim]The relic fades. Nothing was saved.[/dim]\n")
            raise typer.Exit()

    relic = save_relic(root, title.strip(), content, tags=tag_list, source=source_label)
    console.print(f"\n  [bold {_P}]✓[/bold {_P}]  Relic [bold]{relic['id']}[/bold] — [bold]{title}[/bold]")

    console.print()
    if not non_interactive:
        if Confirm.ask(f"  [bold {_P}]Distill spells from this relic now?[/bold {_P}]", default=False):
            _relic_distill_impl(root, relic["id"])
            return
    console.print(f"  [dim]Run [bold]lore relic distill {relic['id']}[/bold] to extract spells.[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# lore relic list
# ---------------------------------------------------------------------------

@relic_app.command("list")
def relic_list() -> None:
    """List all captured relics."""
    from .relics import list_relics

    root = _require_root()
    relics = list_relics(root)
    if not relics:
        console.print(
            "[yellow]No relics found. Run [bold]lore relic capture[/bold] to preserve your first artifact.[/yellow]"
        )
        return

    table = Table(show_header=True, header_style=f"bold {_A}", expand=True, box=box.SIMPLE)
    table.add_column("ID",      style="dim",        width=10, no_wrap=True)
    table.add_column("Title",   style=f"bold {_P}", min_width=20, overflow="fold")
    table.add_column("Preview", min_width=40,        overflow="fold")
    table.add_column("Tags",    width=16,            no_wrap=True)
    table.add_column("✦",       width=4,             no_wrap=True)
    table.add_column("Date",    width=10,            no_wrap=True)

    for r in relics:
        linked = r.get("linked_memories", [])
        preview = (
            r.get("summary", "").strip()
            or r.get("content", "").replace("\n", " ")[:80]
        )
        spell_count = len(linked)
        table.add_row(
            r.get("id", ""),
            r.get("title", ""),
            f"[dim]{preview}[/dim]" if preview else "[dim]—[/dim]",
            ", ".join(r.get("tags", [])) or "[dim]—[/dim]",
            f"[bold green]{spell_count}[/bold green]" if spell_count else "[dim]—[/dim]",
            r.get("created_at", "")[:10],
        )

    console.print()
    console.print(table)
    console.print(
        f"  [dim]{len(relics)} relic(s).  "
        f"Run [bold]lore relic distill <id>[/bold] to extract spells.[/dim]\n"
    )


# ---------------------------------------------------------------------------
# lore relic distill  (internal impl + public command)
# ---------------------------------------------------------------------------

def _relic_distill_impl(root: Path, relic_id: str) -> None:
    """Shared distill logic used by both `relic distill` and the post-capture prompt."""
    from rich.prompt import Prompt
    from rich.rule import Rule as _Rule
    from .relics import get_relic, link_memory_to_relic
    from .store import add_memory
    from .search import index_memory
    from .config import load_config

    relic = get_relic(root, relic_id)
    if not relic:
        err_console.print(f"[red]Relic '{relic_id}' not found.[/red]")
        return

    console.print()
    console.print(Panel(
        f"[bold {_A}]🏺  Distilling — {relic['title']}[/bold {_A}]\n"
        f"[dim]ID: {relic['id']}[/dim]",
        border_style=_BD, padding=(0, 2), style=f"on {_BG}",
    ))
    console.print()

    # Show a content preview so the user has the context in front of them.
    preview = relic["content"][:600]
    if len(relic["content"]) > 600:
        preview += f"\n[dim]… ({len(relic['content']) - 600} more chars — run [bold]lore relic view {relic_id}[/bold] for full text)[/dim]"
    console.print(f"[dim]{preview}[/dim]")
    console.print()
    console.print(_Rule(f"  [bold {_A}]Extract Spells[/bold {_A}]  ", style=_BD))
    console.print(f"  [dim]Type each memory you want to keep. Enter [bold].[/bold] or blank line to finish.[/dim]")
    console.print()

    cfg = load_config(root)
    valid_cats = cfg.get("categories", ["decisions", "facts", "preferences", "summaries"])
    cats_display = "  ".join(f"[bold]{c}[/bold]" if i == 0 else f"[dim]{c}[/dim]"
                             for i, c in enumerate(valid_cats))
    console.print(f"  [dim]Tomes available:[/dim]  {cats_display}\n")

    saved = 0
    spell_num = 1
    default_cat = valid_cats[0] if valid_cats else "facts"
    while True:
        console.print(f"  [dim]─── Spell #{spell_num} ───────────────────────────────────────────[/dim]")
        mem_content = Prompt.ask(
            f"  [bold {_P}]✦ Inscription[/bold {_P}]  [dim]the wisdom to enshrine  (. to seal the book)[/dim]",
            default="",
        )
        if not mem_content.strip() or mem_content.strip() == ".":
            break
        cat = Prompt.ask(
            f"  [bold {_P}]✦ Tome[/bold {_P}]         [dim]which grimoire?[/dim]",
            default=default_cat,
        )
        default_cat = cat  # sticky for next iteration

        with console.status(
            f"  [dim]Inscribing spell #{spell_num} into the {cat} tome…[/dim]",
            spinner="dots",
        ):
            entry = add_memory(root, cat, mem_content.strip(), tags=[], source=f"relic:{relic_id}")
            index_memory(root, entry["id"], mem_content.strip())
            link_memory_to_relic(root, relic_id, entry["id"])

        console.print(f"  [bold {_P}]✓[/bold {_P}]  Spell [bold]{entry['id']}[/bold] sealed into [bold]{cat}[/bold].\n")
        saved += 1
        spell_num += 1

    console.print()
    if saved:
        console.print(
            f"  [bold {_P}]✓[/bold {_P}]  {saved} spell(s) distilled from [bold]{relic['title']}[/bold]."
        )
    else:
        console.print(f"  [dim]No spells extracted. The relic remains sealed.[/dim]")
    console.print()


@relic_app.command("distill")
def relic_distill(
    relic_id: Annotated[str, typer.Argument(help="Relic ID to distill memories from")],
) -> None:
    """Distill a relic into spellbook memories — you choose what to keep."""
    root = _require_root()
    _relic_distill_impl(root, relic_id)


# ---------------------------------------------------------------------------
# lore relic view
# ---------------------------------------------------------------------------

@relic_app.command("view")
def relic_view(
    relic_id: Annotated[str, typer.Argument(help="Relic ID to view")],
) -> None:
    """View the full content of a relic."""
    from rich.markdown import Markdown
    from .relics import get_relic

    root = _require_root()
    relic = get_relic(root, relic_id)
    if not relic:
        err_console.print(f"[red]Relic '{relic_id}' not found.[/red]")
        raise typer.Exit(code=1)

    linked = relic.get("linked_memories", [])
    summary_line = f"\n\n[italic]{relic['summary']}[/italic]" if relic.get("summary") else ""
    console.print()
    console.print(Panel(
        f"[bold {_A}]{relic['title']}[/bold {_A}]\n"
        f"[dim]ID: {relic['id']}  ·  {relic['created_at'][:10]}  ·  "
        f"Tags: {', '.join(relic.get('tags', [])) or 'none'}  ·  "
        f"Spells: {len(linked)}[/dim]"
        + summary_line,
        border_style=_BD, style=f"on {_BG}",
    ))
    console.print()
    console.print(Markdown(relic["content"]))
    if linked:
        console.print()
        console.print(f"  [dim]Linked spells:[/dim] {', '.join(linked)}")
    console.print()


# ---------------------------------------------------------------------------
# lore relic remove
# ---------------------------------------------------------------------------

@relic_app.command("remove")
def relic_remove(
    relic_id: Annotated[str, typer.Argument(help="Relic ID to delete")],
) -> None:
    """Permanently delete a relic from the spellbook."""
    from rich.prompt import Confirm
    from .relics import remove_relic, get_relic

    root = _require_root()
    relic = get_relic(root, relic_id)
    if not relic:
        err_console.print(f"[red]Relic '{relic_id}' not found.[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n  [bold]Title:[/bold] {relic['title']}")
    console.print(f"  [bold]Spells linked:[/bold] {len(relic.get('linked_memories', []))}")
    console.print()
    if not Confirm.ask(f"  [bold red]Permanently destroy this relic?[/bold red]", default=False):
        console.print("  [dim]Reprieved. Nothing was deleted.[/dim]\n")
        raise typer.Exit()

    remove_relic(root, relic_id)
    console.print(f"\n  [bold {_P}]✓[/bold {_P}]  Relic [bold]{relic_id}[/bold] has been destroyed.\n")
