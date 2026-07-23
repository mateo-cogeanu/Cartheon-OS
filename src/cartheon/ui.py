"""Pixel-styled GTK 4 shell for Cartheon OS."""

from __future__ import annotations

import math
from pathlib import Path
import time
from typing import Callable

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from .system_controls import SystemStatus


CSS = b"""
window {
  background: #070912;
  color: #f5f7ff;
  font-family: monospace;
}
.screen-title {
  font-size: 42px;
  font-weight: 900;
}
.game-title {
  font-size: 34px;
  font-weight: 900;
}
.message {
  color: #bac1d9;
  font-size: 18px;
}
.detail {
  color: #717b9e;
  font-size: 14px;
}
.error {
  color: #ff668c;
}
.cover-frame {
  background: #11172b;
  border: 6px solid #35406d;
  border-radius: 16px;
  padding: 6px;
}
.play-button {
  min-width: 250px;
  min-height: 58px;
  border: 4px solid #baffc9;
  border-radius: 12px;
  background: #24b85a;
  color: #06130b;
  font-size: 25px;
  font-weight: 900;
  box-shadow: 0 7px #116b34;
}
.play-button:hover, .play-button:focus {
  background: #59e681;
  border-color: #ffffff;
}
.settings-panel {
  background: #0e1427;
  border: 6px solid #8e9cff;
  border-radius: 10px;
  padding: 24px;
}
.settings-title {
  color: #cbd1ff;
  font-size: 36px;
  font-weight: 900;
}
.settings-button {
  min-width: 560px;
  min-height: 46px;
  border: 3px solid #35406d;
  border-radius: 6px;
  background: #151d36;
  color: #e9ebff;
  font-size: 19px;
  font-weight: 800;
}
.settings-button:hover, .settings-button:focus {
  background: #313d70;
  border-color: #f4f5ff;
}
.danger-button {
  border-color: #9c3650;
  color: #ffb3c5;
}
.eject-button {
  border-color: #8f7f35;
  color: #fff0a6;
}
"""


class PixelRings(Gtk.DrawingArea):
    """Three cut rings rendered as chunky pixels instead of smooth arcs."""

    def __init__(self, size: int = 190) -> None:
        super().__init__()
        self.set_content_width(size)
        self.set_content_height(size)
        self._started = time.monotonic()
        self._active = False
        self.set_draw_func(self._draw)
        self.add_tick_callback(self._tick)

    def set_active(self, active: bool) -> None:
        self._active = active
        self._started = time.monotonic()
        self.queue_draw()

    def _tick(self, _widget: Gtk.Widget, _clock: Gdk.FrameClock) -> bool:
        if self._active:
            self.queue_draw()
        return True

    def _draw(self, _area: Gtk.DrawingArea, context, width: int, height: int) -> None:
        cx, cy = width / 2, height / 2
        elapsed = time.monotonic() - self._started
        phase = math.floor(elapsed * 12) / 12 * 1.7 if self._active else 0.0
        pixel = max(4, round(min(width, height) / 38))
        colors = ((0.36, 0.49, 1.0), (0.52, 0.40, 1.0), (0.25, 0.78, 0.92))

        for ring, radius in enumerate((42, 59, 77)):
            context.set_source_rgb(*colors[ring])
            direction = 1 if ring % 2 == 0 else -1
            for step in range(72):
                angle = step / 72 * math.tau + phase * direction + ring * 0.8
                segment = (step + ring * 8) % 36
                if segment in range(0, 7) or segment in range(20, 24):
                    continue
                x = round((cx + math.cos(angle) * radius) / pixel) * pixel
                y = round((cy + math.sin(angle) * radius) / pixel) * pixel
                context.rectangle(x - pixel / 2, y - pixel / 2, pixel, pixel)
            context.fill()

        context.set_source_rgb(0.92, 0.94, 1.0)
        unit = pixel * 2
        context.rectangle(cx - unit * 1.5, cy - unit * 2, unit * 3, unit * 4)
        context.fill()
        context.set_source_rgb(0.10, 0.14, 0.28)
        context.rectangle(cx - unit, cy - unit, unit * 2, pixel)
        context.rectangle(cx - unit, cy, unit * 2, pixel)
        context.fill()


class ShellWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application, title="Cartheon")
        self.fullscreen()
        self.set_default_size(1280, 720)
        self.connect("close-request", lambda *_args: True)

        self._play: Callable[[], None] = lambda: None
        self._settings_action: Callable[[str], None] = lambda _action: None
        self._base_page = "waiting"
        self._settings_in_game = False
        self._has_cartridge = False
        self._game_running = False

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.pages = Gtk.Stack()
        self.pages.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.pages.set_transition_duration(140)
        self.set_child(self.pages)

        self._build_waiting_page()
        self._build_cartridge_page()
        self._build_status_page()
        self._build_settings_page()

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._key_pressed)
        self.add_controller(keys)

    def set_callbacks(
        self,
        play: Callable[[], None],
        settings_action: Callable[[str], None],
    ) -> None:
        self._play = play
        self._settings_action = settings_action

    @staticmethod
    def _centered_page(spacing: int = 16) -> Gtk.Box:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
        page.set_halign(Gtk.Align.CENTER)
        page.set_valign(Gtk.Align.CENTER)
        page.set_margin_top(28)
        page.set_margin_bottom(28)
        page.set_margin_start(28)
        page.set_margin_end(28)
        return page

    def _build_waiting_page(self) -> None:
        page = self._centered_page(18)
        self.waiting_rings = PixelRings(210)
        self.waiting_rings.set_halign(Gtk.Align.CENTER)
        page.append(self.waiting_rings)
        title = Gtk.Label(label="PLEASE INSERT A GAME CARTRIDGE")
        title.add_css_class("screen-title")
        title.set_wrap(True)
        title.set_justify(Gtk.Justification.CENTER)
        page.append(title)
        self.waiting_detail = Gtk.Label(label="")
        self.waiting_detail.add_css_class("detail")
        page.append(self.waiting_detail)
        self.pages.add_named(page, "waiting")

    def _build_cartridge_page(self) -> None:
        page = self._centered_page(14)
        self.cover_stack = Gtk.Stack()
        self.cover_stack.set_size_request(390, 390)
        self.cover_picture = Gtk.Picture()
        self.cover_picture.set_content_fit(Gtk.ContentFit.COVER)
        self.cover_picture.set_can_shrink(True)
        self.cover_picture.set_size_request(390, 390)
        self.cover_stack.add_named(self.cover_picture, "picture")
        placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        placeholder.set_halign(Gtk.Align.CENTER)
        placeholder.set_valign(Gtk.Align.CENTER)
        self.cover_rings = PixelRings(220)
        self.cover_rings.set_active(True)
        placeholder.append(self.cover_rings)
        no_cover = Gtk.Label(label="NO COVER ART")
        no_cover.add_css_class("detail")
        placeholder.append(no_cover)
        self.cover_stack.add_named(placeholder, "placeholder")
        cover_frame = Gtk.Frame()
        cover_frame.add_css_class("cover-frame")
        cover_frame.set_child(self.cover_stack)
        page.append(cover_frame)

        self.cartridge_title = Gtk.Label()
        self.cartridge_title.add_css_class("game-title")
        self.cartridge_title.set_wrap(True)
        self.cartridge_title.set_justify(Gtk.Justification.CENTER)
        page.append(self.cartridge_title)

        self.play_button = Gtk.Button(label="\u25b6  PLAY")
        self.play_button.add_css_class("play-button")
        self.play_button.set_halign(Gtk.Align.CENTER)
        self.play_button.connect("clicked", lambda _button: self._play())
        page.append(self.play_button)
        hint = Gtk.Label(label="[ ENTER ] PLAY    [ ESC ] SETTINGS")
        hint.add_css_class("detail")
        page.append(hint)
        self.pages.add_named(page, "cartridge")

    def _build_status_page(self) -> None:
        page = self._centered_page(14)
        self.status_rings = PixelRings(220)
        self.status_rings.set_active(True)
        page.append(self.status_rings)
        self.status_title = Gtk.Label()
        self.status_title.add_css_class("game-title")
        self.status_title.set_wrap(True)
        self.status_title.set_justify(Gtk.Justification.CENTER)
        page.append(self.status_title)
        self.status_message = Gtk.Label()
        self.status_message.add_css_class("message")
        self.status_message.set_wrap(True)
        self.status_message.set_justify(Gtk.Justification.CENTER)
        page.append(self.status_message)
        self.status_detail = Gtk.Label()
        self.status_detail.add_css_class("detail")
        self.status_detail.set_wrap(True)
        self.status_detail.set_justify(Gtk.Justification.CENTER)
        page.append(self.status_detail)
        self.pages.add_named(page, "status")

    def _settings_button(
        self, label: str, action: str, extra_class: str | None = None
    ) -> Gtk.Button:
        button = Gtk.Button(label=label)
        button.add_css_class("settings-button")
        if extra_class:
            button.add_css_class(extra_class)
        button.connect("clicked", lambda _button: self._settings_action(action))
        self.settings_buttons.append(button)
        return button

    def _build_settings_page(self) -> None:
        outer = self._centered_page()
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        panel.add_css_class("settings-panel")
        outer.append(panel)

        title = Gtk.Label(label="SETTINGS")
        title.add_css_class("settings-title")
        panel.append(title)

        self.settings_buttons: list[Gtk.Button] = []
        self.volume_button = self._settings_button("VOLUME: --  [ \u2190 / \u2192 ]", "volume_up")
        panel.append(self.volume_button)
        self.mute_button = self._settings_button("MUTE: --", "mute")
        panel.append(self.mute_button)
        self.bluetooth_button = self._settings_button("BLUETOOTH: --", "bluetooth")
        panel.append(self.bluetooth_button)
        self.wifi_button = self._settings_button("WI-FI: --", "wifi")
        panel.append(self.wifi_button)
        self.quit_button = self._settings_button(
            "QUIT CURRENT GAME", "quit_game", "danger-button"
        )
        panel.append(self.quit_button)
        self.eject_button = self._settings_button(
            "SAFELY EJECT CARTRIDGE", "eject", "eject-button"
        )
        panel.append(self.eject_button)
        panel.append(self._settings_button("BACK", "back"))

        self.settings_status = Gtk.Label(label="")
        self.settings_status.add_css_class("detail")
        self.settings_status.set_wrap(True)
        self.settings_status.set_justify(Gtk.Justification.CENTER)
        panel.append(self.settings_status)
        hint = Gtk.Label(label="[ \u2191 / \u2193 ] SELECT    [ ENTER ] CHOOSE    [ ESC ] BACK")
        hint.add_css_class("detail")
        panel.append(hint)
        self.pages.add_named(outer, "settings")

    def _key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        page = self.pages.get_visible_child_name()
        if keyval == Gdk.KEY_Escape:
            if page == "settings":
                self._settings_action("back")
            else:
                self._settings_action("open")
            return True
        if page != "settings":
            return False
        if keyval in (Gdk.KEY_Up, Gdk.KEY_Down):
            visible = [
                button
                for button in self.settings_buttons
                if button.get_visible() and button.get_sensitive()
            ]
            if not visible:
                return True
            focus = self.get_focus()
            try:
                index = visible.index(focus)
            except ValueError:
                index = 0
            else:
                index += -1 if keyval == Gdk.KEY_Up else 1
            visible[index % len(visible)].grab_focus()
            return True
        if self.get_focus() is self.volume_button:
            if keyval == Gdk.KEY_Left:
                self._settings_action("volume_down")
                return True
            if keyval == Gdk.KEY_Right:
                self._settings_action("volume_up")
                return True
        del state
        return False

    def _show_base(self, name: str) -> None:
        self._base_page = name
        self.pages.set_visible_child_name(name)
        self.present()

    def show_waiting(self, detail: str = "") -> None:
        self._has_cartridge = False
        self._game_running = False
        self.waiting_rings.set_active(bool(detail))
        self.waiting_detail.set_label(detail)
        self.set_cursor_from_name("none")
        self._show_base("waiting")

    def show_cartridge(self, game_title: str, cover: Path | None) -> None:
        self._has_cartridge = True
        self._game_running = False
        self.cartridge_title.set_label(game_title.upper())
        loaded = False
        if cover is not None:
            try:
                texture = Gdk.Texture.new_from_filename(str(cover))
            except GLib.Error:
                texture = None
            if texture is not None:
                self.cover_picture.set_paintable(texture)
                self.cover_stack.set_visible_child_name("picture")
                loaded = True
        if not loaded:
            self.cover_picture.set_paintable(None)
            self.cover_stack.set_visible_child_name("placeholder")
        self.set_cursor_from_name("default")
        self._show_base("cartridge")
        self.play_button.grab_focus()

    def show_booting(self, game_title: str) -> None:
        self._game_running = True
        self.status_rings.set_active(True)
        self.status_title.set_label(game_title.upper())
        self.status_message.set_label("CARTRIDGE STARTING")
        self.status_message.remove_css_class("error")
        self.status_detail.set_label("Preparing your game...")
        self._show_base("status")

    def show_loading(self, game_title: str) -> None:
        self._game_running = True
        self.status_rings.set_active(True)
        self.status_title.set_label(game_title.upper())
        self.status_message.set_label("LOADING...")
        self.status_message.remove_css_class("error")
        self.status_detail.set_label("The first Wine launch can take a little longer")
        self._show_base("status")

    def hide_for_game(self) -> None:
        self._game_running = True
        self.hide()

    def show_error(self, error: str) -> None:
        self._game_running = False
        self.status_rings.set_active(False)
        self.status_title.set_label("CARTRIDGE COULD NOT START")
        self.status_message.set_label(error)
        self.status_message.add_css_class("error")
        self.status_detail.set_label("Correct the cartridge, then remove and reinsert it")
        self._show_base("status")

    def show_settings(
        self,
        status: SystemStatus | None,
        in_game: bool,
        has_cartridge: bool,
    ) -> None:
        self._settings_in_game = in_game
        self._has_cartridge = has_cartridge
        self.quit_button.set_visible(in_game)
        self.eject_button.set_visible(has_cartridge and not in_game)
        self.settings_status.set_label("Reading system settings...")
        self.settings_status.remove_css_class("error")
        self.pages.set_visible_child_name("settings")
        self.set_cursor_from_name("default")
        self.present()
        if status is not None:
            self.update_settings(status)
        next(
            button
            for button in self.settings_buttons
            if button.get_visible() and button.get_sensitive()
        ).grab_focus()

    @staticmethod
    def _switch_text(value: bool | None) -> str:
        if value is None:
            return "UNAVAILABLE"
        return "ON" if value else "OFF"

    def update_settings(self, status: SystemStatus) -> None:
        volume = "--" if status.volume is None else f"{status.volume}%"
        self.volume_button.set_label(f"VOLUME: {volume}  [ \u2190 / \u2192 ]")
        self.mute_button.set_label(f"MUTE: {self._switch_text(status.muted)}")
        self.bluetooth_button.set_label(
            f"BLUETOOTH: {self._switch_text(status.bluetooth)}"
        )
        self.wifi_button.set_label(f"WI-FI: {self._switch_text(status.wifi)}")
        self.settings_status.set_label("")

    def settings_message(self, message: str, error: bool = False) -> None:
        self.settings_status.set_label(message)
        if error:
            self.settings_status.add_css_class("error")
        else:
            self.settings_status.remove_css_class("error")

    def close_settings(self) -> None:
        if self._settings_in_game:
            self.hide()
            return
        self.pages.set_visible_child_name(self._base_page)
        self.present()


class CartheonApplication(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id="org.cartheon.Shell")
        self.window: ShellWindow | None = None

    def do_activate(self) -> None:
        if self.window is None:
            self.window = ShellWindow(self)
        self.window.present()


def on_ui(callback, *args) -> None:
    GLib.idle_add(callback, *args)
