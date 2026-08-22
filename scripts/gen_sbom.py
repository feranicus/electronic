#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_sbom.py — a CycloneDX Software Bill of Materials for what cybergod.ai actually ships.

    python scripts/gen_sbom.py            # writes the served SBOM
    python scripts/gen_sbom.py --check    # fail if the committed SBOM is stale (for ship.py)

WHY, AND WHY NOW. CRA Annex I Part II requires a manufacturer to maintain an SBOM for a product
with digital elements, and BSI TR-03183-2 is the most detailed public specification of what a
CRA-grade SBOM must contain. From 11 December 2027 our white-label/OEM build is exactly such a
product. It is also a sales asset today: we sell compliance assessments, and being able to hand a
partner an SBOM for our own product is the demonstration that we do what we advise.

WHY A SOURCE SBOM FROM THE MANIFESTS, and not a Trivy image scan. Our images build in two different
places (colttechbot/cassandra in GitHub Actions, colt-web on the droplet), so there is no single
image to scan on the machine that runs this. Trivy is also not installed on the operator's PC, and
requiring a tool install is a manual step (operating principle 1). The dependency MANIFESTS -- the
requirements.txt files and package-lock.json -- are the authoritative list of the components WE
chose, which is precisely what CRA asks a manufacturer to declare. This SBOM covers the application
dependencies; it does NOT enumerate base-image OS packages, and it says so in its own metadata
rather than pretending to be complete. That honesty is the same doctrine as "absence of evidence is
never a finding".

CycloneDX 1.5, because it is the format BSI TR-03183-2 accepts and the one Trivy, Grype and Dependency-
Track all read, so the file is useful to a partner's own tooling, not just ours.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "webapp", "frontend", "public", ".well-known", "sbom.cdx.json")

# The manifests that describe what the SHIPPED product depends on. Deliberately NOT the whole repo:
# jobhuntwow and the MEDDPICC droplet are separate projects, and a bill of materials that lists
# another product's dependencies is wrong, not thorough.
PY_MANIFESTS = [
    "webapp/backend/requirements.txt",
    "requirements.txt",
    "hermes-skills/shodan-assessment/requirements.txt",
]
NPM_LOCKS = ["webapp/frontend/package-lock.json"]


def _norm(name):
    return re.sub(r"[^a-z0-9._-]+", "-", (name or "").strip().lower())


def _py_components():
    """Read pinned Python dependencies. A comment or a blank line is not a component, and an
    unpinned line is recorded with version 'unspecified' rather than silently dropped -- an
    unpinned dependency is itself a finding a reader should see."""
    out = {}
    for rel in PY_MANIFESTS:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        for raw in open(p, encoding="utf-8"):
            line = raw.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            m = re.match(r"^([A-Za-z0-9._-]+)\s*(?:\[[^\]]*\])?\s*([=<>!~]=?)?\s*([0-9][\w.*+-]*)?",
                         line)
            if not m:
                continue
            name, op, ver = m.group(1), m.group(2), m.group(3)
            version = ver if (op in ("==", "~=", ">=") and ver) else "unspecified"
            out[_norm(name)] = {"type": "library", "name": name, "version": version,
                                "purl": "pkg:pypi/%s@%s" % (_norm(name), version),
                                "ecosystem": "pypi", "pinned": op == "==" and bool(ver)}
    return out


def _npm_components():
    """Read the RESOLVED npm tree from package-lock.json (lockfile v2/v3 `packages` map). The lock,
    not package.json, because the lock is what actually gets installed -- the same reason a
    reproducible build reads the lock."""
    out = {}
    for rel in NPM_LOCKS:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        try:
            data = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        for path, meta in (data.get("packages") or {}).items():
            if not path or "node_modules/" not in path:
                continue
            name = path.split("node_modules/")[-1]
            ver = meta.get("version") or "unspecified"
            out["npm:" + name + "@" + ver] = {
                "type": "library", "name": name, "version": ver,
                "purl": "pkg:npm/%s@%s" % (name, ver), "ecosystem": "npm",
                "pinned": ver != "unspecified"}
    return out


def build():
    comps = list(_py_components().values()) + list(_npm_components().values())
    comps.sort(key=lambda c: (c["ecosystem"], c["name"].lower()))
    doc = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:" + _uuid_from(comps),
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tools": [{"vendor": "Cybergod LLC", "name": "gen_sbom.py", "version": "1.0"}],
            "component": {"type": "application", "name": "cybergod.ai",
                          "version": _git_short(),
                          "supplier": {"name": "Cybergod LLC / S4Biz Group"}},
            # HONEST SCOPE, stated in the document itself. A reader must not mistake this for a full
            # image SBOM: it is the application dependency tree, not the base-image OS packages.
            "properties": [
                {"name": "cybergod:scope",
                 "value": "application dependencies (pypi + npm) from committed manifests; "
                          "base-image OS packages are NOT enumerated"},
                {"name": "cybergod:standard", "value": "CycloneDX 1.5; aligned to BSI TR-03183-2"},
                {"name": "cybergod:components", "value": str(len(comps))},
            ],
        },
        "components": [{"type": c["type"], "name": c["name"], "version": c["version"],
                        "purl": c["purl"], "scope": "required"} for c in comps],
    }
    return doc


def _uuid_from(comps):
    """A deterministic serial number from the component set, so an unchanged dependency tree
    produces an unchanged SBOM and --check does not churn on every run."""
    h = hashlib.sha256(json.dumps(sorted(c["purl"] for c in comps)).encode()).hexdigest()
    return "%s-%s-%s-%s-%s" % (h[:8], h[8:12], h[12:16], h[16:20], h[20:32])


def _git_short():
    head = os.path.join(ROOT, ".git", "HEAD")
    try:
        ref = open(head, encoding="utf-8").read().strip()
        if ref.startswith("ref:"):
            ref = open(os.path.join(ROOT, ".git", ref[5:]), encoding="utf-8").read().strip()
        return ref[:12]
    except Exception:
        return "unknown"


def _stable(doc):
    """A copy whose volatile fields (timestamp, serial) are blanked, so two runs of the SAME
    dependency tree compare equal. --check compares this, not the raw file."""
    d = json.loads(json.dumps(doc))
    d["metadata"]["timestamp"] = ""
    d["serialNumber"] = ""
    d["metadata"]["component"]["version"] = ""
    for pr in d["metadata"]["properties"]:
        pass
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="fail if the committed SBOM no longer matches the manifests")
    a = ap.parse_args()
    doc = build()
    if a.check:
        if not os.path.exists(OUT):
            sys.exit("[X] no SBOM at %s. Run: python scripts/gen_sbom.py" % OUT)
        have = json.load(open(OUT, encoding="utf-8"))
        if _stable(have) != _stable(doc):
            sys.exit("[X] SBOM is STALE: a dependency changed and the committed SBOM was not "
                     "regenerated. Run: python scripts/gen_sbom.py")
        print("  SBOM current: %d components" % len(doc["components"]))
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(doc, open(OUT, "w", encoding="utf-8"), indent=2)
    # keep the served dist copy in step if it exists, so a build already on disk is not stale
    dist = OUT.replace("/public/", "/dist/").replace("\\public\\", "\\dist\\")
    if os.path.isdir(os.path.dirname(dist)):
        json.dump(doc, open(dist, "w", encoding="utf-8"), indent=2)
    print("wrote %s  (%d components: %d pypi, %d npm)"
          % (OUT, len(doc["components"]),
             sum(1 for c in doc["components"] if c["purl"].startswith("pkg:pypi")),
             sum(1 for c in doc["components"] if c["purl"].startswith("pkg:npm"))))


if __name__ == "__main__":
    main()
