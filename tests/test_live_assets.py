from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NETWORK_SETUP = (
    PROJECT_ROOT
    / "packaging/cartheon/rootfs/usr/lib/cartheon/cartheon-network-setup"
)
MAIN_MODULE = PROJECT_ROOT / "src/cartheon/main.py"


class LiveAssetTests(unittest.TestCase):
    def test_password_entry_uses_supported_gtk4_api(self) -> None:
        source = NETWORK_SETUP.read_text()
        self.assertNotIn("self.password.set_placeholder_text", source)

    def test_controller_starts_after_window_creation(self) -> None:
        source = MAIN_MODULE.read_text()
        self.assertIn('app.connect_after("activate", activated)', source)
        self.assertNotIn('app.connect("activate", activated)', source)


if __name__ == "__main__":
    unittest.main()
