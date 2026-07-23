import subprocess
import unittest
from unittest.mock import patch

from cartheon.system_controls import (
    BluetoothDevice,
    change_bluetooth_device,
    connect_wifi,
    disconnect_wifi,
    reconnect_paired_bluetooth_devices,
    scan_bluetooth_devices,
    scan_wifi_networks,
    split_escaped_fields,
    _scan_rssi,
)


def result(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class SystemControlTests(unittest.TestCase):
    def test_parses_colored_bluez_scan_rssi_events(self) -> None:
        output = (
            "[\u001b[0;93mCHG\u001b[0m] Device AA:BB:CC:DD:EE:01 "
            "RSSI: 0xffffffc4 (-60)\n"
            "[CHG] Device AA:BB:CC:DD:EE:02 RSSI: 0xffffffa2 (-94)\n"
        )
        self.assertEqual(
            _scan_rssi(output),
            {
                "AA:BB:CC:DD:EE:01": -60,
                "AA:BB:CC:DD:EE:02": -94,
            },
        )

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
        networks = scan_wifi_networks(force_rescan=True)
        self.assertEqual(run.call_args.kwargs["timeout"], 45)
        self.assertEqual(run.call_args.args[-1], "yes")
        self.assertEqual([network.ssid for network in networks], ["Arcade", "Guest"])
        self.assertTrue(networks[0].connected)
        self.assertFalse(networks[1].secured)

    @patch("cartheon.system_controls._run")
    def test_wifi_menu_open_uses_cached_scan_results(self, run) -> None:
        run.return_value = result()
        scan_wifi_networks()
        self.assertEqual(run.call_args.args[-1], "no")

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

    @patch("cartheon.system_controls.time.sleep")
    @patch("cartheon.system_controls.subprocess.Popen")
    @patch("cartheon.system_controls._run")
    def test_bluetooth_scan_marks_paired_and_connected_devices(
        self, run, popen, _sleep
    ) -> None:
        popen.return_value.communicate.return_value = (
            "[CHG] Device AA:BB:CC:DD:EE:01 RSSI: 0xffffffd8 (-40)\n"
            "[CHG] Device AA:BB:CC:DD:EE:03 RSSI: 0xffffffb5 (-75)\n",
            "",
        )
        run.side_effect = [
            result(
                "Device AA:BB:CC:DD:EE:01 Pixel Pad\n"
                "Device AA:BB:CC:DD:EE:02 Headphones\n"
                "Device AA:BB:CC:DD:EE:03 Arcade Stick\n"
            ),
            result("Connected: no\nPaired: no\nTrusted: no\n"),
            result("Connected: yes\nPaired: yes\nTrusted: yes\nRSSI: -81\n"),
            result("Connected: no\nPaired: yes\nTrusted: yes\n"),
        ]
        devices = scan_bluetooth_devices()
        self.assertEqual(devices[0].name, "Headphones")
        self.assertTrue(devices[0].connected)
        self.assertEqual(
            [device.name for device in devices[1:]],
            ["Pixel Pad", "Arcade Stick"],
        )
        self.assertEqual(devices[1].signal, 100)
        self.assertTrue(devices[2].paired)

    @patch("cartheon.system_controls._run")
    def test_reconnects_previously_paired_bluetooth_devices(self, run) -> None:
        run.side_effect = [
            result("Powered: yes\n"),
            result(
                "Device AA:BB:CC:DD:EE:01 Pixel Pad\n"
                "Device AA:BB:CC:DD:EE:02 Headphones\n"
            ),
            result("Connected: no\nPaired: yes\nTrusted: yes\n"),
            result(),
            result("Connected: yes\nPaired: yes\nTrusted: yes\n"),
        ]
        self.assertEqual(
            reconnect_paired_bluetooth_devices(),
            ["Pixel Pad"],
        )
        self.assertEqual(
            run.call_args_list[3].args,
            ("bluetoothctl", "connect", "AA:BB:CC:DD:EE:01"),
        )

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
