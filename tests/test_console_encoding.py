#!/usr/bin/env python3
"""A gate must survive the OPERATOR's console, and a crash must not be reported as a defect.

WHAT HAPPENED. The engine i18n gate printed PASS for all 237 German strings and all 237 Russian
ones, then died:

    PASS ru: composed titles translate (template + product + host count)   0 of 33 fail
    Traceback (most recent call last):
      File "test_engine_i18n.py", line 43, in check
        print("  %-4s %s%s" % (...))
    UnicodeEncodeError: 'charmap' codec can't encode characters in position 65-68

and ship.py announced

    [X] ENGINE i18n REGRESSION - a document language we advertise would ship English finding text.

Every translation was correct. A Windows console is cp1252, the check prints WHAT IT COMPARED, and
for Russian that detail is Cyrillic. The gate could not render its own PASS.

TWO SEPARATE DEFECTS, and both are tested here:
  1. The gate depended on the console encoding. Sixth instance in this repo of "validated in a UTF-8
     sandbox, handed to the operator's box" (httpx, esbuild/win32, os.uname, ...). Fixed at the one
     place that launches every gate — ship.py sets PYTHONIOENCODING for children and reconfigures
     its own streams, since it prints their captured output — and in the gate itself, for anyone
     running it directly.
  2. ship.py could not tell a CRASH from a FINDING. A check that raised has said nothing about its
     subject; calling it a regression in the subject sends the next hour down the wrong road.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(HERE, "hermes-skills", "shodan-assessment", "scripts", "test_engine_i18n.py")


def _run(gate, encoding):
    """Run a gate with the operator's console encoding forced."""
    env = dict(os.environ, PYTHONIOENCODING=encoding)
    env.pop("PYTHONWARNINGS", None)
    return subprocess.run([sys.executable, gate], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=300, cwd=HERE)


def test_the_i18n_gate_survives_a_cp1252_console():
    """THE EXACT REPRODUCTION: cp1252 is what a Windows console gives you."""
    r = _run(GATE, "cp1252")
    assert "UnicodeEncodeError" not in (r.stdout + r.stderr), (
        "the gate died rendering its own output on a cp1252 console. It says nothing about the "
        "translations; it means the check cannot run where the operator runs it.")
    assert r.returncode == 0, "the i18n gate failed under cp1252:\n" + (r.stdout + r.stderr)[-800:]


def test_the_gate_survives_even_if_reconfigure_itself_fails():
    """DEFEAT BOTH GUARDS, or you are measuring the other one.

    The first fix was ONE layer: reconfigure() inside a try/except. If it ever failed — an older
    Python, a redirected stream, a platform that refuses — the gate fell straight back to cp1252 and
    died again in the same place, SILENTLY, because the except swallowed it. Measured: with
    reconfigure() forced to raise under cp1252 the one-layer version exited 1 with
    UnicodeEncodeError. So the printing itself is now total (say() re-encodes with backslashreplace
    on UnicodeEncodeError) and the evidence degrades to escapes instead of the gate dying.
    """
    src = open(GATE, encoding="utf-8").read()
    anchor = '_s.reconfigure(encoding="utf-8", errors="replace")'
    assert anchor in src, "the reconfigure guard is gone; this test no longer measures anything"
    broken = src.replace(anchor, 'raise RuntimeError("reconfigure unavailable")')
    tmp = os.path.join(os.path.dirname(GATE), "_probe_encoding_tmp.py")
    open(tmp, "w", encoding="utf-8").write(broken)
    try:
        r = _run(tmp, "cp1252")
        assert "UnicodeEncodeError" not in (r.stdout + r.stderr), (
            "with reconfigure() unavailable the gate still dies on a cp1252 console - the fix is "
            "one silent layer deep, which is how it would come back unnoticed")
        assert r.returncode == 0, (r.stdout + r.stderr)[-600:]
        assert "the host count is declined" in r.stdout, \
            "the gate stopped reporting rather than degrading its output"
    finally:
        # a harness that writes real files must clean up even when killed mid-run
        if os.path.exists(tmp):
            os.unlink(tmp)


def test_the_i18n_gate_still_passes_on_a_utf8_console():
    """Both directions: a fix that only works on one encoding is half a fix."""
    r = _run(GATE, "utf-8")
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    assert "хост" in r.stdout, \
        "the Russian evidence is no longer printed - the detail was silently dropped, not fixed"


def test_ship_sets_the_child_encoding_and_its_own():
    src = open(os.path.join(HERE, "ship.py"), encoding="utf-8").read()
    code = "\n".join(ln.split("#")[0] for ln in src.splitlines())   # never match our own comment
    assert "PYTHONIOENCODING" in code, \
        "children inherit os.environ; without this every gate depends on the console"
    assert "reconfigure(" in code, \
        "ship.py prints the children's captured output, so its OWN streams need it too"


def test_a_crashed_gate_is_not_reported_as_a_defect_in_its_subject():
    """Run the real decision function over the real shapes."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ship_gate_msg", os.path.join(HERE, "ship.py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules["ship_gate_msg"] = m
    try:
        spec.loader.exec_module(m)
    except SystemExit:
        pass

    class P:
        def __init__(self, out, err):
            self.stdout, self.stderr = out, err

    crash = P("  PASS ru: composed titles translate\n",
              "Traceback (most recent call last):\n"
              "UnicodeEncodeError: 'charmap' codec can't encode characters\n")
    try:
        m.gate_failed("ENGINE i18n", crash, "would ship English finding text")
        raise AssertionError("gate_failed did not exit")
    except SystemExit as e:
        msg = str(e)
    assert "CRASHED" in msg and "NOT a finding" in msg, \
        "a gate that raised was reported as a defect in the thing it checks"
    assert "English finding text" not in msg, \
        "the crash message repeats the regression claim, which is the wrong culprit"

    real = P("  FAIL de: every finding title is translated   7 of 237 missing\n1 FAILURE(S)\n", "")
    try:
        m.gate_failed("ENGINE i18n", real, "would ship English finding text")
        raise AssertionError("gate_failed did not exit")
    except SystemExit as e:
        msg = str(e)
    assert "REGRESSION" in msg and "CRASHED" not in msg, \
        "a genuine failure was downgraded to a crash - now real defects read as tooling noise"


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
