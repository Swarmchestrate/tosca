from importlib.metadata import version, PackageNotFoundError

from .sardou import Sardou # noqa: F401

try:
    __version__ = version("sardou")
except PackageNotFoundError:
    __version__ = "unknown"
