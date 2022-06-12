"""
.. include:: ../README.md
"""

try:
    import importlib.metadata as metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore

try:
    __version__ = metadata.version(__package__ or __name__)
except metadata.PackageNotFoundError:
    import toml

    __version__ = (
        toml.load("pyproject.toml")
        .get("tool", {})
        .get("poetry", {})
        .get("version", "unknown")
        + "-dev"
    )

from .source import source
from .shell_config import ShellConfig
