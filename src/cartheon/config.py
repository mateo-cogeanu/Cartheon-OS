"""Parse and validate the untrusted game.cfg found on a cartridge."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import tomllib


class ConfigError(ValueError):
    """Raised when a cartridge manifest is missing or unsafe."""


_SAFE_ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]{0,63}$")
_BLOCKED_ENV = {
    "BASH_ENV",
    "ENV",
    "GCONV_PATH",
    "GTK_PATH",
    "LD_AUDIT",
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
    "PATH",
    "PYTHONHOME",
    "PYTHONPATH",
    "SHELLOPTS",
    "WINELOADER",
    "WINEDLLPATH",
}


def _reject_unknown(table: dict[str, object], allowed: set[str], name: str) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise ConfigError(f"unknown {name} field: {unknown[0]}")


@dataclass(frozen=True, slots=True)
class WineOptions:
    prefix: str = "local"
    debug: bool = False
    esync: bool = True
    fsync: bool = True
    ntsync: bool = True


@dataclass(frozen=True, slots=True)
class GameConfig:
    root: Path
    title: str
    executable: Path
    runtime: str
    working_directory: Path
    cover: Path | None = None
    gamemode: bool = True
    arguments: tuple[str, ...] = ()
    environment: dict[str, str] = field(default_factory=dict)
    boot_animation_seconds: float = 4.0
    wine: WineOptions = field(default_factory=WineOptions)

    @property
    def executable_path(self) -> Path:
        return self.root / self.executable

    @property
    def working_directory_path(self) -> Path:
        return self.root / self.working_directory


def _table(value: object, name: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a TOML table")
    return value


def _string(value: object, name: str, *, default: str | None = None) -> str:
    if value is None and default is not None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} must be a non-empty string")
    if "\x00" in value:
        raise ConfigError(f"{name} contains a NUL byte")
    return value.strip()


def _relative_path(value: object, name: str, *, default: str | None = None) -> Path:
    raw = _string(value, name, default=default)
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        raise ConfigError(f"{name} must stay inside the cartridge")
    if path == Path(".") and name == "game.executable":
        raise ConfigError("game.executable must name a file")
    return path


def _bool(value: object, name: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ConfigError(f"{name} must be true or false")
    return value


def _ensure_inside(root: Path, path: Path, name: str) -> None:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"{name} resolves outside the cartridge") from exc


def _find_cover(root: Path) -> Path | None:
    candidates = sorted(
        (
            path
            for path in root.iterdir()
            if path.is_file()
            and path.stem.casefold() == "cover"
            and bool(path.suffix)
        ),
        key=lambda path: path.name.casefold(),
    )
    for candidate in candidates:
        _ensure_inside(root, candidate, "cover artwork")
        if candidate.stat().st_size <= 32 * 1024 * 1024:
            return candidate
    return None


def load_config(cartridge_root: str | os.PathLike[str]) -> GameConfig:
    root = Path(cartridge_root).resolve(strict=True)
    manifest = root / "game.cfg"
    if not manifest.is_file():
        raise ConfigError("the cartridge root does not contain game.cfg")
    if manifest.stat().st_size > 128 * 1024:
        raise ConfigError("game.cfg is larger than 128 KiB")

    try:
        with manifest.open("rb") as handle:
            raw = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"game.cfg is not valid TOML: {exc}") from exc

    version = raw.get("version")
    if version != 1:
        raise ConfigError("game.cfg must contain version = 1")

    _reject_unknown(raw, {"version", "game", "display", "wine"}, "top-level")

    game = _table(raw.get("game"), "game")
    display = _table(raw.get("display"), "display")
    wine_raw = _table(raw.get("wine"), "wine")
    _reject_unknown(
        game,
        {
            "title",
            "executable",
            "runtime",
            "working_directory",
            "arguments",
            "environment",
            "gamemode",
        },
        "game",
    )
    _reject_unknown(display, {"boot_animation_seconds"}, "display")
    _reject_unknown(wine_raw, {"prefix", "debug", "esync", "fsync", "ntsync"}, "wine")

    title = _string(game.get("title"), "game.title")
    if len(title) > 100:
        raise ConfigError("game.title must be at most 100 characters")

    executable = _relative_path(game.get("executable"), "game.executable")
    runtime = _string(game.get("runtime"), "game.runtime", default="native").lower()
    if runtime not in {"native", "wine"}:
        raise ConfigError("game.runtime must be 'native' or 'wine'")
    working_directory = _relative_path(
        game.get("working_directory"), "game.working_directory", default="."
    )
    gamemode = _bool(game.get("gamemode"), "game.gamemode", True)

    args_raw = game.get("arguments", [])
    if not isinstance(args_raw, list) or len(args_raw) > 128:
        raise ConfigError("game.arguments must be an array with at most 128 entries")
    arguments: list[str] = []
    for index, argument in enumerate(args_raw):
        if not isinstance(argument, str) or "\x00" in argument:
            raise ConfigError(f"game.arguments[{index}] must be a string without NUL bytes")
        if len(argument) > 4096:
            raise ConfigError(f"game.arguments[{index}] is too long")
        arguments.append(argument)

    env_raw = _table(game.get("environment"), "game.environment")
    environment: dict[str, str] = {}
    for key, value in env_raw.items():
        if not _SAFE_ENV_NAME.fullmatch(key) or key in _BLOCKED_ENV:
            raise ConfigError(f"game.environment contains unsafe name: {key}")
        if not isinstance(value, (str, int, float, bool)):
            raise ConfigError(f"game.environment.{key} must be a scalar")
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        if "\x00" in rendered or len(rendered) > 4096:
            raise ConfigError(f"game.environment.{key} has an invalid value")
        environment[key] = rendered

    animation = display.get("boot_animation_seconds", 4.0)
    if not isinstance(animation, (int, float)) or isinstance(animation, bool):
        raise ConfigError("display.boot_animation_seconds must be a number")
    if not 1.0 <= float(animation) <= 30.0:
        raise ConfigError("display.boot_animation_seconds must be between 1 and 30")

    prefix = _string(wine_raw.get("prefix"), "wine.prefix", default="local").lower()
    if prefix not in {"local", "cartridge"}:
        raise ConfigError("wine.prefix must be 'local' or 'cartridge'")
    wine = WineOptions(
        prefix=prefix,
        debug=_bool(wine_raw.get("debug"), "wine.debug", False),
        esync=_bool(wine_raw.get("esync"), "wine.esync", True),
        fsync=_bool(wine_raw.get("fsync"), "wine.fsync", True),
        ntsync=_bool(wine_raw.get("ntsync"), "wine.ntsync", True),
    )

    executable_path = root / executable
    working_path = root / working_directory
    _ensure_inside(root, executable_path, "game.executable")
    _ensure_inside(root, working_path, "game.working_directory")
    if not executable_path.is_file():
        raise ConfigError(f"game executable does not exist: {executable}")
    if not working_path.is_dir():
        raise ConfigError(f"working directory does not exist: {working_directory}")

    return GameConfig(
        root=root,
        title=title,
        executable=executable,
        runtime=runtime,
        working_directory=working_directory,
        cover=_find_cover(root),
        gamemode=gamemode,
        arguments=tuple(arguments),
        environment=environment,
        boot_animation_seconds=float(animation),
        wine=wine,
    )
