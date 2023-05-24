# python-shell-source
A python module for sourcing variables from shell scripts.

## Installation

You can install this package with pip or conda.
```sh
$ pip install shell-source
```
```sh
$ conda install -c abrahammurciano shell-source
```

## Documentation

The full documentation is available [here](https://abrahammurciano.github.io/python-shell-source/shell_source)

## Usage
This module provides a function `source` which attempts to mimic the shell's source command.

The purpose of this function is to allow you to run a shell script which sets either environment variables or local variables, and then give you access to those variables. Normally this is not a straght-forward task, but this function achieves it by running the script in its intended shell then injecting commands to the shell to write its local variables and its environment variables to a temporary file. Finally it reads the temporary file and parses it to return to you with exactly the data you asked for.

### Basic Usage

If you just pass a script and an interpreter you'll get back all the environment variables and local variables visible to and set by the script.

```py
>>> from shell_source import source
>>> variables = source("path/to/script.sh", "bash")
>>> # It returns a dictionary of local and environment variables known by the script.
>>> variables
{"USER": "abraham", "PATH": "/bin:/usr/bin", ..., "foo": "bar"}
```

### Requesting Specific Variables

If you specify the argument `variables`, then only those variables you passed will be present as keys in the returned dictionary.

```py
>>> source("path/to/script.sh", "zsh", variables=("foo", "bar", "biz"))
{"foo": ..., "bar": ..., "biz", ...}
```

### Ignoring Local Variables

If you don't want to obtain any local variables set by the script, but only want the environment variables, you can pass `ignore_locals=True`.

### Passing Arguments to the shell

If you want to pass arguments to the shell, for example `-x` or `-e`, you can pass it directly in the `shell` argument.

```py
>>> source("path/to/script.sh", "bash -x")
```

### Passing Arguments to the script

If you want to pass arguments to the script being sourced, you can pass them in the `args` argument.

```py
>>> source("path/to/script.sh", "bash", args=("foo", "bar"))
```

### Supporting Different Shells

This module has been tested to work with `bash`, `zsh`, and `ksh` out of the box. You can use any other shell that's somewhat posix compliant, but it it doesn't work, you may have to create a class derived from the `Scripter` class to indicate to `source` how to interact with the shell you want to use.

Some specialized implementations of `Scripter` are provided in `shell_source.scripters` for shells that are not posix compliant, such as `csh`, `tcsh` and `fish`.

For example, to use `tcsh` to source a script, you can use the `CshScripter` class like so:

```py
>>> source("path/to/script.csh", "tcsh", scripter=CshScripter())
```
