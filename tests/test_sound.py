from pathlib import Path
import tempfile
import unittest
from unittest import mock
import wave

from cartheon.sound import (
    SAMPLE_RATE,
    play_cartridge_boot_sound,
    render_cartridge_boot_sound,
)


class SoundTests(unittest.TestCase):
    def test_renders_a_short_mono_cartridge_jingle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "boot.wav"
            render_cartridge_boot_sound(target)
            with wave.open(str(target), "rb") as sound:
                self.assertEqual(sound.getnchannels(), 1)
                self.assertEqual(sound.getframerate(), SAMPLE_RATE)
                self.assertGreater(sound.getnframes(), SAMPLE_RATE // 2)
                self.assertLess(sound.getnframes(), SAMPLE_RATE * 2)

    @mock.patch("cartheon.sound.subprocess.Popen")
    @mock.patch("cartheon.sound.shutil.which", return_value="/usr/bin/pw-play")
    def test_plays_the_cached_jingle_without_blocking(
        self, _which: mock.Mock, popen: mock.Mock
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(
                "os.environ",
                {"XDG_CACHE_HOME": temporary},
                clear=False,
            ):
                self.assertTrue(play_cartridge_boot_sound())
                sound = Path(temporary) / "cartheon/cartridge-boot.wav"
                self.assertTrue(sound.is_file())
        self.assertEqual(popen.call_args.args[0][0], "/usr/bin/pw-play")
        self.assertTrue(popen.call_args.kwargs["start_new_session"])


if __name__ == "__main__":
    unittest.main()
