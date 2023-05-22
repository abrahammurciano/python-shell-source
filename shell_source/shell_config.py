from dataclasses import dataclass


@dataclass
class ShellConfig:
    """
    This class instructs this library how to interact with the shell. If you want to use a shell that doesn't behave like most mainstream ones, you can pass an instance of this class to `source` with the correct string templates.

    Anything mentioned here in curly braces reffers to a variable of that name in a string template.

    Args:
        source_cmd: How to source a {script}.
        exit_cmd: How to exit the shell with a given exit {code}.
        redirect_stdout: How to redirect the output of a {cmd} to a {file}.
        boolean_or: How to run {cmd1} and if it fails, run {cmd2}.
        get_var: How to get the value of a variable named {var}.
        get_all_locals: How to print all local variables.
        prev_exit_code: How to get the exit code of the previous command.
    """

    source_cmd: str = "source {script}"
    exit_cmd: str = "exit {code}"
    redirect_stdout: str = "{cmd} >> {file}"
    boolean_or: str = "{cmd1} || {cmd2}"
    get_var: str = "${var}"
    get_all_locals: str = "set"
    prev_exit_code: str = "$?"
