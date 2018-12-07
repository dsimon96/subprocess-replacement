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


if __name__ == "__main__":
    unittest.main()
