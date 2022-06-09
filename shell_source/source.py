import logging
import re
import shlex
import subprocess
from pathlib import Path
from typing import Collection, Dict, Iterable, Mapping, Sequence, Union
from .shell_config import ShellConfig


logger = logging.getLogger(__name__)


def source(
    script: Union[str, Path],
    shell: str = "sh",
    *,
    variables: Collection[str] = (),
    ignore_locals: bool = False,
    check: bool = False,
    env: Mapping[str, str] = {},
    redirect_stdout_to: Union[str, Path] = "/dev/stderr",
    shell_config: ShellConfig = ShellConfig(),
) -> Dict[str, str]:
    """Run a shell script and return its variables as a dictionary.

    > NOTE: If the script defines variables with newlines in their values it is undefined behaviour, though it will not raise an exception.

    Args:
        script: The shell script to source.
        shell: The shell to use. If the shell you give is in the path it's name suffices, otherwise give the path to it. Default is sh.
        variables: The names of the variables set in the script to return. By default, all variables are returned.
        ignore_locals: If True, no local variables set by the script are returned.
        check: If True, a subprocess.CalledProcessError is raised if the script fails.
        env: A dictionary of environment variables to use. By default the environment is cleared. To keep the current environment, pass `None` or `os.environ`.
        redirect_output_to: The file to send the output of the script to. By default it's sent to stderr. It cannot be sent to stdout. To suppress it completely, pass "/dev/null".
        shell_config: An instance of ShellConfig that specifies how to interact with the shell. If your shell is (somewhat) posix-compliant the default should work.
    """
    return _parse_stdout(
        subprocess.run(
            shlex.split(shell),
            input=_get_cmds(
                str(script),
                check,
                variables,
                str(redirect_stdout_to),
                ignore_locals,
                shell_config,
            ),
            check=check,
            env=env,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout
    )


_SPLIT_PATTERN = re.compile(r"[\t= ]")


def _parse_stdout(stdout: str) -> Dict[str, str]:
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
    script: str,
    check: bool,
    variables: Collection[str],
    redirect_stdout_to: str,
    ignore_locals: bool,
    shell_config: ShellConfig,
) -> str:
    source_cmd = shell_config.source_cmd.format(script=script)
    redirected = shell_config.redirect_stdout.format(
        cmd=source_cmd, file=redirect_stdout_to
    )
    exit_or_true = (
        shell_config.exit_cmd.format(code=shell_config.prev_exit_code)
        if check
        else "true"
    )
    full_source_cmd = shell_config.boolean_or.format(cmd1=redirected, cmd2=exit_or_true)
    get_vars_cmds = _get_vars_cmds(variables, ignore_locals, shell_config)
    return " ;\n".join((full_source_cmd, *get_vars_cmds))


def _get_vars_cmds(
    variables: Collection[str], ignore_locals: bool, shell_config: ShellConfig
) -> Iterable[str]:
    if variables:
        return (
            f"echo {var}={shell_config.get_var.format(var=var)}" for var in variables
        )
    return [*(() if ignore_locals else (shell_config.get_all_locals,)), "env"]
