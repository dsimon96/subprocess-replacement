"""
assorted unit tests for childprocess
"""

import unittest
from childprocess import ChildProcessBuilder as CPB

class TestChildprocess(unittest.TestCase):

    def test_basic_stdout(self):
        cp = CPB("echo foo").spawn()
        self.assertTrue(cp)
        self.assertEqual(b'foo', cp.stdout.readline().strip())
        self.assertTrue(cp.is_finished())

    def test_basic_pipeline(self):
        cp1 = CPB("echo 'foo bar baz'").spawn()
        cp2 = CPB("wc -w", stdin=cp1.stdout).spawn()
        self.assertEqual(b'3', cp2.stdout.readline().strip())


if __name__ == "__main__":
    unittest.main()
