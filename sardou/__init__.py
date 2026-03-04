from importlib.metadata import PackageNotFoundError, version

from .sardou import Sardou  # noqa: F401

try:
    __version__ = version("sardou")
except PackageNotFoundError:
    __version__ = "unknown"
