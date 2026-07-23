import subprocess
import unittest
from unittest.mock import patch

from cartheon.system_controls import (
    BluetoothDevice,
    change_bluetooth_device,
    connect_wifi,
    disconnect_wifi,
    scan_bluetooth_devices,
    scan_wifi_networks,
    split_escaped_fields,
)


def result(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class SystemControlTests(unittest.TestCase):
    def test_split_nmcli_fields_retains_colons(self) -> None:
        self.assertEqual(
            split_escaped_fields(r"yes:Arcade\: Upstairs:82:WPA2"),
            ["yes", "Arcade: Upstairs", "82", "WPA2"],
        )

    @patch("cartheon.system_controls._run")
    def test_wifi_scan_deduplicates_and_prioritizes_connected(self, run) -> None:
        run.return_value = result(
            "no:Arcade:45:WPA2\nyes:Arcade:28:WPA2\nno:Guest:72:--\n"
        )
        networks = scan_wifi_networks()
        self.assertEqual([network.ssid for network in networks], ["Arcade", "Guest"])
        self.assertTrue(networks[0].connected)
        self.assertFalse(networks[1].secured)

    @patch("cartheon.system_controls._run")
    def test_wifi_connect_passes_password_without_a_shell(self, run) -> None:
        run.return_value = result()
        self.assertEqual(connect_wifi("Arcade", "secret"), "Connected to Arcade")
        run.assert_called_once_with(
            "nmcli",
            "--wait",
            "35",
            "device",
            "wifi",
            "connect",
            "Arcade",
            "password",
            "secret",
            timeout=45,
        )

    @patch("cartheon.system_controls._run")
    def test_wifi_disconnect_uses_active_wireless_profile(self, run) -> None:
        run.side_effect = [
            result("Ethernet:802-3-ethernet\nArcade:802-11-wireless\n"),
            result(),
        ]
        self.assertEqual(disconnect_wifi(), "Disconnected Arcade")
        self.assertEqual(
            run.call_args_list[1].args,
            ("nmcli", "connection", "down", "id", "Arcade"),
        )

    @patch("cartheon.system_controls._run")
    def test_bluetooth_scan_marks_paired_and_connected_devices(self, run) -> None:
        run.side_effect = [
            result(),
            result(
                "Device AA:BB:CC:DD:EE:01 Pixel Pad\n"
                "Device AA:BB:CC:DD:EE:02 Headphones\n"
            ),
            result("Connected: no\nPaired: no\n"),
            result("Connected: yes\nPaired: yes\n"),
        ]
        devices = scan_bluetooth_devices()
        self.assertEqual(devices[0].name, "Headphones")
        self.assertTrue(devices[0].connected)
        self.assertFalse(devices[1].paired)

    @patch("cartheon.system_controls._run")
    def test_new_bluetooth_device_is_paired_trusted_and_connected(self, run) -> None:
        run.return_value = result()
        device = BluetoothDevice(
            address="AA:BB:CC:DD:EE:FF",
            name="Pixel Pad",
            connected=False,
            paired=False,
        )
        self.assertEqual(change_bluetooth_device(device), "Connected Pixel Pad")
        commands = [call.args[:2] for call in run.call_args_list]
        self.assertEqual(
            commands,
            [
                ("bluetoothctl", "--timeout"),
                ("bluetoothctl", "trust"),
                ("bluetoothctl", "connect"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
