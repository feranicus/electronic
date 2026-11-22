"""test_model_chain.py — the chain head has FIFTEEN homes, and a deprecation found them by grep.

WHAT HAPPENED (22 Nov 2026). DigitalOcean deprecated `deepseek-3.2`. CLAUDE.md says
`enrich._FALLBACKS` is the ONE HOME for the chain, and that is true of the chain - but the HEAD of
it is separately hardcoded as a fallback default in eleven other files: the shield panel, the
release-notes panel, the staging quorum, proteus, audit_fp, author_geopol, the assistant's default
model, cassandra-bot, patchwatch and its provisioner, and the browser's defense.js. Fifteen lines.
I found them with a grep, which is exactly the method CLAUDE.md class 35 says not to trust:
"counting by hand is how the fourth wiring point is missed".

So this file DERIVES the set. Every model id written into the tree must be one the chain actually
uses, or be explicitly recorded as something else (a price row for a model we no longer call, a
probe list, an incident's evidence). Next time a vendor deprecates something, one line changes and
the suite names every straggler instead of a person remembering to grep.

IT DOES NOT ASSERT WHICH MODEL IS CORRECT. Only the API knows that, which is what modelcheck.py
asks before a deploy - `deepseek-v4-flash` was a marketing name that 404'd for days.
"""
import ast
import io
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts")


def _read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def chain():
    """The live chain, read from its one home."""
    for line in _read(os.path.join(ENGINE, "enrich.py")).split("\n"):
        if line.startswith("_FALLBACKS = ["):
            body = line.split("[", 1)[1].rsplit("]", 1)[0]
            return [m.strip().strip("\"'") for m in body.split(",") if m.strip()]
    raise AssertionError("no _FALLBACKS in enrich.py - the chain moved and this file is blind")


# Files that legitimately name a model the chain does NOT use, and why. Each entry is a decision,
# not a waiver: a path here is a file somebody has to think about when a model changes.
ALLOWED_ELSEWHERE = {
    # Price and catalogue tables describe models we may meet, not models we call. A ledger row
    # written last month still has to be priced after the model is retired.
    "hermes-skills/shodan-assessment/scripts/enrich.py": "RATES prices retired models too",
    "hermes-skills/shodan-assessment/scripts/model_watch.py": "the published price table",
    "hermes-skills/shodan-assessment/scripts/model_probe.py": "probes ids that may not exist",
    "probe_models.py": "a bake-off probes candidates by definition",
    "compare_models.py": "a bake-off probes candidates by definition",
    "cost_report.py": "names the runaway models from the 2026-09-01 incident",
    "agent_forensics.py": "synthesises traffic that names models",
    "webapp/backend/app/spend_watch.py": "names the runaway models from the incident",
}

# The code homes that must track the chain HEAD. Derived below and asserted to be complete, so a
# twelfth file that starts hardcoding the head is a failure rather than a surprise in six months.
HEAD_HOMES = [
    "webapp/backend/app/shield_panel.py",
    "webapp/backend/app/release_notes.py",
    "webapp/backend/app/settings.py",
    "deploy/stagegate/quorum.py",
    "hermes-skills/shodan-assessment/scripts/proteus.py",
    "hermes-skills/shodan-assessment/scripts/audit_fp.py",
    "hermes-skills/shodan-assessment/scripts/author_geopol.py",
    "cassandra-bot/cassandra_bot.py",
    "patchwatch/patchwatch.py",
    "patchwatch/provision_patchwatch.py",
    "webapp/frontend/public/defense.js",
]


def _code_lines(path):
    """Source lines with comments and docstrings removed.

    THE REASON THIS EXISTS: the rename I did stripped comments but not DOCSTRINGS, and rewrote a
    line inside `_chain()`'s docstring that described an August incident - inventing a bug that
    never happened to a model that did not exist then. Prose about the past is not a code home.
    """
    src = _read(path)
    if path.endswith(".js"):
        out = []
        for ln in src.split("\n"):
            t = ln.strip()
            if t.startswith("//") or t.startswith("*") or t.startswith("/*"):
                continue
            out.append(ln.split("//")[0])
        return "\n".join(out)
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            d = ast.get_docstring(node, clean=False)
            if d:
                src = src.replace(d, "")
    return "\n".join(ln for ln in src.split("\n") if not ln.strip().startswith("#"))


# A VENDOR IS NOT A MODEL, and that distinction cost this test two false findings on its first
# run: audit_fp.py holds `("deepseek", "llama", "gemma", ...)` - a list of VENDOR STEMS used to
# decide whether two models share a failure domain - and a German locale string reads
# "DeepSeek-Texte". Flagging either would have sent somebody to "fix" correct code, which is how a
# guard gets switched off. A model id carries a VERSION.
_VENDORS = ("deepseek", "llama", "gemma", "kimi", "mistral", "openai-gpt", "glm", "qwen",
            "nemotron")
_VERSIONED = re.compile(r"^[a-z0-9]+(?:[.\-][a-z0-9]+)*[.\-]?\d[a-z0-9.\-]*$", re.I)


def _model_ids(text):
    """Quoted strings that are a serverless model ID: a vendor stem AND a version. `"deepseek"`
    alone is the vendor; `deepseek-v4.1-flash` is the model."""
    out = set()
    for m in re.findall(r"""["']([a-z0-9][a-z0-9.\-]{5,40})["']""", text, re.I):
        low = m.lower()
        if not any(low.startswith(v) for v in _VENDORS):
            continue
        if low in _VENDORS:
            continue                       # the bare vendor name
        if not _VERSIONED.match(low):
            continue                       # "deepseek-texte" and friends are prose
        out.add(m)
    return out


def test_the_chain_is_four_models_from_four_vendors():
    """The whole point of the chain: a 429, an outage or a blind spot is provider-wide, so a chain
    of four models from one vendor is one model wearing four hats."""
    c = chain()
    assert len(c) >= 3, c
    stems = [m.split("-")[0].lower() for m in c]
    assert len(set(stems)) == len(stems), (
        "two models in the chain come from the same vendor, which is the same failure twice: %s" % c)


@pytest.mark.parametrize("rel", HEAD_HOMES)
def test_every_head_home_names_the_current_head(rel):
    """Each of these restates the chain HEAD as its own default. They are separate deployables -
    patchwatch runs on the droplet, cassandra-bot is its own container, defense.js runs in a
    browser - so they cannot import the one home, and that is exactly why they go stale."""
    head = chain()[0]
    text = _code_lines(os.path.join(ROOT, rel))
    found = _model_ids(text)
    stale = {m for m in found
             if m.split("-")[0].lower() == head.split("-")[0].lower() and m != head}
    assert not stale, (
        "%s still names %s; the chain head is %s. A deprecated model here is a request that 404s "
        "on a surface nobody watches." % (rel, ", ".join(sorted(stale)), head))


def test_no_other_file_quietly_hardcodes_a_chain_vendor():
    """DERIVE N (class 35). If a twelfth file starts naming a chain model, it joins HEAD_HOMES by
    decision - it does not get discovered during the next deprecation by somebody's grep."""
    known = {os.path.normpath(p) for p in HEAD_HOMES} | {os.path.normpath(p) for p in
                                                         ALLOWED_ELSEWHERE}
    known.add(os.path.normpath("hermes-skills/shodan-assessment/scripts/enrich.py"))
    chain_stems = {m.split("-")[0].lower() for m in chain()}
    offenders = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs
                   if d not in ("node_modules", ".git", "venv", ".venv", "__pycache__", "dist",
                                "docs", "marketing", "shodan-out", "jobhuntwow-app", "tests",
                                "obs", "Klima", "locales", "legal-locales", "partners-locales")]
        for f in files:
            if not f.endswith((".py", ".js")) or f.startswith("test_"):
                continue
            full = os.path.join(base, f)
            rel = os.path.normpath(os.path.relpath(full, ROOT))
            if rel in known:
                continue
            found = _model_ids(_code_lines(full))
            hits = {m for m in found if m.split("-")[0].lower() in chain_stems}
            if hits:
                offenders.append("%s -> %s" % (rel, ", ".join(sorted(hits))))
    assert not offenders, (
        "a model id is hardcoded somewhere nobody will look during the next deprecation:\n  "
        + "\n  ".join(offenders)
        + "\nAdd the file to HEAD_HOMES (it must track the head) or to ALLOWED_ELSEWHERE with a "
          "reason (it legitimately names another model).")


def test_the_head_is_priced_in_both_tables():
    """An unpriced model is billed at FALLBACK_PRICE, which is the dearest rate we know - the
    budget would then be enforcing a number nobody measured, and the spend watcher would alarm on
    arithmetic rather than on spend."""
    head = chain()[0]
    enrich = _read(os.path.join(ENGINE, "enrich.py"))
    watch = _read(os.path.join(ENGINE, "model_watch.py"))
    assert re.search(r'"%s"\s*:\s*\(' % re.escape(head), enrich), (
        "%s has no row in enrich.RATES" % head)
    assert re.search(r'"%s"\s*:\s*\(' % re.escape(head), watch), (
        "%s has no row in model_watch's price table" % head)


def test_the_two_price_tables_agree_about_the_head():
    """Two homes for one price is a value that drifts, and the newer one always loses. They are
    separate on purpose (one bills, one watches), so they are compared instead of merged."""
    head = chain()[0]

    def rate(src):
        m = re.search(r'"%s"\s*:\s*\(\s*([\d.]+)\s*,\s*([\d.]+)' % re.escape(head), src)
        return (float(m.group(1)), float(m.group(2))) if m else None

    a = rate(_read(os.path.join(ENGINE, "enrich.py")))
    b = rate(_read(os.path.join(ENGINE, "model_watch.py")))
    assert a and b, (a, b)
    assert a == b, "enrich.RATES says %s and model_watch says %s for %s" % (a, b, head)


def test_the_catalogue_is_checked_before_the_deploy_not_after():
    """`deepseek-v4-flash` came off a pricing page, went to the head of the chain, and 404'd on
    every assessment for days. do_verify() catches that - in step 5, after production is already
    running it."""
    ship = _read(os.path.join(ROOT, "ship.py"))
    code = "\n".join(ln for ln in ship.split("\n") if not ln.strip().startswith("#"))
    assert "modelcheck.py" in code, "nothing asks the catalogue before deploying"
    # ANCHOR ON THE CALL (class 4). ship.py does `import stagegate`; it never writes the filename,
    # so the first version of this assertion raised ValueError looking for "stagegate.py" - a
    # check that cannot find its own subject.
    gate = code.index("stagegate.run(")
    assert code.index("modelcheck.py") < gate, (
        "the catalogue check runs after the staging gate; a bad model id would reach the twin "
        "and then production before anything noticed")
