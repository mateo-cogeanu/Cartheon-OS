"""Construct and run a cartridge game without invoking a shell."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
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


def _cartridge_id(config: GameConfig) -> str:
    payload = f"{config.root}:{config.title}:{config.executable}".encode()
    return hashlib.sha256(payload).hexdigest()[:20]


def build_launch_spec(config: GameConfig, data_home: Path | None = None) -> LaunchSpec:
    env = os.environ.copy()
    env.update(config.environment)
    executable = str(config.executable_path)

    if config.runtime == "native":
        argv = (executable, *config.arguments)
    else:
        wine = shutil.which("wine")
        if wine is None:
            raise LaunchError("Wine is not installed")
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

    return LaunchSpec(argv=tuple(argv), cwd=config.working_directory_path, env=env)


class GameProcess:
    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self.process = process

    @classmethod
    def start(cls, spec: LaunchSpec) -> "GameProcess":
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
        return cls(process)

    def poll(self) -> int | None:
        return self.process.poll()

    def stop(self, timeout: float = 8.0) -> None:
        if self.poll() is not None:
            return
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=2)
        except ProcessLookupError:
            pass
