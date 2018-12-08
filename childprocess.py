import io
import os
import shlex
import signal
import subprocess
import sys
from enum import Enum
from typing import Dict, List, Tuple, Union

class ChildProcessIO(Enum):
    """The desired creation behavior for a ChildProcess's standard input/output/error file descriptors.

    Can be supplied to ChildProcessBuilder.stdin, ChildProcessBuidler.stdout, or ChildProcessBuilder.stderr.

    Values:
    PIPE - Open a pipe to the I/O stream, and make it accessible via ChildProcess.stdin/stdout/stderr
    INHERIT - Upon creation, inherit the corresponding I/O stream from the parent process
    NULL - Provide empty input, or ignore output
    STDOUT - Redirect STDERR to the same file descriptor as STDOUT. Only valid for ChildProcessBuilder.stderr"""
    PIPE = 1
    INHERIT = 2
    NULL = 3
    STDOUT = 4

class ChildProcess():
    """A child process.

    Should not be instantiated directly - instead, use ChildProcessBuilder.spawn() to get an instance.

    May be used with Python's `with` statement - upon the exit of the block, the process will be terminated non-forcefully.
    See `ChildProcess.terminate`"""
    def __init__(self, args, env, cwd, stdin, stdout, stderr):
        self._args = args
        self._env = env
        self._cwd = cwd

        popen_stdin, deferred_input = self._make_stdin(stdin)
        popen_stdout = self._make_stdout(stdout)
        popen_stderr = self._make_stderr(stderr)

        self._is_stopped = False
        self._popen = subprocess.Popen(
            args, cwd=cwd, env=env,
            stdin=popen_stdin, stdout=popen_stdout, stderr=popen_stderr)

        if deferred_input:
            self._popen.stdin.write(deferred_input)

    @property
    def args(self):
        """The argument array provided upon the ChildProcess's creation. Read-only."""
        return self._args

    @property
    def env(self):
        """The environment variable definitions provided upon the ChildProcess's creation. Read-only."""
        return self._env

    @property
    def cwd(self):
        """The working directory of the ChildProcess, provided upon the ChildProcess's creation. Read-only."""
        return self._cwd

    @property
    def pid(self):
        """The system's pid for the child process. Read-only."""
        return self._popen.pid

    @property
    def exit_code(self):
        """Either the integer exit code of the child process, or None if it is still running. Read-only.

        One can spin-wait for a child process to exit with `while process.exit_code is None`."""
        self._popen.poll()
        return self._popen.returncode

    @property
    def stdin(self):
        """The input stream for the child process, if it was created by ChildProcessIO.PIPE.

        Also accessible if input was provided in string format.

        Attempts to access an inaccessible child process file descriptor result in a RuntimeError."""
        if not self._stdin_writeable:
            raise RuntimeError("The process's stdin pipe is inaccessible")
        return self._popen.stdin

    @property
    def stdout(self):
        """The output stream for the child process, if it was created by ChildProcessIO.PIPE.

        Attempts to access an inaccessible child process file descriptor result in a RuntimeError."""
        if not self._stdout_readable:
            raise RuntimeError("The process's stdout pipe is inaccessible")
        return self._popen.stdout

    @property
    def stderr(self):
        """The error output stream for the child process, if it was created by ChildProcessIO.PIPE.

        Attempts to access an inaccessible child process file descriptor result in a RuntimeError."""
        if not self._stderr_readable:
            raise RuntimeError("The process's stderr pipe is inaccessible")
        return self._popen.stderr

    def _make_stdin(self, stdin):
        if stdin == ChildProcessIO.PIPE:
            self._stdin_writeable = True
            return subprocess.PIPE, None
        elif stdin == ChildProcessIO.INHERIT:
            self._stdin_writeable = False
            return sys.stdin, None
        elif stdin == ChildProcessIO.NULL:
            self._stdin_writeable = False
            return open(os.devnull, 'r'), None
        elif isinstance(stdin, io.IOBase):
            self._stdin_writeable = False
            return stdin, None
        else:
            self._stdin_writeable = True
            return subprocess.PIPE, stdin

    def _make_stdout(self, stdout):
        if stdout == ChildProcessIO.PIPE or stdout == ChildProcessIO.STDOUT:
            self._stdout_readable = True
            return subprocess.PIPE
        elif stdout == ChildProcessIO.INHERIT:
            self._stdout_readable = False
            return sys.stdout
        elif stdout == ChildProcessIO.NULL:
            self._stdout_readable = False
            return open(os.devnull, 'w')
        else:
            self._stdout_readable = False
            return stdout

    def _make_stderr(self, stderr):
        if stderr == ChildProcessIO.PIPE:
            self._stderr_readable = True
            return subprocess.PIPE
        elif stderr == ChildProcessIO.STDOUT:
            self._stderr_readable = False
            return subprocess.STDOUT
        elif stderr == ChildProcessIO.INHERIT:
            self._stderr_readable = False
            return sys.stderr
        elif stderr == ChildProcessIO.NULL:
            self._stderr_readable = False
            return open(os.devnull, 'w')
        else:
            self._stderr_readable = False
            return stderr

    def start(self):
        """Resume execution of a process which has previously been stopped.

        Requires platform support - if unsupported on this platform, raises an OSError."""
        if not hasattr(signal, "SIGCONT"):
            raise OSError("No platform support for stopping/starting processes")
        self._is_stopped = False
        self.kill(signal.SIGCONT)

    def stop(self):
        """Suspend execution of a running process.

        Requires platform support - if unsupported on this platform, raises an OSError."""
        if not hasattr(signal, "SIGTSTP"):
            raise OSError("No platform support for stopping/starting processes")
        self.kill(signal.SIGTSTP)
        self._is_stopped = True

    def terminate(self, force=False):
        """Request that a process terminate execution.

        Requests to terminate may be ignored by the child process, and may not be serviced
        if the process is stopped. If this is undesirable, a process may be forced to exit
        (even when stopped) by the `force` argument, though this may result in the process
        failing to close open files or database connections.

        Parameters
        ----------
        force: bool, optional
            Terminate the process immediately in a way that cannot be ignored.
        """
        if force:
            self._popen.kill()
        else:
            self._popen.terminate()

    def is_running(self):
        """Return true if the process is executing, and false otherwise"""
        return not (self.is_finished() or self.is_stopped())

    def is_stopped(self):
        """Return true if the process is suspended but not yet finished, and false otherwise"""
        return not self.is_finished() and self._is_stopped

    def is_finished(self):
        """Return true if the process has exited, and false otherwise"""
        return self.exit_code is not None

    def wait_for_finish(self, timeout=None):
        """Block until the process finishes. May optionally wait up to a maximum length of time

        If the process does not terminate after `timeout` seconds, raise a
        `subprocess.TimeoutExpired` exception. It is safe to catch this exception and retry.

        Returns the process.

        Parameters
        ----------
        timeout: int, optional
            Amount of time in seconds to wait for the process to finish.

        Returns
        -------
        ChildProcess
            The process on which it was called, in order to enable 'fluent programming'
        """

        self._popen.wait(timeout)
        return self

    def kill(self, signal):
        """Send a signal to the process.

        The available signals are defined in the `signal` module"""
        self._popen.send_signal(signal)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if not self.is_finished():
            self._popen.kill()


class ChildProcessBuilder():
    """Builder to obtain instances of ChildProcess.

    One ChildProcessBuilder may be used to obtain any number of ChildProcess instances."""
    def __init__(self, args, env=None, cwd=None, stdin=None, stdout=None, stderr=None):
        """Initialize the attributes of the builder.

        Refer to documentation for each attribute for their default behavior and the particulars of their usage.

        Parameters
        ----------
        args
            The desired value of the arguments (see ChildProcessBuilder.args). Required.
        env
            The desired environment variable definitions (see ChildProcessBuilder.env). Optional.
        cwd
            The desired current working directory (see ChildProcessBuilder.cwd). Optional.
        stdin
            The desired standard input (see ChildProcessBuilder.stdin). Optional.
        stdout
            The desired standard output (see ChildProcessBuilder.stdout). Optional.
        stderr
            The desired standard error output (see ChildProcessBuilder.stderr). Optional."""
        self.args = args
        self.env = env
        self.cwd = cwd
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def spawn(self):
        """Create a child process from the current ChildProcessBuilder attributes.

        Returns
        -------
        ChildProcess
            The spawned ChildProcess
        """
        return ChildProcess(self.args, self.env, self.cwd, self.stdin, self.stdout, self.stderr)

    @property
    def args(self) -> List[str]:
        """The arguments with which the child process will be created, as a list of string tokens.

        As is convention, args[0] is the name of the executable that should be invoked.

        May be provided as a List of tokens, each of which will be converted to a string.
        May be provided as a string, which will be tokenized in a Posix-compatible manner."""
        return self._args

    @args.setter
    def args(self, value: Union[str, List, Tuple]):
        if isinstance(value, str):
            self._args = shlex.split(value)
        elif isinstance(value, list) or isinstance(value, tuple):
            try:
                self._args = [str(obj) for obj in value]
            except:
                raise TypeError("Arguments must be convertible to strings")

    @property
    def env(self) -> Dict[str, str]:
        """Definitions of environment variables with which the child process will be created.

        The environment variables are a mapping of KEY to VALUE, where both KEY and VALUE are strings.
        The default behavior is to inherit the environment variable definitions from its parent process.

        May be modified in-place by dictionary methods (`builder.env[key] = value`), or a new dictionary may
        be provided.
        """
        return self._env

    @env.setter
    def env(self, value: Dict[str, str]):
        if value is None:
            value = dict(os.environ)
        if isinstance(value, dict):
            try:
                self._env = {str(k):str(v) for k,v in value.items()}
            except:
                raise TypeError("Environment variable names and values must be convertible to strings")
        else:
            raise TypeError("Environment variable definitions must be a dictionary")

    @property
    def cwd(self):
        """The current working directory for the child process.

        The basis of any relative paths used by the child process.
        The default behavior is to inherit the current working directory from its parent process.

        May be provided in a format convertible to a normalized `os.path`"""
        return self._cwd

    @cwd.setter
    def cwd(self, value):
        if value is None:
            value = os.getcwd()
        try:
            self._cwd = os.path.normpath(value)
        except:
            raise TypeError("Child process's current working directory must be a path-like object")

    @property
    def stdin(self):
        """The desired standard input creation behavior for the child process.

        Values include:
        ChildProcessIO.PIPE (default) - open a parent-accessible writeable pipe to the stdin fd
        ChildProcessIO.INHERIT - use the parent process's standard input fd
        ChildProcessIO.NULL - provide null input (EOF)
        A Python string - Open a PIPE to the stdin fd, and write the contents of the string upon creation
        A file-like object - the contents read from the object will be provided to the process as input

        It is the client's responsibility to make sure that standard input is used in a safe manner.
        Particular concerns include the limitations of system I/O buffers and the safe sharing of files."""
        return self._stdin

    @stdin.setter
    def stdin(self, value):
        if value is None:
            value = ChildProcessIO.PIPE
        if isinstance(value, io.BufferedReader):
            self._stdin = value.raw
        elif isinstance(value, str) or isinstance(value, io.IOBase):
            self._stdin = value
        elif value in ChildProcessIO:
            if value == ChildProcessIO.STDOUT:
                raise ValueError("Cannot pipe a process's output to its own input")
            else:
                self._stdin = value
        else:
            raise TypeError("Input can be redirected from a string, a file-like object, or a ChildProcessIO special value")

    @property
    def stdout(self):
        """The desired standard output creation behavior for the child process.

        Values include:
        ChildProcessIO.PIPE (default) - open a parent-accessible readable pipe to the stdout fd
        ChildProcessIO.INHERIT - use the parent process's standard output fd
        ChildProcessIO.NULL - ignore output
        A file-like object - the contents output by the process will be written to the object

        It is the client's responsibility to make sure that standard output is used in a safe manner.
        Particular concerns include the limitations of system I/O buffers and the safe sharing of files."""
        return self._stdout

    @stdout.setter
    def stdout(self, value):
        if value is None:
            value = ChildProcessIO.PIPE
        if isinstance(value, io.IOBase) or value in ChildProcessIO:
            self._stdout = value
        else:
            raise TypeError("Output can be redirected to a file-like object, or a ChildProcessIO special value")

    @property
    def stderr(self):
        """The desired standard error output creation behavior for the child process.

        Values include:
        ChildProcessIO.PIPE (default) - open a parent-accessible readable pipe to the stderr fd
        ChildProcessIO.INHERIT - use the parent process's standard error output fd
        ChildProcessIO.NULL - ignore error output
        A file-like object - the contents output by the process to stderr will be written to the object

        It is the client's responsibility to make sure that standard error output is used in a safe manner.
        Particular concerns include the limitations of system I/O buffers and the safe sharing of files."""
        return self._stderr

    @stderr.setter
    def stderr(self, value):
        if value is None:
            value = ChildProcessIO.PIPE
        if isinstance(value, io.IOBase) or value in ChildProcessIO:
            self._stderr = value
        else:
            raise TypeError("Error output can be redirected to a file-like object, or a ChildProcessIO special value")

class PipelineBuilder():
    """A convenience wrapper for ChildProcessBuilder to construct a pipeline of processes with each's output piped to the next's input.

    The parameters env, cwd, and stderr are shared by all processes in the pipeline.

    stdin describes the input proved to the first process, and stdout describes the output behavior of the last process."""
    def __init__(self, commands, env=None, cwd=None, stdin=None, stdout=None, stderr=None):
        if env is None:
            env = dict(os.environ)
        if cwd is None:
            cwd = os.getcwd()
        if stdin is None:
            stdin = ChildProcessIO.PIPE
        if stdout is None:
            stdout = ChildProcessIO.PIPE
        if stderr is None:
            stderr = ChildProcessIO.PIPE
        self.commands = commands
        self.env = env
        self.cwd = cwd
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def spawn_all(self):
        """Create the processes for the pipeline.

        Returns
        -------
        list
            A list of the created processes in order
        """
        res = []
        next_input = self.stdin
        builder = ChildProcessBuilder([], env=self.env, cwd=self.cwd, stderr=self.stderr)

        for command in self.commands[:-1]:
            builder.args = command
            builder.stdin = next_input

            proc = builder.spawn()
            res.append(proc)
            next_input = proc.stdout

        builder.args = self.commands[-1]
        builder.stdin = next_input
        builder.stdout = self.stdout

        proc = builder.spawn()
        res.append(proc)

        return res

    @property
    def commands(self):
        """The commands for the processes in the pipeline to execute.

        Commands may be provided as a list where each will be provided to the 'args' parameter of the ChildProcessBuilder,
        or as a string separated by pipe characters."""
        return self._commands

    @commands.setter
    def commands(self, value):
        if isinstance(value, str):
            value = value.split("|")

        if isinstance(value, list):
            if not value:
                raise ValueError("At least one command must be supplied")
            self._commands = value
        else:
            raise TypeError("The commands should be supplied as a list or as a string with pipe characters")
