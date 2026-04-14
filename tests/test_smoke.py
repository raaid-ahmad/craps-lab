"""Smoke tests verifying the package imports and exposes a valid version."""

from __future__ import annotations

import re

import craps_lab

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][\w.-]+)?$")


def test_package_has_valid_semver() -> None:
    version = craps_lab.__version__
    assert _SEMVER_RE.match(version) is not None, (
        f"__version__ is not valid semver: {version!r}"
    )
