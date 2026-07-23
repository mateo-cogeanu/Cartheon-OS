"""System and cartridge health checks with portable text-report export."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import platform
import shutil
import subprocess

from .config import GameConfig
from .gamepad import connected_gamepad_names


@dataclass(frozen=True, slots=True)
class DiagnosticCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    created_at: datetime
    checks: tuple[DiagnosticCheck, ...]

    @property
    def summary(self) -> str:
        failures = sum(check.status == "FAIL" for check in self.checks)
        warnings = sum(check.status == "WARN" for check in self.checks)
        if failures:
            return f"{failures} FAILED  /  {warnings} WARNINGS"
        if warnings:
            return f"READY WITH {warnings} WARNINGS"
        return "ALL CHECKS PASSED"

    def render(self) -> str:
        lines = [
            "Cartheon OS Diagnostic Report",
            f"Generated: {self.created_at.astimezone().isoformat(timespec='seconds')}",
            f"Summary: {self.summary}",
            "",
        ]
        for check in self.checks:
            lines.extend((f"[{check.status}] {check.name}", check.detail, ""))
        return "\n".join(lines)


def _run(*arguments: str, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(arguments),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _command(
    name: str,
    arguments: tuple[str, ...],
    detail_from_output,
) -> DiagnosticCheck:
    try:
        result = _run(*arguments)
    except (OSError, subprocess.SubprocessError) as exc:
        return DiagnosticCheck(name, "FAIL", str(exc))
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "Command failed"
        return DiagnosticCheck(name, "FAIL", detail.splitlines()[0])
    return DiagnosticCheck(name, "PASS", detail_from_output(result.stdout))


def _gpu_check() -> DiagnosticCheck:
    try:
        result = _run("lspci", "-nnk")
    except (OSError, subprocess.SubprocessError) as exc:
        return DiagnosticCheck("GPU DRIVER", "FAIL", str(exc))
    if result.returncode != 0:
        return DiagnosticCheck(
            "GPU DRIVER",
            "FAIL",
            result.stderr.strip() or "Could not inspect PCI graphics devices",
        )

    graphics: list[str] = []
    current = ""
    for line in result.stdout.splitlines():
        if line and not line[0].isspace():
            current = line if any(
                marker in line for marker in ("VGA compatible", "3D controller", "Display controller")
            ) else ""
            if current:
                graphics.append(current.split(": ", 1)[-1])
        elif current and "Kernel driver in use:" in line:
            graphics[-1] += f" / {line.split(':', 1)[1].strip()}"
    if not graphics:
        return DiagnosticCheck("GPU DRIVER", "FAIL", "No graphics adapter detected")
    missing_driver = any(" / " not in item for item in graphics)
    return DiagnosticCheck(
        "GPU DRIVER",
        "WARN" if missing_driver else "PASS",
        "; ".join(graphics),
    )


def _vulkan_detail(output: str) -> str:
    version = next(
        (line.strip() for line in output.splitlines() if "Vulkan Instance Version" in line),
        "Vulkan available",
    )
    device = next(
        (
            line.split("=", 1)[1].strip()
            for line in output.splitlines()
            if "deviceName" in line and "=" in line
        ),
        "",
    )
    return f"{version}; {device}" if device else version


def _wine_detail(output: str) -> str:
    return output.strip().splitlines()[0] if output.strip() else "Wine available"


def _audio_detail(output: str) -> str:
    return "PipeWire/WirePlumber audio graph available" if output.strip() else "Audio service available"


def _cartridge_check(config: GameConfig | None) -> DiagnosticCheck:
    if config is None:
        return DiagnosticCheck("CARTRIDGE", "WARN", "No game cartridge inserted")
    try:
        usage = shutil.disk_usage(config.root)
        free_gib = usage.free / (1024**3)
        filesystem = _run(
            "findmnt",
            "--noheadings",
            "--output",
            "FSTYPE",
            "--target",
            str(config.root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return DiagnosticCheck("CARTRIDGE", "FAIL", str(exc))
    filesystem_name = filesystem.stdout.strip() if filesystem.returncode == 0 else "unknown"
    status = "PASS" if filesystem_name.casefold() == "exfat" else "WARN"
    return DiagnosticCheck(
        "CARTRIDGE",
        status,
        (
            f"{config.title} / {config.runtime.upper()} / "
            f"{filesystem_name.upper()} / {free_gib:.1f} GiB free"
        ),
    )


def run_diagnostics(config: GameConfig | None = None) -> DiagnosticReport:
    controllers = connected_gamepad_names()
    checks = (
        DiagnosticCheck("KERNEL", "PASS", platform.release()),
        _gpu_check(),
        _command("VULKAN", ("vulkaninfo", "--summary"), _vulkan_detail),
        _command("WINE", ("wine", "--version"), _wine_detail),
        _command("AUDIO", ("wpctl", "status"), _audio_detail),
        DiagnosticCheck(
            "CONTROLLERS",
            "PASS" if controllers else "WARN",
            ", ".join(controllers) if controllers else "No controller connected",
        ),
        _cartridge_check(config),
    )
    return DiagnosticReport(datetime.now().astimezone(), checks)


def export_report(report: DiagnosticReport, cartridge_root: Path) -> Path:
    root = cartridge_root.resolve(strict=True)
    timestamp = report.created_at.strftime("%Y%m%d-%H%M%S")
    for suffix in ("", *(f"-{index}" for index in range(1, 100))):
        destination = root / f"cartheon-diagnostics-{timestamp}{suffix}.txt"
        try:
            with destination.open("x", encoding="utf-8") as handle:
                handle.write(report.render())
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            continue
        return destination
    raise OSError("Could not choose a unique diagnostic report name")
