# Changelog

All notable repository changes are recorded here using Europe/Prague timestamps
in ISO 8601 format.

## Unreleased

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
