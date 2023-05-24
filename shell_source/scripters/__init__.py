"""
Scripters can be passed to `source()` to allow it to interact with different shells.

The default `Scripter` is for (mostly) posix-compliant shells. If your shell is not posix-compliant, you must pass a specialized Scripter to `source()`. It is known to work with `bash`, `zsh`, `ksh`, and `fish`.

This module also provides a specialized `Scripter` for csh and tcsh called `CshScripter`.
"""

from .csh_scripter import CshScripter
from .fish_scripter import FishScripter
from .scripter import Scripter

__all__ = ("Scripter", "CshScripter", "FishScripter")
