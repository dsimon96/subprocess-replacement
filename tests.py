"""
assorted unit tests for childprocess
"""

import unittest
from childprocess import ChildProcessBuilder as CPB
from childprocess import PipelineBuilder as PB

class TestChildprocess(unittest.TestCase):

    def test_basic_stdout(self):
        cp = CPB("echo foo").spawn()
        self.assertTrue(cp)
        self.assertEqual(b'foo', cp.wait_for_finish().stdout.readline().strip())
        self.assertTrue(cp.is_finished())

    def test_blocking(self):
        cp = CPB("sleep 0.2").spawn()
        cp.wait_for_finish()
        self.assertTrue(cp.is_finished())

    def test_basic_pipeline(self):
        cp1 = CPB("echo 'foo bar baz'").spawn()
        cp2 = CPB("wc -w", stdin=cp1.stdout).spawn()
        self.assertEqual(b'3', cp2.stdout.readline().strip())

    def test_pipeline_builder(self):
        procs = PB("echo 'foo bar baz foo\n qux bat' | grep 'bar' | wc -w").spawn_all()
        self.assertEqual(b'4', procs[-1].stdout.readline().strip())

    def test_process_env(self):
        cp = CPB("env", env={"FOO" : "bar"}).spawn()
        self.assertEqual(b'FOO=bar', cp.wait_for_finish().stdout.readline().strip())

    def test_process_cwd(self):
        cp = CPB("ls", cwd="./examples").spawn()
        self.assertEqual(cp.wait_for_finish().stdout.readline().strip(), b'piping.py')

    def test_state(self):
        sleeper = CPB("sleep 10s").spawn()
        self.assertTrue(sleeper)
        self.assertTrue(sleeper.is_running())
        self.assertFalse(sleeper.is_stopped())
        self.assertFalse(sleeper.is_finished())
        sleeper.stop()
        self.assertTrue(sleeper.is_stopped())
        self.assertFalse(sleeper.is_running())
        self.assertFalse(sleeper.is_finished())
        sleeper.start()
        self.assertTrue(sleeper.is_running())
        self.assertFalse(sleeper.is_stopped())
        self.assertFalse(sleeper.is_finished())
        sleeper.terminate()
        sleeper.wait_for_finish(timeout=5)
        self.assertTrue(sleeper.is_finished())
        self.assertFalse(sleeper.is_running())
        self.assertFalse(sleeper.is_stopped())


if __name__ == "__main__":
    unittest.main()
