# Changelog

All notable repository changes are recorded here using Europe/Prague timestamps
in ISO 8601 format.

## Unreleased

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
