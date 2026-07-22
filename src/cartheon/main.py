"""Cartheon shell controller."""

from __future__ import annotations

import argparse
from pathlib import Path
import threading
import time

from .config import ConfigError, GameConfig, load_config
from .devices import Cartridge, CartridgeMonitor
from .launcher import GameProcess, LaunchError, build_launch_spec


class Controller:
    def __init__(self, window, manual_cartridge: Path | None = None) -> None:
        self.window = window
        self.manual_cartridge = manual_cartridge
        self.monitor: CartridgeMonitor | None = None
        self.process: GameProcess | None = None
        self.active_device: str | None = None
        self._generation = 0
        self._lock = threading.Lock()

    @staticmethod
    def _ui(callback, *args) -> None:
        from .ui import on_ui

        on_ui(callback, *args)

    def start(self) -> None:
        if self.manual_cartridge is not None:
            cartridge = Cartridge("manual", self.manual_cartridge, "manual")
            threading.Thread(target=self._insert, args=(cartridge,), daemon=True).start()
            return
        self.monitor = CartridgeMonitor(self._insert, self._remove, self._device_error)
        self.monitor.start()

    def stop(self) -> None:
        if self.monitor:
            self.monitor.stop()
        with self._lock:
            self._generation += 1
            process = self.process
            self.process = None
        if process:
            process.stop()

    def _device_error(self, message: str) -> None:
        # Discovery errors should be visible but should not kill the monitor.
        if self.active_device is None:
            self._ui(self.window.show_error, message)

    def _insert(self, cartridge: Cartridge) -> None:
        with self._lock:
            if self.active_device is not None:
                return
            self.active_device = cartridge.device
            self._generation += 1
            generation = self._generation
        try:
            config = load_config(cartridge.mountpoint)
        except (ConfigError, OSError) as exc:
            self._ui(self.window.show_error, str(exc))
            return
        self._ui(self.window.show_booting, config.title)
        threading.Thread(
            target=self._launch_and_watch,
            args=(config, generation),
            name="game-launcher",
            daemon=True,
        ).start()

    def _launch_and_watch(self, config: GameConfig, generation: int) -> None:
        started = time.monotonic()
        try:
            spec = build_launch_spec(config)
            process = GameProcess.start(spec)
        except (LaunchError, OSError) as exc:
            self._ui(self.window.show_error, str(exc))
            return
        with self._lock:
            if generation != self._generation:
                process.stop()
                return
            self.process = process

        remaining = config.boot_animation_seconds - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)
        if not self._current(generation):
            return
        exit_code = process.poll()
        if exit_code is not None:
            self._ui(self.window.show_error, f"The game exited during startup (code {exit_code})")
            return
        self._ui(self.window.show_loading, config.title)

        loading_started = time.monotonic()
        running_shown = False
        while self._current(generation):
            exit_code = process.poll()
            if exit_code is not None:
                with self._lock:
                    if self.process is process:
                        self.process = None
                if exit_code == 0:
                    self._ui(
                        self.window.show_waiting,
                        "Game closed — remove and reinsert the cartridge to play again",
                    )
                else:
                    self._ui(self.window.show_error, f"The game exited with code {exit_code}")
                return
            if not running_shown and time.monotonic() - loading_started >= 8:
                running_shown = True
                self._ui(self.window.show_running, config.title)
            time.sleep(0.5)

    def _current(self, generation: int) -> bool:
        with self._lock:
            return generation == self._generation

    def _remove(self, cartridge: Cartridge) -> None:
        with self._lock:
            if cartridge.device != self.active_device:
                return
            self._generation += 1
            self.active_device = None
            process = self.process
            self.process = None
        if process:
            process.stop()
        self._ui(self.window.show_waiting)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--cartridge", type=Path, help="developer mode: use a directory as a cartridge")
    args, gtk_args = parser.parse_known_args(argv)

    from .ui import CartheonApplication

    app = CartheonApplication()
    controller_holder: list[Controller] = []

    def activated(application: CartheonApplication) -> None:
        if controller_holder:
            return
        assert application.window is not None
        controller = Controller(application.window, args.cartridge)
        controller_holder.append(controller)
        controller.start()

    def shutdown(_application: CartheonApplication) -> None:
        if controller_holder:
            controller_holder[0].stop()

    app.connect("activate", activated)
    app.connect("shutdown", shutdown)
    return app.run(gtk_args)


if __name__ == "__main__":
    raise SystemExit(main())
