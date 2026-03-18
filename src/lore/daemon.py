"""Spellbook daemon — watches .lore for changes and auto-exports AI context files."""
from __future__ import annotations

import os
import signal
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


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
        on_change: Callable[[str], None],
    ) -> None:
        super().__init__()
        self._root = root
        self._debounce = debounce
        self._on_change = on_change
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def _schedule(self, src_path: str) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce, self._on_change, args=(src_path,))
            self._timer.daemon = True
            self._timer.start()

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and str(event.src_path).endswith(".yaml"):
            self._schedule(str(event.src_path))

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and str(event.src_path).endswith(".yaml"):
            self._schedule(str(event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and str(event.src_path).endswith(".yaml"):
            self._schedule(str(event.src_path))


_PID_FILENAME = "spellbook.pid"


def pid_file(root: Path) -> Path:
    from .config import memory_dir
    return memory_dir(root) / _PID_FILENAME


def run_spellbook(
    root: Path,
    debounce: float = 1.5,
    on_state_change: Callable[[SpellbookState], None] | None = None,
    stop_event: threading.Event | None = None,
) -> None:
    """Start the spellbook daemon loop — blocks until stop_event is set.

    Args:
        root: Project root containing .lore/
        debounce: Seconds to wait after last change before re-exporting.
        on_state_change: Optional callback, called on every state transition.
        stop_event: Threading event; set it to stop the loop cleanly.
    """
    from .config import memory_dir
    from .export import export_all

    if stop_event is None:
        stop_event = threading.Event()

    state = SpellbookState(status=SpellbookStatus.WATCHING)

    def _notify() -> None:
        if on_state_change:
            on_state_change(state)

    def _do_export(src_path: str) -> None:
        state.status = SpellbookStatus.CASTING
        state.last_scroll = Path(src_path).name
        _notify()
        try:
            export_all(root)
            state.cast_count += 1
            state.last_cast = datetime.now(timezone.utc)
        except Exception as exc:
            state.errors.append(str(exc))
        finally:
            state.status = SpellbookStatus.WATCHING
            _notify()

    watch_path = str(memory_dir(root))
    handler = _LoreEventHandler(root, debounce, _do_export)
    observer = Observer()
    observer.schedule(handler, watch_path, recursive=True)
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


def daemonize(root: Path, debounce: float = 1.5) -> None:
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
        run_spellbook(root, debounce=debounce)
    finally:
        pf.unlink(missing_ok=True)
        os._exit(0)
