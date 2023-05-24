import logging
import re
import shlex
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Collection, Dict, Iterable, Sequence, Union

from .scripters import Scripter

logger = logging.getLogger(__name__)


def source(
    script: Union[str, Path],
    shell: str = "sh",
    *,
    args: Iterable[str] = (),
    variables: Collection[str] = (),
    ignore_locals: bool = False,
    scripter: Scripter = Scripter(),
    **subprocess_kwargs,
) -> Dict[str, str]:
    """Run a shell script and return its variables as a dictionary.

    > NOTE: If the script defines variables with newlines in their values it is undefined behaviour, though it will not raise an exception.

    Args:
        script: The shell script to source. It may contain arguments, file redirections, etc so long as it is supported by the shell you give.
        shell: The shell to use. If the shell you give is in the path it's name suffices, otherwise give the path to it. You may also pass flags, such as -x or -e. Default is "sh".
        args: Any extra arguments to pass to the sourced script. Default is no arguments.
        variables: The names of the variables set in the script to return. By default, all variables are returned.
        ignore_locals: If True, no local variables set by the script are returned. Default is False.
        scripter: An instance of Scripter that knows how to interact with the given shell. If your shell is (somewhat) posix-compliant the default should work. `csh` and `tcsh` must use `CshScripter`.
        subprocess_kwargs: Any other keyword arguments are passed to subprocess.run. By default, check=True is passed. Also, args, input and text are not allowed.
    """
    subprocess_kwargs.setdefault("check", True)
    disallowed_kwargs = {"args", "input", "text"}
    if disallowed_kwargs & subprocess_kwargs.keys():
        raise TypeError(
            f"Illegal arguments to source(): {', '.join(disallowed_kwargs & subprocess_kwargs.keys())}"
        )
    with TemporaryDirectory() as tmpdir:
        vars_file = Path(tmpdir) / "vars"
        stdin = scripter.script(
            script,
            vars_file,
            args=args,
            variables=variables,
            ignore_locals=ignore_locals,
        )
        subprocess.run(
            shlex.split(shell),
            input=stdin,
            text=True,
            **subprocess_kwargs,
        )
        return _parse_vars(vars_file.read_text())


_SPLIT_PATTERN = re.compile(r"[\t= ]")


def _parse_vars(stdout: str) -> Dict[str, str]:
    return {
        name: value.strip()
        for name, value in (
            re.split(_SPLIT_PATTERN, line, 1) for line in _split_lines(stdout)
        )
    }


def _split_lines(stdout: str) -> Sequence[str]:
    """Splits lines of stdout but groups lines that can't be valid on their own together with the previous line."""
    result = []
    for line in stdout.splitlines():
        if re.search(_SPLIT_PATTERN, line):
            result.append(line)
        else:
            try:
                result[-1] += line
            except IndexError:
                logger.warning(
                    f"Expected a line matching '.*[\t=].*' but instead found '{line}'. Ignoring this line."
                )
    return result
