#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
key_dir="$project_dir/config/includes.chroot/etc/apt/keyrings"
install -d "$key_dir"
curl --fail --silent --show-error --location \
    https://dl.winehq.org/wine-builds/winehq.key \
    --output "$key_dir/winehq-archive.key"
