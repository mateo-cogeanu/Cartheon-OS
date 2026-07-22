#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

if [ "$(uname -s)" != "Linux" ] || [ "$(uname -m)" != "x86_64" ]; then
    echo "Build the ISO on an x86_64 Linux host (Debian 13 is recommended)." >&2
    exit 1
fi
if [ "$(id -u)" -ne 0 ]; then
    echo "live-build must run as root; rerun this script with sudo." >&2
    exit 1
fi
if ! command -v lb >/dev/null || ! command -v dpkg-deb >/dev/null; then
    echo "Missing build tools. Run scripts/bootstrap-host.sh as root first." >&2
    exit 1
fi

./scripts/build-app-deb.sh
./scripts/prepare-winehq.sh

kernel_count=$(find config/packages.chroot -maxdepth 1 -type f -name 'linux-image-*-cartheon_*.deb' | wc -l)
if [ "$kernel_count" -ne 1 ]; then
    echo "Exactly one Cartheon Kernel 7 package is required. Run make kernel first." >&2
    exit 1
fi
kernel_deb=$(find config/packages.chroot -maxdepth 1 -type f -name 'linux-image-*-cartheon_*.deb' -print -quit)
kernel_package=$(dpkg-deb --field "$kernel_deb" Package)
kernel_release=${kernel_package#linux-image-}
kernel_major=${kernel_release%%.*}
if [ "$kernel_major" -lt 7 ]; then
    echo "The live image requires Kernel 7 or newer; found $kernel_package." >&2
    exit 1
fi

./auto/config
lb build

iso=$(find . -maxdepth 1 -type f -name 'cartheon-os-amd64.hybrid.iso' -print -quit)
if [ -z "$iso" ]; then
    echo "live-build finished but did not produce the expected ISO." >&2
    exit 1
fi
mv "$iso" cartheon-os-amd64.iso
sha256sum cartheon-os-amd64.iso > cartheon-os-amd64.iso.sha256
