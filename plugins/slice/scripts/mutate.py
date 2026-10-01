#!/usr/bin/env python3
"""Mutation runner for the slice QA gate.

Applies each mutant, proves it applied, runs the tests, restores the file byte for byte, proves the
tree is back, and prints one line per mutant. Test output goes to a log file per mutant, never to
stdout, so a run of thirty mutants costs thirty lines of context rather than thirty test logs.

Usage:
    mutate.py MUTANTS.jsonl [--logs DIR] [--only ID[,ID...]] [--timeout SECONDS] [--no-baseline]

Each line of MUTANTS.jsonl is one JSON object:

    {"id": "Q1",
     "file": "server/internal/httpserver/cursor.go",
     "old": "for _, p := range op.query {",
     "new": "for _, p := range op.query[:1] {",
     "cmd": "go test -count=1 ./server/internal/httpserver/",
     "build": "go test -count=1 -run '^$' ./server/internal/httpserver/",
     "fail": "^--- FAIL: (\\S+)",
     "why": "digest binds only the first filter"}

- `old` must occur exactly once in `file`; the mutant is refused otherwise (an ambiguous anchor
  mutates the wrong place, or two places).
- `cmd` runs from the current directory. Its exit code is the verdict: 0 = SURVIVED, anything
  else = KILLED, provided the build check passed.
- `build` (optional, recommended) compiles without running. If it fails, the mutant is INVALID,
  not killed: a compile error is not a caught mutation.
- `fail` is a regex whose first group names a failing test. A kill with no named test is reported
  as KILLED? (unnamed), so a crash or timeout is not mistaken for a test catching the mutant.
- A line may set "cmd"/"build"/"fail" once in a {"defaults": {...}} object instead; later lines
  inherit them.

The baseline (every distinct `cmd` with no mutant applied) must pass first, or nothing is run: a
red baseline reports every mutant as killed.
"""

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time


def sh(cmd, log, timeout):
    """Run cmd through the shell, append its output to log, return (exit code, output, seconds)."""
    start = time.time()
    # Its own process group, so a timeout kills the test runner and everything it started, not
    # just the shell: an orphaned hung test keeps a CPU busy and skews every later timing.
    if os.name == "nt":
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             start_new_session=True)
    try:
        raw, _ = p.communicate(timeout=timeout)
        out, code = raw.decode("utf-8", "replace"), p.returncode
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.killpg(p.pid, signal.SIGKILL)
        raw, _ = p.communicate()
        out = raw.decode("utf-8", "replace") + f"\n[mutate.py] TIMEOUT after {timeout}s\n"
        code = 124
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"$ {cmd}\n{out}\n[exit {code}]\n")
    return code, out, time.time() - start


def tree_state():
    """Tracked files' state (git status, untracked excluded: builds and tests leave caches behind),
    or None outside a repo. Untracked mutated files are covered by the per-file digest instead."""
    try:
        return subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


_last_stamp = {}


def touch(path, before):
    """Give every write an mtime at least a second past both the file's mtime `before` the write
    and this file's previous stamp. Caches keyed on (whole-second mtime, size) -- Python's .pyc,
    make, some test runners -- otherwise reuse a stale build whenever a same-size mutant or restore
    lands in the same second as the version they compiled, and the run reports that version's
    verdict as this one's. A fast suite hits it on the very first mutant, against the baseline."""
    stamp = max(time.time(), before + 1.0, _last_stamp.get(path, 0.0) + 1.0)
    _last_stamp[path] = stamp
    os.utime(path, (stamp, stamp))


def digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load(path):
    defaults, mutants = {}, []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            obj = json.loads(line)
            if "defaults" in obj:
                defaults.update(obj["defaults"])
                continue
            m = {**defaults, **obj}
            for key in ("id", "file", "old", "new", "cmd"):
                if key not in m:
                    sys.exit(f"{path}:{n}: mutant is missing '{key}'")
            mutants.append(m)
    ids = [m["id"] for m in mutants]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        sys.exit(f"duplicate mutant ids: {sorted(dupes)}")
    return mutants


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mutants")
    ap.add_argument("--logs", default="mutation-logs")
    ap.add_argument("--only", default="")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--no-baseline", action="store_true")
    a = ap.parse_args()

    mutants = load(a.mutants)
    if a.only:
        wanted = set(a.only.split(","))
        mutants = [m for m in mutants if m["id"] in wanted]
    os.makedirs(a.logs, exist_ok=True)

    if not a.no_baseline:
        for cmd in dict.fromkeys(m["cmd"] for m in mutants):
            code, _, secs = sh(cmd, os.path.join(a.logs, "baseline.log"), a.timeout)
            if code != 0:
                print(f"BASELINE RED ({code}, {secs:.0f}s): {cmd} -- see {a.logs}/baseline.log; nothing run")
                return 2
        print(f"baseline green ({len(set(m['cmd'] for m in mutants))} command(s))")

    clean = tree_state()
    rows, counts = [], {}
    for m in mutants:
        log = os.path.join(a.logs, f"{m['id']}.log")
        open(log, "w").close()
        path = m["file"]
        with open(path, "rb") as f:
            original = f.read()
        before = os.stat(path).st_mtime
        try:
            text = original.decode("utf-8")
        except UnicodeDecodeError:
            text = None
        hits = text.count(m["old"]) if text is not None else 0
        if text is None:
            verdict, detail = "REFUSED", "not a UTF-8 text file; apply this mutant by hand"
        elif hits != 1:
            verdict, detail = "REFUSED", f"anchor found {hits} times"
        else:
            mutated = text.replace(m["old"], m["new"], 1)
            try:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(mutated)
                touch(path, before)
                # Prove it applied: the file changed, and show the changed line.
                if digest(path) == hashlib.sha256(original).hexdigest():
                    verdict, detail = "REFUSED", "mutation is a no-op on the bytes"
                else:
                    line_no = text[: text.index(m["old"])].count("\n") + 1
                    with open(log, "a", encoding="utf-8") as f:
                        f.write(f"[mutate.py] {path}:{line_no}\n- {m['old']}\n+ {m['new']}\n\n")
                    verdict, detail = None, ""
                    if m.get("build"):
                        code, _, _ = sh(m["build"], log, a.timeout)
                        if code != 0:
                            verdict, detail = "INVALID", "does not compile"
                    if verdict is None:
                        code, out, secs = sh(m["cmd"], log, a.timeout)
                        if code == 0:
                            verdict, detail = "SURVIVED", f"{secs:.0f}s"
                        else:
                            names = []
                            if m.get("fail"):
                                names = list(dict.fromkeys(re.findall(m["fail"], out, re.M)))
                            if code == 124:
                                verdict, detail = "KILLED?", "timeout (hang, not a named test)"
                            elif names:
                                verdict = "KILLED"
                                detail = ", ".join(names[:3]) + (f" (+{len(names) - 3})" if len(names) > 3 else "")
                            else:
                                verdict, detail = "KILLED?", f"exit {code}, no named failing test"
            finally:
                with open(path, "wb") as f:
                    f.write(original)
                touch(path, before)
        if digest(path) != hashlib.sha256(original).hexdigest() or tree_state() != clean:
            print(f"{m['id']}: RESTORE FAILED -- tree differs from before the run; stopping")
            return 3
        counts[verdict] = counts.get(verdict, 0) + 1
        row = f"{m['id']:<8} {verdict:<9} {path}  {detail}"
        if m.get("why"):
            row += f"  # {m['why']}"
        rows.append(row)
        print(row, flush=True)

    print("summary: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + f"; logs in {a.logs}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
