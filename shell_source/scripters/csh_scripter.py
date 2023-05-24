from pathlib import Path
from typing import Collection, Iterable, Union

from .scripter import Scripter


class CshScripter(Scripter):
    """A specialized Scripter for csh. Pass a instance of this class to `source` to source csh scripts."""

    def trap(self, command: str) -> str:
        return "true"  # csh doesn't support trap. This is a no-op.

    def script(
        self,
        script: Union[str, Path],
        vars_file: Path,
        *,
        args: Iterable[str] = (),
        variables: Collection[str] = (),
        ignore_locals: bool = False,
    ) -> str:
        source = self.source(script, args)
        write_variables = self.write_variables(vars_file, variables, ignore_locals)
        post_source = self.forward_status(write_variables)
        return f"{source} ;\n{post_source} ;"

    def forward_status(self, command: str) -> str:
        """Get a command that saves the current exit status of the previous command, runs a command, then restores the exit status.

        Args:
            command: The command to run.
        """
        return f"set saved_status=$status ;\n{command} ;\nset status=$saved_status"
