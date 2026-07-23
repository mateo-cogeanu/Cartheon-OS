"""Cartheon shell controller."""

from __future__ import annotations

import argparse
from pathlib import Path
import signal
import subprocess
import threading
import time

from .config import ConfigError, GameConfig, load_config
from .devices import Cartridge, CartridgeMonitor, DeviceError, eject_device
from .launcher import GameProcess, LaunchError, build_launch_spec
from .system_controls import (
    BluetoothDevice,
    change_bluetooth_device,
    connect_wifi,
    disconnect_wifi,
    perform,
    read_status,
    scan_bluetooth_devices,
    scan_wifi_networks,
)


class Controller:
    def __init__(self, window, manual_cartridge: Path | None = None) -> None:
        self.window = window
        self.manual_cartridge = manual_cartridge
        self.monitor: CartridgeMonitor | None = None
        self.process: GameProcess | None = None
        self.active_device: str | None = None
        self.active_cartridge: Cartridge | None = None
        self.active_config: GameConfig | None = None
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
            self.active_cartridge = cartridge
            self._generation += 1
        try:
            config = load_config(cartridge.mountpoint)
        except (ConfigError, OSError) as exc:
            self._ui(self.window.show_error, str(exc))
            return
        with self._lock:
            self.active_config = config
        self._ui(self.window.show_cartridge, config.title, config.cover)

    def play(self) -> None:
        with self._lock:
            config = self.active_config
            if config is None or self.process is not None:
                return
            self._generation += 1
            generation = self._generation
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

        # Keep the pixel boot animation only until the game has a real window.
        # As soon as Openbox manages that window, remove Cartheon instead of
        # presenting a loading page over a game that is already playable.
        boot_deadline = started + config.boot_animation_seconds
        shell_hidden = False
        while self._current(generation) and time.monotonic() < boot_deadline:
            exit_code = process.poll()
            if exit_code is not None:
                with self._lock:
                    if self.process is process:
                        self.process = None
                self._ui(
                    self.window.show_error,
                    f"The game exited during startup (code {exit_code})",
                )
                return
            if process.has_window():
                shell_hidden = True
                self._ui(self.window.hide_for_game)
                break
            time.sleep(0.1)
        if not self._current(generation):
            return
        if not shell_hidden:
            exit_code = process.poll()
            if exit_code is not None:
                with self._lock:
                    if self.process is process:
                        self.process = None
                self._ui(
                    self.window.show_error,
                    f"The game exited during startup (code {exit_code})",
                )
                return
            self._ui(self.window.show_loading, config.title)

        loading_started = time.monotonic()
        while self._current(generation):
            exit_code = process.poll()
            if exit_code is not None:
                with self._lock:
                    if self.process is process:
                        self.process = None
                if exit_code == 0:
                    self._show_cartridge()
                else:
                    self._ui(self.window.show_error, f"The game exited with code {exit_code}")
                return
            if not shell_hidden and process.has_window():
                shell_hidden = True
                self._ui(self.window.hide_for_game)
            elif not shell_hidden and time.monotonic() - loading_started >= 20:
                # Some override-redirect fullscreen games never register an
                # EWMH client window. Avoid covering them forever.
                shell_hidden = True
                self._ui(self.window.hide_for_game)
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
            self.active_cartridge = None
            self.active_config = None
            process = self.process
            self.process = None
        if process:
            process.stop()
        self._ui(self.window.show_waiting)

    def _show_cartridge(self) -> None:
        with self._lock:
            config = self.active_config
        if config is None:
            self._ui(self.window.show_waiting)
        else:
            self._ui(self.window.show_cartridge, config.title, config.cover)

    def quit_game(self) -> None:
        with self._lock:
            self._generation += 1
            process = self.process
            self.process = None
        if process is not None:
            process.stop(timeout=2)
        self._show_cartridge()

    def open_settings(self) -> bool:
        with self._lock:
            in_game = self.process is not None and self.process.poll() is None
            has_cartridge = self.active_cartridge is not None
        self._ui(self.window.show_settings, None, in_game, has_cartridge)

        def refresh() -> None:
            status = read_status()
            self._ui(self.window.update_settings, status)

        threading.Thread(target=refresh, name="settings-status", daemon=True).start()
        return True

    def settings_action(self, action: str, payload: object | None = None) -> None:
        if action == "open":
            self.open_settings()
            return
        if action == "back":
            self._ui(self.window.close_settings)
            return
        if action == "submenu_back":
            self.open_settings()
            return
        if action == "quit_game":
            threading.Thread(target=self.quit_game, name="quit-game", daemon=True).start()
            return
        if action == "eject":
            threading.Thread(target=self._safe_eject, name="safe-eject", daemon=True).start()
            return
        if action in {"wifi_open", "wifi_refresh"}:
            threading.Thread(
                target=self._load_wifi_menu,
                args=(action == "wifi_refresh",),
                name="wifi-scan",
                daemon=True,
            ).start()
            return
        if action in {"bluetooth_open", "bluetooth_refresh"}:
            threading.Thread(
                target=self._load_bluetooth_menu,
                name="bluetooth-scan",
                daemon=True,
            ).start()
            return
        if action == "wifi_connect":
            if (
                not isinstance(payload, tuple)
                or len(payload) != 2
                or not all(isinstance(value, str) for value in payload)
            ):
                self._ui(self.window.settings_message, "Invalid Wi-Fi selection", True)
                return
            threading.Thread(
                target=self._change_wifi_connection,
                args=(payload[0], payload[1]),
                name="wifi-connect",
                daemon=True,
            ).start()
            return
        if action == "wifi_disconnect":
            threading.Thread(
                target=self._disconnect_wifi,
                name="wifi-disconnect",
                daemon=True,
            ).start()
            return
        if action == "bluetooth_device":
            if not isinstance(payload, BluetoothDevice):
                self._ui(self.window.settings_message, "Invalid Bluetooth selection", True)
                return
            threading.Thread(
                target=self._change_bluetooth_device,
                args=(payload,),
                name="bluetooth-device",
                daemon=True,
            ).start()
            return
        if action in {"wifi_toggle", "bluetooth_toggle"}:
            threading.Thread(
                target=self._toggle_radio,
                args=(action,),
                name=f"setting-{action}",
                daemon=True,
            ).start()
            return

        def change_setting() -> None:
            try:
                message = perform(action)
                status = read_status()
            except (RuntimeError, ValueError) as exc:
                self._ui(self.window.settings_message, str(exc), True)
                return
            self._ui(self.window.settings_message, message, False)
            self._ui(self.window.update_settings, status)

        threading.Thread(
            target=change_setting,
            name=f"setting-{action}",
            daemon=True,
        ).start()

    def _load_wifi_menu(self, force_rescan: bool = False, message: str = "") -> None:
        status = read_status()
        self._ui(self.window.show_wifi_loading, status)
        if not status.wifi:
            self._ui(self.window.show_wifi_menu, [], status, message, False)
            return
        try:
            networks = scan_wifi_networks(force_rescan=force_rescan)
            status = read_status()
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            self._ui(
                self.window.show_wifi_menu,
                [],
                read_status(),
                str(exc),
                True,
            )
            return
        self._ui(self.window.show_wifi_menu, networks, status, message, False)

    def _load_bluetooth_menu(self, message: str = "") -> None:
        status = read_status()
        self._ui(self.window.show_bluetooth_loading, status)
        if not status.bluetooth:
            self._ui(self.window.show_bluetooth_menu, [], status, message, False)
            return
        try:
            devices = scan_bluetooth_devices()
            status = read_status()
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            self._ui(
                self.window.show_bluetooth_menu,
                [],
                read_status(),
                str(exc),
                True,
            )
            return
        self._ui(self.window.show_bluetooth_menu, devices, status, message, False)

    def _change_wifi_connection(self, ssid: str, password: str) -> None:
        try:
            message = connect_wifi(ssid, password)
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            self._ui(
                self.window.show_wifi_menu,
                [],
                read_status(),
                str(exc),
                True,
            )
            return
        self._load_wifi_menu(message=message)

    def _disconnect_wifi(self) -> None:
        try:
            message = disconnect_wifi()
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            self._ui(
                self.window.show_wifi_menu,
                [],
                read_status(),
                str(exc),
                True,
            )
            return
        self._load_wifi_menu(message=message)

    def _change_bluetooth_device(self, device: BluetoothDevice) -> None:
        try:
            message = change_bluetooth_device(device)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            self._ui(
                self.window.show_bluetooth_menu,
                [],
                read_status(),
                str(exc),
                True,
            )
            return
        self._load_bluetooth_menu(message)

    def _toggle_radio(self, action: str) -> None:
        try:
            message = perform(action)
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            if action == "wifi_toggle":
                self._ui(
                    self.window.show_wifi_menu,
                    [],
                    read_status(),
                    str(exc),
                    True,
                )
            else:
                self._ui(
                    self.window.show_bluetooth_menu,
                    [],
                    read_status(),
                    str(exc),
                    True,
                )
            return
        if action == "wifi_toggle":
            self._load_wifi_menu(message=message)
        else:
            self._load_bluetooth_menu(message)

    def _safe_eject(self) -> None:
        with self._lock:
            cartridge = self.active_cartridge
            if self.process is not None:
                self._ui(
                    self.window.settings_message,
                    "Quit the game before ejecting its cartridge.",
                    True,
                )
                return
        if cartridge is None:
            return
        try:
            eject_device(cartridge)
        except DeviceError as exc:
            self._ui(self.window.settings_message, str(exc), True)
            return
        with self._lock:
            self._generation += 1
            self.active_device = None
            self.active_cartridge = None
            self.active_config = None
        self._ui(self.window.show_waiting, "Cartridge safely ejected")


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
        application.window.set_callbacks(controller.play, controller.settings_action)
        controller_holder.append(controller)
        controller.start()
        from gi.repository import GLib

        GLib.unix_signal_add(
            GLib.PRIORITY_DEFAULT,
            signal.SIGUSR1,
            controller.open_settings,
        )

    def shutdown(_application: CartheonApplication) -> None:
        if controller_holder:
            controller_holder[0].stop()

    # Run after CartheonApplication.do_activate() has created and presented the
    # window. A normal signal handler runs before the class handler on installed
    # systems, leaving the waiting screen visible but never starting detection.
    app.connect_after("activate", activated)
    app.connect("shutdown", shutdown)
    return app.run(gtk_args)


if __name__ == "__main__":
    raise SystemExit(main())
