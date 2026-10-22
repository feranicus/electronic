"""A probe's budget must scale with the window it is asked about.

THE RUN, 2026-10-20. The operator asked why the DigitalOcean charges stopped on 12 October and
reached for the verb built for that question:

    python cost_report.py --whodunit --days 22

    calls to the jobhuntwow LLM proxy: 0
    VERDICT: CANNOT DECIDE
      the Loki query did not run (ssh failed (rc=124): TIMEOUT after 180s).

The refusal was right and the 180 was the defect. That one ssh session issues 23 Loki range
queries plus four greps over the whole events.log, serially, and the budget was a constant while
the work scales with `--days`. The default 10 days fitted. 22 could not, and nothing in the output
said which half was slow.

Three separate faults, each guarded below:

  1. ONE BUDGET FOR EVERYTHING. A single `timeout=180` on the outer ssh, so one slow section
     starved every other section. The events.log greps do not depend on `--days` at all, so a
     large file could consume the whole budget before Loki was asked a single question.
  2. A PINNED RESOLUTION. The hourly queries used a fixed 3600s step, so a 22-day window asked
     Loki for 528 points per query, four times, while a 10-day window asked for 240. The cost of
     a query grew with the window for no analytical gain.
  3. A CUT SECTION RENDERED AS A ZERO. `proxy_hits` defaulted to 0 and printed as a measured
     number, so a query that never ran was reported as "0 calls". Defect class 7: a detail that
     renders identically whether or not anything was measured is templated output. Class 1 says
     the same thing from the other side: a check that cannot see its subject must not answer.
"""
import io
import math
import os
import re
import subprocess
import sys
import contextlib

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import cost_report as cr  # noqa: E402

SRC = os.path.join(ROOT, "cost_report.py")


def _budgets(days):
    """The arithmetic loki_correlate() performs, kept here so the test states the property rather
    than re-importing a private helper. If the formula moves, the assertions below still describe
    what must be true of it."""
    step_hours = max(6, int(math.ceil(days * 24.0 / 120)))
    hourly_step = max(3600, int(days * 86400 / 400))
    ssh_budget = min(600, 150 + 12 * days)
    return step_hours, hourly_step, ssh_budget


def test_the_ssh_budget_grows_with_the_window():
    """THE BUG, as a property. 22 days must be given more than 10 days, and more than the 180
    seconds that failed."""
    _, _, b10 = _budgets(10)
    _, _, b22 = _budgets(22)
    assert b22 > b10, "a longer window is given no more time than a shorter one"
    assert b22 > 180, (
        "22 days still gets %ds, and 180 is the number that produced rc=124" % b22)


def test_the_budget_is_bounded_so_a_probe_cannot_hang_forever():
    """A diagnostic that hangs is its own outage. The ceiling matters as much as the floor."""
    for d in (1, 10, 22, 60):
        _, _, b = _budgets(d)
        assert 60 <= b <= 600, "days=%d produced a %ds budget" % (d, b)


def test_the_point_count_stays_bounded_as_the_window_grows():
    """A PINNED STEP MAKES A LONG WINDOW COST MORE PER QUERY. At a fixed 3600s, 22 days is 528
    points and 60 days is 1,440. Deriving the step holds it flat."""
    counts = []
    for d in (7, 22, 60):
        _, hourly_step, _ = _budgets(d)
        counts.append(int(d * 86400 / hourly_step))
    assert max(counts) <= 420, "point count grew to %s across the windows" % counts
    assert max(counts) - min(counts) <= 420, counts


def test_every_remote_query_carries_its_own_clock():
    """ONE SLOW SECTION MUST NOT STARVE THE REST (the first fault). Each helper the script defines
    has to be wrapped, or a single hung query consumes the whole run again."""
    script = cr._loki_script(cr.LOKI_QUERIES, 1, 2, "21600", 7200)
    for fn in ("q()", "s()", "h()"):
        i = script.find(fn)
        assert i != -1, "the %s helper is gone from the generated script" % fn
        body = script[i:i + 240]
        assert "timeout " in body, "%s has no timeout of its own: %s" % (fn, body[:120])
    assert "timeout %d sh -c" % cr.FILE_BUDGET_S in script, (
        "the events.log scan is unbudgeted, so a large file starves Loki")


def test_a_cut_query_is_marked_rather_than_returning_empty():
    """An empty answer and a question nobody asked look identical. The marker is what tells them
    apart downstream."""
    script = cr._loki_script(cr.LOKI_QUERIES, 1, 2, "21600", 7200)
    assert script.count("__CUT__") >= 3, (
        "fewer than three helpers emit a cut marker, so a timed-out query reads as 'no data'")


def test_the_file_section_reports_being_cut():
    script = cr._loki_script(cr.LOKI_QUERIES, 1, 2, "21600", 7200)
    assert "file_cut=" in script, "a cut events.log scan says nothing about having been cut"
    assert "NOT measured" in script, (
        "the cut message does not say the counts are unmeasured, which is the whole point")


def test_the_parser_records_the_cut():
    fe = cr.file_evidence("jhw_mount=/v/x\nfile=/v/x/events.log size=99\n"
                          "file_cut=the events.log scan exceeded 45s and was cut")
    assert fe["cut"], "the cut marker was parsed away"
    clean = cr.file_evidence("jhw_mount=/v/x\njhw_lines=3")
    assert clean["cut"] == "" and clean["jhw_lines"] == 3, (
        "a healthy run is being reported as cut: %s" % clean)


def test_an_unmeasured_proxy_count_renders_as_UNKNOWN_not_as_zero():
    """THE THIRD FAULT, and the one that actually misleads a reader. `0` and `we never looked` are
    opposite findings, and the operator's run printed the first while meaning the second."""
    base = {"loki": "x", "days": 22, "file": {}, "visible": {}, "proxy_hits": 0,
            "proxy_sources": [], "verdict": "", "action": "", "note": "",
            "hourly": [], "samples": []}

    def render(w):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                cr.render_whodunit(w)
            except Exception:                       # noqa: BLE001 - rendering detail, not the point
                pass
        return [ln for ln in buf.getvalue().splitlines() if "LLM proxy" in ln]

    cut = render(dict(base, measured=False))
    assert cut and "UNKNOWN" in cut[0], (
        "an unmeasured proxy count printed as a number: %s" % cut)
    assert "0" not in cut[0].split("UNKNOWN")[0], cut

    real = render(dict(base, measured=True, proxy_hits=17))
    assert real and "17" in real[0], (
        "a measured count no longer prints its value: %s" % real)


def test_the_generated_script_is_valid_shell_and_the_file_section_runs(tmp_path):
    """PARSE IS NOT RUN (class 48), and this section is three levels of nested quoting inside a
    `sh -c` inside a Python string, which is exactly where a script looks right and dies on the
    droplet. Generate it, parse it, then execute the real file section against a real file."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    from test_teamwork import shell_harness_allowed
    ok, why = shell_harness_allowed()
    if not ok:
        pytest.skip(why)
    script = cr._loki_script(cr.LOKI_QUERIES, 1, 2, "21600", 7200)
    r = subprocess.run(["bash", "-n"], input=script.encode("utf-8"),
                       capture_output=True, timeout=60)
    assert r.returncode == 0, "the droplet would get invalid shell:\n%s" % r.stderr.decode()

    # PROVE THE FIXTURE (class 12): the section must actually produce the lines the parser wants.
    log = tmp_path / "events.log"
    # TWO jhw-web lines and one that is not, so the count proves it is selecting rather than
    # counting every line. The first version of this fixture held one jhw line and asserted two,
    # which failed the code for the fixture's mistake (class 12: prove the fixture first).
    log.write_bytes(b'{"evt": "http", "service": "jhw-web", "ip": "1.2.3.4", '
                    b'"path": "/v1/chat/completions"}\n'
                    b'{"evt": "http", "service": "colt-web", "ip": "5.6.7.8", "path": "/api/me"}\n'
                    b'{"evt": "http", "service": "jhw-web", "ip": "9.9.9.9", '
                    b'"path": "/v1/chat/completions"}\n')
    seg = [ln for ln in script.splitlines() if "timeout %d sh -c" % cr.FILE_BUDGET_S in ln]
    assert seg, "the budgeted file section is not in the script"
    cmd = seg[0].strip()
    cmd = cmd[cmd.index("timeout"):]
    if cmd.endswith("; then :; else"):
        cmd = cmd[:-len("; then :; else")]
    r2 = subprocess.run(["bash", "-c", cmd.replace('"$F"', '"%s"' % log)],
                        capture_output=True, timeout=120)
    out = r2.stdout.decode("utf-8", "replace")
    assert "jhw_lines=2" in out, "the file scan miscounted or the quoting broke:\n%s" % out
    assert "proxy=" in out, "no proxy line was extracted:\n%s" % out


def test_the_timeout_is_not_pinned_back_to_a_constant():
    """ANCHOR ON THE CALL SITE (class 4). The repair is worthless if someone re-pins the number."""
    src = open(SRC, encoding="utf-8").read()
    body = "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith("#"))
    i = body.find("_loki_script(LOKI_QUERIES")
    assert i != -1, "the loki call site moved; this guard is reading the wrong thing"
    call = body[i:i + 220]
    assert "timeout=ssh_budget" in call, (
        "the ssh budget is a literal again, which is the 2026-10-20 failure: %s" % call[:150])
