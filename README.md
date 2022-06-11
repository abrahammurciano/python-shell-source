# python-shell-source
A python module for sourcing variables from shell scripts

## Installation
```sh
$ pip install shell-source
```

## Documentation

The full documentation is available [here](https://abrahammurciano.github.io/python-shell-source/shell_source)

## Usage
This module provides a function `source` which attempts to mimic the shell's `source` command.

The purpose of this function is to allow you to run a shell script which sets either environment variables or local variables, and then give you access to those variables. Normally this is not a straght-forward task, but this function achieves it by running the script in its intended shell then injecting commands to the shell to print its local variables and its environment variables. Finally it collects the shell's stdout and parses it to return to you with exactly the data you asked for.

### Basic Usage

If you just pass a script (and possibly an interpreter) you'll get back all the environment variables and local variables visible to the script.

```py
>>> from shell_source import source
>>> # determines which shell to use from the shebang
>>> variables = source("path/to/script.sh")
>>> # Specify exactly which interpreter you want (recommended)
>>> variables = source("path/to/script.sh", "bash")
>>> # It returns a dictionary of local and environment variables known by the script.
>>> variables
{"USER": "abraham", "PATH": "/bin:/usr/bin", ..., "foo": "bar"}
```

### Requesting Specific Variables

If you specify the argument `variables`, then only those variables you passed will be present as keys in the returned dictionary.

```py
>>> source("path/to/script.sh", variables=("foo", "bar", "biz"))
{"foo": ..., "bar": ..., "biz", ...}
```

### Ignoring Local Variables

If you don't want to obtain any local variables set by the script, but only want the environment variables, you can pass `ignore_locals=True`.

### Supporting Different Shells

This module has been tested to work with `bash`, `zsh`, `csh`, `tcsh`, `ksh`, and `fish`. You can use any other shell that's somewhat posix compliant, but it it doesn't work, you may use the `ShellConfig` class to indicate to `source()` how to interact with your shell.

The class `ShellConfig` contains several string templates which are used to run the necessary commands with the shell. If the shell you want to use doesn't support any of the commands set by default in that class, you can pass an instance of `ShellConfig` to `source()` to override the default templates.

For example, imagine you have a strange shell that uses `@foo` instead of `$foo` to get the value of the variable foo, and that redirects the output of a command like this:
```
$ redirect 'echo hello' to /path/to/file
```

You would call `source` like this to tell it how to interact with your shell:
```py
source(
	"path/to/script.sh",
	"myshell",
	shell_config=ShellConfig(
		redirect_stdout="redirect '{cmd}' to {file}",
		get_var="@{var}",
	)
)
```