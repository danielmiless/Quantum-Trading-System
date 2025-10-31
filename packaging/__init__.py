"""Packaging utilities for building desktop distributions."""

from .build import build_release, build_target
from .build_config import BuildConfig, PlatformConfig

__all__ = ["build_release", "build_target", "BuildConfig", "PlatformConfig"]

