from importlib.metadata import version

from .sardou import Sardou

try:
    __version__ = version("sardou")
except PackageNotFoundError:
    __version__ = "unknown"