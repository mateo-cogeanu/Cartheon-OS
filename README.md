# Cartheon OS

Cartheon OS turns an x86_64 PC into a cartridge-style game console. It boots into
one fullscreen screen, watches for an exFAT drive with `game.cfg` in its root,
plays a cartridge animation, and launches either a native Linux game or a Windows
game through Wine.

This repository is a buildable **0.1 hardware-validation prototype**, not a
finished universal console. It deliberately uses mature distribution plumbing
for the dangerous parts: Debian 13 (trixie) live-build, UDisks2 mounting,
LightDM, and the Calamares graphical installer.

## Current stack

- x86_64 only
- Debian 13 live/install image
- pinned Linux 7.1.4 source, compiled into a Debian kernel package
- WineHQ stable, with a build-time check requiring Wine 11 or newer
- Debian DXVK 2.6, Vulkan/Mesa, GameMode, PipeWire, controller input, and common
  AMD/Intel/Wi-Fi firmware
- hybrid BIOS/UEFI ISO and Calamares graphical installer
- fullscreen GTK 4 appliance shell with no desktop, taskbar, or file manager

Kernel 7 and Wine 11 are both real releases. The pin is intentionally explicit:
the kernel tarball is SHA-256 checked, while Wine comes from WineHQ's signed APT
repository and is version-checked inside the image build.

## How a cartridge works

Format a removable drive as exFAT, place `game.cfg` in its root, and copy the game
files named by that manifest. See [the Windows example](examples/windows-cartridge/game.cfg)
or [the Linux example](examples/native-cartridge/game.cfg).

```toml
version = 1

[game]
title = "My Game"
executable = "Game/MyGame.exe"
runtime = "wine"               # "wine" or "native"
working_directory = "Game"
arguments = ["-fullscreen"]
gamemode = true

[display]
boot_animation_seconds = 4.0

[wine]
prefix = "local"               # or "cartridge"
debug = false
esync = true
fsync = true
ntsync = true
```

`local` keeps the Wine prefix and saves on the installed OS. `cartridge` keeps
the prefix in `.cartheon/wineprefix` on the exFAT drive, making it portable but
slower and much larger.

The parser rejects absolute paths, `..`, symlinks which escape the cartridge,
NUL bytes, oversized manifests, shell execution, and loader-injection variables
such as `LD_PRELOAD`. A game executable is still trusted code; only insert media
you trust.

## Build the ISO

Use a clean Debian 13 x86_64 machine with at least 40 GB free and 16 GB RAM
recommended. Kernel compilation is the slow part.

```sh
sudo ./scripts/bootstrap-host.sh
make test
make kernel
sudo make iso
```

Outputs:

- `cartheon-os-amd64.iso`
- `cartheon-os-amd64.iso.sha256`

The kernel build uses the Linux builder's current distribution kernel config as
a broad hardware baseline, then forces exFAT, NTSYNC, DRM, sound, HID, FUSE, and
other required features. If `/boot/config-$(uname -r)` is unavailable, it falls
back to `x86_64_defconfig`; that fallback is useful for development but should
not be used for a public hardware image.

To update the kernel, pass both an official version and its official SHA-256:

```sh
KERNEL_VERSION=7.x.y KERNEL_SHA256=... make kernel
```

## Test before real hardware

Run the parser/unit suite on any machine with Python 3.11 or newer:

```sh
make test
make lint
```

On a Linux desktop with GTK 4 Python bindings installed, develop the shell
without a block device:

```sh
PYTHONPATH=src python3 -m cartheon.main --cartridge /path/to/test-cartridge
```

Boot the ISO first in QEMU with UEFI and a virtual USB/exFAT disk, then test AMD,
Intel, and NVIDIA hardware separately. Press **F10** or use the small installer
button on the live image to open Calamares.

The prototype kernel is not Secure Boot signed. Disable Secure Boot in the test
machine's firmware before booting this ISO. A production image should add a
project signing key, signed kernel/modules, and a shim enrollment process.

## What “plays all games” can realistically mean

Wine 11 substantially broadens Windows compatibility, but no Linux/Wine system
can promise every Windows game. Kernel anti-cheat, DRM, Microsoft Store/UWP,
special hardware drivers, launchers, and individual game bugs can still prevent
a title from running. NVIDIA's proprietary driver is also not bundled in this
prototype. The honest project goal is **broad native and Wine compatibility with
per-cartridge settings**, followed by a tested compatibility catalog.

## Repository map

- `src/cartheon/` — manifest parser, detector, launcher, and GTK shell
- `tests/` — dependency-free unit tests
- `config/` and `auto/` — Debian live-build configuration
- `packaging/cartheon/` — appliance session Debian-package payload
- `scripts/` — host bootstrap, Kernel 7, WineHQ, package, and ISO builds
- `docs/game-cfg.md` — complete cartridge manifest reference
