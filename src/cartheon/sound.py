"""Tiny original 8-bit sounds synthesized without bundled binary assets."""

from __future__ import annotations

from pathlib import Path
import math
import os
import shutil
import struct
import subprocess
import wave


SAMPLE_RATE = 44_100
JINGLE = (
    (392.00, 0.09),
    (523.25, 0.09),
    (659.25, 0.09),
    (783.99, 0.15),
    (0.0, 0.035),
    (987.77, 0.08),
    (739.99, 0.07),
    (1174.66, 0.15),
)


def render_cartridge_boot_sound(path: Path) -> None:
    """Render a short square-wave arpeggio with a deliberately silly chirp."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    phase = 0.0
    for frequency, duration in JINGLE:
        frame_count = round(SAMPLE_RATE * duration)
        for index in range(frame_count):
            if frequency == 0:
                sample = 0.0
            else:
                # A tiny pitch wobble on the last half gives the boot chirp a
                # playful cartridge-console character.
                wobble = 1.0 + 0.012 * math.sin(index / SAMPLE_RATE * math.tau * 18)
                phase = (phase + frequency * wobble / SAMPLE_RATE) % 1.0
                square = 1.0 if phase < 0.5 else -1.0
                attack = min(1.0, index / max(1, SAMPLE_RATE * 0.004))
                release = min(
                    1.0,
                    (frame_count - index) / max(1, SAMPLE_RATE * 0.018),
                )
                sample = square * 0.16 * attack * release
            frames.extend(struct.pack("<h", round(sample * 32767)))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(frames)


def play_cartridge_boot_sound() -> bool:
    player = shutil.which("pw-play")
    if player is None:
        return False
    cache_home = Path(
        os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")
    )
    sound = cache_home / "cartheon" / "cartridge-boot.wav"
    try:
        if not sound.is_file():
            render_cartridge_boot_sound(sound)
        subprocess.Popen(
            (player, str(sound)),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except (OSError, wave.Error):
        return False
    return True
