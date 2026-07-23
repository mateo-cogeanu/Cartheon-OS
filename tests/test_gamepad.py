import unittest

from cartheon.gamepad import (
    ABS_HAT0X,
    ABS_X,
    BTN_DPAD_DOWN,
    BTN_EAST,
    BTN_MODE,
    BTN_SELECT,
    BTN_SOUTH,
    BTN_START,
    GamepadEventMapper,
)


class GamepadEventMapperTests(unittest.TestCase):
    def test_maps_console_buttons_to_navigation(self) -> None:
        mapper = GamepadEventMapper()
        self.assertEqual(mapper.key(BTN_DPAD_DOWN, 1), ("down",))
        self.assertEqual(mapper.key(BTN_SOUTH, 1), ("accept",))
        self.assertEqual(mapper.key(BTN_EAST, 1), ("back",))
        self.assertEqual(mapper.key(BTN_MODE, 1), ("menu",))

    def test_start_select_chord_opens_menu_once_per_press(self) -> None:
        mapper = GamepadEventMapper()
        self.assertEqual(mapper.key(BTN_START, 1), ())
        self.assertEqual(mapper.key(BTN_SELECT, 1), ("menu",))
        self.assertEqual(mapper.key(BTN_SELECT, 2), ())
        mapper.key(BTN_SELECT, 0)
        self.assertEqual(mapper.key(BTN_SELECT, 1), ("menu",))

    def test_hat_and_stick_emit_once_until_centered(self) -> None:
        mapper = GamepadEventMapper()
        self.assertEqual(mapper.absolute(ABS_HAT0X, 1, -1, 1), ("right",))
        self.assertEqual(mapper.absolute(ABS_HAT0X, 1, -1, 1), ())
        self.assertEqual(mapper.absolute(ABS_HAT0X, 0, -1, 1), ())
        self.assertEqual(mapper.absolute(ABS_HAT0X, -1, -1, 1), ("left",))
        self.assertEqual(mapper.absolute(ABS_X, 32767, -32768, 32767), ("right",))


if __name__ == "__main__":
    unittest.main()
