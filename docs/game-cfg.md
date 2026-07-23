# `game.cfg` reference (version 1)

`game.cfg` is UTF-8 TOML stored in the root of an exFAT cartridge. It is limited
to 128 KiB. All paths use `/` separators and are relative to the cartridge root.

Optional cover artwork is stored beside the manifest as `cover.<extension>`.
Cartheon uses GTK's installed image loaders rather than restricting the filename
to one extension. Common PNG, JPEG, WebP, GIF, BMP, TIFF, SVG, and AVIF files are
supported when the corresponding loader is present. The first decodable
case-insensitive `cover.*` file is used, with a maximum size of 32 MiB.

## Required fields

| Field | Type | Meaning |
|---|---|---|
| `version` | integer | Must be `1`. |
| `game.title` | string | Display name, at most 100 characters. |
| `game.executable` | string | Existing file inside the cartridge. |

## Optional fields

| Field | Default | Meaning |
|---|---:|---|
| `game.runtime` | `"native"` | `"native"` or `"wine"`. |
| `game.working_directory` | `"."` | Existing directory inside the cartridge. |
| `game.arguments` | `[]` | Argument array; never parsed by a shell. |
| `game.gamemode` | `true` | Wrap the process with `gamemoderun` when available. |
| `game.environment` | `{}` | Uppercase scalar environment variables. |
| `display.boot_animation_seconds` | `4.0` | Animation duration from 1–30 seconds. |
| `wine.prefix` | `"local"` | `"local"` or `"cartridge"`. |
| `wine.debug` | `false` | Enable verbose Wine logging. |
| `wine.esync` | `true` | Set `WINEESYNC=1`. |
| `wine.fsync` | `true` | Set `WINEFSYNC=1`. |
| `wine.ntsync` | `true` | Set `WINE_NTSYNC=1`. |

Environment variable names must match `[A-Z_][A-Z0-9_]*`. Cartheon blocks
variables which can replace loaders or inject host libraries, including `PATH`,
`LD_PRELOAD`, `LD_LIBRARY_PATH`, `WINELOADER`, and `WINEDLLPATH`.

For Linux cartridges, compile for x86_64 and include all non-system shared
libraries next to the game or in an AppImage-like bundle. exFAT has no Unix
permission metadata; Cartheon relies on the UDisks2 mount's executable mode.
