import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from cartheon.config import load_config
from cartheon.launcher import GameProcess, LaunchSpec, build_launch_spec


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
        side_effect=lambda name: (
            f"/usr/bin/{name}" if name in {"wine", "wineserver"} else None
        ),
    )
    def test_wine_uses_local_prefix_and_ntsync(self, _which: mock.Mock) -> None:
        _root, config = self.cartridge("wine")
        with tempfile.TemporaryDirectory() as data:
            spec = build_launch_spec(config, Path(data))
            self.assertEqual(spec.argv[0], "/usr/bin/wine")
            self.assertEqual(spec.wine_server, "/usr/bin/wineserver")
            self.assertEqual(spec.argv[-2:], ("--safe", "two words"))
            self.assertEqual(spec.env["WINE_NTSYNC"], "1")
            self.assertTrue(spec.env["WINEPREFIX"].startswith(data))

    @mock.patch(
        "cartheon.launcher.shutil.which",
        side_effect=lambda name: (
            f"/usr/bin/{name}" if name in {"wine", "wineserver"} else None
        ),
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

    @mock.patch("cartheon.launcher.subprocess.run")
    def test_detects_a_new_game_window(self, run: mock.Mock) -> None:
        run.return_value = subprocess.CompletedProcess(
            [],
            0,
            "_NET_CLIENT_LIST(WINDOW): window id # 0x200001, 0x40000a\n",
            "",
        )
        process = mock.Mock()
        spec = LaunchSpec(("game",), Path("/tmp"), {})
        game = GameProcess(process, spec, {"0x200001"})
        self.assertTrue(game.has_window())

    @mock.patch("cartheon.launcher.subprocess.Popen")
    def test_wine_launcher_exit_waits_for_the_complete_prefix(
        self, popen: mock.Mock
    ) -> None:
        primary = mock.Mock()
        primary.poll.return_value = 0
        waiter = mock.Mock()
        waiter.poll.return_value = None
        popen.return_value = waiter
        spec = LaunchSpec(
            ("wine", "game.exe"),
            Path("/tmp"),
            {"WINEPREFIX": "/tmp/prefix"},
            wine_server="/usr/bin/wineserver",
        )
        game = GameProcess(primary, spec, set())
        self.assertIsNone(game.poll())
        popen.assert_called_once()
        self.assertEqual(popen.call_args.args[0], ("/usr/bin/wineserver", "-w"))

    @mock.patch("cartheon.launcher.os.killpg")
    @mock.patch("cartheon.launcher.subprocess.run")
    def test_quit_stops_the_entire_wine_prefix(
        self, run: mock.Mock, _killpg: mock.Mock
    ) -> None:
        primary = mock.Mock()
        primary.pid = 42
        primary.poll.return_value = None
        spec = LaunchSpec(
            ("wine", "game.exe"),
            Path("/tmp"),
            {"WINEPREFIX": "/tmp/prefix"},
            wine_server="/usr/bin/wineserver",
        )
        game = GameProcess(primary, spec, set())
        game.stop()
        self.assertEqual(run.call_args.args[0], ("/usr/bin/wineserver", "-k"))


if __name__ == "__main__":
    unittest.main()
