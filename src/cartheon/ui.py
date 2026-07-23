"""Pixel-styled, keyboard-first GTK 4 shell for Cartheon OS."""

from __future__ import annotations

import math
from pathlib import Path
import time
from typing import Callable

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from .system_controls import BluetoothDevice, SystemStatus, WifiNetwork


CSS = b"""
window {
  background: #070912;
  color: #f5f7ff;
  font-family: "ProggyTinyTT", "Terminus", monospace;
  font-weight: 400;
}
label {
  text-shadow: 2px 2px #000000;
}
.screen-title {
  font-size: 64px;
  font-weight: 400;
}
.game-title {
  font-size: 54px;
  font-weight: 400;
}
.message {
  color: #bac1d9;
  font-size: 30px;
}
.detail {
  color: #8792b8;
  font-size: 23px;
}
.error {
  color: #ff668c;
}
.cover-frame {
  background: #11172b;
  border: 6px solid #35406d;
  border-radius: 4px;
  padding: 6px;
  box-shadow: 8px 8px #02030a;
}
button {
  outline: none;
  transition: none;
}
.play-button {
  min-width: 250px;
  min-height: 58px;
  border: 4px solid #baffc9;
  border-radius: 4px;
  background: #24b85a;
  color: #06130b;
  font-size: 40px;
  font-weight: 400;
  box-shadow: 0 8px #116b34;
}
.play-button:focus {
  background: #59e681;
  border-color: #ffffff;
  box-shadow: 0 8px #ffffff;
}
.settings-panel {
  background: #0e1427;
  border: 6px solid #8e9cff;
  border-radius: 0;
  padding: 22px;
  box-shadow: 10px 10px #02030a;
}
.settings-title {
  color: #d7dcff;
  font-size: 54px;
  font-weight: 400;
}
.settings-button {
  min-width: 570px;
  min-height: 44px;
  border: 3px solid #35406d;
  border-radius: 0;
  background: #151d36;
  color: #e9ebff;
  font-size: 30px;
  font-weight: 400;
  box-shadow: 4px 4px #050711;
}
.settings-button:focus {
  background: #313d70;
  border-color: #ffffff;
  color: #ffffff;
  box-shadow: 4px 4px #8e9cff;
}
.network-button {
  min-width: 530px;
  min-height: 40px;
  font-size: 27px;
}
.connected-button {
  border-color: #51dc7e;
  color: #9affbb;
}
.danger-button {
  border-color: #9c3650;
  color: #ffb3c5;
}
.eject-button {
  border-color: #8f7f35;
  color: #fff0a6;
}
entry {
  min-width: 530px;
  min-height: 42px;
  border: 3px solid #35406d;
  border-radius: 0;
  background: #080c18;
  color: #ffffff;
  caret-color: #8e9cff;
  font-family: "ProggyTinyTT", "Terminus", monospace;
  font-size: 30px;
  box-shadow: 4px 4px #02030a;
}
entry:focus {
  border-color: #ffffff;
}
scrollbar slider {
  min-width: 12px;
  min-height: 20px;
  border-radius: 0;
  background: #8e9cff;
}
"""


SettingsPayload = object | None


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

        # A compact 2.5-inch SSD silhouette makes the removable-storage idea
        # explicit without overpowering the orbit animation.
        unit = pixel

        def ssd_path(offset_x: float = 0, offset_y: float = 0) -> None:
            points = (
                (-3, -6),
                (3, -6),
                (4, -5),
                (4, 5),
                (3, 6),
                (-3, 6),
                (-4, 5),
                (-4, -5),
            )
            context.move_to(
                cx + (points[0][0] + offset_x) * unit,
                cy + (points[0][1] + offset_y) * unit,
            )
            for x, y in points[1:]:
                context.line_to(
                    cx + (x + offset_x) * unit,
                    cy + (y + offset_y) * unit,
                )
            context.close_path()

        context.set_source_rgb(0.01, 0.02, 0.06)
        ssd_path(1, 1)
        context.fill()
        context.set_source_rgb(0.14, 0.16, 0.19)
        ssd_path()
        context.fill()

        context.set_source_rgb(0.33, 0.36, 0.42)
        context.rectangle(cx - 3 * unit, cy - 5 * unit, 6 * unit, unit)
        context.rectangle(cx - 3 * unit, cy - 4 * unit, unit, 8 * unit)
        context.fill()

        context.set_source_rgb(0.07, 0.08, 0.11)
        context.rectangle(cx - 2 * unit, cy - 4 * unit, 4 * unit, 8 * unit)
        context.fill()

        context.set_source_rgb(0.42, 0.45, 0.49)
        screw_size = max(2, unit / 2)
        for screw_x, screw_y in ((-2.5, -4.5), (2, -4.5), (-2.5, 3), (2, 3)):
            context.rectangle(
                cx + screw_x * unit,
                cy + screw_y * unit,
                screw_size,
                screw_size,
            )
        context.fill()

        # Three upright glyphs are stacked from top to bottom: S, S, D.
        ssd_glyphs = (
            ("111", "100", "111", "001", "111"),
            ("111", "100", "111", "001", "111"),
            ("110", "101", "101", "101", "110"),
        )
        glyph_pixel = max(2, pixel // 2)
        context.set_source_rgb(0.47, 0.54, 0.62)
        for glyph_index, glyph in enumerate(ssd_glyphs):
            for glyph_y, row in enumerate(glyph):
                for column, enabled in enumerate(row):
                    if enabled == "1":
                        stack_row = glyph_index * 6 + glyph_y
                        context.rectangle(
                            cx + (column - 1.5) * glyph_pixel,
                            cy + (stack_row - 8.5) * glyph_pixel,
                            glyph_pixel,
                            glyph_pixel,
                        )
        context.fill()

        # Two differently sized bottom blocks form the SSD's SATA connector.
        context.set_source_rgb(0.04, 0.05, 0.07)
        context.rectangle(cx - 3 * unit, cy + 4.5 * unit, 3 * unit, 1.5 * unit)
        context.rectangle(cx + unit / 2, cy + 4.5 * unit, 2.5 * unit, 1.5 * unit)
        context.fill()


class ShellWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application, title="Cartheon")
        self.fullscreen()
        self.set_default_size(1280, 720)
        self.connect("close-request", lambda *_args: True)

        self._play: Callable[[], None] = lambda: None
        self._settings_action: Callable[[str, SettingsPayload], None] = (
            lambda _action, _payload=None: None
        )
        self._base_page = "waiting"
        self._settings_in_game = False
        self._has_cartridge = False
        self._game_running = False
        self._wifi_networks: list[WifiNetwork] = []
        self._bluetooth_devices: list[BluetoothDevice] = []
        self._pending_wifi: WifiNetwork | None = None
        self._menu_focusables: dict[str, list[Gtk.Widget]] = {}

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.pages = Gtk.Stack()
        self.pages.set_transition_type(Gtk.StackTransitionType.NONE)
        self.set_child(self.pages)

        self._build_waiting_page()
        self._build_cartridge_page()
        self._build_status_page()
        self._build_settings_page()
        self._build_wifi_page()
        self._build_wifi_password_page()
        self._build_bluetooth_page()

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._key_pressed)
        self.add_controller(keys)
        self.set_cursor_from_name("none")

    def set_callbacks(
        self,
        play: Callable[[], None],
        settings_action: Callable[[str, SettingsPayload], None],
    ) -> None:
        self._play = play
        self._settings_action = settings_action

    @staticmethod
    def _centered_page(spacing: int = 16) -> Gtk.Box:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
        page.set_halign(Gtk.Align.CENTER)
        page.set_valign(Gtk.Align.CENTER)
        page.set_margin_top(24)
        page.set_margin_bottom(24)
        page.set_margin_start(28)
        page.set_margin_end(28)
        return page

    def _build_waiting_page(self) -> None:
        page = self._centered_page(18)
        self.waiting_rings = PixelRings(210)
        self.waiting_rings.set_active(True)
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

        self.play_button = Gtk.Button(label=">  PLAY")
        self.play_button.add_css_class("play-button")
        self.play_button.set_halign(Gtk.Align.CENTER)
        self.play_button.connect("clicked", lambda _button: self._play())
        page.append(self.play_button)
        hint = Gtk.Label(label="[ A / ENTER ] PLAY    [ HOME / ESC ] SETTINGS")
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

    def _panel(self, title_text: str) -> tuple[Gtk.Box, Gtk.Box]:
        outer = self._centered_page()
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        panel.add_css_class("settings-panel")
        outer.append(panel)
        title = Gtk.Label(label=title_text)
        title.add_css_class("settings-title")
        panel.append(title)
        return outer, panel

    def _menu_button(
        self,
        buttons: list[Gtk.Widget],
        label: str,
        action: str | None = None,
        payload: SettingsPayload = None,
        extra_class: str | None = None,
    ) -> Gtk.Button:
        button = Gtk.Button(label=label)
        button.add_css_class("settings-button")
        if extra_class:
            button.add_css_class(extra_class)
        if action is not None:
            button.connect(
                "clicked",
                lambda _button, selected_action=action, selected_payload=payload: (
                    self._settings_action(selected_action, selected_payload)
                ),
            )
        buttons.append(button)
        return button

    @staticmethod
    def _status_label() -> Gtk.Label:
        label = Gtk.Label(label="")
        label.add_css_class("detail")
        label.set_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        return label

    @staticmethod
    def _hint() -> Gtk.Label:
        hint = Gtk.Label(
            label="[ D-PAD ] SELECT    [ A / ENTER ] CHOOSE    [ B / ESC ] BACK"
        )
        hint.add_css_class("detail")
        return hint

    def _build_settings_page(self) -> None:
        outer, panel = self._panel("SETTINGS")
        buttons: list[Gtk.Widget] = []
        self.volume_button = self._menu_button(
            buttons, "VOLUME: --  [ LEFT / RIGHT ]", "volume_up"
        )
        panel.append(self.volume_button)
        self.mute_button = self._menu_button(buttons, "MUTE: --", "mute")
        panel.append(self.mute_button)
        self.wifi_button = self._menu_button(buttons, "WI-FI SETTINGS  >", "wifi_open")
        panel.append(self.wifi_button)
        self.bluetooth_button = self._menu_button(
            buttons, "BLUETOOTH SETTINGS  >", "bluetooth_open"
        )
        panel.append(self.bluetooth_button)
        self.quit_button = self._menu_button(
            buttons, "QUIT CURRENT GAME", "quit_game", extra_class="danger-button"
        )
        panel.append(self.quit_button)
        self.eject_button = self._menu_button(
            buttons,
            "SAFELY EJECT CARTRIDGE",
            "eject",
            extra_class="eject-button",
        )
        panel.append(self.eject_button)
        panel.append(self._menu_button(buttons, "<  BACK", "back"))
        self.settings_status = self._status_label()
        panel.append(self.settings_status)
        panel.append(self._hint())
        self._menu_focusables["settings"] = buttons
        self.pages.add_named(outer, "settings")

    def _build_wifi_page(self) -> None:
        outer, panel = self._panel("WI-FI")
        fixed_buttons: list[Gtk.Widget] = []
        self.wifi_toggle_button = self._menu_button(
            fixed_buttons, "WI-FI POWER: --", "wifi_toggle"
        )
        panel.append(self.wifi_toggle_button)
        panel.append(
            self._menu_button(fixed_buttons, "SCAN FOR NETWORKS", "wifi_refresh")
        )
        self.wifi_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(245)
        scroll.set_max_content_height(245)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self.wifi_list)
        panel.append(scroll)
        self.wifi_back_button = self._menu_button(
            fixed_buttons, "<  SETTINGS", "submenu_back"
        )
        panel.append(self.wifi_back_button)
        self.wifi_status = self._status_label()
        panel.append(self.wifi_status)
        panel.append(self._hint())
        self._wifi_fixed_buttons = fixed_buttons
        self._menu_focusables["wifi"] = fixed_buttons
        self.pages.add_named(outer, "wifi")

    def _build_wifi_password_page(self) -> None:
        outer, panel = self._panel("WI-FI PASSWORD")
        self.wifi_password_network = Gtk.Label(label="")
        self.wifi_password_network.add_css_class("message")
        panel.append(self.wifi_password_network)
        instruction = Gtk.Label(label="TYPE THE PASSWORD, OR LEAVE EMPTY FOR A SAVED NETWORK")
        instruction.add_css_class("detail")
        instruction.set_wrap(True)
        panel.append(instruction)
        self.wifi_password = Gtk.PasswordEntry()
        self.wifi_password.set_show_peek_icon(False)
        self.wifi_password.connect("activate", lambda _entry: self._submit_wifi_password())
        panel.append(self.wifi_password)
        buttons: list[Gtk.Widget] = [self.wifi_password]
        connect = self._menu_button(buttons, "CONNECT", None)
        connect.connect("clicked", lambda _button: self._submit_wifi_password())
        panel.append(connect)
        back = self._menu_button(buttons, "<  NETWORKS", None)
        back.connect("clicked", lambda _button: self._show_menu_page("wifi"))
        panel.append(back)
        panel.append(self._hint())
        self._menu_focusables["wifi_password"] = buttons
        self.pages.add_named(outer, "wifi_password")

    def _build_bluetooth_page(self) -> None:
        outer, panel = self._panel("BLUETOOTH")
        fixed_buttons: list[Gtk.Widget] = []
        self.bluetooth_toggle_button = self._menu_button(
            fixed_buttons, "BLUETOOTH POWER: --", "bluetooth_toggle"
        )
        panel.append(self.bluetooth_toggle_button)
        panel.append(
            self._menu_button(fixed_buttons, "SCAN FOR DEVICES", "bluetooth_refresh")
        )
        self.bluetooth_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(245)
        scroll.set_max_content_height(245)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self.bluetooth_list)
        panel.append(scroll)
        self.bluetooth_back_button = self._menu_button(
            fixed_buttons, "<  SETTINGS", "submenu_back"
        )
        panel.append(self.bluetooth_back_button)
        self.bluetooth_status = self._status_label()
        panel.append(self.bluetooth_status)
        panel.append(self._hint())
        self._bluetooth_fixed_buttons = fixed_buttons
        self._menu_focusables["bluetooth"] = fixed_buttons
        self.pages.add_named(outer, "bluetooth")

    @staticmethod
    def _clear_box(box: Gtk.Box) -> None:
        while child := box.get_first_child():
            box.remove(child)

    def _show_menu_page(self, page: str) -> None:
        self.pages.set_visible_child_name(page)
        self.set_cursor_from_name("none")
        self.present()
        self.fullscreen()
        GLib.idle_add(self.fullscreen)
        focusables = self._visible_focusables(page)
        if focusables:
            focusables[0].grab_focus()

    def _visible_focusables(self, page: str) -> list[Gtk.Widget]:
        return [
            widget
            for widget in self._menu_focusables.get(page, [])
            if widget.get_visible() and widget.get_sensitive()
        ]

    def _key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        del state
        actions = {
            Gdk.KEY_Escape: "back",
            Gdk.KEY_Return: "accept",
            Gdk.KEY_KP_Enter: "accept",
            Gdk.KEY_Up: "up",
            Gdk.KEY_Down: "down",
            Gdk.KEY_Left: "left",
            Gdk.KEY_Right: "right",
        }
        action = actions.get(keyval)
        return self.handle_navigation(action) if action is not None else False

    def handle_navigation(self, action: str) -> bool:
        if not self.get_visible() and action != "menu":
            return False
        page = self.pages.get_visible_child_name() or ""
        if action in {"back", "menu"}:
            if page == "settings":
                self._settings_action("back", None)
            elif page in {"wifi", "bluetooth"}:
                self._show_menu_page("settings")
            elif page == "wifi_password":
                self._show_menu_page("wifi")
            else:
                self._settings_action("open", None)
            return True
        if page == "cartridge" and action == "accept":
            self._play()
            return True
        focusables = self._visible_focusables(page)
        if not focusables:
            return False
        if action in {"up", "down"}:
            focus = self.get_focus()
            try:
                index = focusables.index(focus)
            except ValueError:
                index = 0
            else:
                index += -1 if action == "up" else 1
            focusables[index % len(focusables)].grab_focus()
            return True
        if action == "accept":
            focus = self.get_focus()
            if isinstance(focus, Gtk.Button):
                focus.activate()
                return True
        if page == "settings" and self.get_focus() is self.volume_button:
            if action == "left":
                self._settings_action("volume_down", None)
                return True
            if action == "right":
                self._settings_action("volume_up", None)
                return True
        return False

    def _show_base(self, name: str) -> None:
        self._base_page = name
        self.pages.set_visible_child_name(name)
        self.set_cursor_from_name("none")
        self.present()
        self.fullscreen()
        GLib.idle_add(self.fullscreen)

    def show_waiting(self, detail: str = "") -> None:
        self._has_cartridge = False
        self._game_running = False
        self.waiting_rings.set_active(True)
        self.waiting_detail.set_label(detail.upper())
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
        self._show_base("cartridge")
        self.play_button.grab_focus()

    def show_booting(self, game_title: str) -> None:
        self._game_running = True
        self.status_rings.set_active(True)
        self.status_title.set_label(game_title.upper())
        self.status_message.set_label("CARTRIDGE STARTING")
        self.status_message.remove_css_class("error")
        self.status_detail.set_label("PREPARING YOUR GAME...")
        self._show_base("status")

    def show_loading(self, game_title: str) -> None:
        self._game_running = True
        self.status_rings.set_active(True)
        self.status_title.set_label(game_title.upper())
        self.status_message.set_label("LOADING...")
        self.status_message.remove_css_class("error")
        self.status_detail.set_label("THE FIRST WINE LAUNCH CAN TAKE A LITTLE LONGER")
        self._show_base("status")

    def hide_for_game(self) -> None:
        self._game_running = True
        self.hide()

    def show_error(self, error: str) -> None:
        self._game_running = False
        self.status_rings.set_active(False)
        self.status_title.set_label("CARTRIDGE COULD NOT START")
        self.status_message.set_label(error.upper())
        self.status_message.add_css_class("error")
        self.status_detail.set_label("CORRECT THE CARTRIDGE, THEN REMOVE AND REINSERT IT")
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
        self.settings_status.set_label("READING SYSTEM SETTINGS...")
        self.settings_status.remove_css_class("error")
        if status is not None:
            self.update_settings(status)
        self._show_menu_page("settings")

    @staticmethod
    def _switch_text(value: bool | None) -> str:
        if value is None:
            return "UNAVAILABLE"
        return "ON" if value else "OFF"

    def update_settings(self, status: SystemStatus) -> None:
        volume = "--" if status.volume is None else f"{status.volume}%"
        self.volume_button.set_label(f"VOLUME: {volume}  [ LEFT / RIGHT ]")
        self.mute_button.set_label(f"MUTE: {self._switch_text(status.muted)}")
        if status.wifi:
            wifi_detail = status.wifi_connection or "ON - NOT CONNECTED"
        else:
            wifi_detail = self._switch_text(status.wifi)
        self.wifi_button.set_label(f"WI-FI: {wifi_detail.upper()}  >")
        if status.bluetooth:
            if status.bluetooth_connected:
                bluetooth_detail = f"{len(status.bluetooth_connected)} CONNECTED"
            else:
                bluetooth_detail = "ON - NO DEVICES"
        else:
            bluetooth_detail = self._switch_text(status.bluetooth)
        self.bluetooth_button.set_label(f"BLUETOOTH: {bluetooth_detail}  >")
        self.wifi_toggle_button.set_label(
            f"WI-FI POWER: {self._switch_text(status.wifi)}"
        )
        self.bluetooth_toggle_button.set_label(
            f"BLUETOOTH POWER: {self._switch_text(status.bluetooth)}"
        )
        self.settings_status.set_label("")

    def show_wifi_loading(self, status: SystemStatus) -> None:
        self.update_settings(status)
        self._clear_box(self.wifi_list)
        self.wifi_status.set_label(
            "SCANNING FOR NETWORKS..." if status.wifi else "WI-FI IS OFF"
        )
        self.wifi_status.remove_css_class("error")
        self._menu_focusables["wifi"] = list(self._wifi_fixed_buttons)
        self._show_menu_page("wifi")

    def show_wifi_menu(
        self,
        networks: list[WifiNetwork],
        status: SystemStatus,
        message: str = "",
        error: bool = False,
    ) -> None:
        self._wifi_networks = networks
        self.update_settings(status)
        self._clear_box(self.wifi_list)
        dynamic: list[Gtk.Widget] = []
        for network in networks:
            if network.connected:
                marker = "[CONNECTED]"
            elif network.secured:
                marker = "[LOCKED]"
            else:
                marker = "[OPEN]"
            label = f"{marker} {network.ssid}  {network.signal}%"
            button = self._menu_button(
                dynamic,
                label,
                extra_class="network-button",
            )
            if network.connected:
                button.add_css_class("connected-button")
            button.connect(
                "clicked",
                lambda _button, selected=network: self._select_wifi(selected),
            )
            self.wifi_list.append(button)
        self._menu_focusables["wifi"] = (
            self._wifi_fixed_buttons[:2] + dynamic + self._wifi_fixed_buttons[2:]
        )
        if message:
            self.wifi_status.set_label(message.upper())
        elif not status.wifi:
            self.wifi_status.set_label("WI-FI IS OFF")
        elif not networks:
            self.wifi_status.set_label("NO NETWORKS FOUND")
        else:
            self.wifi_status.set_label("")
        if error:
            self.wifi_status.add_css_class("error")
        else:
            self.wifi_status.remove_css_class("error")
        self._show_menu_page("wifi")

    def _select_wifi(self, network: WifiNetwork) -> None:
        if network.connected:
            self._settings_action("wifi_disconnect", None)
        elif network.secured:
            self._pending_wifi = network
            self.wifi_password_network.set_label(network.ssid.upper())
            self.wifi_password.set_text("")
            self._show_menu_page("wifi_password")
            self.wifi_password.grab_focus()
        else:
            self._settings_action("wifi_connect", (network.ssid, ""))

    def _submit_wifi_password(self) -> None:
        if self._pending_wifi is None:
            self._show_menu_page("wifi")
            return
        self._settings_action(
            "wifi_connect",
            (self._pending_wifi.ssid, self.wifi_password.get_text()),
        )
        self.wifi_password.set_text("")
        self._show_menu_page("wifi")

    def show_bluetooth_loading(self, status: SystemStatus) -> None:
        self.update_settings(status)
        self._clear_box(self.bluetooth_list)
        self.bluetooth_status.set_label(
            "SCANNING FOR DEVICES..." if status.bluetooth else "BLUETOOTH IS OFF"
        )
        self.bluetooth_status.remove_css_class("error")
        self._menu_focusables["bluetooth"] = list(self._bluetooth_fixed_buttons)
        self._show_menu_page("bluetooth")

    def show_bluetooth_menu(
        self,
        devices: list[BluetoothDevice],
        status: SystemStatus,
        message: str = "",
        error: bool = False,
    ) -> None:
        self._bluetooth_devices = devices
        self.update_settings(status)
        self._clear_box(self.bluetooth_list)
        dynamic: list[Gtk.Widget] = []
        for device in devices:
            if device.connected:
                marker = "[CONNECTED]"
            elif device.paired:
                marker = "[PAIRED]"
            else:
                marker = "[NEW]"
            signal = "--" if device.signal is None else str(device.signal)
            button = self._menu_button(
                dynamic,
                f"{marker} {device.name}  {signal}%",
                extra_class="network-button",
            )
            if device.connected:
                button.add_css_class("connected-button")
            button.connect(
                "clicked",
                lambda _button, selected=device: self._settings_action(
                    "bluetooth_device", selected
                ),
            )
            self.bluetooth_list.append(button)
        self._menu_focusables["bluetooth"] = (
            self._bluetooth_fixed_buttons[:2]
            + dynamic
            + self._bluetooth_fixed_buttons[2:]
        )
        if message:
            self.bluetooth_status.set_label(message.upper())
        elif not status.bluetooth:
            self.bluetooth_status.set_label("BLUETOOTH IS OFF")
        elif not devices:
            self.bluetooth_status.set_label("NO DEVICES FOUND")
        else:
            self.bluetooth_status.set_label("")
        if error:
            self.bluetooth_status.add_css_class("error")
        else:
            self.bluetooth_status.remove_css_class("error")
        self._show_menu_page("bluetooth")

    def settings_message(self, message: str, error: bool = False) -> None:
        self.settings_status.set_label(message.upper())
        if error:
            self.settings_status.add_css_class("error")
        else:
            self.settings_status.remove_css_class("error")

    def close_settings(self) -> None:
        if self._settings_in_game:
            self.hide()
            return
        self.pages.set_visible_child_name(self._base_page)
        self.set_cursor_from_name("none")
        self.present()
        self.fullscreen()
        GLib.idle_add(self.fullscreen)


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
