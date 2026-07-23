from datetime import datetime
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cartheon.diagnostics import (
    DiagnosticCheck,
    DiagnosticReport,
    export_report,
    run_diagnostics,
)


def result(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class DiagnosticTests(unittest.TestCase):
    @patch("cartheon.diagnostics.connected_gamepad_names")
    @patch("cartheon.diagnostics._run")
    def test_collects_gpu_vulkan_wine_audio_and_controller_health(
        self,
        run,
        gamepads,
    ) -> None:
        gamepads.return_value = ("Pixel Pad",)

        def command(*arguments, **_kwargs):
            if arguments[0] == "lspci":
                return result(
                    "00:02.0 VGA compatible controller: Example GPU\n"
                    "\tKernel driver in use: example\n"
                )
            if arguments[0] == "vulkaninfo":
                return result(
                    "Vulkan Instance Version: 1.4.0\n"
                    "deviceName = Example GPU\n"
                )
            if arguments[0] == "wine":
                return result("wine-11.0\n")
            if arguments[0] == "wpctl":
                return result("Audio\n")
            raise AssertionError(arguments)

        run.side_effect = command
        report = run_diagnostics()
        statuses = {check.name: check.status for check in report.checks}
        self.assertEqual(statuses["GPU DRIVER"], "PASS")
        self.assertEqual(statuses["VULKAN"], "PASS")
        self.assertEqual(statuses["CONTROLLERS"], "PASS")
        self.assertEqual(statuses["CARTRIDGE"], "WARN")

    def test_exports_a_timestamped_report_without_overwriting(self) -> None:
        report = DiagnosticReport(
            datetime.fromisoformat("2026-07-23T17:00:00+02:00"),
            (DiagnosticCheck("KERNEL", "PASS", "7.1.4"),),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = export_report(report, root)
            second = export_report(report, root)
            self.assertNotEqual(first, second)
            self.assertIn("[PASS] KERNEL", first.read_text())
            self.assertTrue(second.name.endswith("-1.txt"))


if __name__ == "__main__":
    unittest.main()
