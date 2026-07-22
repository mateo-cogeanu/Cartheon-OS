from pathlib import Path
import tempfile
import unittest
from unittest import mock

from cartheon.config import load_config
from cartheon.launcher import build_launch_spec


def manifest(runtime: str, prefix: str = "local") -> str:
    return f"""
version = 1
[game]
title = "Launcher Test"
executable = "Bin/game.exe"
runtime = "{runtime}"
working_directory = "Bin"
arguments = ["--safe", "two words"]
[game.environment]
GAME_SETTING = "value"
[wine]
prefix = "{prefix}"
ntsync = true
"""


class LauncherTests(unittest.TestCase):
    def cartridge(self, runtime: str, prefix: str = "local") -> tuple[Path, object]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "Bin").mkdir()
        (root / "Bin/game.exe").write_bytes(b"binary")
        (root / "game.cfg").write_text(manifest(runtime, prefix))
        config = load_config(root)
        return config.root, config

    @mock.patch("cartheon.launcher.shutil.which", return_value=None)
    def test_native_command_is_not_a_shell_string(self, _which: mock.Mock) -> None:
        root, config = self.cartridge("native")
        spec = build_launch_spec(config)
        self.assertEqual(
            spec.argv,
            (str(root / "Bin/game.exe"), "--safe", "two words"),
        )
        self.assertEqual(spec.cwd, root / "Bin")

    @mock.patch(
        "cartheon.launcher.shutil.which",
        side_effect=lambda name: "/usr/bin/wine" if name == "wine" else None,
    )
    def test_wine_uses_local_prefix_and_ntsync(self, _which: mock.Mock) -> None:
        _root, config = self.cartridge("wine")
        with tempfile.TemporaryDirectory() as data:
            spec = build_launch_spec(config, Path(data))
            self.assertEqual(spec.argv[0], "/usr/bin/wine")
            self.assertEqual(spec.argv[-2:], ("--safe", "two words"))
            self.assertEqual(spec.env["WINE_NTSYNC"], "1")
            self.assertTrue(spec.env["WINEPREFIX"].startswith(data))

    @mock.patch(
        "cartheon.launcher.shutil.which",
        side_effect=lambda name: "/usr/bin/wine" if name == "wine" else None,
    )
    def test_wine_can_keep_prefix_on_cartridge(self, _which: mock.Mock) -> None:
        root, config = self.cartridge("wine", "cartridge")
        spec = build_launch_spec(config)
        self.assertEqual(spec.env["WINEPREFIX"], str(root / ".cartheon/wineprefix"))

    @mock.patch(
        "cartheon.launcher.shutil.which",
        side_effect=lambda name: "/usr/bin/gamemoderun" if name == "gamemoderun" else None,
    )
    def test_native_game_uses_gamemode_when_available(self, _which: mock.Mock) -> None:
        root, config = self.cartridge("native")
        spec = build_launch_spec(config)
        self.assertEqual(spec.argv[:2], ("/usr/bin/gamemoderun", str(root / "Bin/game.exe")))


if __name__ == "__main__":
    unittest.main()
