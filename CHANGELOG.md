# Changelog

All notable repository changes are recorded here using Europe/Prague timestamps
in ISO 8601 format.

## Unreleased

### 2026-07-23T15:21:10+02:00

- Fixed playable Windows game windows being covered again by Cartheon's loading
  screen: the shell now detects the first new Openbox-managed client window and
  immediately gets out of the game's way.
- Made Windows process supervision follow the complete Wine-prefix lifetime via
  `wineserver -w`, preventing launcher hand-offs from being mistaken for game
  exit, and made **Quit Current Game** stop the entire prefix with
  `wineserver -k`.
- Added game-window, Wine hand-off, and full-prefix quit regression tests; bumped
  the shell package to `0.2.3`.

### 2026-07-23T15:04:50+02:00

- Made opening Wi-Fi settings use NetworkManager's cached background results so
  adapters that interrupt their active association during a forced scan do not
  drop the shell's current connection; a fresh radio scan now occurs only when
  the user explicitly chooses **Scan for Networks**.
- Added cached-versus-forced scan regression coverage and bumped the shell
  package to `0.2.2`.

### 2026-07-23T14:52:41+02:00

- Extended the 8-bit visual language across every Cartheon shell screen with
  the Terminus pixel typeface, square block controls, stepped shadows, and
  instant page transitions.
- Replaced the Wi-Fi toggle with a keyboard-navigable network menu supporting
  power, rescanning, password entry, connection switching, and disconnect.
- Replaced the Bluetooth toggle with a nearby-device menu supporting power,
  scanning, pairing/trusting/connecting new devices, and disconnecting active
  devices.
- Hid the mouse pointer everywhere in the Cartheon shell while leaving game
  windows unaffected; added wireless parsing/action tests and bumped the shell
  package to `0.2.1`.

### 2026-07-23T13:59:42+02:00

- Replaced immediate cartridge launch with an 8-bit cover screen that discovers
  `cover.*` artwork, shows the manifest title, and waits for the green Play
  button or Enter key.
- Reworked the shell with pixel-styled spinning cut rings and removed the
  `CARTHEON OS` label from the empty-cartridge screen.
- Added an Escape settings menu with keyboard navigation, volume, mute,
  Bluetooth, Wi-Fi, safe cartridge ejection, and in-game Quit.
- Added a global Ctrl+Alt+Escape Openbox shortcut that raises settings over a
  game, plus cover, ejection, and shortcut regression tests; bumped the shell
  package to `0.2.0`.

### 2026-07-23T13:39:23+02:00

- Fixed the installed appliance's cartridge controller starting before its GTK
  window exists, which left a functional-looking waiting screen while silently
  disabling all cartridge detection.
- Added an explicit UDisks2 mount policy for Cartheon users in the `plugdev`
  group, added a startup-order regression check, and bumped the shell package
  to `0.1.10`.

### 2026-07-23T13:27:58+02:00

- Fixed cartridge discovery for USB SSD adapters and other exFAT drives whose
  partition does not repeat the parent disk's removable, hot-plug, or transport
  flags; Cartheon now recognizes every exFAT disk or partition.
- Added an unflagged-SSD regression test and bumped the shell package to
  `0.1.9`.

### 2026-07-23T12:28:51+02:00

- Fixed the live Wi-Fi assistant crash caused by calling the unsupported
  `set_placeholder_text()` method on GTK 4's `PasswordEntry`, which left only
  Openbox's black background and mouse pointer visible.
- Added a regression check for the incompatible GTK call and bumped the shell
  package to `0.1.8`.

### 2026-07-23T11:58:09+02:00

- Prevented unsupported X11 screen-saver or DPMS operations from terminating
  the live session before setup appears, fixing the black screen with only a
  mouse pointer.
- Made NetworkManager startup recoverable inside the graphical network assistant
  and used noninteractive sudo for deterministic auto-start; bumped the shell to
  `0.1.7`.

### 2026-07-23T10:50:56+02:00

- Changed live USB startup to open the fullscreen network and Calamares setup
  flow automatically, without briefly showing or depending on the cartridge
  shell.
- Removed every installer control and shortcut from the installed appliance
  screen and removed its exFAT/game.cfg subtitle for a clean cartridge prompt;
  bumped the shell to `0.1.6`.

### 2026-07-23T09:21:26+02:00

- Added a graphical pre-install network assistant that detects an existing wired
  connection or scans and connects to secured, open, and hidden Wi-Fi networks.
- Blocked Calamares from starting until internet access is verified, preventing
  package downloads from failing partway through setup; bumped the shell to
  `0.1.5`.

### 2026-07-22T20:24:35+02:00

- Added the Python Cairo/GTK bridge required by the animated cartridge logo,
  allowing the Cartheon appliance window to finish constructing at login;
  declared GTK 4's GDK version explicitly and bumped the shell to `0.1.4`.

### 2026-07-22T19:56:41+02:00

- Fixed ownership of the pre-created `player` home so graphical session files
  can be created, and restored LightDM as the VT/Xorg owner with an explicit
  Cartheon autologin session; bumped the shell package to `0.1.3`.

### 2026-07-22T19:05:52+02:00

- Replaced LightDM-dependent autologin with a dedicated VT1 systemd appliance
  service that starts the Cartheon X session directly as `player` and restarts
  it on failure; bumped the shell package to `0.1.2`.

### 2026-07-22T18:40:06+02:00

- Fixed `auto/clean` to preserve the caller's requested live-build cleanup
  scope instead of converting every cleanup into a full purge.

### 2026-07-22T18:38:08+02:00

- Bumped the Cartheon shell package to `0.1.1` and made its build filename
  derive from the control metadata, ensuring changed packages upgrade during
  incremental live-image builds.

### 2026-07-22T18:34:53+02:00

- Initialized the pre-created `player` account with Debian Live's standard
  credential state so PAM permits LightDM autologin into the Cartheon session.

### 2026-07-22T18:12:36+02:00

- Made the hardware-support hook create the custom kernel's initial initramfs
  when package installation precedes `initramfs-tools`, ensuring live-build can
  export a complete boot pair into the ISO.

### 2026-07-22T18:05:13+02:00

- Registered the `7.1.4-cartheon` custom kernel as live-build's sole Linux
  flavour so its kernel and initramfs are exported into the ISO boot directory.

### 2026-07-22T17:48:51+02:00

- Preseeded acceptance of the Intel IPW2100/IPW2200 firmware license so broad
  legacy Wi-Fi support installs during noninteractive live-image builds.

### 2026-07-22T17:46:24+02:00

- Updated the Cartheon application package dependency from obsolete
  `policykit-1` to Debian 13's `polkitd`, matching the live-image package list.

### 2026-07-22T17:42:29+02:00

- Fixed the live-build `auto/build` entry point to use its non-recursive
  `noauto` handoff instead of repeatedly restarting the Cartheon ISO wrapper.

### 2026-07-22T17:40:30+02:00

- Disabled every DWARF choice before selecting `DEBUG_INFO_NONE`, verified
  against Linux 7.1.4 Kconfig so the no-debug release setting persists.

### 2026-07-22T17:37:52+02:00

- Explicitly selected Kernel 7's `DEBUG_INFO_NONE` Kconfig choice so release
  builds no longer create multi-gigabyte debug-symbol packages.

### 2026-07-22T16:55:57+02:00

- Added the missing `libdw-dev` Kernel 7 packaging dependency to the Debian
  builder bootstrap after validating the build on a clean x86_64 machine.

### 2026-07-22T16:48:02+02:00

- Removed the GitHub Actions workflow so pushes and pull requests no longer
  start automated repository jobs.

### 2026-07-22T16:40:35+02:00

- Expanded the live image with broad AMD, Intel, and NVIDIA GPU firmware and
  open-source graphics support.
- Added AMD and Intel CPU microcode, current Debian backports firmware, and
  common Wi-Fi, Ethernet, audio DSP, Bluetooth, storage, and controller support.
- Added explicit 64-bit and 32-bit Mesa, OpenGL, and Vulkan drivers so Wine
  games can use GPU acceleration on both architectures.
- Expanded the custom Kernel 7 configuration for newer Intel Xe graphics,
  CPU power management, IOMMU, USB4, audio, Bluetooth, cameras, and virtual GPUs.
- Regenerated every installed kernel initramfs after firmware installation.
- Replaced the obsolete `policykit-1` package name with Debian 13's `polkitd`
  package so the live image dependency set resolves on Trixie.

### 2026-07-22T16:35:11+02:00

- Created the initial Cartheon OS x86_64 prototype.
- Added removable exFAT cartridge discovery and strict `game.cfg` validation.
- Added native Linux, Wine 11+, NTSYNC, DXVK, and GameMode launch support.
- Added the fullscreen GTK cartridge, boot-animation, loading, and error interface.
- Added the Debian 13 live-build configuration and Calamares graphical installer.
- Added the pinned Linux 7.1.4 build and checksum verification workflow.
- Added cartridge examples, project documentation, packaging, tests, and CI checks.
- Added repository guidance requiring a timestamped changelog entry for every change.
