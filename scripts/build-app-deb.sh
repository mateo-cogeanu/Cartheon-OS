#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
stage_dir=$(mktemp -d "${TMPDIR:-/tmp}/cartheon-deb.XXXXXX")
trap 'rm -rf -- "$stage_dir"' EXIT HUP INT TERM

install -d "$stage_dir/DEBIAN" "$stage_dir/usr/lib/cartheon/cartheon"
cp -R "$project_dir/packaging/cartheon/DEBIAN/." "$stage_dir/DEBIAN/"
cp -R "$project_dir/packaging/cartheon/rootfs/." "$stage_dir/"
for source_file in "$project_dir"/src/cartheon/*.py; do
    install -m 0644 "$source_file" "$stage_dir/usr/lib/cartheon/cartheon/"
done

chmod 0755 \
    "$stage_dir/DEBIAN/postinst" \
    "$stage_dir/usr/bin/cartheon-shell" \
    "$stage_dir/usr/bin/cartheon-validate" \
    "$stage_dir/usr/bin/cartheon-session" \
    "$stage_dir/usr/lib/cartheon/cartheon-installer"
chmod 0440 "$stage_dir/etc/sudoers.d/cartheon-installer"

output_dir="$project_dir/config/packages.chroot"
install -d "$output_dir"
dpkg-deb --root-owner-group --build "$stage_dir" "$output_dir/cartheon-shell_0.1.0_all.deb"
