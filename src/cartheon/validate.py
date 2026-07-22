"""Command-line validation for cartridge authors."""

from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Cartheon game cartridge")
    parser.add_argument("cartridge", help="path to the cartridge root")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.cartridge)
    except (ConfigError, OSError) as exc:
        print(f"invalid cartridge: {exc}", file=sys.stderr)
        return 1
    print(f"valid cartridge: {config.title} ({config.runtime})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
