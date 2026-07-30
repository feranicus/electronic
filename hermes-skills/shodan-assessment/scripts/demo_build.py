#!/usr/bin/env python3
"""
demo_build.py — build the FABRICATED "Trojan Empire" demo artifacts.

WHY PRE-BAKED, NOT A LIVE RUN
-----------------------------
The Demo is public: anyone who reaches it can produce the full deck set. If each visit ran the real
engine it would burn Shodan query credits and DO inference tokens on a fictional company, and a
scripted crawler could drain both. It would also be dishonest — the whole point is that the numbers
are invented, so there is nothing to discover.

So the demo is DETERMINISTIC: fabricated findings -> the SAME deterministic deck builders the real
product uses -> five artifacts, built once, served as static files. The visitor sees exactly the
artifacts a paying engagement produces, with exactly the same rendering pipeline, and we spend
nothing per visit.

HONESTY IS A REQUIREMENT, NOT A DISCLAIMER
Every artifact and every screen states that the data is fabricated. The company does not exist; the
IPs are from RFC 5737 / RFC 3849 documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24)
which are reserved by the IETF precisely so they can never route to a real host. Nobody can mistake
a demo finding for a live one, and no real organisation is ever named.

    python demo_build.py --out /data/demo
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

COMPANY = "Trojan Empire"
SAFE = "Trojan_Empire"

# RFC 5737 TEST-NET ranges — guaranteed never to route anywhere real.
BANNER = ("DEMONSTRATION DATA — FABRICATED. Trojan Empire is a fictional company; every host, "
          "certificate, CVE and euro figure on these pages is invented to show the format of the "
          "deliverable. Nothing here was scanned and no real organisation is described.")


def findings():
    """Fabricated findings that exercise EVERY severity band and the high-value detectors."""
    return {
        "target": {
            "company": COMPANY,
            "audience": "Demonstration — fabricated data",
            "date": "2026-07-30",
            "scope": "ASN AS64500 · 3 prefixes · 4 domains: trojan-empire.example, ilion.example +2 more",
            "demo": True,
            "demo_notice": BANNER,
            "owned": {"asns": ["AS64500"], "group_domains": ["ilion.example", "wooden-horse.example"],
                      "related_unscoped": ["odysseus-shipping.example"]},
            "qwen": {"model": "demo-fixture", "cost_usd": 0.0},
        },
        "summary": {"unique_ips": 14, "records": 63, "dropped": 22,
                    "critical": 2, "high": 3, "medium": 3, "low": 2},
        "findings": [
            {"id": "C1", "sev": "CRITICAL", "kind": "secrets_manager", "_enriched": True,
             "title": "Internet-facing secrets / password manager",
             "evidence": ["192.0.2.41:443  nginx 1.24.0  Passbolt  cert CN=vault.trojan-empire.example"],
             "cves": [],
             "what": ["The group's credential vault answers directly on the public internet: "
                      "192.0.2.41:443 presents a Passbolt login page behind nginx, reachable from any "
                      "address on earth with no network-level control in front of it."],
             "why": ["This is the credential store for the rest of the estate, so one authentication "
                     "bypass here yields the keys to every other system rather than a single host. "
                     "Vault products are scanned for continuously and weaponised within days of an "
                     "advisory, and a public login page permits unlimited offline credential stuffing. "
                     "Under DSGVO Art. 32 and NIS2 Art. 21(2)(d) a credential store is a critical "
                     "asset requiring state-of-the-art access control."],
             "rem": [
                 {"tag": "COLT", "title": "Colt SASE / ZTNA — remove the vault from the public internet",
                  "body": "WHY COLT: a patch closes one CVE; brokering the vault behind identity-aware "
                          "access removes the entire public attack surface, so the next advisory is a "
                          "non-event. WHAT YOU GET: the vault reachable only by enrolled, MFA-verified "
                          "identities on managed devices. HOW: Colt ZTNA connector inside your network, "
                          "no inbound firewall rule and no published DNS record, operated 24x7."},
                 {"tag": "COLT", "title": "Colt Managed Security — KEV/EPSS-prioritised patching",
                  "body": "WHY COLT: vault CVEs are exploited faster than a quarterly maintenance "
                          "window. WHAT YOU GET: the vault tracked as a tier-0 asset with emergency "
                          "patch SLAs. HOW: KEV/EPSS-driven prioritisation with Colt-executed change."},
                 {"tag": "PSF", "title": "PSF workshop: Secrets & PKI rationalisation",
                  "body": "Maps every credential store and API key, designs a zero-trust injection "
                          "model and produces a roadmap to retire the internet-facing vault entirely."}],
             "refs": ["MITRE T1190", "MITRE T1555", "NIS2 Art.21(2)(d)", "DSGVO Art.32"]},

            {"id": "C2", "sev": "CRITICAL", "kind": "nas_exposed", "_enriched": True,
             "title": "Internet-facing NAS / storage appliance",
             "evidence": ["192.0.2.77:5001  Synology DiskStation DSM  cert CN=archive.ilion.example"],
             "cves": [],
             "what": ["A Synology DiskStation management interface is published on 192.0.2.77:5001, "
                      "serving the shared file archive for the Ilion subsidiary."],
             "why": ["A NAS is where the file shares and frequently the backups live, which makes it "
                     "the primary ransomware objective rather than a stepping stone. Deadbolt and "
                     "eCh0raix campaigns encrypted tens of thousands of internet-exposed appliances. "
                     "If this device also holds backup copies, a single compromise removes the "
                     "recovery path and with it the NIS2 Art. 21(2)(c) continuity obligation."],
             "rem": [
                 {"tag": "COLT", "title": "Colt SASE / ZTNA — take the management plane off the internet",
                  "body": "WHY COLT: appliance firmware lags and cannot be hardened enough to survive "
                          "continuous exploitation; removing public reachability ends the exposure "
                          "class outright. WHAT YOU GET: staff and site-to-site access with no "
                          "published management port. HOW: Colt-operated ZTNA broker with MFA."},
                 {"tag": "COLT", "title": "Colt Managed Firewall — allowlist management access",
                  "body": "WHY COLT: a default-deny edge policy is enforced independently of the "
                          "appliance's own settings. WHAT YOU GET: scanners never reach the login. "
                          "HOW: Colt-managed rulebase under change control."},
                 {"tag": "VENDOR", "title": "Immutable off-appliance backup copy",
                  "body": "An encrypted NAS must not also destroy the recovery point. Immutable object "
                          "storage or offline rotation, proven by a restore test."}],
             "refs": ["MITRE T1190", "MITRE T1486", "NIS2 Art.21(2)(c)"]},

            {"id": "H1", "sev": "HIGH", "kind": "pbx_exposed", "_enriched": True,
             "title": "Internet-facing PBX / telephony management",
             "evidence": ["198.51.100.12:5001  3CX Webclient  cert CN=trojanempire.3cx.example"],
             "cves": [],
             "what": ["The group's 3CX phone system exposes its web client and management interface "
                      "on 198.51.100.12, hosted on a third-party provider's address space."],
             "why": ["An exposed PBX carries direct financial risk through toll fraud: attackers place "
                     "premium-rate international calls and losses accrue in hours, billed to you. "
                     "3CX was also the vector of a well-documented supply-chain compromise, and SIP "
                     "registrars are brute-forced continuously. Call metadata is personal data under "
                     "DSGVO Art. 32, and a compromised PBX enables convincing voice phishing."],
             "rem": [
                 {"tag": "COLT", "title": "Colt SASE / ZTNA — publish the web client to enrolled users only",
                  "body": "WHY COLT: the softphone must reach the PBX; the whole internet need not. "
                          "WHAT YOU GET: remote working preserved while the management interface "
                          "disappears from scans. HOW: Colt ZTNA for the client, SIP on Colt Voice "
                          "transport rather than the public internet."},
                 {"tag": "COLT", "title": "Colt Voice / SIP trunking — carrier-side fraud controls",
                  "body": "WHY COLT: destination and spend limits stop toll fraud at the carrier, not "
                          "after the invoice. WHAT YOU GET: capped exposure with anomaly alerting."}],
             "refs": ["MITRE T1190", "MITRE T1621", "DSGVO Art.32"]},

            {"id": "H2", "sev": "HIGH", "kind": "vpn_edge", "_enriched": True,
             "title": "Exposed VPN / firewall management plane",
             "evidence": ["198.51.100.30:8443  OpenResty  cert CN=vpn.wooden-horse.example"],
             "cves": [],
             "what": ["A VPN administration portal is reachable on 198.51.100.30:8443 for the "
                      "Wooden Horse logistics subsidiary."],
             "why": ["Edge-appliance management is the single most common ransomware entry point, "
                     "because one valid credential converts directly into network access. Once "
                     "compromised it provides a pivot into the internal network for encryption or "
                     "exfiltration, violating NIS2 Art. 21 network-security expectations."],
             "rem": [
                 {"tag": "COLT", "title": "Colt SASE/SSE with ZTNA — retire the public admin portal",
                  "body": "WHY COLT: firewall rules only hide the port; ZTNA removes the need for a "
                          "public management interface at all. WHAT YOU GET: the portal vanishes from "
                          "scans, access is gated by MFA and device posture. HOW: cloud-delivered SSE."},
                 {"tag": "OSS", "title": "Teleport / OpenZiti",
                  "body": "Open-source ZTNA can provide secure access but requires in-house expertise "
                          "to deploy, scale and maintain — shifting rather than removing the burden."}],
             "refs": ["MITRE T1133", "CISA KEV", "NIS2 Art.21"]},

            {"id": "H3", "sev": "HIGH", "kind": "expired_cert", "_enriched": True,
             "title": "Expired TLS certificate on the mail cluster",
             "evidence": ["203.0.113.20:993  IMAPS  cert EXPIRED 2026-02-11  CN=mail.ilion.example",
                          "203.0.113.20:465  SMTPS  cert EXPIRED 2026-02-11",
                          "203.0.113.20:995  POP3S  cert EXPIRED 2026-02-11"],
             "cves": [],
             "what": ["The Ilion mail cluster presents a certificate that expired on 11 February 2026 "
                      "across IMAPS, SMTPS and POP3S on 203.0.113.20."],
             "why": ["An expired certificate trains users and mail clients to click through trust "
                     "warnings, which is exactly the conditioning an interception attack relies on. "
                     "It also signals unmanaged certificate lifecycle to an attacker profiling the "
                     "estate, and breaches BSI TR-02102 crypto baselines for a mail path carrying "
                     "client correspondence."],
             "rem": [
                 {"tag": "COLT", "title": "Colt Managed Security — certificate lifecycle + monitoring",
                  "body": "WHY COLT: expiry is a process failure, not a one-off fix; automated renewal "
                          "and alerting prevents recurrence. WHAT YOU GET: no surprise expiries and an "
                          "auditable inventory. HOW: ACME automation with Colt-monitored alerting."}],
             "refs": ["BSI TR-02102", "DSGVO Art.32"]},

            {"id": "M1", "sev": "MEDIUM", "kind": "weak_tls", "_enriched": True,
             "title": "Legacy / weak TLS (TLS 1.0 / 1.1)",
             "evidence": ["192.0.2.41:443  nginx", "198.51.100.30:8443  OpenResty",
                          "203.0.113.9:443  Apache httpd"],
             "cves": [],
             "what": ["Three hosts still negotiate TLS 1.0 and 1.1, protocols formally deprecated by "
                      "RFC 8996."],
             "why": ["Deprecated TLS permits downgrade and interception against client data and "
                     "credentials in transit, and is flagged in every compliance audit under PCI-DSS "
                     "4.1 and BSI TR-02102. Continued use is increasingly a contractual problem as "
                     "well as a technical one."],
             "rem": [
                 {"tag": "COLT", "title": "Colt Managed WAF — enforce modern TLS at the edge",
                  "body": "WHY COLT: per-host configuration drifts; terminating TLS at a managed edge "
                          "applies one hardened policy everywhere. WHAT YOU GET: traffic upgraded to "
                          "TLS 1.2+ with central proof of compliance for auditors."}],
             "refs": ["RFC 8996", "PCI-DSS 4.1", "BSI TR-02102"]},

            {"id": "M2", "sev": "MEDIUM", "kind": "verbose_banner", "_enriched": True,
             "title": "Verbose service banners disclose exact versions",
             "evidence": ["192.0.2.41:80  nginx 1.24.0", "203.0.113.9:80  Apache httpd 2.4.58"],
             "cves": [],
             "what": ["Public services advertise precise product and version strings."],
             "why": ["Exact versions let an attacker select a working exploit without touching the "
                     "target, cutting reconnaissance time to near zero. It is cheap to remove and "
                     "contributes to ISO 27001 A.8.2 hardening expectations."],
             "rem": [
                 {"tag": "COLT", "title": "Colt Managed Firewall — sanitise outbound banners",
                  "body": "WHY COLT: a uniform header-rewrite policy at the network edge covers every "
                          "host at once. WHAT YOU GET: generic responses that frustrate scanners."}],
             "refs": ["ISO 27001 A.8.2"]},

            {"id": "M3", "sev": "MEDIUM", "kind": "self_signed", "_enriched": True,
             "title": "Self-signed certificate on an internal-facing service",
             "evidence": ["203.0.113.44:8006  cert self-signed  CN=pve.wooden-horse.example"],
             "cves": [],
             "what": ["A hypervisor management console presents a self-signed certificate."],
             "why": ["Without a trust anchor, users cannot distinguish the real console from an "
                     "impostor, so an interception attack becomes indistinguishable from normal "
                     "operation. On a virtualisation management plane the blast radius is every "
                     "workload the host carries."],
             "rem": [
                 {"tag": "COLT", "title": "Colt Managed Security — CA-signed certificates + renewal",
                  "body": "WHY COLT: a managed internal PKI gives every service a real trust anchor "
                          "without manual reissue. WHAT YOU GET: warnings disappear, MITM is detectable."}],
             "refs": ["BSI TR-02102"]},

            {"id": "L1", "sev": "LOW", "kind": "standard_service", "_enriched": True,
             "title": "Standard services exposed",
             "evidence": ["203.0.113.9:80  Apache httpd", "192.0.2.41:80  nginx"],
             "cves": [],
             "what": ["Ordinary web services on their expected ports."],
             "why": ["Baseline exposure with no defect observed. Recorded so that drift from this "
                     "baseline is visible on the next scan rather than discovered by an attacker."],
             "rem": [{"tag": "COLT", "title": "Colt continuous external re-scan",
                      "body": "Keeps the surface measured over time instead of a point-in-time snapshot."}],
             "refs": []},

            {"id": "L2", "sev": "LOW", "kind": "standard_service", "_enriched": True,
             "title": "Mail transport advertised",
             "evidence": ["203.0.113.20:25  Postfix smtpd"],
             "cves": [],
             "what": ["SMTP is reachable, as a mail exchanger must be."],
             "why": ["Expected and necessary exposure; noted for completeness of the inventory."],
             "rem": [{"tag": "COLT", "title": "Colt Managed Email Security",
                      "body": "Filtering and anti-spoofing in front of the transport."}],
             "refs": []},
        ],
        "strengths": [
            "No database ports, RDP or ICS protocols are exposed anywhere on the estate.",
            "DNSSEC is enabled on the primary domain and all four subsidiaries.",
            "SPF, DKIM and DMARC are published with an enforcing DMARC policy.",
        ],
    }


def build(outdir):
    os.makedirs(outdir, exist_ok=True)
    import run_assessment as RA

    fj = findings()
    fp = os.path.join(outdir, "findings.json")
    json.dump(fj, open(fp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    # SAME deterministic derivations the real product uses — the demo must not be a special case.
    cj = RA.derive_cbiq(fj)
    gj = RA.derive_geopol(fj, {"domains": ["trojan-empire.example"], "asns": ["AS64500"],
                               "nets": [], "org": COMPANY}, cj)
    for name, obj in (("cbiq.json", cj), ("geopol.json", gj)):
        json.dump(obj, open(os.path.join(outdir, name), "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)

    env = {**os.environ, "DECK_LANG": os.environ.get("DECK_LANG", "en")}
    jobs = [
        ("build_findings_deck.js", [fp], "%s_Shodan_Findings.pptx" % SAFE),
        ("build_cbiq_deck.js", [os.path.join(outdir, "cbiq.json")], "%s_C-BIQ.pptx" % SAFE),
        ("build_geopol_deck.js", [os.path.join(outdir, "geopol.json")], "%s_GEOPOL.pptx" % SAFE),
    ]
    built = []
    for script, args, out in jobs:
        dest = os.path.join(outdir, out)
        r = subprocess.run(["node", os.path.join(HERE, script)] + args + [dest],
                           capture_output=True, text=True, timeout=180, env=env)
        if os.path.exists(dest):
            built.append(out)
        else:
            print("[demo] %s FAILED: %s" % (script, (r.stderr or "")[-200:]), file=sys.stderr)

    # The animated GEOPOL HTML (5th deliverable).
    #
    # GO THROUGH author_geopol.py, exactly as run_assessment.py does. The first cut of this function
    # called build_geopol_html.js directly with a content file that was never written — node happily
    # rendered the SKELETON, so a 35KB file appeared, the build reported success, and every headline
    # in it was an empty <h1></h1>. A file existing is not a file being right.
    #
    # author_geopol has a DETERMINISTIC path (it only reaches for a model if one is configured), so
    # the demo is reproducible and costs nothing — which is the whole premise of a pre-baked demo.
    dest = os.path.join(outdir, "%s_GEOPOL_Animated.html" % SAFE)
    r = subprocess.run([sys.executable, os.path.join(HERE, "author_geopol.py"),
                        fp, os.path.join(outdir, "geopol.json"), dest, "--company", COMPANY],
                       capture_output=True, text=True, timeout=240,
                       env={**env, "OUTDIR": outdir})
    if not os.path.exists(dest):
        print("[demo] author_geopol FAILED: %s" % ((r.stderr or r.stdout or "")[-300:]),
              file=sys.stderr)
    else:
        # PROVE it is populated, not a hollow shell, before anyone can download it.
        html = open(dest, encoding="utf-8").read()
        empty = html.count("<h1></h1>") + html.count('<p class="sub"></p>')
        if empty or COMPANY not in html:
            print("[demo] author_geopol produced an EMPTY shell (%d blank headings, company %s) "
                  "- discarding" % (empty, "present" if COMPANY in html else "MISSING"),
                  file=sys.stderr)
            os.remove(dest)

    # The fabrication notice must travel WITH the artifact. This page gets forwarded as a link, and
    # a link carries none of the /demo page's context — so the banner is injected into the document
    # itself, fixed to the top of the viewport where it cannot be scrolled away from.
    if os.path.exists(dest):
        html = open(dest, encoding="utf-8").read()
        banner = (
            '<div style="position:fixed;top:0;left:0;right:0;z-index:99999;'
            'background:#F7C844;color:#08121f;font:700 12.5px/1.45 system-ui,sans-serif;'
            'letter-spacing:.04em;padding:9px 16px;text-align:center;'
            'box-shadow:0 2px 14px rgba(0,0,0,.5)">DEMONSTRATION &mdash; FABRICATED DATA. '
            '&ldquo;Trojan Empire&rdquo; is a fictional company; every host, certificate, CVE and '
            'euro figure below is invented to show the format of the deliverable. Nothing was '
            'scanned and no real organisation is described.</div>'
            '<div style="height:38px"></div>')
        if "<body" in html:
            i = html.index(">", html.index("<body")) + 1
            html = html[:i] + banner + html[i:]
            open(dest, "w", encoding="utf-8").write(html)
        built.append(os.path.basename(dest))

    print("[demo] built %d artifact(s) in %s: %s" % (len(built), outdir, ", ".join(built)))
    return built


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.environ.get("DEMO_DIR", "/data/demo"))
    a = ap.parse_args()
    built = build(a.out)
    return 0 if len(built) >= 3 else 1


if __name__ == "__main__":
    sys.exit(main())
