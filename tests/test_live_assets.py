from pathlib import Path
import unittest
from xml.etree import ElementTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NETWORK_SETUP = (
    PROJECT_ROOT
    / "packaging/cartheon/rootfs/usr/lib/cartheon/cartheon-network-setup"
)
MAIN_MODULE = PROJECT_ROOT / "src/cartheon/main.py"
OPENBOX_CONFIG = (
    PROJECT_ROOT / "packaging/cartheon/rootfs/etc/cartheon/openbox.xml"
)


class LiveAssetTests(unittest.TestCase):
    def test_password_entry_uses_supported_gtk4_api(self) -> None:
        source = NETWORK_SETUP.read_text()
        self.assertNotIn("self.password.set_placeholder_text", source)

    def test_controller_starts_after_window_creation(self) -> None:
        source = MAIN_MODULE.read_text()
        self.assertIn('app.connect_after("activate", activated)', source)
        self.assertNotIn('app.connect("activate", activated)', source)

    def test_global_settings_shortcut_is_installed(self) -> None:
        root = ElementTree.parse(OPENBOX_CONFIG).getroot()
        namespace = {"openbox": "http://openbox.org/3.4/rc"}
        bindings = root.findall(".//openbox:keybind", namespace)
        shortcut = next(binding for binding in bindings if binding.get("key") == "C-A-Escape")
        command = shortcut.find(".//openbox:command", namespace)
        self.assertEqual(command.text, "/usr/bin/cartheon-menu")


if __name__ == "__main__":
    unittest.main()
