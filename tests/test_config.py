from pathlib import Path
import tempfile
import unittest

from cartheon.config import ConfigError, load_config


VALID_CONFIG = """
version = 1

[game]
title = "Test Game"
executable = "Game/game.bin"
runtime = "native"
working_directory = "Game"
arguments = ["--fullscreen", "player one"]

[game.environment]
TEST_MODE = true

[display]
boot_animation_seconds = 2.5
"""


class ConfigTests(unittest.TestCase):
    def make_cartridge(self, config: str = VALID_CONFIG) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "Game").mkdir()
        (root / "Game/game.bin").write_bytes(b"game")
        (root / "game.cfg").write_text(config)
        return root

    def test_loads_valid_manifest(self) -> None:
        result = load_config(self.make_cartridge())
        self.assertEqual(result.title, "Test Game")
        self.assertEqual(result.runtime, "native")
        self.assertEqual(result.arguments, ("--fullscreen", "player one"))
        self.assertEqual(result.environment, {"TEST_MODE": "true"})
        self.assertEqual(result.boot_animation_seconds, 2.5)

    def test_rejects_parent_traversal(self) -> None:
        config = VALID_CONFIG.replace('"Game/game.bin"', '"../game.bin"')
        with self.assertRaisesRegex(ConfigError, "inside the cartridge"):
            load_config(self.make_cartridge(config))

    def test_rejects_symlink_escape(self) -> None:
        root = self.make_cartridge()
        outside_temp = tempfile.TemporaryDirectory()
        self.addCleanup(outside_temp.cleanup)
        outside = Path(outside_temp.name) / "outside-game"
        outside.write_bytes(b"outside")
        (root / "Game/game.bin").unlink()
        (root / "Game/game.bin").symlink_to(outside)
        with self.assertRaisesRegex(ConfigError, "outside the cartridge"):
            load_config(root)

    def test_rejects_loader_injection(self) -> None:
        config = VALID_CONFIG.replace("TEST_MODE = true", 'LD_PRELOAD = "bad.so"')
        with self.assertRaisesRegex(ConfigError, "unsafe name"):
            load_config(self.make_cartridge(config))

    def test_requires_supported_version(self) -> None:
        config = VALID_CONFIG.replace("version = 1", "version = 2")
        with self.assertRaisesRegex(ConfigError, "version = 1"):
            load_config(self.make_cartridge(config))

    def test_rejects_unknown_field(self) -> None:
        config = VALID_CONFIG.replace('title = "Test Game"', 'title = "Test Game"\ncommand = "bad"')
        with self.assertRaisesRegex(ConfigError, "unknown game field: command"):
            load_config(self.make_cartridge(config))

    def test_rejects_missing_executable(self) -> None:
        root = self.make_cartridge()
        (root / "Game/game.bin").unlink()
        with self.assertRaisesRegex(ConfigError, "does not exist"):
            load_config(root)


if __name__ == "__main__":
    unittest.main()
