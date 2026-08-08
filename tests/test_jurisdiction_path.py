"""test_jurisdiction_path.py — a capability is not shipped until the whole request path accepts it.

THE DEFECT THIS EXISTS FOR, found by the operator looking at the live screen (7 Aug 2026):
the compliance engine had just gained a full Canadian regime set and a `--jurisdiction` flag, every
engine test passed, and the feature was COMPLETELY UNREACHABLE from the web — because
`ComplianceReq` had no jurisdiction field and `/api/compliance` never passed one to the engine.

That is the same shape as the `ru` incident already recorded in CLAUDE.md: the engine could render
Russian decks while `main.py` flattened the language to `en` at the API boundary, so the capability
was invisible in every test that only exercised the engine.

RULE: when you generalise a capability, follow the VALUE end-to-end — UI -> API -> engine — and
assert it at each hop. These tests match the CONCEPT rather than one spelling, because a test
written against the one line you just fixed will miss the next spelling of the same mistake.
"""
import ast
import importlib.util
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "hermes-skills", "shodan-assessment", "scripts")
MAIN = os.path.join(ROOT, "webapp", "backend", "app", "main.py")
API_JS = os.path.join(ROOT, "webapp", "frontend", "src", "api.js")
PAGE = os.path.join(ROOT, "webapp", "frontend", "src", "pages", "Compliance.jsx")


def _read(p):
    return open(p, encoding="utf-8").read()


@pytest.fixture(scope="module")
def ce():
    spec = importlib.util.spec_from_file_location(
        "compliance_enrich", os.path.join(ENGINE, "compliance_enrich.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ hop 1: the ENGINE ---------
def test_the_engine_grades_every_jurisdiction_it_advertises(ce):
    for code in ce.JURISDICTIONS:
        regimes = ce.regimes_for(code)
        assert regimes, "%s advertises no regimes" % code
        assert all(k in ce.FIXED for k in regimes), "%s has a regime with no facts" % code
        doc, _ = ce.build("Test Co", "en", None, code)
        assert doc["jurisdiction"] == code
        assert doc["order"] == regimes


def test_an_unknown_jurisdiction_fails_closed_to_a_real_set(ce):
    """Never an empty regime list: a deck with no regimes looks finished."""
    for junk in ("", "ZZ", "xx", None, "not-a-code"):
        code, entry = ce.jurisdiction(junk)
        assert code == ce.DEFAULT_JURISDICTION
        assert entry["regimes"]


def test_the_cli_accepts_every_advertised_jurisdiction(ce):
    """The process that does the work must accept the value — the `ru` lesson.

    argparse `choices` is a SIXTH home for a value set; this asserts the orchestrator derives it
    rather than restating it.
    """
    src = _read(os.path.join(ENGINE, "compliance_assess.py"))
    assert "--jurisdiction" in src, "the compliance orchestrator has no --jurisdiction flag"
    # No hand-written jurisdiction list anywhere on the engine path.
    code_only = re.sub(r"#[^\n]*", "", src)
    assert not re.search(r'choices\s*=\s*\[[^\]]*["\']CA["\']', code_only), \
        "compliance_assess.py hardcodes a jurisdiction list instead of deriving it"


# --------------------------------------------------------------------- hop 2: the API ---------
def test_the_api_accepts_a_jurisdiction_on_start_and_refine():
    src = _read(MAIN)
    tree = ast.parse(src)
    models = {n.name: n for n in ast.walk(tree)
              if isinstance(n, ast.ClassDef) and n.name in ("ComplianceReq", "ComplianceRefineReq")}
    assert set(models) == {"ComplianceReq", "ComplianceRefineReq"}, "compliance models missing"
    for name, node in models.items():
        fields = [t.target.id for t in node.body if isinstance(t, ast.AnnAssign)]
        assert "jurisdiction" in fields, (
            "%s has no `jurisdiction` field — the API would silently discard it, which is exactly "
            "how the Canadian regime set was unreachable from the web while every engine test "
            "passed" % name)


def test_the_api_actually_forwards_it_to_the_engine():
    """A field the model accepts and the handler drops is worse than no field: it looks wired."""
    src = _read(MAIN)
    for handler in ("/api/compliance", "/api/compliance/{job_id}/refine"):
        assert handler in src
    # both compliance _run_job launches must carry the flag
    launches = re.findall(r"_run_job\((?:[^()]|\([^()]*\))*COMPLIANCE_ENGINE(?:[^()]|\([^()]*\))*\)", src)
    assert len(launches) >= 2, "expected a start and a refine launch of the compliance engine"
    for L in launches:
        assert "--jurisdiction" in L, (
            "a compliance run is launched without --jurisdiction:\n%s" % L[:220])


def test_the_api_resolves_through_the_engine_registry_not_its_own_list():
    src = re.sub(r"#[^\n]*", "", _read(MAIN))
    assert "def jurisdiction_ok" in src, "no resolver — the API would need its own list"
    # The resolver must consult the engine module, not a literal.
    body = src[src.index("def jurisdiction_ok"):]
    body = body[:body.index("\n@app") if "\n@app" in body else len(body)]
    assert "_compliance_mod" in body, "jurisdiction_ok does not ask the engine what it supports"
    assert not re.search(r'\[["\']EU["\']\s*,\s*["\']CA["\']\]', body), \
        "jurisdiction_ok hardcodes the jurisdiction list — a second source of truth"


def test_there_is_a_public_capability_endpoint():
    """The UI must be able to ASK, the way it asks /api/langs, instead of shipping a copy."""
    src = _read(MAIN)
    assert '"/api/jurisdictions"' in src or "'/api/jurisdictions'" in src


# ----------------------------------------------------------------------- hop 3: the UI --------
def test_the_frontend_sends_the_jurisdiction_on_both_calls():
    src = _read(API_JS)
    for fn in ("startCompliance", "complianceRefine"):
        m = re.search(r"export const %s[^;]+;" % fn, src, re.S)
        assert m, "%s missing from api.js" % fn
        assert "jurisdiction" in m.group(0), (
            "%s does not send the jurisdiction — the refine run would silently re-grade against "
            "the wrong regime set the moment the operator answers a question" % fn)


def test_the_page_offers_the_choice_and_does_not_hardcode_the_regimes():
    src = _read(PAGE)
    assert "getJurisdictions" in src, "the Compliance page never asks which jurisdictions exist"
    assert "startCompliance(name, lang, juris)" in src or re.search(
        r"startCompliance\([^)]*juris", src), "the page does not pass its selection to the API"
    # The old lede named the three EU regimes in the page itself, which is simply false for Canada.
    jsx = re.sub(r"\{?/\*.*?\*/\}?", "", src, flags=re.S)
    for eu_only in ("<b>NIS2</b>", "<b>Cyber Resilience Act</b>", "<b>EU AI Act</b>"):
        assert eu_only not in jsx, (
            "the Compliance page hardcodes %s — a second source of truth that is wrong for every "
            "non-EU jurisdiction" % eu_only)
