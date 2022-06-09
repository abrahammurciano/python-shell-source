from functools import cached_property
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
from typing import Mapping, TextIO
from shell_source import source
import pytest


class Shell:
    def __init__(
        self,
        cmd: str,
        *,
        setenv: str = "export {name}='{value}'\n",
        setlocal: str = "{name}='{value}'\n",
    ):
        self.cmd = cmd
        self.setenv = setenv
        self.setlocal = setlocal

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

    @cached_property
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


@pytest.fixture(
    params=[
        pytest.param(Shell("sh"), id="sh"),
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
            Shell("fish", setlocal="set {name} '{value}'\n"),
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


def test_all_vars(shell: Shell, script: Path):
    result = source(script, shell=shell.cmd)
    for name, value in shell.all_variables.items():
        assert result[name] == value


def test_only_env(shell: Shell, script: Path):
    result = source(script, shell=shell.cmd, ignore_locals=True)
    for name, value in shell.environment_variables.items():
        assert result[name] == value
    for name, value in shell.local_variables.items():
        assert name not in result


def test_specific_vars(shell: Shell, script: Path):
    variables = (
        list(shell.local_variables)[::2] + list(shell.environment_variables)[::2]
    )
    result = source(script, shell=shell.cmd, variables=variables)
    assert result == {name: shell.all_variables[name] for name in variables}


def test_failing_script(shell: Shell, failing_script: Path):
    with pytest.raises(subprocess.CalledProcessError):
        source(failing_script, shell=shell.cmd, check=True)


def test_printing_script(
    shell: Shell,
    printing_script: Path,
    message: str,
    capfd: pytest.CaptureFixture,
):
    source(printing_script, shell=shell.cmd)
    captured = capfd.readouterr()
    assert message not in captured.out
    assert message in captured.err


def test_printing_script_to_null(
    shell: Shell, printing_script: Path, message: str, tmpdir: Path
):
    source(printing_script, shell=shell.cmd, redirect_stdout_to="/dev/null")
    # TODO: Check stdout and stderr are empty


def test_printing_script_to_file(
    shell: Shell, printing_script: Path, message: str, tmpdir: Path
):
    stdout_log = tmpdir / "source.stdout"
    source(printing_script, shell=shell.cmd, redirect_stdout_to=stdout_log)
    with stdout_log.open() as f:
        assert message in f.read()
