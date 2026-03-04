"""Shared pytest marks for the test suite."""

import shutil

import pytest

requires_puccini = pytest.mark.skipif(
    shutil.which("puccini-tosca") is None,
    reason="puccini-tosca not found in PATH",
)
