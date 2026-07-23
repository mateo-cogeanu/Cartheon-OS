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
    wifi_connection: str | None = None
    bluetooth_connected: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WifiNetwork:
    ssid: str
    signal: int
    security: str
    connected: bool = False

    @property
    def secured(self) -> bool:
        return bool(self.security and self.security != "--")


@dataclass(frozen=True, slots=True)
class BluetoothDevice:
    address: str
    name: str
    connected: bool
    paired: bool


def _run(*arguments: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(arguments),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def split_escaped_fields(line: str) -> list[str]:
    """Split nmcli's escaped colon output without losing literal colons."""
    fields: list[str] = []
    field: list[str] = []
    escaped = False
    for character in line:
        if escaped:
            field.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == ":":
            fields.append("".join(field))
            field = []
        else:
            field.append(character)
    if escaped:
        field.append("\\")
    fields.append("".join(field))
    return fields


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


def _wifi_connection() -> str | None:
    try:
        result = _run(
            "nmcli",
            "--terse",
            "--escape",
            "yes",
            "--fields",
            "ACTIVE,SSID",
            "device",
            "wifi",
            "list",
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        fields = split_escaped_fields(line)
        if len(fields) == 2 and fields[0].lower() in {"yes", "*"} and fields[1]:
            return fields[1]
    return None


def _bluetooth_connected_names() -> tuple[str, ...]:
    try:
        result = _run("bluetoothctl", "devices", "Connected")
    except (OSError, subprocess.SubprocessError):
        return ()
    if result.returncode != 0:
        return ()
    names: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=2)
        if len(parts) == 3 and parts[0] == "Device":
            names.append(parts[2])
    return tuple(names)


def read_status() -> SystemStatus:
    volume, muted = _volume_status()
    bluetooth = _bluetooth_status()
    wifi = _wifi_status()
    return SystemStatus(
        volume=volume,
        muted=muted,
        bluetooth=bluetooth,
        wifi=wifi,
        wifi_connection=_wifi_connection() if wifi else None,
        bluetooth_connected=_bluetooth_connected_names() if bluetooth else (),
    )


def scan_wifi_networks() -> list[WifiNetwork]:
    result = _run(
        "nmcli",
        "--terse",
        "--escape",
        "yes",
        "--fields",
        "ACTIVE,SSID,SIGNAL,SECURITY",
        "device",
        "wifi",
        "list",
        "--rescan",
        "yes",
        timeout=45,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(detail or "NetworkManager could not scan for Wi-Fi")

    strongest: dict[str, WifiNetwork] = {}
    for line in result.stdout.splitlines():
        fields = split_escaped_fields(line)
        if len(fields) != 4 or not fields[1]:
            continue
        active, ssid, signal_text, security = fields
        try:
            signal = int(signal_text)
        except ValueError:
            signal = 0
        network = WifiNetwork(
            ssid=ssid,
            signal=signal,
            security=security,
            connected=active.lower() in {"yes", "*"},
        )
        previous = strongest.get(ssid)
        if (
            previous is None
            or network.connected
            or (not previous.connected and signal > previous.signal)
        ):
            strongest[ssid] = network
    return sorted(
        strongest.values(),
        key=lambda network: (
            not network.connected,
            -network.signal,
            network.ssid.casefold(),
        ),
    )


def connect_wifi(ssid: str, password: str = "") -> str:
    if not ssid:
        raise ValueError("A Wi-Fi network name is required")
    command = ["nmcli", "--wait", "35", "device", "wifi", "connect", ssid]
    if password:
        command.extend(("password", password))
    result = _run(*command, timeout=45)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(detail or f"Could not connect to {ssid}")
    return f"Connected to {ssid}"


def disconnect_wifi() -> str:
    result = _run(
        "nmcli",
        "--terse",
        "--escape",
        "yes",
        "--fields",
        "NAME,TYPE",
        "connection",
        "show",
        "--active",
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Could not read active connections")
    connection = None
    for line in result.stdout.splitlines():
        fields = split_escaped_fields(line)
        if len(fields) == 2 and fields[1] in {"802-11-wireless", "wifi"}:
            connection = fields[0]
            break
    if connection is None:
        return "Wi-Fi is not connected"
    result = _run("nmcli", "connection", "down", "id", connection, timeout=30)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(detail or f"Could not disconnect {connection}")
    return f"Disconnected {connection}"


def _bluetooth_info(address: str) -> tuple[bool, bool]:
    result = _run("bluetoothctl", "info", address, timeout=10)
    if result.returncode != 0:
        return False, False
    return "Connected: yes" in result.stdout, "Paired: yes" in result.stdout


def scan_bluetooth_devices() -> list[BluetoothDevice]:
    # The bounded scan updates BlueZ's device cache and exits automatically.
    try:
        _run("bluetoothctl", "--timeout", "6", "scan", "on", timeout=10)
    except subprocess.TimeoutExpired:
        pass
    result = _run("bluetoothctl", "devices", timeout=15)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(detail or "Bluetooth could not list nearby devices")

    devices: list[BluetoothDevice] = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=2)
        if len(parts) != 3 or parts[0] != "Device":
            continue
        connected, paired = _bluetooth_info(parts[1])
        devices.append(
            BluetoothDevice(
                address=parts[1],
                name=parts[2],
                connected=connected,
                paired=paired,
            )
        )
    return sorted(
        devices,
        key=lambda device: (
            not device.connected,
            not device.paired,
            device.name.casefold(),
        ),
    )


def change_bluetooth_device(device: BluetoothDevice) -> str:
    if device.connected:
        result = _run("bluetoothctl", "disconnect", device.address, timeout=20)
        action = "disconnect"
        message = f"Disconnected {device.name}"
    else:
        if not device.paired:
            pair = _run(
                "bluetoothctl",
                "--timeout",
                "30",
                "pair",
                device.address,
                timeout=35,
            )
            if pair.returncode != 0:
                detail = pair.stderr.strip() or pair.stdout.strip()
                raise RuntimeError(detail or f"Could not pair {device.name}")
            _run("bluetoothctl", "trust", device.address, timeout=15)
        result = _run("bluetoothctl", "connect", device.address, timeout=30)
        action = "connect"
        message = f"Connected {device.name}"
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(detail or f"Could not {action} {device.name}")
    return message


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
    elif action == "bluetooth_toggle":
        command = (
            "bluetoothctl",
            "power",
            "off" if status.bluetooth else "on",
        )
        message = "Bluetooth turned off" if status.bluetooth else "Bluetooth turned on"
    elif action == "wifi_toggle":
        command = ("nmcli", "radio", "wifi", "off" if status.wifi else "on")
        message = "Wi-Fi turned off" if status.wifi else "Wi-Fi turned on"
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
