"""Minimal, controller-friendly GTK 4 shell for Cartheon OS."""

from __future__ import annotations

import math
import time

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402


CSS = b"""
window { background: #070912; color: #f5f7ff; }
.eyebrow { color: #8e9cff; font-size: 15px; font-weight: 700; letter-spacing: 4px; }
.title { font-size: 48px; font-weight: 800; }
.message { color: #bac1d9; font-size: 21px; }
.detail { color: #717b9e; font-size: 14px; }
.error { color: #ff7999; font-size: 18px; }
"""


class PulseLogo(Gtk.DrawingArea):
    def __init__(self) -> None:
        super().__init__()
        self.set_content_width(190)
        self.set_content_height(190)
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
        phase = (time.monotonic() - self._started) * 2.2 if self._active else 0.0
        for index, radius in enumerate((42, 58, 76)):
            alpha = 0.88 - index * 0.2
            context.set_source_rgba(0.38, 0.49, 1.0, alpha)
            context.set_line_width(5 - index)
            start = phase * (1 if index % 2 == 0 else -0.75) + index
            context.arc(cx, cy, radius, start, start + math.pi * (1.1 + index * 0.15))
            context.stroke()
        context.set_source_rgb(0.90, 0.93, 1.0)
        context.rectangle(cx - 23, cy - 29, 46, 58)
        context.fill()
        context.set_source_rgb(0.15, 0.19, 0.38)
        context.rectangle(cx - 13, cy - 19, 26, 6)
        context.rectangle(cx - 13, cy - 7, 26, 6)
        context.fill()


class ShellWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application, title="Cartheon OS")
        self.fullscreen()
        self.set_default_size(1280, 720)
        self.set_cursor_from_name("none")
        self.connect("close-request", lambda *_args: True)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        overlay = Gtk.Overlay()
        self.set_child(overlay)
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        center.set_halign(Gtk.Align.CENTER)
        center.set_valign(Gtk.Align.CENTER)
        center.set_size_request(760, -1)
        overlay.set_child(center)

        self.logo = PulseLogo()
        self.logo.set_halign(Gtk.Align.CENTER)
        center.append(self.logo)

        brand = Gtk.Label(label="CARTHEON OS")
        brand.add_css_class("eyebrow")
        center.append(brand)
        self.title = Gtk.Label(label="Please insert a game cartridge")
        self.title.add_css_class("title")
        self.title.set_wrap(True)
        self.title.set_justify(Gtk.Justification.CENTER)
        center.append(self.title)
        self.message = Gtk.Label(label="")
        self.message.add_css_class("message")
        self.message.set_wrap(True)
        center.append(self.message)
        self.detail = Gtk.Label(label="")
        self.detail.add_css_class("detail")
        center.append(self.detail)

    def show_waiting(self, detail: str = "") -> None:
        self.logo.set_active(False)
        self.title.set_label("Please insert a game cartridge")
        self.message.set_label(detail)
        self.message.remove_css_class("error")
        self.detail.set_label("")

    def show_booting(self, game_title: str) -> None:
        self.logo.set_active(True)
        self.title.set_label(game_title)
        self.message.set_label("Cartridge recognized")
        self.message.remove_css_class("error")
        self.detail.set_label("Preparing your game…")

    def show_loading(self, game_title: str) -> None:
        self.logo.set_active(True)
        self.title.set_label(game_title)
        self.message.set_label("Loading…")
        self.detail.set_label("The first Wine launch can take a little longer")

    def show_running(self, game_title: str) -> None:
        self.logo.set_active(False)
        self.title.set_label(game_title)
        self.message.set_label("Game is running")
        self.detail.set_label("Do not remove the cartridge while playing")

    def show_error(self, error: str) -> None:
        self.logo.set_active(False)
        self.title.set_label("Cartridge could not start")
        self.message.set_label(error)
        self.message.add_css_class("error")
        self.detail.set_label("Correct game.cfg, then remove and reinsert the cartridge")


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
