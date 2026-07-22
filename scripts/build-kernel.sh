#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
kernel_version=${KERNEL_VERSION:-7.1.4}
kernel_sha256=${KERNEL_SHA256:-1c63922a119675d38e3ae0f8f6ee07f15c41a786ab9ed66563749bb8c9a08e2e}
jobs=${JOBS:-$(getconf _NPROCESSORS_ONLN)}

if [ "$(uname -m)" != "x86_64" ]; then
    echo "The Cartheon kernel must be built on x86_64 Linux." >&2
    exit 1
fi

kernel_major=${kernel_version%%.*}
case "$kernel_major" in
    *[!0-9]*|'') echo "KERNEL_VERSION must begin with a numeric major version." >&2; exit 1 ;;
esac
if [ "$kernel_major" -lt 7 ]; then
    echo "KERNEL_VERSION must be 7.0 or newer." >&2
    exit 1
fi

build_root="$project_dir/build/kernel"
source_archive="$build_root/linux-$kernel_version.tar.xz"
source_dir="$build_root/linux-$kernel_version"
install -d "$build_root" "$project_dir/config/packages.chroot"

if [ ! -f "$source_archive" ]; then
    curl --fail --location --continue-at - \
        "https://cdn.kernel.org/pub/linux/kernel/v${kernel_major}.x/linux-$kernel_version.tar.xz" \
        --output "$source_archive"
fi
printf '%s  %s\n' "$kernel_sha256" "$source_archive" | sha256sum --check --status || {
    echo "Kernel archive checksum failed." >&2
    exit 1
}

if [ ! -d "$source_dir" ]; then
    tar -C "$build_root" -xf "$source_archive"
fi
cd "$source_dir"

host_config="/boot/config-$(uname -r)"
if [ -r "$host_config" ]; then
    cp "$host_config" .config
else
    make x86_64_defconfig
fi

scripts/config --enable 64BIT
scripts/config --enable SMP
scripts/config --module EXFAT_FS
scripts/config --module FUSE_FS
scripts/config --module NTFS3_FS
scripts/config --module VFAT_FS
scripts/config --module ISO9660_FS
scripts/config --module OVERLAY_FS
scripts/config --module SQUASHFS
scripts/config --enable SQUASHFS_XZ
scripts/config --module BLK_DEV_LOOP
scripts/config --enable BLK_DEV_INITRD
scripts/config --enable DEVTMPFS
scripts/config --enable RD_GZIP
scripts/config --enable RD_XZ
scripts/config --enable INPUT_EVDEV
scripts/config --enable HIDRAW
scripts/config --enable DRM
scripts/config --module DRM_AMDGPU
scripts/config --module DRM_I915
scripts/config --module DRM_XE
scripts/config --module DRM_NOUVEAU
scripts/config --module DRM_VIRTIO_GPU
scripts/config --enable MICROCODE
scripts/config --enable MICROCODE_AMD
scripts/config --enable MICROCODE_INTEL
scripts/config --enable CPU_FREQ
scripts/config --enable X86_AMD_PSTATE
scripts/config --enable X86_INTEL_PSTATE
scripts/config --enable IOMMU_SUPPORT
scripts/config --enable AMD_IOMMU
scripts/config --enable INTEL_IOMMU
scripts/config --enable NTSYNC
scripts/config --enable SND
scripts/config --module SND_HDA_INTEL
scripts/config --module SND_USB_AUDIO
scripts/config --enable SND_SOC
scripts/config --enable HID_GENERIC
scripts/config --module HID_NINTENDO
scripts/config --module HID_PLAYSTATION
scripts/config --module HID_SONY
scripts/config --module JOYSTICK_XPAD
scripts/config --module UHID
scripts/config --module USB_STORAGE
scripts/config --module USB_XHCI_HCD
scripts/config --module USB4
scripts/config --enable TYPEC
scripts/config --enable BT
scripts/config --enable WLAN
scripts/config --enable MEDIA_SUPPORT
scripts/config --enable MEDIA_USB_SUPPORT
scripts/config --module USB_VIDEO_CLASS
scripts/config --module SATA_AHCI
scripts/config --module BLK_DEV_NVME
scripts/config --disable RUST
scripts/config --disable DEBUG_INFO
scripts/config --disable DEBUG_INFO_BTF
scripts/config --set-str SYSTEM_TRUSTED_KEYS ""
scripts/config --set-str SYSTEM_REVOCATION_KEYS ""
yes '' | make olddefconfig

make -j"$jobs" bindeb-pkg \
    LOCALVERSION=-cartheon \
    KDEB_PKGVERSION="$kernel_version-1"

found=0
for package in "$build_root"/linux-image-"$kernel_version"*-cartheon_*.deb; do
    if [ -f "$package" ]; then
        cp "$package" "$project_dir/config/packages.chroot/"
        found=1
    fi
done
if [ "$found" -ne 1 ]; then
    echo "Kernel build completed without a linux-image Debian package." >&2
    exit 1
fi
