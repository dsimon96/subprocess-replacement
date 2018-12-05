import io
import os
import subprocess
from typing import Dict, List, Tuple, Union

class _Pipe():
	def __init__(self, read_owner=None, write_owner=None):
		self._read_owner = read_owner
		self._write_owner = write_owner

	@property
	def read_owner(self):
		return self._read_owner

	@read_owner.setter
	def read_owner(self, proc):
		if self.read_owner is not None:
			raise RuntimeError("Pipe is already being read by another process")
		elif self.write_owner == proc:
			raise RuntimeError("A process cannot write to its own input")
		else:
			self._read_owner = proc

	@property
	def write_owner(self):
		return self._write_owner

	@write_owner.setter
	def write_owner(self, proc):
		if self.write_owner is not None:
			raise RuntimeError("Pipe is already being written to by another process")
		elif self.read_owner == proc:
			raise RuntimeError("A process cannot write to its own input")
		else:
			self._write_owner = proc

class ProcessIO():
	STDOUT = subprocess.STDOUT
	null = os.devnull
	pass

class Process():
	def __init__(self, args, env, cwd, stdin, stdout, stderr):
		pass

class ProcessBuilder():
	def __init__(self, args, env=None, cwd=None, stdin=None, stdout=None, stderr=None):
		if env is None:
			env = dict(os.environ)
		if cwd is None:
			cwd = os.getcwd()
		if stdin is None:
			stdin = _Pipe()
		if stdout is None:
			stdout = _Pipe()
		if stderr is None:
			stderr = _Pipe()
		self.args = args
		self.env = env
		self.cwd = cwd
		self.stdin = stdin
		self.stdout = stdout
		self.stderr = stderr

	def spawn(self):
		"""
		Create a child process from the current 
		"""
		return Process(self.args, self.env, self.cwd, self.stdin, self.stdout, self.stderr)

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
		The environment variables which the child process will be created with
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
		if isinstance(value, str):
			self._stdin = value
		elif isinstance(value, io.IOBase):
			self._stdin = value
		elif isinstance(value, _Pipe):
			value.read_owner = self
			self._stdin = value
		else:
			raise TypeError("Input can be redirected from a string, a file-like object, or another process's output")

	@property
	def stdout(self):
		return self._stdout

	@stdout.setter
	def stdout(self, value):
		if value == ProcessIO.STDOUT:
			pass
		elif isinstance(value, io.IOBase):
			self._stdout = value
		elif isinstance(value, _Pipe):
			value.write_owner = self
			self._stdout = value

	@property
	def stderr(self):
		return self._stderr

	@stderr.setter
	def stderr(self, value):
		if value == ProcessIO.STDOUT:
			self._stderr = value
		elif isinstance(value, io.IOBase):
			self._stderr = value
		elif isinstance(value, _Pipe):
			value._stderr = self
			self._stderr = value
