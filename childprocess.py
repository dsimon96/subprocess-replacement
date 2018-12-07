import io
import os
import signal
import subprocess
import sys
from enum import Enum
from typing import Dict, List, Tuple, Union

class ChildProcessIO(Enum):
	PIPE = 1
	INHERIT = 2
	NULL = 3
	STDOUT = 4

class ChildProcess():
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
		return self._args

	@property
	def env(self):
		return self._env

	@property
	def cwd(self):
		return self._cwd

	@property
	def pid(self):
		return self._popen.pid

	@property
	def exit_code(self):
		self._popen.poll()
		return self._popen.returncode

	@property
	def stdin(self):
		if not self._stdin_writeable:
			raise RuntimeError("The process's stdin pipe is inaccessible")
		return self._popen.stdin

	@property
	def stdout(self):
		if not self._stdout_readable:
			raise RuntimeError("The process's stdout pipe is inaccessible")
		return self._popen.stdout

	@property
	def stderr(self):
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
		if not hasattr(signal, "SIGCONT"):
			raise OSError("No platform support for stopping/starting processes")
		if not self.is_stopped():
			raise RuntimeError("Process is not stopped")
		self._is_stopped = False
		self.kill(signal.SIGCONT)

	def stop(self):
		if not hasattr(signal, "SIGTSTP"):
			raise OSError("No platform support for stopping/starting processes")
		self.kill(signal.SIGTSTP)
		self._is_stopped = True

	def terminate(self, force=False):
		if force:
			self._popen.kill()
		else:
			self._popen.terminate()

	def is_running(self):
		return not (self.is_finished() or self.is_stopped())

	def is_stopped(self):
		return not self.is_finished() and self._is_stopped

	def is_finished(self):
		return self.exit_code is not None

	def wait_for_finish(self, timeout=None):
		self._popen.wait(timeout)

	def kill(self, signal):
		self._popen.send_signal(signal)

class ChildProcessBuilder():
	def __init__(self, args, env=None, cwd=None, stdin=None, stdout=None, stderr=None):
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
		self.args = args
		self.env = env
		self.cwd = cwd
		self.stdin = stdin
		self.stdout = stdout
		self.stderr = stderr

	def spawn(self):
		"""
		Create a child process from the current ChildProcessBuilder configuration
		"""
		return ChildProcess(self.args, self.env, self.cwd, self.stdin, self.stdout, self.stderr)

	@property
	def args(self) -> List[str]:
		return self._args

	@args.setter
	def args(self, value: Union[str, List, Tuple]):
		if isinstance(value, str):
			self._args = value.split()
		elif isinstance(value, list) or isinstance(value, tuple):
			try:
				self._args = [str(obj) for obj in value]
			except:
				raise TypeError("Arguments must be convertible to strings")

	@property
	def env(self) -> Dict[str, str]:
		"""
		The environment variables with which the child process will be created
		"""
		return self._env

	@env.setter
	def env(self, value: Dict[str, str]):
		"""
		Define environment variables
		"""
		if isinstance(value, dict):
			try:
				self._env = {str(k):str(v) for k,v in value.items()}
			except:
				raise TypeError("Environment variable names and values must be convertible to strings")
		else:
			raise TypeError("Environment variable definitions must be a dictionary")

	@property
	def cwd(self):
		return self._cwd

	@cwd.setter
	def cwd(self, value):
		try:
			self._cwd = os.path.normpath(value)
		except:
			raise TypeError("Child process's current working directory must be a path-like object")

	@property
	def stdin(self):
		return self._stdin

	@stdin.setter
	def stdin(self, value):
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
		return self._stdout

	@stdout.setter
	def stdout(self, value):
		if isinstance(value, io.IOBase) or value in ChildProcessIO:
			self._stdout = value
		else:
			raise TypeError("Output can be redirected to a file-like object, or a ChildProcessIO special value")

	@property
	def stderr(self):
		return self._stderr

	@stderr.setter
	def stderr(self, value):
		if isinstance(value, io.IOBase) or value in ChildProcessIO:
			self._stderr = value
		else:
			raise TypeError("Error output can be redirected to a file-like object, or a ChildProcessIO special value")

class PipelineBuilder():
	def __init__(self, commands, env=None, cwd=None, stdin=None, stdout=None, stderr=None):
		self.commands = commands
		self.env = env
		self.cwd = cwd
		self.stdin = stdin
		self.stdout = stdout
		self.stderr = stderr
		# TODO: make these properly-checked attributes

	def spawn_all(self):
		res = []
		next_input = self.stdin
		builder = ChildProcessBuilder([], env=self.env, cwd=self.cwd, stderr=self.stderr)

		for command in self.commands[:-1]:
			builder.args = command
			if next_input is not None:
				builder.stdin = next_input

			proc = builder.spawn()
			res.append(proc)
			next_input = proc.stdout

		builder.args = self.commands[-1]
		builder.stdin = next_input
		if self.stdout:
			builder.stdout = self.stdout

		proc = builder.spawn()
		res.append(proc)

		return res

	@property
	def commands(self):
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
