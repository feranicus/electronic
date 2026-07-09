import shodan_recon as R
import run_assessment as RA

def _ident():
    return {"seed":"AS1","asns":["AS1"],"nets":["1.2.3.0/24"],"org":"Acme","brand":"Acme",
            "asn_holder":"Acme","domains":[],"org_is_carrier":False,"org_is_cdn":False}

def test_variants_and_categories():
    ident = _ident()
    R.merge_variants(ident, orgs=["Acme GmbH"], brands=["acme"], domains=["acme.com"], favicons=["-1234"])
    run = [f for f in R.build_filters(ident) if f.get("run")]
    cats = {f["cat"] for f in run}
    assert "identity" in cats and "sweep" in cats
    clauses = " ".join(f["clause"] for f in run)
    assert 'ssl:"acme"' in clauses
    assert 'http.title:"acme"' in clauses
    assert "http.favicon.hash:-1234" in clauses
    assert 'org:"Acme GmbH"' in clauses

def test_ftype_mapping():
    assert RA.ftype("Exposed VPN / firewall mgmt (2 hosts)") == "vpn"
    assert RA.ftype("Shodan-tagged vulnerabilities (CVE)") == "vuln"
    assert RA.ftype("Exposed database (MariaDB)") == "db"

def test_adversary_inversion():
    # Russian/CIS targets must NOT get pro-Russia APTs; Western ones stay normal
    assert RA._adversary_aligned({"asn_holder":"ROSATOM MINERALS JSC","domains":[]}) is True
    assert RA._adversary_aligned({"brand":"x","domains":["gazprom.ru"]}) is True
    assert RA._adversary_aligned({"asn_holder":"SGL Carbon SE","domains":["sglcarbon.com"]}) is False
