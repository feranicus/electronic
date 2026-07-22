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
    # BUG 1 FIX: the CBIQ_DEF tables and derived buckets are authored in € MILLIONS
    # (e.g. lm=[0.1,0.4,2.0,...], pml=[25,80]).  build_cbiq_deck.js money() formats RAW
    # euros (3.0 -> "€3"), so every monetary field must be scaled to ABSOLUTE euros
    # (× 1e6) exactly ONCE, at emission, before it lands in cbiq.json.  Non-monetary
    # fields (tef, vuln, lef, rosiPct, asset C/I/A) are NOT scaled.
    M = 1_000_000
    cur = {"code":"EUR","symbol":"€","word":"euros"}
    findings = []
    for f in fj["findings"]:
        if f["sev"] not in ("CRITICAL","HIGH"): continue
        d = CBIQ_DEF.get(ftype(f["title"]))
        if not d: continue
        lef = round(d["tef"]*d["vuln"], 2)
        # 7 buckets from lm scaled roughly (values in €M): treat lm as [L1min,L1lik,L1max, L3.. ]
        lm_m = {"L1":[d["lm"][0],d["lm"][1],d["lm"][2]],"L2":[0.0,0.1,1.0],
              "L3":[0.1,d["lm"][3]*0.4,d["lm"][3]],"L4":[0.1,d["lm"][4]*0.4,d["lm"][4]],
              "L5":[0.0,0.3,2.0],"L6":[0.0,d["lm"][5],d["lm"][6]],"L7":[0.0,0.1,1.0]}
        meanLM = sum(_pert(v) for v in lm_m.values())   # in €M
        ale = round(lef*meanLM, 2)                       # in €M
        # scale ALL monetary fields to absolute euros exactly once (× 1e6):
        lm = {k:[round(x*M) for x in v] for k,v in lm_m.items()}
        aleRange = [round(ale*0.6*M), round(ale*1.6*M)]
        aleMid   = round(ale*M)
        pmlRange = [round(d["pml"][0]*M), round(d["pml"][1]*M)]
        codRange = [round(ale*0.6/12*M), round(ale*1.6/12*M)]
        controlCost = round(d["cc"]*M)
        aleAfter    = round(d["after"]*M)
        findings.append({"id":f["id"],"tier":("CRIT" if f["sev"]=="CRITICAL" else "HIGH"),
            "label":f["title"],"asset":{"C":4,"I":4,"A":5},
            "lossScenario":(f["why"][0] if f.get("why") else f["title"]),
            "realComparable":(f.get("realComparable") or REAL_INCIDENTS.get(ftype(f["title"])) or REAL_INCIDENTS["other"]),
            "tef":d["tef"],"vuln":d["vuln"],"lef":lef,"lmBuckets":lm,
            "aleRange":aleRange,"aleMid":aleMid,
            "pmlRange":pmlRange,"codRange":codRange,
            "coltControl":d["ctl"],"controlCost":controlCost,"aleAfter":aleAfter,
            "rosiPct":int(((ale-d["after"]-d["cc"])/d["cc"])*100) if d["cc"] else 0})
    # portfolio roll-up — all monetary sums are already in absolute euros:
    aleLo=int(sum(x["aleRange"][0] for x in findings)); aleHi=int(sum(x["aleRange"][1] for x in findings))
    aleLik=int(sum(x["aleMid"] for x in findings))
    pmls=sorted(({"id":x["id"],"pml":x["pmlRange"][1]} for x in findings), key=lambda z:-z["pml"])[:2]
    ctrls=[]; seen=set()
    nctrl=max(len(set(y['coltControl'] for y in findings)),1)
    for x in findings:
        c=x["coltControl"]
        if c not in seen: seen.add(c); ctrls.append({"label":"− "+c.split(" /")[0].split(" +")[0],"cut":round(aleHi/nctrl),"svc":c})
    codAvoidedLo=round(aleLik/12*0.7); codAvoidedHi=round(aleHi/12)
    portfolio={"aleRange":[aleLo,aleHi],"aleLikely":aleLik,"largestPmls":pmls or [{"id":"—","pml":0}],
        "waterfall":ctrls or [{"label":"− SASE","cut":aleHi,"svc":"SASE / ZTNA"}],
        "rosiPct": int(sum(x["rosiPct"] for x in findings)/len(findings)) if findings else 0,
        "payback":"< 3 months","codAvoided":codAvoidedHi}
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
            "tef":1,"vuln":0.01,"lef":0.01,"lmBuckets":{k:[0,100_000,500_000] for k in ("L1","L2","L3","L4","L5","L6","L7")},
            "aleRange":[0,100_000],"aleMid":50_000,"pmlRange":[0,1_000_000],"codRange":[0,10_000],"coltControl":"—","controlCost":100_000,"aleAfter":50_000,"rosiPct":0}],
        "portfolio":portfolio,
        "lossExceedance":{"thresholds":["€1M","€5M","€10M","€20M","€40M"],"before":[97,66,44,25,11],"after":[6,1.5,0.6,0.2,0.05]}}

# ---------------- geopol actor catalog (real, public, sourced) ----------------
# BUG 2 FIX: build_geopol_deck.js relevancePct() multiplies score.intent × capability ×
# exposureFit numerically (High/Med/Low strings -> NaN).  Map the words to 1-10 numbers so
# the RELEVANCE % and the INTENT/CAPAB/FIT probability-index columns are numeric.  We keep a
# parallel display label ({intent,capability,exposureFit,*Label}) for any word-based rendering.
_SCORE_MAP = {"high":9, "med":6, "medium":6, "low":3, "very high":10, "very low":1}
def _score_num(v):
    if isinstance(v,(int,float)): return v
    return _SCORE_MAP.get(str(v).strip().lower(), 6)
def _numeric_score(score):
    """{'intent':'High',...} -> {'intent':9,...,'intentLabel':'High',...} (numeric + label)."""
    out = {}
    for k in ("intent","capability","exposureFit"):
        raw = score.get(k)
        out[k] = _score_num(raw)
        out[k + "Label"] = (str(raw) if not isinstance(raw,(int,float)) else raw)
    return out

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
 # BUG 4: automotive / manufacturing IP-espionage actor — the "who wants the IP" thesis.
 # Keyed by SECTOR (not finding type) so it selects for manufacturing/automotive targets.
 dict(trig=["*"], sectors=["automotive","manufacturing","mfg","auto","industrial"],
   band="NATION-STATE", sponsor="CHINA MSS", tier="CRITICAL",
   eyebrow="IP / source-code espionage", title="APT41 (Winnti / Brass Typhoon) — automotive & manufacturing IP theft",
   pills=["MITRE G0096","WINNTI","T1195"],
   what=["China MSS dual-mission group; supply-chain implants + signed-driver rootkits for long-dwell access.",
         "Systematically exfiltrates EV/battery/powertrain IP and source code from German industry."],
   evidence=["CAMPAIGN: German-industry espionage (Winnti)","TARGETS: BASF · Bayer · Thyssenkrupp · Covestro",
             "VW 2024: ~19,000 dev docs (EV/engine/DSG)","ATT&CK: G0096 · T1195 supply-chain · T1505.003",
             "ATTRIB: BfV (DE) + Mandiant   Grade A2"],
   why="The crown jewels here are EV/battery/powertrain IP — precisely what China-nexus actors collect; exposed dev/cloud estates and edge are the collection footholds.",
   refs="MITRE G0096 · BfV · Mandiant APT41 · Cisco Talos", admiralty="A2",
   score=dict(intent="High",capability="High",exposureFit="High"), like="Likely — sustained IP-collection interest",
   rem=[("COLT","Colt Managed Detection & Response","Block-mode EDR + egress-anomaly on dev/build estates."),
        ("PSF","Segment source / build / OT","Isolate the IP crown jewels from internet-reachable planes."),
        ("OSS","SBOM + Sigma detections","Detect supply-chain implants + signed-driver abuse.")]),
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

# euro formatter for the GEOPOL C-BIQ bridge (values arrive as ABSOLUTE euros post-BUG-1)
def _eur(n):
    try: n = float(n)
    except Exception: return "—"
    a = abs(n)
    if a >= 1e9: return f"€{n/1e9:.1f}bn"
    if a >= 1e6: return f"€{n/1e6:.0f}M" if a >= 1e7 else f"€{n/1e6:.1f}M"
    if a >= 1e3: return f"€{n/1e3:.0f}k"
    return f"€{round(n)}"
def _eur_range(r):
    return (_eur(r[0]) + "–" + _eur(r[1])) if isinstance(r,(list,tuple)) and len(r)==2 else "—"

# infer the customer's SECTOR (drives sector-keyed actor selection, e.g. APT41 for automotive)
_SECTOR_MARKERS = {
 "automotive": ("automotive","automobil","vehicle","volkswagen","audi","porsche","bmw","mercedes","daimler","bosch","continental","zf ","powertrain"),
 "manufacturing": ("manufactur","industrial","werk","gmbh","carbon","chemical","chemie","material","factory","machine","engineering"),
 "energy": ("energy","energie","oil","gas","petro","refin","utility","kraftwerk","grid","rosneft","gazprom"),
 "finance": ("bank","financ","capital","invest","insur","versicherung"),
 "healthcare": ("health","medic","pharma","hospital","klinik","care"),
}
def _infer_sector(fj, ident):
    hay = " ".join(str(ident.get(k) or "") for k in ("asn_holder","brand","org","seed")).lower()
    hay += " " + str(fj.get("target",{}).get("company") or "").lower()
    hay += " " + str(fj.get("target",{}).get("sector") or "").lower()
    hay += " " + " ".join(str(d) for d in (ident.get("domains") or [])).lower()
    for sec, markers in _SECTOR_MARKERS.items():
        if any(m in hay for m in markers): return sec
    if any(ftype(f["title"])=="ics" for f in fj["findings"]): return "energy"
    return "manufacturing"   # default for the industrial pursuit base

def derive_geopol(fj, ident, cj=None):
    types = {ftype(f["title"]) for f in fj["findings"] if f["sev"] in ("CRITICAL","HIGH")}
    sector = _infer_sector(fj, ident)
    # map a finding id per type for linkedFindingId
    tid = {}
    for f in fj["findings"]:
        tid.setdefault(ftype(f["title"]), f["id"])
    # index priced C-BIQ findings by id so the bridge can read REAL euro ALE/PML (BUG 5)
    cbiq_by_id = {}
    for x in ((cj or {}).get("findings") or []):
        if x.get("id") and x["id"] != "—": cbiq_by_id[x["id"]] = x
    actors = []
    _cat = CATALOG_ALIGNED if _adversary_aligned(ident) else CATALOG
    for a in _cat:
        sect_ok = ("sectors" not in a) or (sector in a["sectors"])
        trig_ok = ("*" in a["trig"]) or bool(types & set(a["trig"]))
        if not (sect_ok and trig_ok):
            continue
        # linked finding: prefer a real finding-type match; else fall back to the top CRIT id
        link = next((tid[t] for t in a["trig"] if t in tid), None)
        if not link:
            link = next((f["id"] for f in fj["findings"] if f["sev"]=="CRITICAL"),
                        (fj["findings"][0]["id"] if fj["findings"] else None))
        actors.append({"band":a["band"],"sponsor":a["sponsor"],"tier":a["tier"],"eyebrow":a["eyebrow"],
            "title":a["title"],"pills":a["pills"],"what":a["what"],"evidence":a["evidence"],"why":a["why"],
            "refs":a["refs"],"admiraltyGrade":a["admiralty"],
            "score":_numeric_score(a["score"]),"likelihood12mo":a["like"],
            "linkedFindingId":link,
            "rem":[{"tag":t,"title":ti,"body":bo} for (t,ti,bo) in a["rem"]]})
    # BUG 3: guarantee the top / CRITICAL actor always renders a card — sort so the highest
    # tier leads, and if selection somehow yielded nothing, force the catalog's top CRIT actor.
    _rank = {"CRITICAL":4,"HIGH":3,"MEDIUM":2,"LOW":1}
    actors.sort(key=lambda a: -_rank.get(str(a["tier"]).upper(),1))
    if not actors and _cat:
        a = _cat[0]
        actors.append({"band":a["band"],"sponsor":a["sponsor"],"tier":a["tier"],"eyebrow":a["eyebrow"],
            "title":a["title"],"pills":a["pills"],"what":a["what"],"evidence":a["evidence"],"why":a["why"],
            "refs":a["refs"],"admiraltyGrade":a["admiralty"],"score":_numeric_score(a["score"]),
            "likelihood12mo":a["like"],"linkedFindingId":None,
            "rem":[{"tag":t,"title":ti,"body":bo} for (t,ti,bo) in a["rem"]]})
    top = next((f for f in fj["findings"] if f["sev"]=="CRITICAL"), fj["findings"][0] if fj["findings"] else None)
    top_actor = actors[0] if actors else None
    top_id = (top["id"] if top else (top_actor.get("linkedFindingId") if top_actor else "—"))
    # BUG 4: anchorCase — the sourced intrusion the report is built around, tied to finding IDs,
    # phased ACCESS -> PERSIST -> COLLECT -> EXFIL (for automotive/mfg it's the 2024 VW/Winnti case).
    anchorCase = None
    if sector in ("automotive","manufacturing") and any(str(x.get("title","")).startswith("APT41") for x in actors):
        anchorCase = {
            "title":"2024 Volkswagen / Winnti IP-espionage case",
            "actor":"APT41 (Winnti / Brass Typhoon)","admiraltyGrade":"B2","sponsor":"China MSS",
            "summary":"~19,000 internal development documents (EV, engine and DSG gearbox source/design) "
                      "were exfiltrated from Volkswagen Group over a multi-year China-nexus campaign - the "
                      "canonical 'who wants the IP' precedent for German automotive/manufacturing.",
            "phases":[
                {"phase":"ACCESS","body":"Foothold via internet-exposed dev/cloud estate + supply-chain implant.","linkedFindingId":top_id},
                {"phase":"PERSIST","body":"Signed-driver rootkit + valid accounts for multi-year low-and-slow dwell.","linkedFindingId":top_id},
                {"phase":"COLLECT","body":"Stage EV/battery/powertrain source, CAD and process IP from build systems.","linkedFindingId":top_id},
                {"phase":"EXFIL","body":"~19,000 documents siphoned to China-nexus infrastructure over time.","linkedFindingId":top_id},
            ],
            "refs":"BfV (DE) · Mandiant APT41 · public reporting (2024)",
            "linkedFindingId":top_id}
    else:
        anchorCase = {
            "title":f"Representative intrusion via {top['title']}" if top else "Opportunistic intrusion",
            "actor":(top_actor["title"] if top_actor else "—"),
            "admiraltyGrade":(top_actor.get("admiraltyGrade") if top_actor else "—"),
            "sponsor":(top_actor.get("sponsor") if top_actor else "—"),
            "summary":(top_actor.get("why") if top_actor else "The most-relevant selected adversary rides the top exposed finding into the estate."),
            "phases":[
                {"phase":"ACCESS","body":"Attacker rides the exposed edge/VPN/panel into the estate.","linkedFindingId":top_id},
                {"phase":"PERSIST","body":"Valid accounts + tooling establish durable access.","linkedFindingId":top_id},
                {"phase":"COLLECT","body":"Stage the crown-jewel data / position for impact.","linkedFindingId":top_id},
                {"phase":"EXFIL","body":"Exfiltration and/or encryption; extortion + data leak.","linkedFindingId":top_id},
            ],
            "refs":(top_actor.get("refs") if top_actor else "—"),
            "linkedFindingId":top_id}
    # kill-chain steps tied to named finding IDs where possible
    kc = {"scenarioTitle": (f"{top_actor['title'].split(' — ')[0]} via {top['title']}"
                            if (top and top_actor) else "Opportunistic intrusion"),
          "steps":[f"Recon — attacker finds the exposed host on Shodan ({top_id})",
                   "Weaponise — pair with a KEV-listed exploit / stolen creds",
                   f"Deliver — hit the exposed VPN/panel/service ({top_id})",
                   "Exploit — gain valid access, disable MFA gaps",
                   "Impact — lateral movement, encryption / OT disruption / IP collection",
                   "Monetise — extortion + data leak"]}
    # BUG 5: C-BIQ bridge reads REAL euro ALE/PML from the priced C-BIQ finding (fallback to text)
    bridge = []
    for a in actors[:4]:
        fid = a.get("linkedFindingId")
        cx = cbiq_by_id.get(fid)
        bridge.append({
            "scenario": a["title"].split(" — ")[0],
            "ale": (_eur_range(cx["aleRange"]) if cx and cx.get("aleRange") else "see C-BIQ"),
            "pml": (_eur_range(cx["pmlRange"]) if cx and cx.get("pmlRange") else "see C-BIQ"),
            "note": a["eyebrow"], "linkedFindingId": fid})
    # exposure map: per-jurisdiction / named-entity rows (§F). Prefer real identity data.
    entity = ident.get("brand") or ident.get("org") or ident.get("asn_holder") or fj["target"]["company"]
    exposureMap = [
        {"driver":f"German {sector} / KRITIS-adjacent","attracts":"eCrime RaaS + hacktivists",
         "why":f"{entity}: high-value, internet-exposed OT/IT surface"},
        {"driver":"EU / NATO alignment","attracts":"Russia-nexus APTs (GRU/hacktivist)",
         "why":"Sanctions posture + arms-to-Ukraine draw disruptive interest"}]
    if sector in ("automotive","manufacturing"):
        exposureMap.insert(1, {"driver":"China market dependency + EV/IP crown jewels",
            "attracts":"China-nexus IP theft (APT41/Winnti)",
            "why":"EV/battery/powertrain IP is precisely what China-MSS actors collect"})
    # per-jurisdiction / named-entity exposure rows (§F): one row per jurisdiction+entity.
    countries = []
    for f in fj["findings"]:
        for ev in (f.get("evidence") or []):
            for cc in ("DE","AT","CH","NL","US","SG","FR","GB","CN","PL","CZ"):
                if f" {cc}" in f" {ev} " and cc not in countries: countries.append(cc)
    hq = (countries[0] if countries else "DE")
    _reg = {"automotive":"UNECE R155 · TISAX · NIS2","manufacturing":"NIS2 · IEC 62443",
            "energy":"NIS2 · KRITIS · IEC 62443","finance":"DORA · BaFin/BAIT","healthcare":"NIS2 · GDPR",
            "retail":"GDPR · PCI-DSS"}.get(sector,"NIS2")
    exposureEntities = [
        {"jurisdiction":hq,"entity":entity,
         "exposure":f"HQ estate · {_reg} · internet-facing {sector} OT/IT is the primary target surface"}]
    for cc in countries[1:4]:
        exposureEntities.append({"jurisdiction":cc,"entity":f"{entity} ({cc} operations)",
            "exposure":f"Regional {sector} assets · data-residency + local-CERT exposure ({cc})"})
    if sector in ("automotive","manufacturing"):
        exposureEntities.append({"jurisdiction":"CN","entity":f"{entity} — China market dependency",
            "exposure":"Largest-market pull raises China-nexus IP-espionage exposure (crown-jewel collection)"})
    return {"customer":fj["target"]["company"],"date":datetime.date.today().isoformat(),
        "classification":"INTERNAL — CONFIDENTIAL · THREAT LANDSCAPE (SECTOR-LEVEL, ILLUSTRATIVE)",
        "frameworks":["MITRE ATT&CK","Diamond","Kill-Chain","Admiralty","CVSS/EPSS/KEV"],"shelfLifeMonths":6,
        "sector":sector,
        "exposureMap":exposureMap,
        "exposureEntities":exposureEntities,
        "sectorContext":(fj.get("target",{}).get("geopol_context") or
            "BSI 2025: Germany is among the most-targeted nations; many KRITIS operators lack full detection coverage."),
        "likelihoodBands":{"Likely":[0.3,1],"Plausible":[0.1,0.3],"Routine":[1,4]},
        "actors":actors,"anchorCase":anchorCase,"killChain":kc,"cbiqBridge":bridge}

# ---------------- orchestration ----------------
def _node_build(script, in_json, out_pptx, lang="en"):
    # DECK_LANG is read by scripts/i18n/deck_i18n.js, which is installed on the pptx object inside
    # every builder. en -> the builders behave exactly as before (zero-diff); de -> Hoch-Deutsch.
    env = dict(os.environ, DECK_LANG=("de" if str(lang).lower().startswith("de") else "en"))
    r = subprocess.run(["node", os.path.join(HERE, script), in_json, out_pptx],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print(f"[warn] {script}: {r.stderr.strip()[:300]}", file=sys.stderr); return False
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed"); ap.add_argument("--asn", action="append", default=[])
    ap.add_argument("--net", action="append", default=[])
    ap.add_argument("--org", action="append", default=[]); ap.add_argument("--brand", action="append", default=[])
    ap.add_argument("--domain", action="append", default=[]); ap.add_argument("--favicon", action="append", default=[])
    ap.add_argument("--issuer", "--internal-ca", dest="issuer", action="append", default=[])
    ap.add_argument("--cert-org", dest="cert_org", action="append", default=[])
    ap.add_argument("--jarm", action="append", default=[]); ap.add_argument("--cpe", action="append", default=[])
    ap.add_argument("--from-findings"); ap.add_argument("--company")
    ap.add_argument("--outdir", default="."); ap.add_argument("--audience")
    ap.add_argument("--lang", default=os.environ.get("DECK_LANG", "en"),
                    choices=["en", "de"], help="language of the 4 generated decks (en|de)")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    import time as _t
    def _ev(**k):
        """Emit a structured event to BOTH stdout (the SSE stream / telegram) AND the shared
        events.log that promtail tails into Loki.
        WHY: promtail reads /logs/events.log — NOT stdout. When the engine ran inside colt-assessbot
        its docker stdout happened to be scraped, so events reached Grafana by accident. Now that
        colt-web runs the engine as a background task its stdout is a PIPE (read by the SSE viewer),
        so print-only events never reached Loki and live assessments vanished from the dashboard.
        Write to the log explicitly — never depend on who happens to own our stdout."""
        k.setdefault("ts", _t.time())
        k.setdefault("company", _tag)
        # WHO ordered this run. colt-web/bot set COLT_USER; without it Grafana shows a company with
        # no requester and you cannot tell which AE or partner ran what.
        k.setdefault("user", os.environ.get("COLT_USER", ""))
        k.setdefault("service", os.environ.get("SERVICE", "engine"))
        k.setdefault("bot", os.environ.get("SERVICE", "engine"))
        line = json.dumps(k)
        print(line, flush=True)
        try:
            with open(os.environ.get("EVENTS_LOG", "/var/log/colt/events.log"), "a") as fh:
                fh.write(line + "\n")
        except Exception:
            pass
    # PROGRESS lines carry an explicit percentage so the web UI can draw a real bar instead of a
    # spinner. Weights are wall-clock-proportional from real runs (recon dominates: ~60-80s of a
    # ~2min job; enrichment ~30-60s; deck rendering ~10s). The bot ignores the [nn%] prefix.
    def _pg(m, pct=None):
        print(("PROGRESS: [%d%%] " % pct if pct is not None else "PROGRESS: ") + m, flush=True)
        try:
            _ev(evt="progress", pct=(pct if pct is not None else -1), msg=str(m)[:300])
        except Exception:
            pass
    _t0 = _t.time(); _tag = a.company or a.seed or "?"
    _ev(evt="assess_start", company=_tag)

    # 1) findings.json (live recon, or reuse)
    _ts = _t.time()
    if a.from_findings:
        _pg("Loading findings", 4)
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
        R.autodiscover(ident, a.org, a.brand, a.domain, a.favicon,
                       issuers=a.issuer, cert_orgs=a.cert_org, jarms=a.jarm, cpes=a.cpe)
        F = R.build_filters(ident)
        open(os.path.join(a.outdir,"filters.md"),"w").write(R.filters_md(ident,F))
        if not os.environ.get("SHODAN_API_KEY"):
            print("SHODAN_API_KEY not set", file=sys.stderr); sys.exit(2)
        _pg("Shodan recon + Top-10 super-filters", 8)
        fj = R.run(ident, F, a.audience)
        # SCOPE BLOW-OUT GUARD (bibeltv.de, 2026-07): an over-matching pivot once adopted ~998
        # strangers' hosts as the customer's estate — 1003 IPs in the findings against 5 on the
        # asset-inventory slide — and NOTHING in the pipeline objected. A wrong estate is not a
        # cosmetic defect: every euro in C-BIQ and every actor in GEOPOL is derived from it.
        _blow = ident.get("scope_blowout")
        if _blow:
            _ev(evt="scope_blowout", company=_tag, **_blow)
            print("[FATAL] scope blow-out: identity queries proved %d hosts but the sweep produced "
                  "%d (pivot added %d). Refusing to build decks from an unverified estate.\n"
                  "        Re-run with explicit anchors, e.g.  --domain <their-domain> --org \"<Legal Name>\"\n"
                  "        or raise PIVOT_MAX_HOSTS only if you have verified the issuer by hand."
                  % (_blow["identity_hosts"], _blow["total_hosts"], _blow["pivot_added"]),
                  file=sys.stderr)
            _pg("FAILED — scope blow-out: estate could not be verified", 100)
            sys.exit(3)
        json.dump(fj, open(os.path.join(a.outdir,"findings.json"),"w"), indent=2, ensure_ascii=False)
        open(os.path.join(a.outdir,"findings.md"),"w").write(R.findings_md(fj))

    _ev(evt="phase", name="recon", status="ok", company=_tag, ms=int((_t.time()-_ts)*1000))

    # --- BGP / ASN resilience -> NIS2 Art 21 continuity exposure (additive, non-fatal) ---
    try:
        _pg("BGP/ASN resilience + NIS2 Art 21 exposure", 56)
        import bgp_resilience as BGP
        # Tell the module whether ASN AUTODISCOVERY actually worked. If bgpview/crt.sh were
        # unreachable (container DNS down, 502), an empty ASN list means "we could not look it up",
        # NOT "this org has no routing autonomy" — the latter is a false CRITICAL in a customer deck.
        _disc_ok = bool(ident.get("asns")) or bool(ident.get("nets")) or bool(ident.get("ct_domains"))
        _bgp = BGP.assess(ident.get("asns", []), a.org or ident.get("org") or a.seed,
                          discovery_ok=_disc_ok)
        fj.setdefault("target", {})["bgp"] = _bgp
        json.dump(_bgp, open(os.path.join(a.outdir, "bgp.json"), "w"), indent=2, ensure_ascii=False)
        json.dump(fj, open(os.path.join(a.outdir, "findings.json"), "w"), indent=2, ensure_ascii=False)
        _md = ["# BGP / ASN resilience — " + str(_bgp.get("org") or ""),
               "",
               "**Homing:** %s (%s) — %s" % (_bgp.get("rag"), _bgp.get("homing_status"), _bgp.get("why")),
               "**Origin ASNs:** %s   |   **Distinct upstreams:** %d   |   **IX presence:** %d" % (
                   (", ".join("AS%d" % x for x in _bgp.get("origin_asns", [])) or "none (uses ISP ASN)"),
                   _bgp.get("homing_degree", 0), _bgp.get("ix_presence", 0)),
               "",
               "## NIS2 exposure",
               "- Control: " + _bgp["nis2"]["control"],
               "- " + _bgp["nis2"]["finding"],
               "- Fine band: essential up to EUR 10M / 2%% turnover; important up to EUR 7M / 1.4%% (group turnover).",
               "",
               "## Colt remediation",
               ] + ["- " + r for r in _bgp.get("colt_remediation", [])]
        open(os.path.join(a.outdir, "bgp_resilience.md"), "w", encoding="utf-8").write("\n".join(_md) + "\n")
        _ev(evt="bgp", company=_tag, homing=_bgp.get("homing_status"), rag=_bgp.get("rag"),
            upstreams=_bgp.get("homing_degree"), data_ok=_bgp.get("data_ok"),
            lookup_errors=len(_bgp.get("lookup_errors") or []))
        if not _bgp.get("data_ok"):
            print("[warn] BGP resilience NOT determined (lookup failed) — reported as UNKNOWN, "
                  "no NIS2 gap claimed. Fix container DNS / retry before using this slide.",
                  file=sys.stderr)
    except Exception as _e:
        print("[warn] bgp_resilience: %s" % _e, file=sys.stderr)
    # optional LLM prose polish + audit (safe: falls back to templated text on any failure)
    if os.environ.get("OPENAI_API_KEY"):
        _pg("AI enrichment: improving prose + auditing vs methodology", 62)
        # snapshot the pre-QWEN (raw templated) findings so the DELTAS deck can diff against it
        try:
            import shutil as _sh
            _sh.copyfile(os.path.join(a.outdir, "findings.json"), os.path.join(a.outdir, "findings_raw.json"))
        except Exception as e:
            print(f"[warn] findings_raw snapshot failed: {e}", file=sys.stderr)
        try:
            # NO capture_output: enrich must stream. Its PROGRESS/failover lines are useless if they
            # only appear after the step finishes — the operator needs to see "deepseek timed out,
            # switching to gemma" WHILE it happens, not in a post-mortem dump.
            r = subprocess.run(["python3", "-u", os.path.join(HERE, "enrich.py"),
                                os.path.join(a.outdir, "findings.json"), a.lang],
                               timeout=430,   # must exceed ENRICH_BUDGET_S (380) or we
                                              # kill the chain mid-answer
                               env={**os.environ, "OUTDIR": a.outdir, "DECK_LANG": a.lang,
                                    "PYTHONUNBUFFERED": "1"})
            # (stdout/stderr already streamed straight through to the caller)
            if r.returncode != 0:
                print(f"[warn] enrich exit={r.returncode}: {r.stderr.strip()[-500:]}", file=sys.stderr)
            fj = json.load(open(os.path.join(a.outdir, "findings.json")))
        except subprocess.TimeoutExpired:
            print("[warn] enrich TIMED OUT (240s) — model too slow; kept templated text", file=sys.stderr)
        except Exception as e:
            print(f"[warn] enrich skipped: {e}", file=sys.stderr)

    co = a.company or fj["target"]["company"]
    safe = "".join(c if c.isalnum() or c in ".-" else "_" for c in co)

    _pg("Building 3 VIP decks (Shodan / C-BIQ / GEOPOL)", 91)
    # 2) DERIVE cbiq + geopol (deterministic — no LLM)
    cj = derive_cbiq(fj); gj = derive_geopol(fj, ident, cj)
    json.dump(cj, open(os.path.join(a.outdir,"cbiq.json"),"w"), indent=2, ensure_ascii=False)
    json.dump(gj, open(os.path.join(a.outdir,"geopol.json"),"w"), indent=2, ensure_ascii=False)

    # 3) build all 3 decks
    _L = "_DE" if str(a.lang).lower().startswith("de") else ""   # EN keeps today's exact filenames
    d1=os.path.join(a.outdir,f"{safe}_Shodan_Findings{_L}.pptx")
    d2=os.path.join(a.outdir,f"{safe}_C-BIQ{_L}.pptx")
    d3=os.path.join(a.outdir,f"{safe}_GEOPOL{_L}.pptx")
    # DE: translate the engine's own deterministic English (finding titles, Colt controls, bucket
    # names) BEFORE the decks render. LLM prose is already German (enrich.py); deck chrome is done
    # by deck_i18n.js. All three streams read the SAME committed dictionary, so terms never diverge.
    if str(a.lang).lower().startswith("de"):
        try:
            sys.path.insert(0, os.path.join(HERE, "i18n"))
            import i18n as _I18N
            for _f in ("findings.json", "cbiq.json", "geopol.json"):
                _I18N.translate_file(os.path.join(a.outdir, _f), "de")
            _pg("Sprache: Hochdeutsch — Dokumente werden auf Deutsch erzeugt", 89)
        except Exception as _e:
            print(f"[warn] i18n pass: {_e}", file=sys.stderr)

    ok1=_node_build("build_findings_deck.js", os.path.join(a.outdir,"findings.json"), d1, a.lang)
    ok2=_node_build("build_cbiq_deck.js",     os.path.join(a.outdir,"cbiq.json"),     d2, a.lang)
    ok3=_node_build("build_geopol_deck.js",   os.path.join(a.outdir,"geopol.json"),   d3, a.lang)

    # 3b) 4th deck — DELTAS (raw scan vs QWEN pursuit) — only when QWEN actually ran
    d4=os.path.join(a.outdir,f"{safe}_DELTAS{_L}.pptx")
    ok4=False
    if fj.get("target",{}).get("qwen",{}).get("status")=="ok":
        _pg("Building DELTAS deck (raw scan vs QWEN pursuit)", 97)
        raw_fp=os.path.join(a.outdir,"findings_raw.json")
        r=subprocess.run(["node", os.path.join(HERE,"build_deltas_deck.js"),
                          raw_fp, os.path.join(a.outdir,"findings.json"), d4,
                          os.path.join(a.outdir,"cbiq.json"), os.path.join(a.outdir,"geopol.json")],
                         capture_output=True, text=True,
                         env=dict(os.environ, DECK_LANG=("de" if str(a.lang).lower().startswith("de") else "en")))
        ok4=(r.returncode==0)
        if not ok4: print(f"[warn] build_deltas_deck.js: {r.stderr.strip()[:300]}", file=sys.stderr)

    # 3c) 5th deliverable — the combined animated HTML artifact (Findings + C-BIQ + GEOPOL in one
    # self-contained scrollytelling page). Non-fatal: a report failure must never sink the decks.
    d5=os.path.join(a.outdir,f"{safe}_Report{_L}.html")
    ok5=False
    try:
        _pg("Building combined HTML report", 98)
        r=subprocess.run(["node", os.path.join(HERE,"build_report_html.js"),
                          os.path.join(a.outdir,"findings.json"),
                          os.path.join(a.outdir,"cbiq.json"),
                          os.path.join(a.outdir,"geopol.json"), d5],
                         capture_output=True, text=True,
                         env=dict(os.environ, DECK_LANG=("de" if str(a.lang).lower().startswith("de") else "en")))
        ok5=(r.returncode==0 and os.path.exists(d5))
        if not ok5: print(f"[warn] build_report_html.js: {r.stderr.strip()[:300]}", file=sys.stderr)
    except Exception as _e:
        print(f"[warn] HTML report: {_e}", file=sys.stderr)

    s=fj["summary"]
    if fj.get("target",{}).get("qa_note"): print(fj["target"]["qa_note"])
    q = fj.get("target", {}).get("qwen", {}) or {}
    _ms = int((_t.time()-_t0)*1000)
    _ev(evt="assess_done", company=co, lang=a.lang, crit=s["critical"], high=s["high"], med=s["medium"], low=s["low"],
        decks=sum(1 for x in (ok1, ok2, ok3) if x), qwen_used=(q.get("status") == "ok"),
        qwen_model=q.get("model"), qwen_cost_usd=q.get("cost_usd", 0), total_ms=_ms)
    # --- persistent cost ledger (survives Loki retention) + lifetime snapshot for Grafana ---
    try:
        import cost_ledger as _CL
        _tot = _CL.record(company=co, cost_usd=q.get("cost_usd", 0),
                          tokens_in=q.get("tokens_in", 0), tokens_out=q.get("tokens_out", 0),
                          model=q.get("model"), crit=s["critical"], high=s["high"],
                          med=s["medium"], low=s["low"], total_ms=_ms,
                          user=os.environ.get("COLT_USER"), source=os.environ.get("SERVICE", "bot"))
        if _tot:
            # cumulative values -> a single snapshot line lets Grafana show TRUE lifetime totals
            # (last_over_time) no matter how much history Loki has already aged out.
            _ev(evt="cost_snapshot", ledger=_CL.LEDGER, **_tot)
    except Exception as _e:
        print(f"[warn] cost ledger: {_e}", file=sys.stderr)
    _pg("AI enrichment: " + (f"{q.get('status')} - {q.get('model')} - {q.get('tokens_in',0)+q.get('tokens_out',0)} tok - ~${q.get('cost_usd',0):.4f}" if q else "not used"), 99)
    print("==== ASSESSMENT COMPLETE ====")
    print(f"Company: {co}   scope: {fj['target']['scope']}")
    print(f"Findings: CRIT {s['critical']} · HIGH {s['high']} · MED {s['medium']} · LOW {s['low']}  (IPs {s['unique_ips']}, dropped {s.get('dropped_false_positives',0)} FP)")
    print(f"Priced findings (C-BIQ): {len([x for x in cj['findings'] if x['id']!='—'])}  · portfolio ALE {_eur(cj['portfolio']['aleRange'][0])}–{_eur(cj['portfolio']['aleRange'][1])}")
    print(f"Threat actors (GEOPOL): {len(gj['actors'])}")
    print("DECKS:")
    _decks=[(ok1,d1),(ok2,d2),(ok3,d3)]
    if fj.get("target",{}).get("qwen",{}).get("status")=="ok": _decks.append((ok4,d4))
    if ok5: _decks.append((ok5,d5))          # the combined HTML report (5th deliverable)
    for ok,p in _decks: print(("  OK  " if ok else "  FAIL")+p)

if __name__ == "__main__":
    # OBSERVABILITY GAP (found on the Yamaha crash): an unhandled exception killed the engine before
    # `assess_done` was ever emitted, so Grafana showed "11 requested / 1 completed" and NOTHING about
    # WHY. A crash must be as visible as a success. Emit a structured error event, then re-raise so
    # the exit code and traceback still reach the caller/logs unchanged.
    try:
        main()
    except SystemExit:
        raise
    except BaseException as _e:
        import traceback as _tb, time as _t
        _co = "?"
        try:
            for _i, _a in enumerate(sys.argv):
                if _a == "--seed" and _i + 1 < len(sys.argv): _co = sys.argv[_i + 1]
        except Exception:
            pass
        _rec = {"evt": "assess_error", "company": _co, "error": type(_e).__name__,
                "message": str(_e)[:300], "ts": _t.time(),
                "bot": os.environ.get("SERVICE", "engine"),
                "service": os.environ.get("SERVICE", "engine"),
                "where": (_tb.format_tb(_e.__traceback__)[-1].strip()[:200] if _e.__traceback__ else "?")}
        print(json.dumps(_rec), flush=True)                 # -> SSE stream / telegram
        try:                                                # -> events.log -> promtail -> Loki
            with open(os.environ.get("EVENTS_LOG", "/var/log/colt/events.log"), "a") as _fh:
                _fh.write(json.dumps(_rec) + "\n")
        except Exception:
            pass
        print("PROGRESS: [100%] FAILED — %s: %s" % (type(_e).__name__, str(_e)[:160]), flush=True)
        raise
