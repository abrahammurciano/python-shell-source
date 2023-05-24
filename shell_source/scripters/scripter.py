import shlex
from pathlib import Path
from typing import Collection, Iterable, Union


class Scripter:
    """This class writes scripts to be executed by a shell.

    This class tries to be compatible with most shells. If you want to use a shell that doesn't behave like most mainstream ones, you can extend this class and pass an instance to `source`. Some specialized subclasses are provided for some shells.
    """

    def script(
        self,
        script: Union[str, Path],
        vars_file: Path,
        *,
        args: Iterable[str] = (),
        variables: Collection[str] = (),
        ignore_locals: bool = False,
    ) -> str:
        """Create a script that sources another script and writes its variables to a file.

        Args:
            script: The shell script to source.
            vars_file: The file to write the variables to.
            args: Any extra arguments to pass to the sourced script. Default is no arguments.
            variables: The names of the variables set in the script to return. By default, all variables are returned.
            ignore_locals: If True, no local variables set by the script are returned. Default is False.
        """
        write_variables = self.write_variables(vars_file, variables, ignore_locals)
        trap = self.trap(write_variables)
        source = self.source(script, args)
        return f"{trap} ;\n{source} ;"

    def source(self, script: Union[str, Path], args: Iterable[str]) -> str:
        """Get a command to source a script.

        Args:
            script: The script to source.
        """
        return f"source {script} {' '.join(shlex.quote(arg) for arg in args)}"

    def trap(self, command: str) -> str:
        """Get a command that sets a trap to execute a command on exit.

        The default implementation uses `trap 'command' EXIT`. For shells which don't immediately exit when a sourced script calls exit, and also don't support trap (such as `csh` and `tcsh`) you should override `script` to not call `trap`.

        Args:
            command: The command to execute on exit.
        """
        return f"trap {shlex.quote(command)} EXIT"

    def dereference(self, variable: str) -> str:
        """Get a command that dereferences the value of a variable.

        The default implementation uses `${variable}`.

        Args:
            variable: The name of the variable to print.
        """
        return f"${{{variable}}}"

    def redirect(self, command: str, output_file: Path) -> str:
        """Get a command that redirects the stdout of a command to a file.

        The default implementation uses `>>`.

        Args:
            command: The command to redirect.
            output_file: The file to redirect to.
        """
        return f"{command} >> {output_file}"

    def print_variables(
        self, variables: Collection[str], ignore_locals: bool
    ) -> Iterable[str]:
        """Get a series of commands that, when executed sequentially, print the requested variables.

        Each variable must be printed in the format `name=value<newline>` or `name<tab>value<newline>`.

        Args:
            variables: The names of the variables set in the script to print. By default, all local and environment variables are printed.
            ignore_locals: If True, local variables not printed. Default is False.
        """
        if variables:
            return (f"echo {var}={self.dereference(var)}" for var in variables)
        commands = []
        if not ignore_locals:
            commands.append(self.print_locals())
        commands.append(self.print_env())
        return commands

    def write_variables(
        self, output_file: Path, variables: Collection[str], ignore_locals: bool
    ) -> str:
        """Get a command that writes the requested variables to a file.

        Args:
            output_file: The file to write the variables to.
            variables: The names of the variables set in the script to write. By default, all local and environment variables are written.
            ignore_locals: If True, local variables not written. Default is False.
        """
        return " ; ".join(
            self.redirect(cmd, output_file)
            for cmd in self.print_variables(variables, ignore_locals)
        )

    def print_locals(self) -> str:
        """Get a command that prints all local variables.

        The default implementation uses `set`.
        """
        return "set"

    def print_env(self) -> str:
        """Get a command that prints all environment variables.

        The default implementation uses `env`.
        """
        return "env"
