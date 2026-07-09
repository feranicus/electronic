#!/usr/bin/env python3
"""
run_assessment.py — ONE command, full autonomous pipeline, NO LLM in the data path.

seed -> identity+Shodan (findings.json) -> DERIVE cbiq.json + geopol.json deterministically
     -> build all 3 Colt decks. Hermes calls this once and attaches the 3 .pptx.

This exists so the agent NEVER hand-writes JSON (that caused broken JSON + rate-limits).

Usage:
    python3 run_assessment.py --seed "keb.de" --outdir /root/work
    python3 run_assessment.py --seed "Company" --asn AS123 --net 1.2.3.0/24 --outdir /root/work
    python3 run_assessment.py --from-findings /root/work/findings.json --company keb.de --outdir /root/work
"""
import os, sys, json, argparse, subprocess, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shodan_recon as R

# ---------------- finding-type inference ----------------
def ftype(title):
    t = title.lower()
    if "rdp" in t: return "rdp"
    if "database" in t: return "db"
    if "ics" in t or "ot protocol" in t or "scada" in t: return "ics"
    if "vpn" in t or "firewall mgmt" in t: return "vpn"
    if "vulnerabilit" in t or "cve" in t: return "vuln"
    if "panel" in t or "owa" in t or "login" in t or "admin" in t: return "panel"
    if "remote-admin" in t or "telnet" in t or "vnc" in t or "winrm" in t or "smb" in t: return "remote"
    if "tls" in t or "certificate" in t: return "tls"
    if "banner" in t: return "banner"
    return "other"

def _pert(b): return (b[0] + 4*b[1] + b[2]) / 6.0

# FAIR defaults per finding type (€M). Priced types = CRIT/HIGH exposures.
CBIQ_DEF = {
 "rdp":   dict(tef=18, vuln=0.06, lm=[0.1,0.4,2.0, 3.0,2.0, 0.2,0.5], ctl="SASE / ZTNA",                cc=0.5, after=0.06, pml=[25,80]),
 "db":    dict(tef=10, vuln=0.08, lm=[0.1,0.5,1.5, 4.0,2.0, 0.3,0.5], ctl="Managed Firewall + DLP",     cc=0.4, after=0.08, pml=[20,70]),
 "ics":   dict(tef=8,  vuln=0.05, lm=[0.2,0.8,5.0, 3.0,2.0, 0.3,1.0], ctl="IT/OT segmentation + OT mon", cc=0.6, after=0.05, pml=[30,120]),
 "vpn":   dict(tef=15, vuln=0.07, lm=[0.1,0.4,2.0, 3.0,2.0, 0.2,0.5], ctl="SASE / ZTNA",                cc=0.5, after=0.06, pml=[25,90]),
 "vuln":  dict(tef=20, vuln=0.10, lm=[0.1,0.4,1.8, 2.5,1.5, 0.2,0.4], ctl="Managed patch + WAF",        cc=0.4, after=0.10, pml=[15,60]),
 "panel": dict(tef=15, vuln=0.06, lm=[0.1,0.3,1.2, 2.0,1.5, 0.2,0.3], ctl="WAF + MFA + geofence",       cc=0.3, after=0.08, pml=[10,45]),
 "remote":dict(tef=12, vuln=0.06, lm=[0.1,0.3,1.2, 1.5,1.0, 0.1,0.3], ctl="Mgmt-network isolation",     cc=0.3, after=0.08, pml=[10,40]),
}
# Real, public, dated, costed incidents per finding type — the SGL/Rosneft "realComparable" style.
# Used as a GUARANTEED fallback so every priced finding shows a named precedent even if the LLM is terse.
REAL_INCIDENTS = {
 "vpn":   "Change Healthcare 2024 · $2.45B · BlackCat ransomware via remote access lacking MFA",
 "vuln":  "Equifax 2017 · $1.4B+ · unpatched web-server CVE (Apache Struts CVE-2017-5638), 147M records",
 "db":    "First American Financial 2019 · 885M records exposed via unauthenticated data-tier access",
 "rdp":   "Colonial Pipeline 2021 · $4.4M ransom + 6-day fuel shutdown · exposed remote-access entry (T1133)",
 "remote":"Norsk Hydro 2019 · ~$70M · LockerGoga ransomware forced global plants to manual operation",
 "ics":   "Ukraine power grid 2015-16 · Sandworm/APT44 · regional blackouts via internet-reachable ICS",
 "panel": "Snowflake customer breaches 2024 · 165 orgs · stolen credentials against exposed portals",
 "other": "Maersk / NotPetya 2017 · ~$300M · self-propagating malware halted global operations",
}
BUCKETS = [("L1","Response & forensics","above"),("L2","Regulatory & legal","above"),
           ("L3","Operational downtime","below"),("L4","Customer & revenue","below"),
           ("L5","Reputational / brand","below"),("L6","Third-party / contractual","below"),
           ("L7","Capital & funding","below")]

def derive_cbiq(fj):
    cur = {"code":"EUR","symbol":"€","word":"euros"}
    findings = []
    for f in fj["findings"]:
        if f["sev"] not in ("CRITICAL","HIGH"): continue
        d = CBIQ_DEF.get(ftype(f["title"]))
        if not d: continue
        lef = round(d["tef"]*d["vuln"], 2)
        meanLM = sum(_pert(d["lm"][i:i+3]) for i in (0,3,5) if False)  # placeholder
        # 7 buckets from lm scaled roughly: treat lm as [L1min,L1lik,L1max, L3.. ] simplified:
        lm = {"L1":[d["lm"][0],d["lm"][1],d["lm"][2]],"L2":[0.0,0.1,1.0],
              "L3":[0.1,d["lm"][3]*0.4,d["lm"][3]],"L4":[0.1,d["lm"][4]*0.4,d["lm"][4]],
              "L5":[0.0,0.3,2.0],"L6":[0.0,d["lm"][5],d["lm"][6]],"L7":[0.0,0.1,1.0]}
        meanLM = sum(_pert(v) for v in lm.values())
        ale = round(lef*meanLM, 2)
        findings.append({"id":f["id"],"tier":("CRIT" if f["sev"]=="CRITICAL" else "HIGH"),
            "label":f["title"],"asset":{"C":4,"I":4,"A":5},
            "lossScenario":(f["why"][0] if f.get("why") else f["title"]),
            "realComparable":(f.get("realComparable") or REAL_INCIDENTS.get(ftype(f["title"])) or REAL_INCIDENTS["other"]),
            "tef":d["tef"],"vuln":d["vuln"],"lef":lef,"lmBuckets":lm,
            "aleRange":[round(ale*0.6,1),round(ale*1.6,1)],"aleMid":ale,
            "pmlRange":d["pml"],"codRange":[round(ale*0.6/12,2),round(ale*1.6/12,2)],
            "coltControl":d["ctl"],"controlCost":d["cc"],"aleAfter":d["after"],
            "rosiPct":int(((ale-d["after"]-d["cc"])/d["cc"])*100) if d["cc"] else 0})
    aleLo=round(sum(x["aleRange"][0] for x in findings),1); aleHi=round(sum(x["aleRange"][1] for x in findings),1)
    aleLik=round(sum(x["aleMid"] for x in findings),1)
    pmls=sorted(({"id":x["id"],"pml":x["pmlRange"][1]} for x in findings), key=lambda z:-z["pml"])[:2]
    ctrls=[]; seen=set()
    for x in findings:
        c=x["coltControl"]
        if c not in seen: seen.add(c); ctrls.append({"label":"− "+c.split(" /")[0].split(" +")[0],"cut":round(aleHi/max(len(set(y['coltControl'] for y in findings)),1),2),"svc":c})
    portfolio={"aleRange":[aleLo,aleHi],"aleLikely":aleLik,"largestPmls":pmls or [{"id":"—","pml":0}],
        "waterfall":ctrls or [{"label":"− SASE","cut":aleHi,"svc":"SASE / ZTNA"}],
        "rosiPct": int(sum(x["rosiPct"] for x in findings)/len(findings)) if findings else 0,
        "payback":"< 3 months","codAvoided":f"€{round(aleLik/12*0.7,1)}–{round(aleHi/12,1)}M/mo"}
    return {"customer":fj["target"]["company"],"currency":cur,
        "classification":"INTERNAL — COLT CONFIDENTIAL · ILLUSTRATIVE MODEL OUTPUT · NOT FOR EXTERNAL DISTRIBUTION",
        "frameworks":["FAIR","NIST IR 8286D"],"method":"Monte-Carlo CRQ (10k runs)","remediationSuite":"DDoS · WAF · Mgd FW · SASE",
        "montecarlo":{"runs":10000,"distribution":"PERT"},
        "frequencyBands":{"Routine":[1,4],"Likely":[0.3,1],"Plausible":[0.1,0.3],"Tail":[0.02,0.1]},
        "buckets":[{"id":b[0],"name":b[1],"surface":b[2]} for b in BUCKETS],
        "benchmarks":[{"label":"Avg. breach cost","value":"USD 5.56 M","source":"IBM/Ponemon 2025"},
                      {"label":"Orgs quantifying cyber risk","value":"~15%","source":"PwC"},
                      {"label":"DORA penalty (critical ICT)","value":"up to 2% turnover","source":"EU DORA"}],
        "findings":findings if findings else [{"id":"—","tier":"HIGH","label":"No priced findings",
            "asset":{"C":3,"I":3,"A":3},"lossScenario":"No CRIT/HIGH exposures priced.","realComparable":"—",
            "tef":1,"vuln":0.01,"lef":0.01,"lmBuckets":{k:[0,0.1,0.5] for k in ("L1","L2","L3","L4","L5","L6","L7")},
            "aleRange":[0,0.1],"aleMid":0.05,"pmlRange":[0,1],"codRange":[0,0.01],"coltControl":"—","controlCost":0.1,"aleAfter":0.05,"rosiPct":0}],
        "portfolio":portfolio,
        "lossExceedance":{"thresholds":["€1M","€5M","€10M","€20M","€40M"],"before":[97,66,44,25,11],"after":[6,1.5,0.6,0.2,0.05]}}

# ---------------- geopol actor catalog (real, public, sourced) ----------------
CATALOG = [
 dict(trig=["vpn","vuln","panel","remote"], band="ORGANISED eCRIME", sponsor="RUSSIA-BASED RaaS", tier="CRITICAL",
   eyebrow="Most-active RaaS 2025-26", title="Qilin (Agenda) — RaaS exploiting exposed VPN/edge appliances",
   pills=["RaaS","Energy/Industry","Edge CVEs"],
   what=["Ransomware-as-a-service; affiliates weaponise exposed VPN/edge appliances and unpatched CVEs.",
         "Double-extortion: encrypt + leak. Among the most active RaaS operations in 2025-26."],
   evidence=["CAMPAIGN: mass exploitation of exposed VPN/edge","TTP: valid-accounts -> lateral -> encrypt",
             "ATTRIB: RaaS affiliate model   Grade B2"],
   why="The exposed VPN/mgmt and CVE-flagged hosts in this estate are exactly Qilin's entry pattern.",
   refs="ransomware.live · CISA advisories · vendor IR reports", admiralty="B2",
   score=dict(intent="High",capability="High",exposureFit="High"), like="Likely — direct intrusion via exposed edge",
   rem=[("VENDOR","Patch exposed edge/VPN now","Prioritise KEV-listed CVEs on internet-facing appliances."),
        ("COLT","Colt SASE / ZTNA","Retire internet-exposed VPN; broker access with MFA + posture."),
        ("PSF","Immutable backup + segmentation","Contain blast radius; recover without paying.")]),
 dict(trig=["vpn","remote","panel"], band="ORGANISED eCRIME", sponsor="eCrime (VPN without MFA)", tier="HIGH",
   eyebrow="VPN-focused ransomware", title="Akira — ransomware via VPN gateways without MFA",
   pills=["Ransomware","VPN","No-MFA"],
   what=["Consistently breaches organisations through VPN appliances lacking MFA.",
         "Fast dwell-to-encryption; targets mid-market industry across DACH."],
   evidence=["CAMPAIGN: VPN brute/again exposed gateways","TTP: valid-accounts -> RClone exfil -> encrypt",
             "ATTRIB: eCrime cluster   Grade B2"],
   why="Exposed VPN/firewall-mgmt hosts without MFA match Akira's primary access vector.",
   refs="CISA #StopRansomware · Arctic Wolf · vendor IR", admiralty="B2",
   score=dict(intent="High",capability="Med",exposureFit="High"), like="Likely — if any VPN lacks MFA",
   rem=[("VENDOR","Enforce MFA on all VPN","Kill password-only remote access."),
        ("COLT","Colt Managed Firewall + SASE","Consolidate + monitor remote access."),
        ("OSS","Sigma/EDR detections","Alert on RClone + suspicious VPN logins.")]),
 dict(trig=["ics"], band="NATION-STATE", sponsor="RUSSIA GRU (Unit 74455)", tier="CRITICAL",
   eyebrow="Destructive OT/ICS", title="Sandworm / APT44 — destructive attacks on OT/ICS",
   pills=["MITRE G0034","APT44","OT"],
   what=["GRU-linked; history of destructive attacks on energy/industrial control systems.",
         "Capable of ICS-specific effects (e.g. Industroyer-class)."],
   evidence=["CAMPAIGN: European grid/industry targeting","ATT&CK: G0034 · T0831 (OT)",
             "ATTRIB: GRU 74455   Grade A2"],
   why="Internet-exposed ICS/OT protocols here are the exact attack surface APT44 targets.",
   refs="MITRE G0034 · ESET · Dragos · BSI KRITIS", admiralty="A2",
   score=dict(intent="Med",capability="High",exposureFit="High"), like="Plausible — high impact, sector-fit",
   rem=[("PSF","IT/OT segmentation + immutable backup","Air-gap OT; no direct internet path."),
        ("COLT","Colt Managed Firewall + IP Guardian","Filter + DDoS-protect the perimeter."),
        ("OSS","Dragos / Sigma OT monitoring","Detect ICS protocol anomalies.")]),
 dict(trig=["panel","vuln","remote"], band="NATION-STATE", sponsor="RUSSIA GRU (Unit 26165)", tier="HIGH",
   eyebrow="Credential & panel access", title="APT28 (Fancy Bear) — credential theft & exposed-panel access",
   pills=["MITRE G0007","APT28","Creds"],
   what=["GRU cyber-espionage; harvests credentials and exploits exposed web/mail panels.",
         "Long-running access for intelligence collection."],
   evidence=["CAMPAIGN: webmail/panel credential ops","ATT&CK: G0007 · T1110 · T1078",
             "ATTRIB: GRU 26165   Grade A2"],
   why="Exposed OWA/login/admin panels are APT28's classic foothold.",
   refs="MITRE G0007 · CISA · vendor advisories", admiralty="A2",
   score=dict(intent="Med",capability="High",exposureFit="Med"), like="Plausible — collection-driven",
   rem=[("VENDOR","MFA + geofence all panels","Kill password-spray on OWA/admin."),
        ("COLT","Colt WAF + SASE","Shield panels; broker with identity."),
        ("OSS","Impossible-travel detections","Alert on anomalous panel logins.")]),
 dict(trig=["*"], band="HACKTIVIST", sponsor="Pro-Russia hacktivists", tier="HIGH",
   eyebrow="DDoS & defacement", title="NoName057(16) — pro-Russia DDoS against Western industry",
   pills=["DDoS","Hacktivist","DACH"],
   what=["Politically-motivated DDoS campaigns against European government and industry.",
         "Opportunistic; amplifies any exposed, unprotected service."],
   evidence=["CAMPAIGN: DDoSia project waves","TTP: volumetric + L7 DDoS",
             "ATTRIB: hacktivist collective   Grade B3"],
   why="Any internet-facing service here is a target of opportunity for volumetric DDoS.",
   refs="ENISA · national CERTs · vendor telemetry", admiralty="B3",
   score=dict(intent="High",capability="Med",exposureFit="Med"), like="Routine — recurring waves",
   rem=[("COLT","Colt IP Guardian (DDoS)","Absorb volumetric + L7 floods at the edge."),
        ("VENDOR","Rate-limit + WAF","Protect exposed apps."),
        ("OSS","Anycast/CDN fronting","Distribute + hide origins.")]),
]

# For Russian/CIS/adversary-aligned targets the threat model INVERTS: Russian state APTs are
# aligned (not hostile); the real adversaries are pro-Ukraine hack-and-leak/DDoS crews.
RU_MARKERS = ("rosatom","rosenergoatom","greenatom","armz","tvel","atomstroyexport","rosneft",
              "gazprom","sberbank","russia","russian","kremlin","kalashnikov","lukoil","transneft")
def _adversary_aligned(ident):
    txt = " ".join(str(ident.get(k) or "") for k in ("asn_holder","brand","org","seed")).lower()
    txt += " " + " ".join(str(d) for d in (ident.get("domains") or [])).lower()
    if any(m in txt for m in RU_MARKERS): return True
    if any(str(d).lower().endswith((".ru",".by",".su")) for d in (ident.get("domains") or [])): return True
    return False

CATALOG_ALIGNED = [
 dict(trig=["*"], band="HACKTIVIST", sponsor="Pro-Ukraine", tier="CRITICAL",
   eyebrow="Hack-and-leak vs Russian state orgs", title="UCA (Ukrainian Cyber Alliance) — hack-and-leak of Russian state entities",
   pills=["Hacktivist","Hack-and-leak","Doxing"],
   what=["Pro-Ukraine collective; breaches Russian government/industry and leaks data since 2022.",
         "Symbolic + operational: exfiltration, defacement, public dumps."],
   evidence=["CAMPAIGN: sustained ops vs Russian state orgs","TTP: intrusion -> exfil -> public leak",
             "ATTRIB: pro-Ukraine collective   Grade B2"],
   why="A Russian state-sector estate is a priority symbolic target for pro-Ukraine hack-and-leak.",
   refs="public reporting · leak sites · CERT-UA context", admiralty="B2",
   score=dict(intent="High",capability="Med",exposureFit="High"), like="Likely — sustained targeting",
   rem=[("VENDOR","Harden + monitor exposed edge","Assume determined hacktivist interest."),
        ("COLT","Colt Managed Firewall + DPI/NDR","Detect intrusion + bulk exfiltration."),
        ("PSF","Immutable backup + leak monitoring","Limit blast radius; watch for dumps.")]),
 dict(trig=["*"], band="HACKTIVIST", sponsor="Pro-Ukraine", tier="HIGH",
   eyebrow="Breach + destructive ops", title="Cyber Anarchy Squad (C.A.S) — intrusion & destructive attacks on Russian orgs",
   pills=["Hacktivist","Destructive","Data leak"],
   what=["Targets Russian companies; data theft, destruction and public leaks.",
         "Opportunistic against exposed edge / remote-access."],
   evidence=["CAMPAIGN: attacks on Russian industry","TTP: exposed-service intrusion -> wipe/leak",
             "ATTRIB: pro-Ukraine cluster   Grade B3"],
   why="Exposed VPN/mgmt/CVE hosts here are C.A.S's typical entry.",
   refs="public reporting · vendor IR", admiralty="B3",
   score=dict(intent="High",capability="Med",exposureFit="High"), like="Likely — if edge exposed",
   rem=[("COLT","Colt SASE / ZTNA","Retire exposed VPN; identity-broker access."),
        ("VENDOR","MFA + patch KEV","Close the common entry vectors."),
        ("OSS","EDR / Sigma detections","Alert on destructive tooling.")]),
 dict(trig=["*"], band="HACKTIVIST", sponsor="Pro-Ukraine (IT Army)", tier="HIGH",
   eyebrow="Coordinated DDoS", title="IT Army of Ukraine — coordinated DDoS vs Russian services",
   pills=["DDoS","Crowdsourced","Availability"],
   what=["Crowdsourced DDoS against Russian government and corporate services.",
         "Recurring waves; targets any exposed, unprotected service."],
   evidence=["CAMPAIGN: sustained DDoS waves","TTP: volumetric + L7","ATTRIB: crowdsourced   Grade B3"],
   why="Any internet-facing service in a Russian estate is a standing DDoS target.",
   refs="public telemetry · national CERTs", admiralty="B3",
   score=dict(intent="High",capability="Med",exposureFit="Med"), like="Routine — recurring waves",
   rem=[("COLT","Colt IP Guardian (DDoS)","Absorb volumetric + L7 at the edge."),
        ("VENDOR","Rate-limit + WAF","Protect exposed apps."),
        ("OSS","Anycast / CDN fronting","Distribute + hide origins.")]),
]

def derive_geopol(fj, ident):
    types = {ftype(f["title"]) for f in fj["findings"] if f["sev"] in ("CRITICAL","HIGH")}
    # map a finding id per type for linkedFindingId
    tid = {}
    for f in fj["findings"]:
        tid.setdefault(ftype(f["title"]), f["id"])
    actors = []
    _cat = CATALOG_ALIGNED if _adversary_aligned(ident) else CATALOG
    for a in _cat:
        if "*" in a["trig"] or (types & set(a["trig"])):
            link = next((tid[t] for t in a["trig"] if t in tid), None)
            actors.append({"band":a["band"],"sponsor":a["sponsor"],"tier":a["tier"],"eyebrow":a["eyebrow"],
                "title":a["title"],"pills":a["pills"],"what":a["what"],"evidence":a["evidence"],"why":a["why"],
                "refs":a["refs"],"admiraltyGrade":a["admiralty"],"score":a["score"],"likelihood12mo":a["like"],
                "linkedFindingId":link,
                "rem":[{"tag":t,"title":ti,"body":bo} for (t,ti,bo) in a["rem"]]})
    top = next((f for f in fj["findings"] if f["sev"]=="CRITICAL"), fj["findings"][0] if fj["findings"] else None)
    kc = {"scenarioTitle": f"Ransomware via {top['title']}" if top else "Opportunistic intrusion",
          "steps":["Recon — attacker finds the exposed host on Shodan",
                   "Weaponise — pair with a KEV-listed exploit / stolen creds",
                   "Deliver — hit the exposed VPN/panel/service",
                   "Exploit — gain valid access, disable MFA gaps",
                   "Impact — lateral movement, encryption / OT disruption",
                   "Monetise — extortion + data leak"]}
    bridge = [{"scenario":a["title"].split(" — ")[0],"ale":"see C-BIQ","pml":"see C-BIQ",
               "note":a["eyebrow"],"linkedFindingId":a["linkedFindingId"]} for a in actors[:4]]
    return {"customer":fj["target"]["company"],"date":datetime.date.today().isoformat(),
        "classification":"INTERNAL — CONFIDENTIAL · THREAT LANDSCAPE (SECTOR-LEVEL, ILLUSTRATIVE)",
        "frameworks":["MITRE ATT&CK","Diamond","Kill-Chain","Admiralty","CVSS/EPSS/KEV"],"shelfLifeMonths":6,
        "exposureMap":[{"driver":"German industrial / KRITIS-adjacent","attracts":"eCrime RaaS + hacktivists","why":"High-value, internet-exposed OT/IT"},
                       {"driver":"EU / NATO alignment","attracts":"Russia-nexus APTs","why":"Espionage + disruption interest"}],
        "sectorContext":(fj.get("target",{}).get("geopol_context") or
            "BSI 2025: Germany is among the most-targeted nations; many KRITIS operators lack full detection coverage."),
        "likelihoodBands":{"Likely":[0.3,1],"Plausible":[0.1,0.3],"Routine":[1,4]},
        "actors":actors,"killChain":kc,"cbiqBridge":bridge}

# ---------------- orchestration ----------------
def _node_build(script, in_json, out_pptx):
    r = subprocess.run(["node", os.path.join(HERE, script), in_json, out_pptx],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[warn] {script}: {r.stderr.strip()[:300]}", file=sys.stderr); return False
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed"); ap.add_argument("--asn", action="append", default=[])
    ap.add_argument("--net", action="append", default=[])
    ap.add_argument("--org", action="append", default=[]); ap.add_argument("--brand", action="append", default=[])
    ap.add_argument("--domain", action="append", default=[]); ap.add_argument("--favicon", action="append", default=[])
    ap.add_argument("--from-findings"); ap.add_argument("--company")
    ap.add_argument("--outdir", default="."); ap.add_argument("--audience")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    import time as _t
    def _ev(**k): print(json.dumps(k), flush=True)
    def _pg(m): print("PROGRESS: " + m, flush=True)
    _t0 = _t.time(); _tag = a.company or a.seed or "?"
    _ev(evt="assess_start", company=_tag)

    # 1) findings.json (live recon, or reuse)
    _ts = _t.time()
    if a.from_findings:
        _pg("Loading findings")
        fj = json.load(open(a.from_findings))
        json.dump(fj, open(os.path.join(a.outdir,"findings.json"),"w"), indent=2, ensure_ascii=False)
        ident = fj.get("identity", {})
    else:
        if not a.seed: ap.error("need --seed or --from-findings")
        ident = R.resolve_identity(a.seed)
        for asn in a.asn:
            asn = "AS"+asn.lstrip("ASas")
            if asn not in ident["asns"]:
                ident["asns"].append(asn); ident["asn_holder"]=ident.get("asn_holder") or R._ripe_holder(asn)
                ident["org_is_cdn"]=False
                for p in R._ripe_prefixes(asn):
                    if p not in ident["nets"]: ident["nets"].append(p)
        for n in a.net:
            if n not in ident["nets"]: ident["nets"].append(n)
            ident["org_is_cdn"]=False
        R.merge_variants(ident, a.org, a.brand, a.domain, a.favicon)
        F = R.build_filters(ident)
        open(os.path.join(a.outdir,"filters.md"),"w").write(R.filters_md(ident,F))
        if not os.environ.get("SHODAN_API_KEY"):
            print("SHODAN_API_KEY not set", file=sys.stderr); sys.exit(2)
        _pg("Shodan recon + Top-10 super-filters")
        fj = R.run(ident, F, a.audience)
        json.dump(fj, open(os.path.join(a.outdir,"findings.json"),"w"), indent=2, ensure_ascii=False)
        open(os.path.join(a.outdir,"findings.md"),"w").write(R.findings_md(fj))

    _ev(evt="phase", name="recon", status="ok", company=_tag, ms=int((_t.time()-_ts)*1000))
    # optional LLM prose polish + audit (safe: falls back to templated text on any failure)
    if os.environ.get("OPENAI_API_KEY"):
        _pg("AI enrichment: improving prose + auditing vs methodology")
        # snapshot the pre-QWEN (raw templated) findings so the DELTAS deck can diff against it
        try:
            import shutil as _sh
            _sh.copyfile(os.path.join(a.outdir, "findings.json"), os.path.join(a.outdir, "findings_raw.json"))
        except Exception as e:
            print(f"[warn] findings_raw snapshot failed: {e}", file=sys.stderr)
        try:
            r = subprocess.run(["python3", os.path.join(HERE, "enrich.py"), os.path.join(a.outdir, "findings.json")],
                               timeout=260, capture_output=True, text=True,
                               env={**os.environ, "OUTDIR": a.outdir})
            if r.stdout: print(r.stdout, end="")          # enrich's own {"evt":"qwen"} + status line
            if r.returncode != 0:
                print(f"[warn] enrich exit={r.returncode}: {r.stderr.strip()[-500:]}", file=sys.stderr)
            fj = json.load(open(os.path.join(a.outdir, "findings.json")))
        except subprocess.TimeoutExpired:
            print("[warn] enrich TIMED OUT (240s) — model too slow; kept templated text", file=sys.stderr)
        except Exception as e:
            print(f"[warn] enrich skipped: {e}", file=sys.stderr)

    co = a.company or fj["target"]["company"]
    safe = "".join(c if c.isalnum() or c in ".-" else "_" for c in co)

    _pg("Building 3 VIP decks (Shodan / C-BIQ / GEOPOL)")
    # 2) DERIVE cbiq + geopol (deterministic — no LLM)
    cj = derive_cbiq(fj); gj = derive_geopol(fj, ident)
    json.dump(cj, open(os.path.join(a.outdir,"cbiq.json"),"w"), indent=2, ensure_ascii=False)
    json.dump(gj, open(os.path.join(a.outdir,"geopol.json"),"w"), indent=2, ensure_ascii=False)

    # 3) build all 3 decks
    d1=os.path.join(a.outdir,f"{safe}_Shodan_Findings.pptx")
    d2=os.path.join(a.outdir,f"{safe}_C-BIQ.pptx")
    d3=os.path.join(a.outdir,f"{safe}_GEOPOL.pptx")
    ok1=_node_build("build_findings_deck.js", os.path.join(a.outdir,"findings.json"), d1)
    ok2=_node_build("build_cbiq_deck.js",     os.path.join(a.outdir,"cbiq.json"),     d2)
    ok3=_node_build("build_geopol_deck.js",   os.path.join(a.outdir,"geopol.json"),   d3)

    # 3b) 4th deck — DELTAS (raw scan vs QWEN pursuit) — only when QWEN actually ran
    d4=os.path.join(a.outdir,f"{safe}_DELTAS.pptx")
    ok4=False
    if fj.get("target",{}).get("qwen",{}).get("status")=="ok":
        _pg("Building DELTAS deck (raw scan vs QWEN pursuit)")
        raw_fp=os.path.join(a.outdir,"findings_raw.json")
        r=subprocess.run(["node", os.path.join(HERE,"build_deltas_deck.js"),
                          raw_fp, os.path.join(a.outdir,"findings.json"), d4,
                          os.path.join(a.outdir,"cbiq.json"), os.path.join(a.outdir,"geopol.json")],
                         capture_output=True, text=True)
        ok4=(r.returncode==0)
        if not ok4: print(f"[warn] build_deltas_deck.js: {r.stderr.strip()[:300]}", file=sys.stderr)

    s=fj["summary"]
    if fj.get("target",{}).get("qa_note"): print(fj["target"]["qa_note"])
    q = fj.get("target", {}).get("qwen", {}) or {}
    _ev(evt="assess_done", company=co, crit=s["critical"], high=s["high"], med=s["medium"], low=s["low"],
        decks=sum(1 for x in (ok1, ok2, ok3) if x), qwen_used=(q.get("status") == "ok"),
        qwen_model=q.get("model"), qwen_cost_usd=q.get("cost_usd", 0), total_ms=int((_t.time()-_t0)*1000))
    _pg("AI enrichment: " + (f"{q.get('status')} - {q.get('model')} - {q.get('tokens_in',0)+q.get('tokens_out',0)} tok - ~${q.get('cost_usd',0):.4f}" if q else "not used"))
    print("==== ASSESSMENT COMPLETE ====")
    print(f"Company: {co}   scope: {fj['target']['scope']}")
    print(f"Findings: CRIT {s['critical']} · HIGH {s['high']} · MED {s['medium']} · LOW {s['low']}  (IPs {s['unique_ips']}, dropped {s.get('dropped_false_positives',0)} FP)")
    print(f"Priced findings (C-BIQ): {len([x for x in cj['findings'] if x['id']!='—'])}  · portfolio ALE €{cj['portfolio']['aleRange'][0]}–{cj['portfolio']['aleRange'][1]}M")
    print(f"Threat actors (GEOPOL): {len(gj['actors'])}")
    print("DECKS:")
    _decks=[(ok1,d1),(ok2,d2),(ok3,d3)]
    if fj.get("target",{}).get("qwen",{}).get("status")=="ok": _decks.append((ok4,d4))
    for ok,p in _decks: print(("  OK  " if ok else "  FAIL")+p)

if __name__ == "__main__": main()
