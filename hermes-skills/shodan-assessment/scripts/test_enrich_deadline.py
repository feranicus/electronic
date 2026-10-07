#!/usr/bin/env python3
"""
test_enrich_deadline.py - the enrichment PHASE is bounded end to end.

AS37468 (Angola Cables, 2026-10-07): recon finished at 118s, then the run sat at 88% past 19
minutes. The serial chain spent 407s on four whole-estate timeouts, and the map-reduce top-up then
ran with NO ceiling (two waves of 150s shards plus a serial 150s-per-batch retry).

Asserts:
  1. Every shard call is sized from the phase deadline at the moment it STARTS, never past it.
  2. A call that would get less than SHARD_FLOOR_S is not issued; its ids stay missing and the
     report says deadline_hit.
  3. The targeted retry stops at the deadline instead of running serially past it.
  4. Without a deadline nothing changes (old callers keep their behaviour), and deadline_hit=False.
  5. ENRICH_WALL_S fails OPEN to the default on garbage.
  6. WIRING (AST): run_assessment passes deadline= to _MR.run, takes the phase clock BEFORE the
     enrich.py subprocess, and imports `time` at module level (a NameError there is swallowed by
     the outer except and silently skips ALL enrichment).
  7. enrich.py stops the chain after ENRICH_CHAIN_TIMEOUT_STOP consecutive timeouts, and a
     NON-timeout failure resets the count (a 403 then a timeout is not two timeouts).

    python test_enrich_deadline.py
"""
import ast
import os
import sys
import threading
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("OPENAI_API_KEY", "test")

import enrich_parallel as P  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("\n      " + detail) if detail else ""))
    if not ok:
        FAILS.append(name)


def _stub_E(answer_after, calls):
    """Fake enrich module. Each call sleeps min(answer_after, timeout) and times out if it must."""
    E = types.SimpleNamespace()
    E.MODELS = ["m-a", "m-b", "m-c", "m-d"]
    E.MODEL = "m-a"
    E.PROMPT = "%s|%s|%s"
    E._bible = lambda: "bible"
    E.lang_block = lambda lang: "lang"
    lock = threading.Lock()

    def _call(prompt, model=None, timeout=None):
        with lock:
            calls.append({"model": model, "timeout": timeout, "start": time.time()})
        if answer_after > timeout:
            time.sleep(timeout)
            raise TimeoutError("The read operation timed out")
        time.sleep(answer_after)
        ids = prompt.rsplit("no omissions: ", 1)[1].split("\n", 1)[0].split(", ")
        body = "x" * 500
        return ('{"findings": [%s]}' % ",".join(
            '{"id": "%s", "what": "%s", "why": "%s"}' % (i, body, body) for i in ids)), {}
    E._call = _call
    import json as _j
    E._json = lambda raw: _j.loads(raw)
    import enrich as _real                     # the payload + grounding gate are real, not stubbed
    E.slim_payload, E.grounded = _real.slim_payload, _real.grounded
    return E


def _fj(n):
    return {"target": {"company": "t"},
            "findings": [{"id": "F%d" % i, "sev": "HIGH", "title": "t%d" % i} for i in range(n)]}


def _run(E, fj, **kw):
    sys.modules["enrich"] = E
    try:
        return P.run(fj, "en", **kw)
    finally:
        sys.modules.pop("enrich", None)


os.environ["ENRICH_SHARD_TIMEOUT"] = "3"
P.SHARD_FLOOR_S = 1

# 1 + 2: 6 shards, 2 workers, every call times out at 3s; deadline 4s away. Wave 1 (2 shards) gets
# 3s; wave 2 starts at ~3s and gets <=1s which is below... make floor 1 so it gets ~1s, wave 3 none.
calls = []
t0 = time.time()
dl = t0 + 4.0
merged, rep = _run(_stub_E(99, calls), _fj(12), shard_size=2, workers=2, deadline=dl)
took = time.time() - t0
late = [c for c in calls if c["start"] + c["timeout"] > dl + 0.5]
check("no shard call is allowed to run past the phase deadline", not late,
      "deadline +4.0s; calls (start offset, timeout): %s"
      % [(round(c["start"] - t0, 1), c["timeout"]) for c in calls])
check("the whole top-up ends near the deadline (took %.1fs, deadline 4.0s, cap 5.0s)" % took,
      took < 5.0)
check("calls that would get < SHARD_FLOOR_S are skipped, not issued (issued %d of 6 shards)"
      % len(calls), len(calls) < 6)
check("report.deadline_hit is True when the wall cut work (got %r)" % rep.get("deadline_hit"),
      rep.get("deadline_hit") is True)
check("cut findings stay MISSING, not invented (missing %d of 12)" % len(rep["missing"]),
      len(rep["missing"]) == 12 and not merged)

# 3: shards answer, but half the ids are 'missing' because a stub returns nothing for odd shards;
# the retry must stop at the deadline.
calls = []


def _half(answer_after):
    E = _stub_E(answer_after, calls)
    inner = E._call

    def _call(prompt, model=None, timeout=None):
        if model in ("m-b", "m-d") and "no omissions" in prompt:
            calls.append({"model": model, "timeout": timeout, "start": time.time()})
            time.sleep(min(timeout, 99))
            raise TimeoutError("timed out")
        return inner(prompt, model, timeout)
    E._call = _call
    return E


# The deadline leaves the retry ~2s: above SHARD_FLOOR_S, below its 3s cap. So the loop guard
# alone does NOT stop it; only a retry call SIZED from the deadline ends on time. (At a tighter
# deadline the loop guard and the shard guard mask each other: defect class 13.)
t0 = time.time()
dl = t0 + 5.0
merged, rep = _run(_half(0.2), _fj(8), shard_size=2, workers=4, deadline=dl)
took = time.time() - t0
retry_calls = [c for c in calls if c["start"] - t0 > 1.0]
check("a retry with time left is SIZED to the deadline (took %.1fs, deadline 5.0s, cap 5.6s)" % took,
      took < 5.6 and retry_calls and all(c["timeout"] < 3 for c in retry_calls),
      "retry calls (start offset, timeout): %s"
      % [(round(c["start"] - t0, 1), c["timeout"]) for c in retry_calls])
check("what DID come back is kept (rewritten %d of 8)" % rep["rewritten"], rep["rewritten"] >= 4)

# 4: no deadline -> behaviour unchanged
calls = []
merged, rep = _run(_stub_E(0.05, calls), _fj(6), shard_size=3, workers=2)
check("no deadline: every shard runs at its own cap (timeouts %s)"
      % sorted({c["timeout"] for c in calls}), {c["timeout"] for c in calls} == {3})
check("no deadline: deadline_hit is False (got %r)" % rep.get("deadline_hit"),
      rep.get("deadline_hit") is False and rep["coverage"] == 1.0)

# 5: fail open
for bad in ("", "abc", "-5"):
    os.environ["ENRICH_WALL_S"] = bad
    w = P.wall_s()
    check("ENRICH_WALL_S=%r -> %d (default %d, floor 60)" % (bad, w, P.WALL_S_DEFAULT),
          w == (60 if bad == "-5" else P.WALL_S_DEFAULT))
os.environ.pop("ENRICH_WALL_S", None)
check("phase_deadline(t0) = t0 + %d" % P.WALL_S_DEFAULT,
      P.phase_deadline(1000.0) == 1000.0 + P.WALL_S_DEFAULT)

# 6: wiring, by AST (comments and docstrings cannot satisfy it)
ra = ast.parse(open(os.path.join(HERE, "run_assessment.py"), encoding="utf-8").read())
mod_imports_time = any(isinstance(n, ast.Import) and any(a.name == "time" for a in n.names)
                       for n in ra.body)
check("run_assessment imports `time` at MODULE level", mod_imports_time)
run_calls = [n for n in ast.walk(ra) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == "run"
             and isinstance(n.func.value, ast.Name) and n.func.value.id == "_MR"]
check("every _MR.run(...) call passes deadline= (found %d call(s))" % len(run_calls),
      run_calls and all(any(k.arg == "deadline" for k in c.keywords) for c in run_calls))
t0_assign = [n.lineno for n in ast.walk(ra) if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == "_t0_enrich" for t in n.targets)]
enrich_sub = [n.lineno for n in ast.walk(ra) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Attribute) and n.func.attr == "run"
              and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess"
              and "enrich.py" in ast.unparse(n)]
check("the phase clock starts BEFORE the enrich.py subprocess (t0 line %s, subprocess line %s)"
      % (t0_assign, enrich_sub),
      len(t0_assign) == 1 and enrich_sub and t0_assign[0] < min(enrich_sub))

# 7: chain stop, executed against a stub _call
import enrich as RealE  # noqa: E402
seq = []


def _scripted(outcomes):
    it = iter(outcomes)

    def _call(prompt, model, timeout, max_tokens=None):
        seq.append(model)
        o = next(it)
        if o == "timeout":
            raise TimeoutError("The read operation timed out")
        raise RuntimeError("HTTP Error 403: Forbidden")
    return _call


def _chain(outcomes, stop="2"):
    del seq[:]
    os.environ["ENRICH_CHAIN_TIMEOUT_STOP"] = stop
    saved = (RealE._call, RealE.MODELS, RealE.ATTEMPTS, RealE.BUDGET_S, RealE._retryable)
    RealE._call = _scripted(outcomes)
    RealE.MODELS = ["m1", "m2", "m3", "m4"]
    RealE.ATTEMPTS = 1
    RealE.BUDGET_S = 10_000
    RealE._retryable = lambda e: True
    try:
        fn = next(getattr(RealE, n) for n in ("enrich", "run", "enrich_findings")
                  if callable(getattr(RealE, n, None)))
        try:
            fn(_fj(2), "en")
        except Exception:
            pass
    finally:
        RealE._call, RealE.MODELS, RealE.ATTEMPTS, RealE.BUDGET_S, RealE._retryable = saved
    return list(seq)


got = _chain(["timeout", "timeout", "timeout", "timeout"])
check("two consecutive timeouts stop the chain (models called: %s)" % got, got == ["m1", "m2"])
got = _chain(["timeout", "403", "timeout", "timeout"])
check("a non-timeout failure resets the count (models called: %s)" % got,
      got == ["m1", "m2", "m3", "m4"])
got = _chain(["timeout", "timeout", "timeout", "timeout"], stop="4")
check("ENRICH_CHAIN_TIMEOUT_STOP=4 lets all four run (models called: %s)" % got,
      got == ["m1", "m2", "m3", "m4"])
os.environ.pop("ENRICH_CHAIN_TIMEOUT_STOP", None)

print()
if FAILS:
    print("FAIL  %d check(s): %s" % (len(FAILS), ", ".join(FAILS)))
    sys.exit(1)
print("PASS  enrichment phase is bounded end to end")
