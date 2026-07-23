"""Non-grabbing Linux gamepad input for the Cartheon appliance shell."""

from __future__ import annotations

import select
import threading
import time
from typing import Callable


EV_KEY = 0x01
EV_ABS = 0x03

ABS_X = 0x00
ABS_Y = 0x01
ABS_HAT0X = 0x10
ABS_HAT0Y = 0x11

BTN_SOUTH = 0x130
BTN_EAST = 0x131
BTN_SELECT = 0x13A
BTN_START = 0x13B
BTN_MODE = 0x13C
BTN_DPAD_UP = 0x220
BTN_DPAD_DOWN = 0x221
BTN_DPAD_LEFT = 0x222
BTN_DPAD_RIGHT = 0x223


class GamepadEventMapper:
    """Translate Linux input events into Cartheon's navigation vocabulary."""

    _BUTTON_ACTIONS = {
        BTN_DPAD_UP: "up",
        BTN_DPAD_DOWN: "down",
        BTN_DPAD_LEFT: "left",
        BTN_DPAD_RIGHT: "right",
        BTN_SOUTH: "accept",
        BTN_EAST: "back",
    }

    def __init__(self) -> None:
        self._held: set[int] = set()
        self._axis_direction: dict[int, int] = {}
        self._menu_chord_active = False

    def key(self, code: int, value: int) -> tuple[str, ...]:
        if value:
            self._held.add(code)
        else:
            self._held.discard(code)

        chord = BTN_START in self._held and BTN_SELECT in self._held
        if chord and not self._menu_chord_active:
            self._menu_chord_active = True
            return ("menu",)
        if not chord:
            self._menu_chord_active = False

        if value != 1:
            return ()
        if code == BTN_MODE:
            return ("menu",)
        action = self._BUTTON_ACTIONS.get(code)
        return (action,) if action is not None else ()

    def absolute(
        self,
        code: int,
        value: int,
        minimum: int,
        maximum: int,
    ) -> tuple[str, ...]:
        if code in {ABS_HAT0X, ABS_HAT0Y}:
            direction = -1 if value < 0 else 1 if value > 0 else 0
        elif code in {ABS_X, ABS_Y} and maximum > minimum:
            midpoint = (minimum + maximum) / 2
            deadzone = (maximum - minimum) * 0.28
            direction = -1 if value < midpoint - deadzone else 1 if value > midpoint + deadzone else 0
        else:
            return ()

        previous = self._axis_direction.get(code, 0)
        self._axis_direction[code] = direction
        if direction == 0 or direction == previous:
            return ()
        if code in {ABS_X, ABS_HAT0X}:
            return ("left" if direction < 0 else "right",)
        return ("up" if direction < 0 else "down",)


def _gamepad_devices():
    from evdev import InputDevice, list_devices

    devices = []
    for path in list_devices():
        try:
            device = InputDevice(path)
            keys = device.capabilities().get(EV_KEY, [])
        except OSError:
            continue
        if BTN_SOUTH in keys:
            devices.append(device)
        else:
            device.close()
    return devices


def connected_gamepad_names() -> tuple[str, ...]:
    try:
        devices = _gamepad_devices()
    except (ImportError, OSError):
        return ()
    try:
        return tuple(sorted((device.name or device.path) for device in devices))
    finally:
        for device in devices:
            device.close()


class GamepadMonitor:
    """Watch evdev devices without grabbing them, so games still receive input."""

    def __init__(
        self,
        on_action: Callable[[str], None],
        rescan_interval: float = 2.0,
    ) -> None:
        self.on_action = on_action
        self.rescan_interval = rescan_interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._devices: dict[str, tuple[object, GamepadEventMapper]] = {}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="gamepad-monitor",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=3)
        self._close_all()

    def _close_all(self) -> None:
        for device, _mapper in self._devices.values():
            try:
                device.close()
            except OSError:
                pass
        self._devices.clear()

    def _rescan(self) -> None:
        try:
            found = {device.path: device for device in _gamepad_devices()}
        except (ImportError, OSError):
            return
        for path in tuple(self._devices):
            if path not in found:
                device, _mapper = self._devices.pop(path)
                device.close()
        for path, device in found.items():
            if path in self._devices:
                device.close()
            else:
                self._devices[path] = (device, GamepadEventMapper())

    def _dispatch_event(self, device, mapper: GamepadEventMapper, event) -> None:
        actions: tuple[str, ...] = ()
        if event.type == EV_KEY:
            actions = mapper.key(event.code, event.value)
        elif event.type == EV_ABS:
            try:
                axis = device.absinfo(event.code)
            except (KeyError, OSError):
                return
            actions = mapper.absolute(event.code, event.value, axis.min, axis.max)
        for action in actions:
            self.on_action(action)

    def _run(self) -> None:
        next_rescan = 0.0
        while not self._stop.is_set():
            now = time.monotonic()
            if now >= next_rescan:
                self._rescan()
                next_rescan = now + self.rescan_interval
            if not self._devices:
                self._stop.wait(min(self.rescan_interval, 0.5))
                continue
            devices = [device for device, _mapper in self._devices.values()]
            try:
                readable, _writable, _errors = select.select(devices, [], [], 0.5)
            except (OSError, ValueError):
                self._close_all()
                continue
            for device in readable:
                entry = self._devices.get(device.path)
                if entry is None:
                    continue
                try:
                    events = device.read()
                except OSError:
                    device.close()
                    self._devices.pop(device.path, None)
                    continue
                for event in events:
                    self._dispatch_event(device, entry[1], event)
        self._close_all()
