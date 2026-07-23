"""Construct and run a cartridge game without invoking a shell."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
import re
import shutil
import signal
import subprocess

from .config import GameConfig


class LaunchError(RuntimeError):
    """Raised when a validated game cannot be started."""


@dataclass(frozen=True, slots=True)
class LaunchSpec:
    argv: tuple[str, ...]
    cwd: Path
    env: dict[str, str]
    wine_server: str | None = None


def _cartridge_id(config: GameConfig) -> str:
    payload = f"{config.root}:{config.title}:{config.executable}".encode()
    return hashlib.sha256(payload).hexdigest()[:20]


def build_launch_spec(config: GameConfig, data_home: Path | None = None) -> LaunchSpec:
    env = os.environ.copy()
    env.update(config.environment)
    executable = str(config.executable_path)
    wine_server: str | None = None

    if config.runtime == "native":
        argv = (executable, *config.arguments)
    else:
        wine = shutil.which("wine")
        if wine is None:
            raise LaunchError("Wine is not installed")
        wine_server = shutil.which("wineserver")
        if wine_server is None:
            raise LaunchError("Wine server is not installed")
        if data_home is None:
            data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
        if config.wine.prefix == "cartridge":
            prefix = config.root / ".cartheon" / "wineprefix"
        else:
            prefix = data_home / "cartheon" / "prefixes" / _cartridge_id(config)
        prefix.mkdir(parents=True, exist_ok=True)
        env.update(
            {
                "WINEPREFIX": str(prefix),
                "WINEDEBUG": "+all" if config.wine.debug else "-all",
                "WINEESYNC": "1" if config.wine.esync else "0",
                "WINEFSYNC": "1" if config.wine.fsync else "0",
                "WINE_NTSYNC": "1" if config.wine.ntsync else "0",
            }
        )
        argv = (wine, executable, *config.arguments)

    gamemoderun = shutil.which("gamemoderun") if config.gamemode else None
    if gamemoderun is not None:
        argv = (gamemoderun, *argv)

    return LaunchSpec(
        argv=tuple(argv),
        cwd=config.working_directory_path,
        env=env,
        wine_server=wine_server,
    )


class GameProcess:
    def __init__(
        self,
        process: subprocess.Popen[bytes],
        spec: LaunchSpec,
        baseline_windows: set[str],
    ) -> None:
        self.process = process
        self.wine_server = spec.wine_server
        self.env = spec.env
        self.baseline_windows = baseline_windows
        self._wine_waiter: subprocess.Popen[bytes] | None = None
        self._game_windows: set[str] = set()

    @staticmethod
    def _window_ids() -> list[str]:
        """Return EWMH client windows in bottom-to-top stacking order."""
        try:
            result = subprocess.run(
                ("xprop", "-root", "_NET_CLIENT_LIST_STACKING"),
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            return []
        if result.returncode != 0:
            return []
        return [
            window.lower()
            for window in re.findall(r"0x[0-9a-fA-F]+", result.stdout)
        ]

    @classmethod
    def start(cls, spec: LaunchSpec) -> "GameProcess":
        baseline_windows = set(cls._window_ids())
        try:
            process = subprocess.Popen(
                spec.argv,
                cwd=spec.cwd,
                env=spec.env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            raise LaunchError(f"could not start the game: {exc}") from exc
        return cls(process, spec, baseline_windows)

    def has_window(self) -> bool:
        """Report when the game has created a new window managed by Openbox."""
        windows = set(self._window_ids()) - self.baseline_windows
        self._game_windows.update(windows)
        return bool(windows)

    def restore_window(self) -> bool:
        """Unminimize, raise, and focus the game's topmost surviving window."""
        current = self._window_ids()
        candidates = [window for window in current if window in self._game_windows]
        if not candidates:
            # Refresh once in case the menu opened before the watcher recorded
            # the game's first EWMH window.
            candidates = [
                window for window in current if window not in self.baseline_windows
            ]
            self._game_windows.update(candidates)
        if not candidates:
            return False
        window = candidates[-1]
        commands = (
            ("wmctrl", "-i", "-r", window, "-b", "remove,hidden"),
            ("wmctrl", "-i", "-a", window),
        )
        for command in commands:
            try:
                result = subprocess.run(
                    command,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3,
                )
            except (OSError, subprocess.SubprocessError):
                return False
            if result.returncode != 0:
                return False
        return True

    def poll(self) -> int | None:
        exit_code = self.process.poll()
        if exit_code is None or self.wine_server is None:
            return exit_code

        # Launchers commonly hand the real game to another Wine process and
        # exit. The Wine server represents the lifetime of the complete prefix,
        # so do not put Cartheon back over a still-running child.
        if self._wine_waiter is None:
            try:
                self._wine_waiter = subprocess.Popen(
                    (self.wine_server, "-w"),
                    env=self.env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError:
                return exit_code
        if self._wine_waiter.poll() is None:
            return None
        return exit_code

    def stop(self, timeout: float = 8.0) -> None:
        if self.poll() is not None:
            return
        if self.wine_server is not None:
            try:
                subprocess.run(
                    (self.wine_server, "-k"),
                    env=self.env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=min(timeout, 5),
                )
            except (OSError, subprocess.SubprocessError):
                pass
        try:
            if self.process.poll() is None:
                os.killpg(self.process.pid, signal.SIGTERM)
                self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=2)
        except ProcessLookupError:
            pass
        if self._wine_waiter is not None:
            try:
                self._wine_waiter.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._wine_waiter.terminate()
