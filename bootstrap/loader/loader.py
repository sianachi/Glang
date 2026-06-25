"""Compatibility wrapper for the historic ``loader.loader`` import path."""

from glang_loader.loader import (
    Loader,
    STD_PREFIX,
    STDLIB_DIR,
    _default_stdlib_dir,
    load,
)

__all__ = [
    "Loader",
    "STD_PREFIX",
    "STDLIB_DIR",
    "_default_stdlib_dir",
    "load",
]
