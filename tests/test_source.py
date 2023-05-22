import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, TextIO

import pytest

from shell_source import ShellConfig, source


@dataclass
class Shell:
    cmd: str
    setenv: str = "export {name}='{value}'\n"
    setlocal: str = "{name}='{value}'\n"
    config: Optional[ShellConfig] = None
    argfmt: str = "${{{pos}}}"

    @property
    def name(self) -> str:
        return re.split(rf"\s|{os.path.sep}", self.cmd)[-1]

    @property
    def local_variables(self) -> Mapping[str, str]:
        return {
            "local_var_name_1": "local_var_value_1",
            "local_var_name_2": "local_var_value_2",
        }

    @property
    def environment_variables(self) -> Mapping[str, str]:
        return {
            "env_var_name_1": "env_var_value_1",
            "env_var_name_2": "env_var_value_2",
        }

    @property
    def all_variables(self) -> Mapping[str, str]:
        return {**self.local_variables, **self.environment_variables}

    def write_script(self, script: TextIO):
        script.write(f"#!/usr/bin/env {self.name}\n")
        script.writelines(
            fmt_str.format(name=name, value=value)
            for variables, fmt_str in (
                (self.local_variables, self.setlocal),
                (self.environment_variables, self.setenv),
            )
            for name, value in variables.items()
        )
        script.flush()

    def get_arg(self, pos: int) -> str:
        return self.argfmt.format(pos=pos)


@pytest.fixture(
    params=[
        pytest.param(Shell("bash"), id="bash"),
        pytest.param(
            Shell(
                "tcsh",
                setenv="setenv {name} '{value}'\n",
                setlocal="set {name}='{value}'\n",
            ),
            id="tcsh",
        ),
        pytest.param(
            Shell(
                "csh",
                setenv="setenv {name} '{value}'\n",
                setlocal="set {name}='{value}'\n",
                config=ShellConfig(prev_exit_code="$status"),
            ),
            id="csh",
        ),
        pytest.param(
            Shell(
                "fish",
                setlocal="set {name} '{value}'\n",
                config=ShellConfig(prev_exit_code="$status"),
                argfmt="$argv[{pos}]",
            ),
            id="fish",
        ),
        pytest.param(Shell("ksh"), id="ksh"),
        pytest.param(Shell("zsh"), id="zsh"),
        pytest.param(Shell("/usr/bin/env bash"), id="env bash"),
    ]
)
def shell(request) -> Shell:
    shell: Shell = request.param
    split_cmd = shlex.split(shell.cmd)
    if shutil.which(split_cmd[1 if "env" in split_cmd[0] else 0]):
        return shell
    pytest.skip(f"The shell {shell.cmd} is not installed on the system.")


@pytest.fixture
def script(tmpdir: Path, shell: Shell) -> Path:
    script = tmpdir / f"{shell.name}.sh"
    with script.open("w") as f:
        shell.write_script(f)
    return script


@pytest.fixture(params=["exit 1", "false"])
def failing_script(request, tmpdir: Path, shell: Shell) -> Path:
    script = tmpdir / f"{shell.name}.failing.sh"
    with script.open("w") as f:
        shell.write_script(f)
        f.write(request.param)
    return script


@pytest.fixture
def message() -> str:
    return "Loaded script successfully!"


@pytest.fixture
def printing_script(tmpdir: Path, shell: Shell, message: str) -> Path:
    script = tmpdir / f"{shell.name}.printing.sh"
    with script.open("w") as f:
        shell.write_script(f)
        f.write(f"echo {message}")
    return script


@pytest.fixture
def arg_printing_script(tmpdir: Path, shell: Shell) -> Path:
    script = tmpdir / f"{shell.name}.arg_printing.sh"
    with script.open("w") as f:
        shell.write_script(f)
        f.write(f"echo {shell.get_arg(1)}")
    return script


@pytest.fixture(
    params=[pytest.param(True, id="check"), pytest.param(False, id="no_check")],
)
def check(request) -> bool:
    return request.param


@pytest.fixture
def source_kwargs(shell: Shell, check: bool) -> Dict[str, Any]:
    return {
        "shell": shell.cmd,
        "check": check,
        **({"shell_config": shell.config} if shell.config else {}),
    }


def test_all_vars(shell: Shell, script: Path, source_kwargs: Dict[str, Any]):
    result = source(script, **source_kwargs)
    for name, value in shell.all_variables.items():
        assert result[name] == value


def test_only_env(shell: Shell, script: Path, source_kwargs: Dict[str, Any]):
    result = source(script, ignore_locals=True, **source_kwargs)
    for name, value in shell.environment_variables.items():
        assert result[name] == value
    for name, value in shell.local_variables.items():
        assert name not in result


def test_specific_vars(shell: Shell, script: Path, source_kwargs: Dict[str, Any]):
    variables = (
        list(shell.local_variables)[::2] + list(shell.environment_variables)[::2]
    )
    result = source(script, variables=variables, **source_kwargs)
    assert result == {name: shell.all_variables[name] for name in variables}


def test_failing_script(shell: Shell, failing_script: Path):
    shell_config_arg: Dict[str, Any] = (
        {"shell_config": shell.config} if shell.config else {}
    )
    with pytest.raises(subprocess.CalledProcessError):
        source(failing_script, shell=shell.cmd, check=True, **shell_config_arg)


def test_printing_script(
    printing_script: Path,
    message: str,
    capfd: pytest.CaptureFixture,
    source_kwargs: Dict[str, Any],
):
    source(printing_script, **source_kwargs)
    captured = capfd.readouterr()
    assert message == captured.out.strip()


def test_arg_printing_script(
    arg_printing_script: Path,
    capfd: pytest.CaptureFixture,
    source_kwargs: Dict[str, Any],
):
    message = "Hello, World!"
    script = f"{arg_printing_script} '{message}'"
    source(script, **source_kwargs)
    captured = capfd.readouterr()
    assert message == captured.out.strip()


def test_suppressed_printing_script(
    printing_script: Path,
    capfd: pytest.CaptureFixture,
    source_kwargs: Dict[str, Any],
):
    source(printing_script, **source_kwargs, stdout=subprocess.DEVNULL)
    captured = capfd.readouterr()
    assert "" == captured.out.strip()


def test_suppressed_printing_script_with_redirection(
    printing_script: Path,
    capfd: pytest.CaptureFixture,
    source_kwargs: Dict[str, Any],
):
    script = f"{printing_script} >> /dev/null"
    source(script, **source_kwargs)
    captured = capfd.readouterr()
    assert "" == captured.out.strip()
