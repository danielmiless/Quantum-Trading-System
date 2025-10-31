"""CLI to build production releases for all supported platforms."""

from __future__ import annotations

import argparse

from packaging.build import build_release


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build production releases")
    parser.add_argument(
        "--platforms",
        nargs="*",
        help="Subset of platforms to build (macos, windows)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_release(args.platforms)


if __name__ == "__main__":
    main()

