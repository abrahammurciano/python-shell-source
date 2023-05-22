import logging
import re
import shlex
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Collection, Dict, Iterable, Mapping, Optional, Sequence, Union

from .shell_config import ShellConfig

logger = logging.getLogger(__name__)


def source(
    script: Union[str, Path],
    shell: str = "sh",
    *,
    variables: Collection[str] = (),
    ignore_locals: bool = False,
    shell_config: ShellConfig = ShellConfig(),
    **subprocess_kwargs,
) -> Dict[str, str]:
    """Run a shell script and return its variables as a dictionary.

    > NOTE: If the script defines variables with newlines in their values it is undefined behaviour, though it will not raise an exception.

    Args:
        script: The shell script to source. It may contain arguments, file redirections, etc so long as it is supported by the shell you give.
        shell: The shell to use. If the shell you give is in the path it's name suffices, otherwise give the path to it. You may also pass flags, such as -x or -e. Default is "sh".
        variables: The names of the variables set in the script to return. By default, all variables are returned.
        ignore_locals: If True, no local variables set by the script are returned. Default is False.
        shell_config: An instance of ShellConfig that specifies how to interact with the given shell. If your shell is (somewhat) posix-compliant the default should work.
        subprocess_kwargs: Any other keyword arguments are passed to subprocess.run. By default, check=True is passed. Also, args, input and text are not allowed.
    """
    check = subprocess_kwargs.pop("check", True)
    disallowed_kwargs = {"args", "input", "text"}
    if disallowed_kwargs & subprocess_kwargs.keys():
        raise TypeError(
            f"Illegal arguments to source(): {', '.join(disallowed_kwargs & subprocess_kwargs.keys())}"
        )
    with TemporaryDirectory() as tmpdir:
        vars_file = Path(tmpdir) / "vars"
        stdin = _get_cmds(
            script=script,
            vars_file=vars_file,
            check=check,
            variables=variables,
            ignore_locals=ignore_locals,
            shell_config=shell_config,
        )
        subprocess.run(
            shlex.split(shell),
            input=stdin,
            text=True,
            check=check,
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


def _get_cmds(
    *,
    script: Union[str, Path],
    vars_file: Path,
    check: bool,
    variables: Collection[str],
    ignore_locals: bool,
    shell_config: ShellConfig,
) -> str:
    """Get a string to be sent to the stdin of the shell."""
    source_cmd = shell_config.source_cmd.format(script=script)
    exit_or_true = (
        shell_config.exit_cmd.format(code=shell_config.prev_exit_code)
        if check
        else "true"
    )
    full_source_cmd = shell_config.boolean_or.format(cmd1=source_cmd, cmd2=exit_or_true)
    get_vars_cmds = (
        shell_config.redirect_stdout.format(cmd=cmd, file=vars_file)
        for cmd in _get_vars_cmds(variables, ignore_locals, shell_config)
    )
    return " ;\n".join((full_source_cmd, *get_vars_cmds))


def _get_vars_cmds(
    variables: Collection[str], ignore_locals: bool, shell_config: ShellConfig
) -> Iterable[str]:
    if variables:
        return (
            f"echo {var}={shell_config.get_var.format(var=var)}" for var in variables
        )
    return [*(() if ignore_locals else (shell_config.get_all_locals,)), "env"]
