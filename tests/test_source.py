import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, TextIO

import pytest

from shell_source import source
from shell_source.scripters import CshScripter, FishScripter, Scripter


@dataclass
class ShellTester:
    cmd: str
    set_env: str = "export {name}='{value}'\n"
    set_local: str = "{name}='{value}'\n"
    argv_fmt: str = "${{{pos}}}"
    scripter: Optional[Scripter] = None

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
                (self.local_variables, self.set_local),
                (self.environment_variables, self.set_env),
            )
            for name, value in variables.items()
        )
        script.flush()

    def get_arg(self, pos: int) -> str:
        return self.argv_fmt.format(pos=pos)


@pytest.fixture(
    params=[
        pytest.param(ShellTester("bash"), id="bash"),
        pytest.param(
            ShellTester(
                "tcsh",
                set_env="setenv {name} '{value}'\n",
                set_local="set {name}='{value}'\n",
                scripter=CshScripter(),
            ),
            id="tcsh",
        ),
        pytest.param(
            ShellTester(
                "csh",
                set_env="setenv {name} '{value}'\n",
                set_local="set {name}='{value}'\n",
                scripter=CshScripter(),
            ),
            id="csh",
        ),
        pytest.param(
            ShellTester(
                "fish",
                set_local="set {name} '{value}'\n",
                argv_fmt="$argv[{pos}]",
                scripter=FishScripter(),
            ),
            id="fish",
        ),
        pytest.param(ShellTester("ksh"), id="ksh"),
        pytest.param(ShellTester("zsh"), id="zsh"),
        pytest.param(ShellTester("/usr/bin/env bash"), id="env bash"),
    ]
)
def shell(request) -> ShellTester:
    shell: ShellTester = request.param
    split_cmd = shlex.split(shell.cmd)
    if shutil.which(split_cmd[1 if "env" in split_cmd[0] else 0]):
        return shell
    pytest.skip(f"The shell {shell.cmd} is not installed on the system.")


@pytest.fixture
def script(tmpdir: Path, shell: ShellTester) -> Path:
    script = tmpdir / f"{shell.name}.sh"
    with script.open("w") as f:
        shell.write_script(f)
    return script


@pytest.fixture(params=["exit 1", "false"])
def failing_script(request, tmpdir: Path, shell: ShellTester) -> Path:
    script = tmpdir / f"{shell.name}.failing.sh"
    with script.open("w") as f:
        shell.write_script(f)
        f.write(request.param)
    return script


@pytest.fixture
def exitting_script(request, tmpdir: Path, shell: ShellTester) -> Path:
    script = tmpdir / f"{shell.name}.exitting.sh"
    with script.open("w") as f:
        shell.write_script(f)
        f.write("exit 0")
    return script


@pytest.fixture
def message() -> str:
    return "Loaded script successfully!"


@pytest.fixture
def printing_script(tmpdir: Path, shell: ShellTester, message: str) -> Path:
    script = tmpdir / f"{shell.name}.printing.sh"
    with script.open("w") as f:
        shell.write_script(f)
        f.write(f"echo {message}")
    return script


@pytest.fixture
def arg_printing_script(tmpdir: Path, shell: ShellTester) -> Path:
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
def source_kwargs(shell: ShellTester, check: bool) -> Dict[str, Any]:
    return {
        "shell": shell.cmd,
        "check": check,
        **({"scripter": shell.scripter} if shell.scripter else {}),
    }


def test_all_vars(shell: ShellTester, script: Path, source_kwargs: Dict[str, Any]):
    result = source(script, **source_kwargs)
    for name, value in shell.all_variables.items():
        assert result[name] == value


def test_only_env(shell: ShellTester, script: Path, source_kwargs: Dict[str, Any]):
    result = source(script, ignore_locals=True, **source_kwargs)
    for name, value in shell.environment_variables.items():
        assert result[name] == value
    for name, value in shell.local_variables.items():
        assert name not in result


def test_specific_vars(shell: ShellTester, script: Path, source_kwargs: Dict[str, Any]):
    variables = (
        list(shell.local_variables)[::2] + list(shell.environment_variables)[::2]
    )
    result = source(script, variables=variables, **source_kwargs)
    assert result == {name: shell.all_variables[name] for name in variables}


def test_failing_script(
    failing_script: Path, source_kwargs: Dict[str, Any], check: bool
):
    if not check:
        pytest.skip("No need to test failing script with check=False.")
    with pytest.raises(subprocess.CalledProcessError):
        source(failing_script, **source_kwargs)


def test_exitting_script(
    exitting_script: Path, source_kwargs: Dict[str, Any], check: bool
):
    if check:
        pytest.skip("No need to test exitting script with check=True.")
    result = source(exitting_script, **source_kwargs)
    for name, value in result.items():
        assert result[name] == value


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
