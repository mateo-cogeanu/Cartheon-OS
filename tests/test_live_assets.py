from pathlib import Path
import unittest
from xml.etree import ElementTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NETWORK_SETUP = (
    PROJECT_ROOT
    / "packaging/cartheon/rootfs/usr/lib/cartheon/cartheon-network-setup"
)
MAIN_MODULE = PROJECT_ROOT / "src/cartheon/main.py"
UI_MODULE = PROJECT_ROOT / "src/cartheon/ui.py"
OPENBOX_CONFIG = (
    PROJECT_ROOT / "packaging/cartheon/rootfs/etc/cartheon/openbox.xml"
)
PACKAGE_CONTROL = PROJECT_ROOT / "packaging/cartheon/DEBIAN/control"


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

    def test_cartheon_shell_never_shows_a_mouse_cursor(self) -> None:
        source = UI_MODULE.read_text()
        self.assertIn('set_cursor_from_name("none")', source)
        self.assertNotIn('set_cursor_from_name("default")', source)

    def test_waiting_screen_rings_keep_spinning(self) -> None:
        source = UI_MODULE.read_text()
        waiting = source.split("def show_waiting", 1)[1].split(
            "def show_cartridge", 1
        )[0]
        self.assertIn("self.waiting_rings.set_active(True)", waiting)
        self.assertGreaterEqual(
            source.count("self.waiting_rings.set_active(True)"),
            2,
        )

    def test_wireless_radios_open_device_menus(self) -> None:
        source = UI_MODULE.read_text()
        self.assertIn('"WI-FI SETTINGS  >"', source)
        self.assertIn('"BLUETOOTH SETTINGS  >"', source)
        self.assertIn('"wifi_password"', source)

    def test_shell_reasserts_fullscreen_after_game_return(self) -> None:
        source = UI_MODULE.read_text()
        show_base = source.split("def _show_base", 1)[1].split(
            "def show_waiting", 1
        )[0]
        close_settings = source.split("def close_settings", 1)[1].split(
            "class CartheonApplication", 1
        )[0]
        self.assertIn("self.fullscreen()", show_base)
        self.assertIn("GLib.idle_add(self.fullscreen)", show_base)
        self.assertIn("self.fullscreen()", close_settings)

    def test_shell_uses_true_pixel_font_and_ssd_centerpiece(self) -> None:
        source = UI_MODULE.read_text()
        self.assertIn('"ProggyTinyTT"', source)
        self.assertIn("def ssd_path", source)
        self.assertIn("ssd_glyphs", source)
        self.assertIn("stacked from top to bottom: S, S, D", source)
        self.assertIn("SSD's SATA connector", source)

    def test_game_window_detector_is_a_runtime_dependency(self) -> None:
        control = PACKAGE_CONTROL.read_text()
        depends = next(
            line.removeprefix("Depends: ").split(", ")
            for line in control.splitlines()
            if line.startswith("Depends: ")
        )
        self.assertIn("x11-utils", depends)
        self.assertIn("wmctrl", depends)
        self.assertIn("fonts-proggy", depends)
        self.assertIn("python3-evdev", depends)

    def test_controller_navigation_and_menu_chord_are_wired(self) -> None:
        main = MAIN_MODULE.read_text()
        ui = UI_MODULE.read_text()
        self.assertIn("GamepadMonitor(self.gamepad_action)", main)
        self.assertIn("self.gamepad.start()", main)
        self.assertIn("def handle_navigation", ui)
        self.assertIn("[ HOME / ESC ] SETTINGS", ui)


if __name__ == "__main__":
    unittest.main()
