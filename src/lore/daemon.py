"""Spellbook daemon — watches .lore for changes and auto-exports AI context files."""
from __future__ import annotations

import os
import signal
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .associations import apply_related_links, suggest_for_entry


def _memory_id_from_event_path(src_path: str) -> str | None:
    path = Path(src_path)
    if path.suffix != ".yaml":
        return None
    stem = path.stem
    if "_" not in stem:
        return None
    mem_id = stem.rsplit("_", 1)[-1].strip()
    return mem_id or None


class SpellbookStatus(str, Enum):
    IDLE = "idle"
    WATCHING = "watching"
    CASTING = "casting"  # actively re-exporting


@dataclass
class SpellbookState:
    status: SpellbookStatus = SpellbookStatus.IDLE
    last_cast: datetime | None = None
    cast_count: int = 0
    last_scroll: str = ""  # filename that triggered the last cast
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class _LoreEventHandler(FileSystemEventHandler):
    """Debounced watchdog handler — fires export after .lore YAML changes settle."""

    def __init__(
        self,
        root: Path,
        debounce: float,
        on_yaml_change: Callable[[str], None],
        on_chronicle_change: Callable[[str], None] | None = None,
        chronicle_path: Path | None = None,
    ) -> None:
        super().__init__()
        self._root = root
        self._debounce = debounce
        self._on_yaml_change = on_yaml_change
        self._on_chronicle_change = on_chronicle_change
        self._chronicle_path = (chronicle_path or (root / "CHRONICLE.md")).resolve()
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def _schedule(self, key: str, callback: Callable[[str], None], src_path: str) -> None:
        with self._lock:
            existing = self._timers.get(key)
            if existing is not None:
                existing.cancel()
            timer = threading.Timer(self._debounce, callback, args=(src_path,))
            timer.daemon = True
            self._timers[key] = timer
            timer.start()

    def _is_chronicle(self, src_path: str) -> bool:
        return Path(src_path).resolve() == self._chronicle_path

    def _handle_event(self, src_path: str) -> None:
        if src_path.endswith(".yaml"):
            self._schedule("yaml", self._on_yaml_change, src_path)
            return
        if self._on_chronicle_change and self._is_chronicle(src_path):
            self._schedule("chronicle", self._on_chronicle_change, src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle_event(str(event.src_path))

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle_event(str(event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle_event(str(event.src_path))


_PID_FILENAME = "spellbook.pid"


def pid_file(root: Path) -> Path:
    from .config import memory_dir
    return memory_dir(root) / _PID_FILENAME


def run_spellbook(
    root: Path,
    debounce: float = 1.5,
    on_state_change: Callable[[SpellbookState], None] | None = None,
    stop_event: threading.Event | None = None,
    sync_chronicle: bool = True,
    associate_on_watch: bool = False,
    associate_top: int = 3,
    associate_min_score: float = 0.55,
) -> None:
    """Start the spellbook daemon loop — blocks until stop_event is set.

    Args:
        root: Project root containing .lore/
        debounce: Seconds to wait after last change before re-exporting.
        on_state_change: Optional callback, called on every state transition.
        stop_event: Threading event; set it to stop the loop cleanly.
    """
    from .config import memory_dir
    from .chronicle import import_chronicle
    from .export import export_all
    from .search import batch_index_memories

    if stop_event is None:
        stop_event = threading.Event()

    state = SpellbookState(status=SpellbookStatus.WATCHING)
    chronicle_path = root / "CHRONICLE.md"
    ignore_chronicle_until = 0.0
    ignore_association_until = 0.0

    def _notify() -> None:
        if on_state_change:
            on_state_change(state)

    def _do_export(src_path: str) -> None:
        nonlocal ignore_chronicle_until, ignore_association_until
        state.status = SpellbookStatus.CASTING
        state.last_scroll = Path(src_path).name
        _notify()
        try:
            export_all(root)

            if associate_on_watch and time.time() >= ignore_association_until:
                mem_id = _memory_id_from_event_path(src_path)
                if mem_id:
                    suggestions = suggest_for_entry(
                        root,
                        entry_id=mem_id,
                        top_k=associate_top,
                        min_score=associate_min_score,
                    )
                    if suggestions:
                        applied = apply_related_links(
                            root,
                            mem_id,
                            [str(item.get("id", "")) for item in suggestions],
                        )
                        if applied:
                            # Prevent immediate recursive retriggers from association writes.
                            ignore_association_until = time.time() + max(2.0, debounce * 2)

            ignore_chronicle_until = time.time() + max(2.0, debounce * 2)
            state.cast_count += 1
            state.last_cast = datetime.now(timezone.utc)
        except Exception as exc:
            state.errors.append(str(exc))
        finally:
            state.status = SpellbookStatus.WATCHING
            _notify()

    def _do_sync_chronicle(src_path: str) -> None:
        nonlocal ignore_chronicle_until
        if not sync_chronicle:
            return
        if time.time() < ignore_chronicle_until:
            return

        try:
            stats = import_chronicle(root, chronicle_path, dry_run=False)
            indexed_pairs = stats.get("indexed_pairs") or []

            # No-op sync: do not export, cast, or bump counters.
            # This avoids CHRONICLE self-trigger loops when the file changed
            # but yielded no new memories to import.
            if int(stats.get("added", 0)) <= 0 and not indexed_pairs:
                return

            state.status = SpellbookStatus.CASTING
            state.last_scroll = Path(src_path).name
            _notify()

            if indexed_pairs:
                batch_index_memories(root, indexed_pairs)
            export_all(root)
            ignore_chronicle_until = time.time() + max(2.0, debounce * 2)
            state.cast_count += 1
            state.last_cast = datetime.now(timezone.utc)
        except Exception as exc:
            state.errors.append(str(exc))
        finally:
            if state.status != SpellbookStatus.WATCHING:
                state.status = SpellbookStatus.WATCHING
                _notify()

    watch_path = str(memory_dir(root))
    handler = _LoreEventHandler(
        root,
        debounce,
        on_yaml_change=_do_export,
        on_chronicle_change=_do_sync_chronicle if sync_chronicle else None,
        chronicle_path=chronicle_path,
    )
    observer = Observer()
    observer.schedule(handler, watch_path, recursive=True)
    if sync_chronicle:
        observer.schedule(handler, str(root), recursive=False)
    observer.start()

    state.status = SpellbookStatus.WATCHING
    _notify()

    try:
        while not stop_event.is_set():
            stop_event.wait(timeout=0.5)
    finally:
        observer.stop()
        observer.join()
        state.status = SpellbookStatus.IDLE
        _notify()


def daemonize(
    root: Path,
    debounce: float = 1.5,
    sync_chronicle: bool = True,
    associate_on_watch: bool = False,
    associate_top: int = 3,
    associate_min_score: float = 0.55,
) -> None:
    """Fork into background, detach from terminal, and write PID file.

    The calling process returns immediately after the first fork so the
    CLI can print a success message.  The grandchild becomes the daemon.
    POSIX only (macOS / Linux).
    """
    pid = os.fork()
    if pid > 0:
        # Original process — return to the CLI so it can print status.
        return

    # Child 1: create a new session so we're no longer tied to the terminal.
    os.setsid()

    # Second fork prevents the daemon from ever re-acquiring a terminal.
    pid2 = os.fork()
    if pid2 > 0:
        os._exit(0)  # Child 1 exits; grandchild continues.

    # --- Grandchild / actual daemon below ---

    # Redirect stdio to /dev/null so nothing leaks to the terminal.
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(devnull, fd)
    os.close(devnull)

    # Write our PID so `lore slumber` can find us.
    pf = pid_file(root)
    pf.write_text(str(os.getpid()))

    def _on_sigterm(signum: int, frame: object) -> None:
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _on_sigterm)

    try:
        run_spellbook(
            root,
            debounce=debounce,
            sync_chronicle=sync_chronicle,
            associate_on_watch=associate_on_watch,
            associate_top=associate_top,
            associate_min_score=associate_min_score,
        )
    finally:
        pf.unlink(missing_ok=True)
        os._exit(0)
