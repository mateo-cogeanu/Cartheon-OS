"""Small, shell-free adapters for appliance settings."""

from __future__ import annotations

from dataclasses import dataclass
import re
import subprocess


@dataclass(frozen=True, slots=True)
class SystemStatus:
    volume: int | None
    muted: bool | None
    bluetooth: bool | None
    wifi: bool | None


def _run(*arguments: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(arguments),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _volume_status() -> tuple[int | None, bool | None]:
    try:
        result = _run("wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@")
    except (OSError, subprocess.SubprocessError):
        return None, None
    if result.returncode != 0:
        return None, None
    match = re.search(r"Volume:\s+([0-9.]+)", result.stdout)
    volume = round(float(match.group(1)) * 100) if match else None
    return volume, "[MUTED]" in result.stdout


def _bluetooth_status() -> bool | None:
    try:
        result = _run("bluetoothctl", "show")
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return "Powered: yes" in result.stdout


def _wifi_status() -> bool | None:
    try:
        result = _run("nmcli", "radio", "wifi")
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip().lower() == "enabled"


def read_status() -> SystemStatus:
    volume, muted = _volume_status()
    return SystemStatus(
        volume=volume,
        muted=muted,
        bluetooth=_bluetooth_status(),
        wifi=_wifi_status(),
    )


def perform(action: str) -> str:
    status = read_status()
    if action == "volume_down":
        command = ("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-")
        message = "Volume lowered"
    elif action == "volume_up":
        command = ("wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "5%+")
        message = "Volume raised"
    elif action == "mute":
        command = ("wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle")
        message = "Mute toggled"
    elif action == "bluetooth":
        command = (
            "bluetoothctl",
            "power",
            "off" if status.bluetooth else "on",
        )
        message = "Bluetooth toggled"
    elif action == "wifi":
        command = ("nmcli", "radio", "wifi", "off" if status.wifi else "on")
        message = "Wi-Fi toggled"
    else:
        raise ValueError(f"unknown system action: {action}")

    try:
        result = _run(*command, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"{action.replace('_', ' ')} failed: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(detail or f"{action.replace('_', ' ')} failed")
    return message
