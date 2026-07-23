import unittest
from unittest import mock

from cartheon.devices import _flatten, _mounted_path, discover_exfat


class DeviceTests(unittest.TestCase):
    def test_flattens_partition_tree(self) -> None:
        devices = [
            {
                "path": "/dev/sdb",
                "children": [
                    {"path": "/dev/sdb1", "fstype": "exfat", "mountpoints": [None]}
                ],
            }
        ]
        self.assertEqual([item["path"] for item in _flatten(devices)], ["/dev/sdb", "/dev/sdb1"])

    def test_uses_first_real_mountpoint(self) -> None:
        self.assertEqual(
            _mounted_path({"mountpoints": [None, "/media/player/GAME"]}),
            __import__("pathlib").Path("/media/player/GAME"),
        )

    @mock.patch("cartheon.devices._lsblk")
    def test_discovers_exfat_ssd_partitions_without_removable_flags(
        self, lsblk: mock.Mock
    ) -> None:
        lsblk.return_value = [
            {"path": "/dev/sda1", "type": "part", "fstype": "ext4", "rm": False},
            {
                "path": "/dev/sdb1",
                "type": "part",
                "fstype": "exfat",
                "rm": False,
                "hotplug": False,
                "tran": None,
            },
            {"path": "/dev/sdc1", "type": "part", "fstype": "ext4", "rm": True},
        ]
        self.assertEqual([item["path"] for item in discover_exfat()], ["/dev/sdb1"])


if __name__ == "__main__":
    unittest.main()
