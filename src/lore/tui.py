"""Textual TUI for lore — retro terminal memory browser."""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import time
import threading

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Input, Label, Static

from rich.markup import escape as _escape
from .store import add_memory, list_memories, remove_memory, update_memory

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

_PHOSPHOR   = "#39ff14"   # main phosphor green
_PHOSPHOR_D = "#1a7a0a"   # dim
_PHOSPHOR_M = "#0d4407"   # very dim / muted
_PHOSPHOR_H = "#66ff44"   # bright highlight
_AMBER      = "#ffaa00"   # accent
_AMBER_D    = "#996600"   # dim amber
_BG         = "#080c08"   # near-black terminal background
_SURFACE    = "#0d120d"   # slightly lighter surface
_PANEL      = "#080f08"   # sidebar bg
_BORDER     = "#1a6606"   # border lines
_RED        = "#cc2222"   # error / delete

# ---------------------------------------------------------------------------
# Sigil banner (Rich markup)
# ---------------------------------------------------------------------------

_BANNER = f"[bold {_AMBER}]◈   L · O · R · E   ◈   AI  PROJECT  MEMORY[/bold {_AMBER}]"

# ---------------------------------------------------------------------------
# Category glyphs — no emoji, old-terminal safe
# ---------------------------------------------------------------------------

_GLYPHS: dict[str, str] = {
    "decisions":   "⚖",
    "facts":       "▸",
    "preferences": "★",
    "summaries":   "◆",
}


def _glyph(cat: str) -> str:
    return _GLYPHS.get(cat, "◉")


# ---------------------------------------------------------------------------
# Shared modal button CSS fragment
# ---------------------------------------------------------------------------

_MODAL_BTN = f"""
    Button {{ margin-left: 1; border: solid {_BORDER}; }}
    #cancel {{ background: {_BG}; color: {_PHOSPHOR_D}; }}
    #cancel:hover {{ background: {_BORDER}; color: {_PHOSPHOR}; }}
"""


# ---------------------------------------------------------------------------
# Detail-view modal  (Enter on a row)
# ---------------------------------------------------------------------------

class DetailScreen(ModalScreen):
    """Full read-only detail view for a memory entry."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("enter",  "dismiss", "Close", show=False),
        Binding("space",  "dismiss", "Close", show=False),
    ]

    CSS = f"""
    DetailScreen {{ align: center middle; }}
    #dialog {{
        width: 80; height: auto;
        border: solid {_BORDER}; background: {_BG}; padding: 1 2;
    }}
    #dialog-title {{
        color: {_AMBER}; text-style: bold; text-align: center;
        width: 1fr; margin-bottom: 1;
    }}
    #content-box {{
        background: {_SURFACE}; color: {_PHOSPHOR_H};
        border: solid {_BORDER}; padding: 0 1; margin: 1 0;
        height: auto;
    }}
    .meta-row {{ height: 1; margin-bottom: 0; }}
    .meta-key {{ color: {_AMBER_D}; width: 12; }}
    .meta-val {{ color: {_PHOSPHOR}; }}
    #hint {{ color: {_PHOSPHOR_M}; text-align: center; margin-top: 1; }}
    """

    def __init__(self, memory: dict) -> None:
        super().__init__()
        self._memory = memory

    def compose(self) -> ComposeResult:
        m = self._memory
        with Vertical(id="dialog"):
            yield Label(f"◈  {m.get('id', '')}  ◈", id="dialog-title", markup=False)
            yield Static(_escape(m.get("content", "")), id="content-box")
            with Horizontal(classes="meta-row"):
                yield Label("CATEGORY", classes="meta-key")
                yield Label(m.get("category", ""), classes="meta-val", markup=False)
            with Horizontal(classes="meta-row"):
                yield Label("TAGS", classes="meta-key")
                yield Label(", ".join(m.get("tags", [])) or "—", classes="meta-val", markup=False)
            with Horizontal(classes="meta-row"):
                yield Label("BRANCH", classes="meta-key")
                yield Label(m.get("git_branch", "—"), classes="meta-val", markup=False)
            with Horizontal(classes="meta-row"):
                yield Label("AUTHOR", classes="meta-key")
                yield Label(m.get("git_author", "—"), classes="meta-val", markup=False)
            with Horizontal(classes="meta-row"):
                yield Label("SOURCE", classes="meta-key")
                yield Label(m.get("source", "manual"), classes="meta-val", markup=False)
            with Horizontal(classes="meta-row"):
                yield Label("CREATED", classes="meta-key")
                yield Label(m.get("created_at", "")[:19], classes="meta-val", markup=False)
            yield Label("[ ENTER · SPACE · ESC to close ]", id="hint", markup=False)


# ---------------------------------------------------------------------------
# Edit-memory modal  (u key)
# ---------------------------------------------------------------------------

class EditMemoryScreen(ModalScreen):
    """Edit an existing memory entry in-place."""

    # Empty bindings so no app-level or sibling-modal bindings (e.g. space)
    # leak through and steal keystrokes from focused Input widgets.
    BINDINGS: ClassVar[list[Binding]] = []

    _CAT     = "#edit-cat"
    _CONTENT = "#edit-content"
    _TAGS    = "#edit-tags"

    CSS = f"""
    EditMemoryScreen {{ align: center middle; }}
    #dialog {{
        width: 72; height: auto;
        border: solid {_AMBER}; background: {_BG}; padding: 1 2;
    }}
    #dialog-title {{
        color: {_AMBER}; text-style: bold; text-align: center;
        width: 1fr; margin-bottom: 1;
    }}
    .field-label {{ color: {_PHOSPHOR_D}; height: 1; }}
    .field-input {{
        background: {_SURFACE}; color: {_PHOSPHOR};
        border: solid {_BORDER}; margin-bottom: 1;
    }}
    .field-input:focus {{ border: solid {_AMBER}; color: {_PHOSPHOR_H}; }}
    #btn-row {{ height: auto; align: right middle; margin-top: 1; }}
    {_MODAL_BTN}
    #save {{
        background: {_BORDER}; color: {_PHOSPHOR};
        border: solid {_AMBER}; text-style: bold;
    }}
    #save:hover {{ background: {_AMBER}; color: {_BG}; }}
    """

    def __init__(self, memory: dict) -> None:
        super().__init__()
        self._memory = memory

    def compose(self) -> ComposeResult:
        m = self._memory
        with Vertical(id="dialog"):
            yield Label(f"◈  EDIT  {m.get('id', '')}  ◈", id="dialog-title", markup=False)
            yield Label("CATEGORY", classes="field-label")
            yield Input(value=m.get("category", ""), id="edit-cat", classes="field-input")
            yield Label("CONTENT", classes="field-label")
            yield Input(value=m.get("content", ""), id="edit-content", classes="field-input")
            yield Label("TAGS  (comma-separated)", classes="field-label")
            yield Input(value=", ".join(m.get("tags", [])), id="edit-tags", classes="field-input")
            with Horizontal(id="btn-row"):
                yield Button("[[ CANCEL ]]", id="cancel")
                yield Button("[[ SAVE  ]]", id="save")

    def on_mount(self) -> None:
        # call_after_refresh ensures focus sticks after Textual's internal
        # focus management runs — plain .focus() in on_mount can be overwritten
        # in Textual 8.x before the first render cycle completes.
        self.call_after_refresh(self.query_one(self._CONTENT, Input).focus)

    def on_key(self, event) -> None:
        """Explicitly route space into the focused Input.

        Textual 8.x routes keys through all screens in the stack, so the
        underlying DataTable's space binding can intercept before the Input
        widget sees the character.  This handler catches any space that
        bubbled past the Input and inserts it directly.
        """
        if event.key == "space" and isinstance(self.focused, Input):
            inp = self.focused
            pos = inp.cursor_position
            inp.value = inp.value[:pos] + " " + inp.value[pos:]
            inp.cursor_position = pos + 1
            event.prevent_default()
            event.stop()

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#save")
    def save(self) -> None:
        cat     = self.query_one(self._CAT,     Input).value.strip() or "facts"
        content = self.query_one(self._CONTENT, Input).value.strip()
        tags_raw = self.query_one(self._TAGS,   Input).value.strip()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        if not content:
            self.query_one(self._CONTENT, Input).focus()
            return
        self.dismiss({
            "id":       self._memory["id"],
            "category": cat,
            "content":  content,
            "tags":     tags,
        })

    @on(Input.Submitted)
    def on_submit(self, event: Input.Submitted) -> None:
        if event.input.id == "edit-cat":
            self.query_one(self._CONTENT, Input).focus()
        elif event.input.id == "edit-content":
            self.query_one(self._TAGS, Input).focus()
        else:
            self.save()


# ---------------------------------------------------------------------------
# Add-memory modal
# ---------------------------------------------------------------------------

class AddMemoryScreen(ModalScreen):
    """Modal dialog to add a new memory."""

    BINDINGS: ClassVar[list[Binding]] = []

    def on_key(self, event) -> None:
        """Explicitly route space into the focused Input (Textual 8.x workaround)."""
        if event.key == "space" and isinstance(self.focused, Input):
            inp = self.focused
            pos = inp.cursor_position
            inp.value = inp.value[:pos] + " " + inp.value[pos:]
            inp.cursor_position = pos + 1
            event.prevent_default()
            event.stop()

    _CAT     = "#cat-input"
    _CONTENT = "#content-input"
    _TAGS    = "#tags-input"

    CSS = f"""
    AddMemoryScreen {{ align: center middle; }}
    #dialog {{
        width: 72; height: auto;
        border: solid {_BORDER}; background: {_BG}; padding: 1 2;
    }}
    #dialog-title {{
        color: {_AMBER}; text-style: bold; text-align: center;
        width: 1fr; margin-bottom: 1;
    }}
    .field-label {{ color: {_PHOSPHOR_D}; height: 1; }}
    .field-input {{
        background: {_SURFACE}; color: {_PHOSPHOR};
        border: solid {_BORDER}; margin-bottom: 1;
    }}
    .field-input:focus {{ border: solid {_AMBER}; color: {_PHOSPHOR_H}; }}
    #btn-row {{ height: auto; align: right middle; margin-top: 1; }}
    {_MODAL_BTN}
    #save {{
        background: {_BORDER}; color: {_PHOSPHOR};
        border: solid {_PHOSPHOR}; text-style: bold;
    }}
    #save:hover {{ background: {_PHOSPHOR}; color: {_BG}; }}
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("◈  ADD MEMORY  ◈", id="dialog-title", markup=False)
            yield Label("CATEGORY", classes="field-label")
            yield Input(placeholder="decisions / facts / preferences / summaries",
                        id="cat-input", classes="field-input")
            yield Label("CONTENT", classes="field-label")
            yield Input(placeholder="What should lore remember?",
                        id="content-input", classes="field-input")
            yield Label("TAGS  (comma-separated, optional)", classes="field-label")
            yield Input(placeholder="api, architecture",
                        id="tags-input", classes="field-input")
            with Horizontal(id="btn-row"):
                yield Button("[[ CANCEL ]]", id="cancel")
                yield Button("[[ SAVE  ]]", id="save")

    def on_mount(self) -> None:
        self.call_after_refresh(self.query_one(self._CAT, Input).focus)

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#save")
    def save(self) -> None:
        cat = self.query_one(self._CAT, Input).value.strip() or "facts"
        content = self.query_one(self._CONTENT, Input).value.strip()
        tags_raw = self.query_one(self._TAGS, Input).value.strip()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        if not content:
            self.query_one(self._CONTENT, Input).focus()
            return
        self.dismiss({"category": cat, "content": content, "tags": tags})

    @on(Input.Submitted)
    def on_submit(self, event: Input.Submitted) -> None:
        if event.input.id == "cat-input":
            self.query_one(self._CONTENT, Input).focus()
        elif event.input.id == "content-input":
            self.query_one(self._TAGS, Input).focus()
        else:
            self.save()


# ---------------------------------------------------------------------------
# Confirm-delete modal
# ---------------------------------------------------------------------------

class ConfirmDeleteScreen(ModalScreen):
    """Confirm before deleting a memory."""

    CSS = f"""
    ConfirmDeleteScreen {{ align: center middle; }}
    #dialog {{
        width: 56; height: auto;
        border: solid {_RED}; background: {_BG}; padding: 1 2;
    }}
    #dialog-title {{
        color: {_RED}; text-style: bold; text-align: center;
        width: 1fr; margin-bottom: 1;
    }}
    #preview {{ color: {_PHOSPHOR_D}; margin-bottom: 1; width: 1fr; }}
    #btn-row {{ height: auto; align: right middle; margin-top: 1; }}
    {_MODAL_BTN}
    #confirm {{
        background: #2a0000; color: {_RED};
        border: solid {_RED}; text-style: bold;
    }}
    #confirm:hover {{ background: {_RED}; color: {_BG}; }}
    """

    def __init__(self, content: str) -> None:
        super().__init__()
        self._content = content

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("◈  DELETE MEMORY?  ◈", id="dialog-title", markup=False)
            preview = self._content[:68] + ("…" if len(self._content) > 68 else "")
            yield Label(preview, id="preview", markup=False)
            with Horizontal(id="btn-row"):
                yield Button("[[ CANCEL ]]", id="cancel")
                yield Button("[[ DELETE ]]", id="confirm")

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#confirm")
    def confirm(self) -> None:
        self.dismiss(True)


# ---------------------------------------------------------------------------
# Stats sidebar widget
# ---------------------------------------------------------------------------

class StatsPanel(Static):
    """Shows memory counts per category."""

    def update_stats(self, memories: list[dict]) -> None:
        by_cat: dict[str, int] = {}
        for m in memories:
            cat = m.get("category", "?")
            by_cat[cat] = by_cat.get(cat, 0) + 1

        lines: list[str] = [
            f"[bold {_AMBER}]CATEGORIES[/bold {_AMBER}]",
            f"[{_BORDER}]───────────────[/{_BORDER}]",
        ]
        for cat in sorted(by_cat):
            g = _glyph(cat)
            n = by_cat[cat]
            lines.append(
                f"[{_AMBER}]{g}[/{_AMBER}] [{_PHOSPHOR}]{cat:<10}[/{_PHOSPHOR}]"
                f" [bold {_PHOSPHOR_H}]{n}[/bold {_PHOSPHOR_H}]"
            )
        if not by_cat:
            lines.append(f"[{_PHOSPHOR_M}]no memories yet[/{_PHOSPHOR_M}]")
        lines += [
            "",
            f"[{_BORDER}]───────────────[/{_BORDER}]",
            f"[{_AMBER_D}]TOTAL[/{_AMBER_D}]  [bold {_PHOSPHOR}]{len(memories)}[/bold {_PHOSPHOR}]",
        ]
        self.update("\n".join(lines))


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

class LoreApp(App):
    """Lore — retro terminal memory browser."""

    ENABLE_COMMAND_PALETTE = False

    _TABLE  = "#memory-table"
    _SEARCH = "#search-input"
    _STATUS = "#status-bar"

    CSS = f"""
    Screen {{
        background: {_BG}; color: {_PHOSPHOR}; layout: vertical;
    }}
    #banner {{
        height: 3; background: {_BG}; color: {_AMBER}; text-style: bold;
        border: solid {_BORDER};
        content-align: center middle; text-align: center;
    }}
    #main {{ height: 1fr; layout: horizontal; }}
    #sidebar {{
        width: 22; background: {_PANEL};
        border-right: solid {_BORDER}; padding: 1;
    }}
    StatsPanel {{ height: auto; }}
    DataTable {{
        background: {_BG}; color: {_PHOSPHOR}; border: none; height: 1fr;
        scrollbar-background: {_SURFACE}; scrollbar-color: {_BORDER};
        scrollbar-color-hover: {_AMBER}; scrollbar-corner-color: {_BG};
    }}
    DataTable > .datatable--header {{
        background: {_SURFACE}; color: {_AMBER}; text-style: bold;
    }}
    DataTable > .datatable--header-cursor {{
        background: {_SURFACE}; color: {_AMBER};
    }}
    DataTable > .datatable--cursor {{
        background: {_AMBER}; color: {_BG}; text-style: bold;
    }}
    DataTable > .datatable--odd-row {{ background: {_SURFACE}; }}
    DataTable > .datatable--even-row {{ background: {_BG}; }}
    #searchbar {{
        height: 3; background: {_SURFACE}; border-top: solid {_BORDER};
        padding: 0 1; align: left middle;
    }}
    #search-prompt {{ width: auto; color: {_AMBER}; padding: 0 1; }}
    #search-input {{
        background: {_BG}; color: {_PHOSPHOR};
        border: none;
        width: 1fr; height: 1;
    }}
    #search-input:focus {{
        background: {_SURFACE}; color: {_PHOSPHOR_H};
        border: none;
    }}
    #status-bar {{
        height: 1; background: {_SURFACE}; border-top: solid {_BORDER};
        color: {_PHOSPHOR_D}; padding: 0 1;
    }}
    Footer {{ background: {_PANEL}; color: {_PHOSPHOR_M}; }}
    Footer > .footer--key {{
        background: {_BORDER}; color: {_PHOSPHOR_H}; text-style: bold;
    }}
    Footer > .footer--description {{ color: {_PHOSPHOR_D}; }}
    Footer > .footer--highlight-key {{
        background: {_AMBER}; color: {_BG}; text-style: bold;
    }}
    Footer > .footer--highlight {{ color: {_AMBER}; }}
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("a",      "add_memory",    "Add"),
        Binding("u",      "edit_memory",   "Edit"),
        Binding("d",      "delete_memory", "Delete"),
        Binding("e",      "export_all",    "Export"),
        Binding("r",      "refresh",       "Refresh"),
        Binding("/",      "focus_search",  "Search"),
        Binding("escape", "clear_search",  "Clear", show=False),
        Binding("q",      "quit",          "Quit"),
    ]

    _query: reactive[str] = reactive("")
    _all_memories: list[dict] = []
    _load_gen: int = 0

    def __init__(self, root: Path) -> None:
        super().__init__()
        self._root = root

    def compose(self) -> ComposeResult:
        yield Static(_BANNER, id="banner")
        with Horizontal(id="main"):
            with Vertical(id="sidebar"):
                yield StatsPanel(id="stats")
            yield DataTable(id="memory-table", cursor_type="row", zebra_stripes=True)
        with Horizontal(id="searchbar"):
            yield Static("▸ SEARCH", id="search-prompt")
            yield Input(placeholder="filter memories…", id="search-input")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(self._TABLE, DataTable)
        table.add_columns("ID", "CATEGORY", "CONTENT", "TAGS", "SOURCE")
        self.load_memories()
        self._start_watcher()

    def _start_watcher(self) -> None:
        """Watch .lore/ for changes and reload on any YAML write."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            app = self
            store_path = str(self._root / ".lore")
            _debounce: list[threading.Timer] = []

            class _Handler(FileSystemEventHandler):
                def on_any_event(self, event):
                    if event.is_directory:
                        return
                    if not str(event.src_path).endswith(".yaml"):
                        return
                    # debounce: wait 300ms after last event
                    for t in _debounce:
                        t.cancel()
                    _debounce.clear()
                    t = threading.Timer(0.3, lambda: app.call_from_thread(app.load_memories))
                    _debounce.append(t)
                    t.start()

            observer = Observer()
            observer.schedule(_Handler(), store_path, recursive=True)
            observer.daemon = True
            observer.start()
        except Exception:
            pass  # watchdog unavailable — live reload silently disabled

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    @work(thread=True)
    def load_memories(self) -> None:
        _SCAN = ["▸ scanning store ", "▸ scanning store .", "▸ scanning store ..", "▸ scanning store ..."]
        for i, frame in enumerate(_SCAN):
            self.call_from_thread(self._set_status, frame)
            time.sleep(0.07)
        memories = list_memories(self._root)
        self.call_from_thread(self._populate, memories, True)

    def _populate(self, memories: list[dict], animate: bool = False) -> None:
        self._all_memories = memories
        self.query_one(StatsPanel).update_stats(memories)
        if animate:
            self._stream_rows(memories)
        else:
            self._apply_filter(self._query)

    @work(thread=True)
    def _stream_rows(self, memories: list[dict]) -> None:
        """Animate rows trickling in one-by-one like a terminal readout."""
        self._load_gen += 1
        gen = self._load_gen
        q = self._query.lower()
        visible = [
            m for m in memories
            if not q
            or q in m.get("content", "").lower()
            or q in m.get("category", "").lower()
            or q in ", ".join(m.get("tags", [])).lower()
        ]
        self.call_from_thread(self.query_one, self._TABLE, DataTable)
        # clear first
        self.call_from_thread(lambda: self.query_one(self._TABLE, DataTable).clear())
        for i, m in enumerate(visible):
            if self._load_gen != gen:
                return
            cat     = m.get("category", "")
            content = m.get("content", "")
            tags    = ", ".join(m.get("tags", []))
            row = (
                m.get("id", ""),
                f"{_glyph(cat)} {cat}",
                content[:80] + ("…" if len(content) > 80 else ""),
                tags,
                m.get("source", "manual"),
            )
            mem_id = m.get("id")
            self.call_from_thread(
                lambda r=row, k=mem_id, g=gen: (
                    self.query_one(self._TABLE, DataTable).add_row(*r, key=k)
                    if self._load_gen == g else None
                )
            )
            # stagger — faster as it loads
            delay = max(0.03, 0.12 - i * 0.008)
            time.sleep(delay)
            self.call_from_thread(
                self._set_status,
                f"▸ loaded {i + 1}/{len(visible)} memor{'y' if i == 0 else 'ies'}"
            )
        n = len(visible)
        total = len(memories)
        suffix = f"  [{total} total]" if q and n != total else ""
        self.call_from_thread(
            self._set_status,
            f"▸ {n} memor{'y' if n == 1 else 'ies'} in store{suffix}  ▮"
        )

    def _apply_filter(self, query: str) -> None:
        table = self.query_one(self._TABLE, DataTable)
        table.clear()
        q = query.lower()
        shown = 0
        for m in self._all_memories:
            content = m.get("content", "")
            cat     = m.get("category", "")
            tags    = ", ".join(m.get("tags", []))
            if q and q not in content.lower() and q not in cat.lower() and q not in tags.lower():
                continue
            table.add_row(
                m.get("id", ""),
                f"{_glyph(cat)} {cat}",
                content[:80] + ("…" if len(content) > 80 else ""),
                tags,
                m.get("source", "manual"),
                key=m.get("id"),
            )
            shown += 1
        status = f"▸ {shown} match(es) for '{query}'" if q else f"▸ {shown} memor{'y' if shown == 1 else 'ies'} in store"
        self._set_status(status)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    @on(Input.Changed, "#search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        self._query = event.value
        self._apply_filter(self._query)

    def action_focus_search(self) -> None:
        self.query_one(self._SEARCH, Input).focus()

    def action_clear_search(self) -> None:
        inp = self.query_one(self._SEARCH, Input)
        inp.value = ""
        inp.blur()
        self.query_one(self._TABLE, DataTable).focus()

    # ------------------------------------------------------------------
    # Add memory
    # ------------------------------------------------------------------

    def action_add_memory(self) -> None:
        self.push_screen(AddMemoryScreen(), self._on_add_result)

    def _on_add_result(self, result: dict | None) -> None:
        if not result:
            return
        self._set_status("writing to store…")
        self._save_memory(result["category"], result["content"], result["tags"])

    @work(thread=True)
    def _save_memory(self, category: str, content: str, tags: list[str]) -> None:
        from .search import index_memory
        entry = add_memory(self._root, category, content, tags=tags)
        index_memory(self._root, entry["id"], content)
        self.call_from_thread(self._on_saved, entry)

    def _on_saved(self, entry: dict) -> None:
        memories = list_memories(self._root)
        self._all_memories = memories
        self.query_one(StatsPanel).update_stats(memories)
        self._stream_rows(memories)
        self._set_status(f"▸ ✓  [{entry['id']}] written → {entry['category']}/")

    # ------------------------------------------------------------------
    # Detail view  (Enter on row)
    # ------------------------------------------------------------------

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        mem_id = str(event.row_key.value) if event.row_key else None
        if not mem_id:
            return
        memory = next((m for m in self._all_memories if m.get("id") == mem_id), None)
        if memory:
            self.push_screen(DetailScreen(memory))

    # ------------------------------------------------------------------
    # Edit memory  (u key)
    # ------------------------------------------------------------------

    def action_edit_memory(self) -> None:
        table = self.query_one(self._TABLE, DataTable)
        try:
            row = table.get_row_at(table.cursor_row)
        except Exception:
            return
        mem_id = str(row[0])
        memory = next((m for m in self._all_memories if m.get("id") == mem_id), None)
        if memory:
            self.push_screen(EditMemoryScreen(memory), self._on_edit_result)

    def _on_edit_result(self, result: dict | None) -> None:
        if not result:
            return
        self._set_status("▸ updating…")
        self._do_edit(result)

    @work(thread=True)
    def _do_edit(self, result: dict) -> None:
        from .search import index_memory, remove_from_index
        mem_id = result["id"]
        remove_from_index(self._root, mem_id)
        updated = update_memory(self._root, mem_id, {
            "category": result["category"],
            "content":  result["content"],
            "tags":     result["tags"],
        })
        if updated:
            index_memory(self._root, mem_id, result["content"])
        memories = list_memories(self._root)
        self.call_from_thread(self._populate, memories, False)
        msg = f"▸ ✓  [{mem_id}] updated" if updated else f"▸ ✗  [{mem_id}] not found"
        self.call_from_thread(self._set_status, msg)

    # ------------------------------------------------------------------
    # Delete memory
    # ------------------------------------------------------------------

    def action_delete_memory(self) -> None:
        table = self.query_one(self._TABLE, DataTable)
        try:
            row_index = table.cursor_row
            row = table.get_row_at(row_index)
        except Exception:
            return
        mem_id  = str(row[0])
        content = str(row[2])
        self.push_screen(
            ConfirmDeleteScreen(content),
            lambda ok: self._on_delete_confirm(ok, mem_id),
        )

    def _on_delete_confirm(self, confirmed: bool, mem_id: str) -> None:
        if confirmed:
            self._do_delete(mem_id)

    @work(thread=True)
    def _do_delete(self, mem_id: str) -> None:
        from .search import remove_from_index
        remove_memory(self._root, mem_id)
        remove_from_index(self._root, mem_id)
        memories = list_memories(self._root)
        self.call_from_thread(self._populate, memories, True)
        self.call_from_thread(self._set_status, f"▸ [{mem_id}] removed from store")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def action_export_all(self) -> None:
        self._set_status("▸ exporting…")
        self._do_export()

    @work(thread=True)
    def _do_export(self) -> None:
        from .export import export_all
        paths = export_all(self._root)
        names = ", ".join(str(p.name) for p in paths)
        self.call_from_thread(self._set_status, f"▸ ✓ exported: {names}")

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def action_refresh(self) -> None:
        self._set_status("▸ refreshing…")
        self.load_memories()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _set_status(self, msg: str) -> None:
        self.query_one(self._STATUS, Static).update(f"[{_PHOSPHOR_D}]▸[/{_PHOSPHOR_D}] {msg}")
