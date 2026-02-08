"""Shared Terraform utility functions."""

import functools
import shutil


@functools.lru_cache(maxsize=1)
def is_terraform_available() -> bool:
    """Check if terraform binary is available on PATH. Result is cached."""
    return shutil.which("terraform") is not None
