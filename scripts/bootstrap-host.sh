#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this host bootstrap as root on Debian 13 x86_64." >&2
    exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    bc bison build-essential ca-certificates cpio curl debhelper debootstrap dosfstools \
    dpkg-dev dwarves fakeroot flex gnupg grub-efi-amd64-bin grub-pc-bin isolinux \
    kmod libdw-dev libelf-dev libssl-dev live-build mtools rsync squashfs-tools syslinux-common \
    xorriso xz-utils zstd
