"""Find and mount exFAT cartridges through UDisks2."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import threading
import time
from typing import Callable


@dataclass(frozen=True, slots=True)
class Cartridge:
    device: str
    mountpoint: Path
    filesystem_uuid: str


class DeviceError(RuntimeError):
    pass


def _lsblk() -> list[dict[str, object]]:
    result = subprocess.run(
        [
            "lsblk",
            "--json",
            "--paths",
            "--output",
            "PATH,TYPE,FSTYPE,UUID,MOUNTPOINTS,RM,HOTPLUG,TRAN",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return json.loads(result.stdout).get("blockdevices", [])


def _flatten(devices: list[dict[str, object]]) -> list[dict[str, object]]:
    flattened: list[dict[str, object]] = []
    for device in devices:
        flattened.append(device)
        children = device.get("children")
        if isinstance(children, list):
            flattened.extend(_flatten(children))
    return flattened


def discover_exfat() -> list[dict[str, object]]:
    try:
        devices = _flatten(_lsblk())
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise DeviceError(f"could not inspect block devices: {exc}") from exc
    return [
        device
        for device in devices
        if str(device.get("fstype", "")).lower() == "exfat"
        and str(device.get("type", "")) in {"part", "disk"}
    ]


def _mounted_path(device: dict[str, object]) -> Path | None:
    points = device.get("mountpoints")
    if isinstance(points, list):
        for point in points:
            if point:
                return Path(str(point))
    return None


def mount_device(device: dict[str, object]) -> Cartridge:
    device_path = str(device.get("path", ""))
    if not device_path.startswith("/dev/"):
        raise DeviceError("invalid block-device path")
    mountpoint = _mounted_path(device)
    if mountpoint is None:
        try:
            result = subprocess.run(
                ["udisksctl", "mount", "--no-user-interaction", "--block-device", device_path],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise DeviceError(f"could not mount {device_path}: {exc}") from exc
        # Do not parse human-readable udisksctl output. Ask lsblk for authoritative state.
        del result
        refreshed = next((item for item in discover_exfat() if item.get("path") == device_path), None)
        mountpoint = _mounted_path(refreshed or {})
    if mountpoint is None or not mountpoint.is_dir():
        raise DeviceError(f"{device_path} has no usable mount point")
    return Cartridge(
        device=device_path,
        mountpoint=mountpoint,
        filesystem_uuid=str(device.get("uuid") or device_path),
    )


def eject_device(cartridge: Cartridge) -> None:
    commands = (
        ("unmount", "--no-user-interaction", "--block-device", cartridge.device),
        ("power-off", "--no-user-interaction", "--block-device", cartridge.device),
    )
    for arguments in commands:
        try:
            result = subprocess.run(
                ["udisksctl", *arguments],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise DeviceError(f"could not safely eject {cartridge.device}: {exc}") from exc
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            raise DeviceError(message or f"could not safely eject {cartridge.device}")


class CartridgeMonitor:
    """A conservative poller; it also works when udev events were missed during boot."""

    def __init__(
        self,
        on_insert: Callable[[Cartridge], None],
        on_remove: Callable[[Cartridge], None],
        on_error: Callable[[str], None],
        interval: float = 1.5,
    ) -> None:
        self.on_insert = on_insert
        self.on_remove = on_remove
        self.on_error = on_error
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._known: dict[str, Cartridge] = {}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="cartridge-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=3)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                devices = discover_exfat()
                current_paths = {str(item.get("path")) for item in devices}
                for path, cartridge in tuple(self._known.items()):
                    if path not in current_paths:
                        del self._known[path]
                        self.on_remove(cartridge)
                for device in devices:
                    path = str(device.get("path"))
                    if path in self._known:
                        continue
                    try:
                        cartridge = mount_device(device)
                    except DeviceError as exc:
                        self.on_error(str(exc))
                        continue
                    self._known[path] = cartridge
                    self.on_insert(cartridge)
            except DeviceError as exc:
                self.on_error(str(exc))
            self._stop.wait(self.interval)
