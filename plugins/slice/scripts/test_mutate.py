#!/usr/bin/env python3
"""Tests for mutate.py, run against a throwaway git repo: `python3 test_mutate.py`.

Each case is a harness failure that would have made a QA run lie, and was seen to happen:
a stale (mtime, size)-keyed cache reporting the previous mutant's verdict, a hung test orphaned
by its timeout, an untracked file left mutated, a compile error counted as a kill.
"""

import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mutate.py")

CALC = textwrap.dedent("""\
    def clamp(x, lo, hi):
        if x < lo:
            return lo
        if x > hi:
            return hi
        return x
    """)

TESTS = textwrap.dedent("""\
    import unittest
    from calc import clamp
    class T(unittest.TestCase):
        def test_low(self): self.assertEqual(clamp(-1, 0, 5), 0)
        def test_mid(self): self.assertEqual(clamp(3, 0, 5), 3)
    """)

DEFAULTS = ('{"defaults": {"cmd": "python3 -m unittest -v test_calc 2>&1", '
            '"build": "python3 -c \'import calc\'", '
            '"fail": "^(test_\\\\w+) .*\\\\.\\\\.\\\\. (?:FAIL|ERROR)"}}')


class MutateTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="mutate-test-")
        self.git("init", "-q")
        self.write("calc.py", CALC)
        self.write("test_calc.py", TESTS)
        self.write(".gitignore", "__pycache__/\nm.jsonl\nlogs/\nnewmod.py\n")
        self.git("add", "-A")
        self.git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.dir, check=True)

    def write(self, name, text):
        with open(os.path.join(self.dir, name), "w") as f:
            f.write(text)

    def read(self, name):
        with open(os.path.join(self.dir, name)) as f:
            return f.read()

    @staticmethod
    def running_tests():
        p = subprocess.run(["pgrep", "-f", "unittest -v test_calc"], stdout=subprocess.PIPE)
        return set(p.stdout.split())

    def run_mutants(self, *lines, timeout=10):
        self.write("m.jsonl", "\n".join((DEFAULTS,) + lines) + "\n")
        p = subprocess.run([sys.executable, RUNNER, "m.jsonl", "--logs", "logs",
                            "--timeout", str(timeout)],
                           cwd=self.dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout * 10 + 30)  # a runner that hangs is a failure, not a stall
        out = p.stdout.decode()
        verdicts = {}
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].startswith(("M", "N")) and parts[0][1:].isdigit():
                verdicts[parts[0]] = parts[1]
        return p.returncode, out, verdicts

    def test_verdicts_and_restore(self):
        code, out, v = self.run_mutants(
            '{"id": "M1", "file": "calc.py", "old": "if x < lo:", "new": "if x > lo:"}',
            '{"id": "M2", "file": "calc.py", "old": "    return hi", "new": "    return lo"}',
            '{"id": "M3", "file": "calc.py", "old": "return", "new": "yield"}',
            '{"id": "M4", "file": "calc.py", "old": "def clamp(x, lo, hi):", "new": "def clamp(x, lo, hi)"}',
        )
        self.assertEqual(code, 0, out)
        self.assertEqual(v, {"M1": "KILLED", "M2": "SURVIVED", "M3": "REFUSED", "M4": "INVALID"}, out)
        self.assertIn("test_low", out)
        self.assertEqual(self.read("calc.py"), CALC)

    def test_same_size_mutant_does_not_inherit_the_previous_verdict(self):
        # M1 and its restore are the same size; without a fresh mtime, Python's .pyc from M1
        # is reused for M2 and M2 is reported KILLED by M1's failures.
        _, out, v = self.run_mutants(
            '{"id": "M1", "file": "calc.py", "old": "if x < lo:", "new": "if x > lo:"}',
            '{"id": "M2", "file": "calc.py", "old": "    return hi", "new": "    return lo"}',
        )
        self.assertEqual(v.get("M2"), "SURVIVED", out)

    def test_timeout_kills_the_whole_process_group(self):
        before = self.running_tests()
        _, out, v = self.run_mutants(
            '{"id": "M5", "file": "calc.py", "old": "    return x\\n", '
            '"new": "    import time\\n    while True: time.sleep(0.1)\\n"}',
            timeout=3,
        )
        self.assertEqual(v.get("M5"), "KILLED?", out)
        time.sleep(0.5)
        self.assertEqual(self.running_tests() - before, set(), "a hung test outlived its timeout")
        self.assertEqual(self.read("calc.py"), CALC)

    def test_untracked_file_is_restored(self):
        self.write("newmod.py", "def f():\n    return 1\n")
        _, out, v = self.run_mutants(
            '{"id": "N1", "file": "newmod.py", "old": "return 1", "new": "return 2"}')
        self.assertEqual(v.get("N1"), "SURVIVED", out)
        self.assertEqual(self.read("newmod.py"), "def f():\n    return 1\n")

    def test_red_baseline_runs_nothing(self):
        self.write("test_calc.py", TESTS.replace("clamp(3, 0, 5), 3", "clamp(3, 0, 5), 4"))
        code, out, v = self.run_mutants(
            '{"id": "M1", "file": "calc.py", "old": "if x < lo:", "new": "if x > lo:"}')
        self.assertEqual(code, 2, out)
        self.assertEqual(v, {}, out)
        self.assertIn("BASELINE RED", out)


if __name__ == "__main__":
    unittest.main()
