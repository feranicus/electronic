#!/usr/bin/env python3
"""build_roadmap_deck.py — the cybergod.ai 2027 roadmap, in the S4biz template.

    python marketing/build_roadmap_deck.py [--out PATH] [--template PATH]

THE TEMPLATE IS NOT RE-IMPLEMENTED. Every helper (Deck, card, bullets, stat, the palette, the
wordmark chrome) is imported from build_consensus_deck.py, which read them off
S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx. Three decks, one template implementation, so
they cannot drift. Same doctrine as legal.jsx and the deck i18n dictionary.

CONTENT RULES, enforced here and stated so the next person does not soften them:

1. NO UNSUBSTANTIATED COMPARISON AGAINST A NAMED COMPETITOR. We have never benchmarked cybergod
   against Shodan, Censys, Bitsight, SecurityScorecard or anyone else. The differentiation argued
   here is ARCHITECTURAL (what follows from owning the collection and from a deterministic
   judgement layer), which a reader can check without trusting us and which a competitor's next
   release cannot refute. An unsubstantiated superiority claim against a named product is also
   comparative advertising under UWG s.6 and the UCP Directive.

2. EVERY NUMBER IS OURS AND MEASURED, OR IT IS NOT ON THE SLIDE. The operating figures come from
   this repository and the live cost ledger. Market sizing is deliberately absent: we do not have
   a defensible number for it, and a made-up TAM on a roadmap deck is the fastest way to lose a
   technical audience. The limits slide says so out loud.

3. NO CVE IDENTIFIERS. The engine's own hallucination guard exists because a model invented
   CVE-2021-44244 for Log4Shell. A roadmap deck does not need identifiers, so it names exposure
   CLASSES instead and cannot be wrong about a number nobody checked.

4. NO EM DASHES and no AI-tell cadence, per the standing rule on public-facing copy.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  — one template implementation, reused
    AMBER, BODY, CYAN, Deck, DISPLAY, GREEN, INDIGO, INK, LINE, MONO, MUTED, RED, TEXT,
    VIOLET, WHITE, _rect, _tb, bullets, card, stat,
)

from deck_chrome import W2, W3, W4, X2, X3, X4, guarded  # noqa: E402


def build(template, out):
    # Title guard and geometry from deck_chrome.py, shared with the two proposal decks. No tail
    # colour is passed, so this deck keeps the template's violet tail.
    d = guarded(Deck(template))
    FOOT = "S4biz Group · Cybergod LLC · roadmap 2027 · confidential"

    # =============================================================================== 01 TITLE ===
    s = d.slide("cybergod.ai · product roadmap · 2027",
                [("OWN THE SIGNAL.", WHITE), ("OWN THE JUDGEMENT.", WHITE),
                 ("OWN THE OUTCOME.", VIOLET)],
                footer=FOOT, hero=True)
    _tb(s, 0.55, 1.35, 9.00, 0.32, "> roadmap --year 2027 --moat own-collection --tier recurring",
        12, VIOLET, MONO)
    _tb(s, 0.57, 4.45, 11.60, 0.45,
        "From an assessment that rents its data to a platform that owns its signal, reasons over "
        "it, and sells the outcome as a subscription.", 12, BODY, TEXT)
    for i, (v, lab, col) in enumerate([
            ("3", "firehoses we\ncollect ourselves", CYAN),
            ("4", "new discovery\ndomains", VIOLET),
            ("6", "service tiers\none ladder", INDIGO),
            ("0", "packets to the\ncustomer, still", GREEN),
            ("1", "command\nstill ships it all", AMBER)]):
        x = 0.55 + i * 2.49
        _rect(s, x, 5.45, 2.29, 1.35, INK, LINE)
        _rect(s, x, 5.45, 2.29, 0.06, col, None)
        _tb(s, x + 0.16, 5.61, 1.99, 0.50, v, 22, col, DISPLAY, True)
        _tb(s, x + 0.16, 6.07, 1.99, 0.66, lab, 9.5, WHITE, TEXT, True, space=1.15)

    # ========================================================================= 02 THE ARGUMENT ===
    s = d.slide("the governing thought", "Situation, complication,", " answer",
                "Read the three boxes in order. Everything after this slide is detail.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("SITUATION", CYAN, "The product works",
             "One company name in, five evidence-grade deliverables out, in three document "
             "languages. 229 assessments run to date at under half a US cent of inference each, "
             "measured in our own cost ledger. The precision work is done and it is tested."),
            ("COMPLICATION", RED, "The spine is rented",
             "Discovery leans on a third-party index we neither own nor control. Our plan already "
             "blocks two query classes. A price move, a terms change or an outage is an "
             "existential dependency, and every competitor can buy the identical data."),
            ("ANSWER", VIOLET, "Own what compounds",
             "Collect the public firehoses ourselves, extend into cloud, identity and AI "
             "workloads where the incumbent index cannot see, and sell continuous outcomes rather "
             "than a one-off report.")]):
        card(s, X3[i], 2.05, W3, 2.55, k, kc, h, b)
    _rect(s, 0.55, 4.90, 12.23, 1.65, INK, LINE)
    _rect(s, 0.55, 4.90, 12.23, 0.06, VIOLET, None)
    _tb(s, 0.80, 5.12, 11.70, 0.30, "THE ONE SENTENCE", 9, VIOLET, MONO, True)
    _tb(s, 0.80, 5.45, 11.70, 0.95,
        "Anyone can buy the same scan data tomorrow morning. Nobody can buy nine months of "
        "ownership gates, attribution rules and adversarial review, and in 2027 nobody will be "
        "able to buy the collection either, because we will be running it ourselves.",
        13, WHITE, TEXT, space=1.25)

    # ======================================================================= 03 TODAY, HONESTLY ===
    s = d.slide("baseline", "What already ships", " today",
                "The roadmap builds on this. It does not replace it.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("DISCOVERY", CYAN, "Scope that holds",
             "One seed resolves ASNs, prefixes, brand domains, certificates and group structure. "
             "The ownership gate, co-tenant guard, public-suffix rule and per-domain budget exist "
             "because each one was paid for by a real false positive."),
            ("ANALYSIS", VIOLET, "33 detector classes",
             "Edge appliances, exposed management planes, secrets managers, NAS, backup consoles, "
             "PBX, ECM, non-production, OT and end-of-life software, plus certificate and email "
             "authentication posture from DNS alone."),
            ("DELIVERY", INDIGO, "Five artifacts",
             "Findings, C-BIQ loss modelling on FAIR, geopolitical threat profile, a combined "
             "animated report and a customer-safe run log. English, German and Russian. "
             "White-labelled to the partner's own brand.")]):
        card(s, X3[i], 2.05, W3, 2.55, k, kc, h, b)
    for i, (v, lab) in enumerate([("42", "deterministic gates\nbefore anything ships"),
                                  ("388", "automated tests\nin the suite"),
                                  ("170+", "defect classes\ndocumented, not repeated"),
                                  ("4", "model vendors\nno shared failure domain"),
                                  ("11", "regimes graded\nEU and Canada")]):
        stat(s, 0.55 + i * 2.49, 4.95, 2.29, v, lab)

    # ======================================================================== 04 WHERE THE MOAT ===
    s = d.slide("the defensible part", "The moat is not the", " data",
                "Which is exactly why the 2027 plan is to own the data as well.", FOOT)
    card(s, X2[0], 2.05, W2, 2.15, "COMMODITY", MUTED, "What anyone can buy",
         "A port-scan index is a purchase, not an advantage. Two vendors querying the same index "
         "with the same filters produce the same host list. Differentiation cannot live here, and "
         "on our current plan we do not even get the full query surface.")
    card(s, X2[1], 2.05, W2, 2.15, "PROPRIETARY", CYAN, "What nobody can buy",
         "The judgement layer. Whether a host is the customer's at all. Whether a certificate "
         "name is theirs or a neighbour's on a shared address. Whether a finding is attributable "
         "or a co-tenant's. Nine months of incidents encoded as rules and tests.")
    _rect(s, 0.55, 4.45, 12.23, 2.10, INK, LINE)
    _rect(s, 0.55, 4.45, 12.23, 0.06, CYAN, None)
    _tb(s, 0.80, 4.68, 11.70, 0.30, "THE 2027 MOVE", 9, CYAN, MONO, True)
    bullets(s, 0.80, 5.05, 11.60, [
        "Keep the judgement layer as the thing competitors cannot copy, and keep hardening it "
        "with every engagement.",
        "Add owned COLLECTION underneath it, so the inputs stop being a purchase order and start "
        "being an asset that grows every day we run.",
        "Point both at surfaces the incumbent index does not cover: cloud storage, identity "
        "tenancy and AI workloads."], gap=0.44, size=10.5)

    # ========================================================================= 05 FOUR PILLARS ===
    s = d.slide("roadmap 2027", "Four pillars and one", " ladder",
                "Three build the product. The fourth turns it into recurring revenue.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("PILLAR 1", CYAN, "Own the signal",
             "Ingest Certificate Transparency, BGP and RPKI, and gTLD zone files ourselves. Build "
             "our own passive DNS from them. The third-party index becomes one optional input "
             "instead of the spine."),
            ("PILLAR 2", VIOLET, "Cloud and identity",
             "Storage exposure, SaaS tenancy mapping and identity-provider posture from public "
             "metadata. This is where the modern breach starts and it is invisible to a port "
             "scanner."),
            ("PILLAR 3", INDIGO, "AI workloads",
             "Find exposed inference endpoints, notebooks, orchestrators, experiment trackers and "
             "vector stores, then connect each one to the AI Act obligation we already grade."),
            ("PILLAR 4", GREEN, "Adviser, not scanner",
             "Attack paths instead of lists, prioritisation by reachability instead of severity, "
             "and proof that a fix worked. Delivered continuously.")]):
        card(s, X4[i], 2.05, W4, 2.60, k, kc, h, b, bsize=9.5)
    _rect(s, 0.55, 4.95, 12.23, 1.55, INK, LINE)
    _tb(s, 0.80, 5.15, 11.70, 0.30, "AND THE COMMERCIAL LADDER THEY UNLOCK", 9, AMBER, MONO, True)
    _tb(s, 0.80, 5.50, 11.70, 0.85,
        "Discover, Assess, Monitor, Verify, Comply, Defend. Every pillar adds a rung, and every "
        "rung is a reason for the same customer to pay again next quarter rather than once.",
        12, BODY, TEXT, space=1.25)

    # ================================================================= 06 PILLAR 1 - COLLECTION ===
    s = d.slide("pillar 1 · own the signal", "Three firehoses, free and", " legal",
                "All three are public, continuous and permitted. None requires a packet to the "
                "customer.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("CERTIFICATE LOGS", CYAN, "Every cert, globally",
             "Browsers require certificates to be publicly logged, so the logs are a complete, "
             "real-time record of names being brought online. Today we query two aggregators per "
             "target. Ingesting the logs directly gives continuous discovery and a historical "
             "index that nobody can rate-limit or withdraw."),
            ("ROUTING", VIOLET, "BGP and RPKI",
             "Public route-collector archives give the authoritative view of who announces what. "
             "It replaces the four ASN lookup services we currently chain, and it opens a finding "
             "class we cannot produce today: routing that is invalid or newly announced by "
             "somebody who should not be announcing it."),
            ("ZONE DATA", INDIGO, "Registry zone files",
             "Zone-file access for the generic top-level domains is available under an ICANN "
             "programme. Combined with the names harvested from certificate logs it gives us our "
             "own passive DNS, which is the single most useful discovery asset in this business "
             "and one we would own outright.")]):
        card(s, X3[i], 2.05, W3, 3.15, k, kc, h, b, bsize=9.5)
    _tb(s, 0.55, 5.45, 12.23, 0.90,
        "None of this is mass scanning. We are not building a worse copy of somebody else's port "
        "scanner, and the promise that we send no packets to the assessed company stays exactly "
        "as it is written on the partner pack and in the Terms of Use.",
        11, MUTED, TEXT, space=1.25)

    # ==================================================================== 07 WHAT IT UNLOCKS ===
    s = d.slide("pillar 1 · consequences", "What owning collection", " changes",
                "Four things become possible that are not possible while we rent.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("CONTINUOUS", CYAN, "Minutes, not quarters",
             "A certificate is logged the moment it is issued. We learn about a new subdomain, a "
             "new environment or a new acquisition on the day it appears, not on the day somebody "
             "re-runs an assessment."),
            ("HISTORY", VIOLET, "An index that is ours",
             "Every name we have ever seen, kept. That supports change detection, dormant-asset "
             "discovery and incident reconstruction, and its value compounds with every month it "
             "runs."),
            ("NEW FINDINGS", INDIGO, "Classes we cannot see",
             "Routing anomalies, certificate issuance outside policy at scale, and names that "
             "appear before the service does. None of these come from a port scan, so none of "
             "them are available to a competitor buying the same index."),
            ("INDEPENDENCE", GREEN, "One input, not the spine",
             "The third-party index stays, because it is genuinely good at banners and it is "
             "cheap. It stops being the thing that can end the product.")]):
        card(s, X4[i], 2.05, W4, 2.85, k, kc, h, b, bsize=9.5)
    _rect(s, 0.55, 5.20, 12.23, 1.30, INK, LINE)
    _rect(s, 0.55, 5.20, 12.23, 0.06, AMBER, None)
    _tb(s, 0.80, 5.42, 11.70, 0.95,
        "The honest limit, stated here rather than discovered later: certificate logs tell us a "
        "NAME exists, not what is listening on it. Owning collection improves discovery and "
        "history. It does not replace a banner, which is why the third-party index stays.",
        11, BODY, TEXT, space=1.25)

    # ============================================================== 08 PILLAR 2 - CLOUD + IDP ===
    s = d.slide("pillar 2 · cloud and identity", "Where the breach actually", " starts",
                "All of it from public metadata. Still no packets to the customer's own systems.",
                FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("STORAGE", CYAN, "Public buckets",
             "Object storage left readable is one of the most common causes of large data loss "
             "and a port scanner cannot see it at all. Brand-token permutation across the major "
             "providers, checked for public listing, reported with the exact object count and "
             "nothing downloaded."),
            ("SAAS TENANCY", VIOLET, "Who they actually use",
             "We already detect Microsoft 365 and PBX tenancies from DNS. Extend it to the "
             "collaboration, CRM, ticketing and data-platform vendors. The result is a supplier "
             "map, which is both a risk finding and the best qualification data a partner can "
             "have."),
            ("IDENTITY", INDIGO, "The real front door",
             "Identity providers publish their configuration openly. Federation setup, tenant "
             "discovery and legacy authentication posture are all readable without touching the "
             "customer. Identity is where attackers go first and it is absent from every "
             "port-based view.")]):
        card(s, X3[i], 2.05, W3, 3.15, k, kc, h, b, bsize=9.5)
    _tb(s, 0.55, 5.45, 12.23, 0.90,
        "Upsell consequence: a supplier map turns one assessment into a conversation about every "
        "vendor in it. That is the most natural expansion path this product has, and today we "
        "throw the data away.", 11, MUTED, TEXT, space=1.25)

    # ================================================================ 09 PILLAR 3 - AI WORKLOADS ===
    s = d.slide("pillar 3 · ai workloads", "The exposure nobody is", " selling yet",
                "Every organisation is deploying this stack right now, and almost none of it is "
                "being assessed.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("SERVING", CYAN, "Inference endpoints",
             "Self-hosted model servers frequently ship with no authentication by default and are "
             "stood up by data teams outside the security review. An exposed one is both a "
             "compute theft problem and a data-exfiltration path."),
            ("PLATFORM", VIOLET, "Notebooks and clusters",
             "Notebook servers, distributed compute dashboards, workflow orchestrators and "
             "experiment trackers. Several of these have documented remote-execution exposure "
             "when reachable, and they routinely hold credentials to everything else."),
            ("DATA", INDIGO, "Vector and feature stores",
             "The vector database is where the proprietary corpus ends up after retrieval "
             "augmentation. Exposed, it leaks the training and reference material itself, which "
             "is usually the most sensitive asset in the estate."),
            ("SUPPLY CHAIN", GREEN, "Public model artifacts",
             "Organisation accounts on public model hubs, published weights and datasets that "
             "were meant to be private, and unsafe serialisation formats that execute on load.")]):
        card(s, X4[i], 2.05, W4, 2.85, k, kc, h, b, bsize=9.5)
    _rect(s, 0.55, 5.20, 12.23, 1.30, INK, LINE)
    _rect(s, 0.55, 5.20, 12.23, 0.06, VIOLET, None)
    _tb(s, 0.80, 5.42, 11.70, 0.95,
        "THE PART COMPETITORS CANNOT COPY QUICKLY: we already grade the EU AI Act. Joining "
        "\"here is your exposed inference endpoint\" to \"here is the article it puts you in "
        "breach of, and the deadline\" needs both halves. We are the only ones holding both.",
        11, WHITE, TEXT, space=1.25)

    # ================================================================ 10 PILLAR 4 - INTELLIGENCE ===
    s = d.slide("pillar 4 · intelligence", "From a list to a", " path",
                "A list of findings is a scan result. A path with a business consequence is "
                "advice.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("GRAPH", CYAN, "Chains, not items",
             "Model the estate as a graph and report the route: this reachable service, plus this "
             "stale record, plus this issuance gap, reaches that crown jewel. Customers act on "
             "chains. They argue with lists."),
            ("PRIORITY", VIOLET, "Reachability first",
             "Rank by whether an attacker can actually get there from the internet and what it "
             "reaches, not by a severity score copied from a database. A medium on the path to "
             "the finance system outranks a critical on an isolated host."),
            ("PROOF", GREEN, "Verify the fix",
             "Re-run the exact check that produced the finding and show it closed, with a date. "
             "This is what makes a retainer defensible and it is what turns a report into a "
             "programme.")]):
        card(s, X3[i], 2.05, W3, 2.55, k, kc, h, b)
    _rect(s, 0.55, 4.90, 12.23, 1.60, INK, LINE)
    _tb(s, 0.80, 5.10, 11.70, 0.30, "AND THE MODELS GET DEEPER, WITHOUT GETTING MORE AUTHORITY",
        9, AMBER, MONO, True)
    _tb(s, 0.80, 5.45, 11.70, 0.90,
        "Specialist reviewers per domain, each bound to the evidence in front of it, arguing "
        "against each other before anything reaches a slide. The rule does not change: code "
        "decides, models advise, and no identifier reaches a customer without evidence.",
        11.5, BODY, TEXT, space=1.25)

    # =================================================================== 11 CONTINUOUS + BENCH ===
    s = d.slide("the commercial hinge", "Snapshot becomes", " subscription",
                "This is the single largest change in the plan, and it is mostly plumbing we "
                "already have.", FOOT)
    card(s, X2[0], 2.05, W2, 2.45, "MONITORING", CYAN, "Assess on a schedule",
         "The engine already runs unattended and already writes structured events. Running it on "
         "a cadence and reporting only the DELTA turns a one-off report into a service: new "
         "asset appeared, certificate about to lapse, environment exposed last night. The "
         "customer hears from us between invoices, which is the whole point.")
    card(s, X2[1], 2.05, W2, 2.45, "BENCHMARK", VIOLET, "Peers, anonymised",
         "229 assessments and counting is already a dataset. Aggregated and anonymised, it "
         "supports a sentence no competitor can write without the same volume: how this estate "
         "compares to its sector. It needs care on privacy and honesty about sample size, and it "
         "gets both.")
    for i, (v, lab, col) in enumerate([
            ("ONE-OFF", "what we sell today\nreport, then silence", MUTED),
            ("RECURRING", "what we sell in 2027\ndelta, proof, retainer", CYAN),
            ("EXPANSION", "supplier map and\nAI estate open doors", VIOLET),
            ("PARTNER-LED", "white label already\nships, so it scales", GREEN)]):
        x = 0.55 + i * 3.10
        _rect(s, x, 4.80, 2.88, 1.65, INK, LINE)
        _rect(s, x, 4.80, 2.88, 0.06, col, None)
        _tb(s, x + 0.18, 5.02, 2.52, 0.34, v, 13, col, DISPLAY, True)
        _tb(s, x + 0.18, 5.42, 2.52, 0.90, lab, 9.5, BODY, TEXT, space=1.2)

    # ========================================================================== 12 TIER LADDER ===
    s = d.slide("packaging", "Six tiers, one", " ladder",
                "Each rung is a separate decision for the buyer and a separate line for the "
                "partner.", FOOT)
    rows = [("DISCOVER", "Free, self-service, one public artifact. Lead generation, not a product.",
             MUTED),
            ("ASSESS", "The five deliverables as they ship today. One company, one point in time.",
             CYAN),
            ("MONITOR", "Scheduled re-assessment with delta alerting and change history. Recurring.",
             CYAN),
            ("VERIFY", "Authorised active validation. Requires written authorisation on file, "
             "recorded in the run.", AMBER),
            ("COMPLY", "Regime grading and the roadmap deck. EU today, Canada today, more as "
             "demand appears.", VIOLET),
            ("DEFEND", "The inline shield and the attack digest, run for the customer's own "
             "estate.", GREEN)]
    # SIX ROWS IS AN ARITHMETIC PROBLEM, like every fixed-height row in this repository. At a 0.80
    # step the last row ends at 6.77 and the note beneath it runs to 7.18, straight through the
    # footer at 7.04. Measured, then tightened, rather than rendered and hoped for.
    y = 1.98
    for name, desc, col in rows:
        _rect(s, 0.55, y, 12.23, 0.70, INK, LINE)
        _rect(s, 0.55, y, 0.06, 0.70, col, None)
        _tb(s, 0.80, y + 0.14, 2.10, 0.30, name, 12, col, DISPLAY, True)
        _tb(s, 3.00, y + 0.16, 9.55, 0.45, desc, 10.5, BODY, TEXT)
        y += 0.78
    _tb(s, 0.55, 6.72, 12.23, 0.26,
        "No prices on this slide, deliberately. A published price is a negotiating position given "
        "away, and it goes stale the day a tier changes.", 9, MUTED, MONO)

    # ============================================================================ 13 SEQUENCING ===
    s = d.slide("sequencing", "What lands, and in what", " order",
                "Ordered by dependency, not by excitement. Each quarter ships something sellable.",
                FOOT)
    for i, (q, col, head, items) in enumerate([
            ("Q1", CYAN, "Collect", ["Certificate log ingestion",
                                     "Own passive DNS index",
                                     "Continuous discovery loop",
                                     "Monitor tier goes live"]),
            ("Q2", VIOLET, "Expand", ["Storage exposure checks",
                                      "SaaS and identity mapping",
                                      "Supplier map deliverable",
                                      "Routing and RPKI findings"]),
            ("Q3", INDIGO, "Reason", ["AI workload discovery",
                                      "AI Act finding linkage",
                                      "Attack-path graph",
                                      "Reachability ranking"]),
            ("Q4", GREEN, "Prove", ["Remediation verification",
                                    "Peer benchmarking",
                                    "Partner API and connectors",
                                    "Marketplace listing"])]):
        x = X4[i]
        _rect(s, x, 2.05, W4, 3.55, INK, LINE)
        _rect(s, x, 2.05, W4, 0.06, col, None)
        _tb(s, x + 0.22, 2.28, W4 - 0.44, 0.30, q, 11, col, MONO, True)
        _tb(s, x + 0.22, 2.58, W4 - 0.44, 0.36, head, 15, WHITE, DISPLAY, True)
        bullets(s, x + 0.22, 3.10, W4 - 0.44, items, gap=0.46, dot=col, size=9.5, dotsize=0.09)
    _tb(s, 0.55, 5.85, 12.23, 0.70,
        "Q1 is the load-bearing quarter. Everything after it assumes we are collecting our own "
        "names continuously, so if only one thing gets built, it is that one.",
        11, BODY, TEXT, space=1.25)

    # ====================================================================== 14 WHAT WE WILL NOT ===
    s = d.slide("scope discipline", "What we will not", " build",
                "A roadmap without exclusions is a wish list. These are refusals, not omissions.",
                FOOT)
    for i, (k, h, b) in enumerate([
            ("REFUSED", "Mass internet scanning",
             "It would break the promise printed on the partner pack, the Terms of Use and the "
             "Article 13 notice, that we send no packets to the assessed company. It is also "
             "capital-intensive and we would be a worse version of an existing product."),
            ("REFUSED", "Anything offensive",
             "No scanning back, no probing an attacker's infrastructure, no exploitation. It is "
             "criminal in every jurisdiction we operate in, the address is usually a compromised "
             "third party, and one such packet ends the passive promise permanently."),
            ("REFUSED", "Models with authority",
             "No model decides a side effect, blocks an address or changes scope. Four vendors "
             "advise, deterministic code decides. The consensus panel has been wrong often enough "
             "that this is a measured position, not a philosophical one.")]):
        card(s, X3[i], 2.05, W3, 2.85, k, RED, h, b, bsize=9.5)
    _rect(s, 0.55, 5.20, 12.23, 1.30, INK, LINE)
    _tb(s, 0.80, 5.42, 11.70, 0.95,
        "Also not on this roadmap: a published comparison against a named competitor. We have not "
        "benchmarked one, an unsubstantiated superiority claim is comparative advertising, and "
        "the architectural argument is stronger anyway because a reader can check it.",
        11, BODY, TEXT, space=1.25)

    # ========================================================================= 15 HOW WE MEASURE ===
    s = d.slide("accountability", "How we will know it", " worked",
                "Each of these is already measurable in the systems we run. No new dashboard "
                "required.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("COVERAGE", CYAN, "Parity, then better",
             "We already fail the build when the engine finds less than a hand-built expert "
             "harvest of the same target. The 2027 target is to pass that test using our own "
             "collection, with the third-party index switched off."),
            ("PRECISION", VIOLET, "False positives stay at zero",
             "Every new discovery source is a new way to put a stranger in a customer's report. "
             "Each one ships with the same ownership and attribution gates and its own regression "
             "test, or it does not ship."),
            ("ECONOMICS", INDIGO, "Cost per assessment",
             "Measured per run in the ledger today. More sources and more reasoning must not move "
             "it materially, and if it does, the slide says so."),
            ("COMMERCIAL", GREEN, "Share that recurs",
             "The share of revenue on a monitoring or compliance subscription rather than a "
             "one-off assessment. Today that number is zero.")]):
        card(s, X4[i], 2.05, W4, 2.85, k, kc, h, b, bsize=9.5)
    _tb(s, 0.55, 5.20, 12.23, 0.70,
        "The point of naming a target you can fail is that it can be checked next year by "
        "somebody who does not trust this deck.", 11, MUTED, TEXT, space=1.25)

    # ============================================================================= 16 THE RISKS ===
    s = d.slide("honest limits", "What could make this", " wrong",
                "Stated now, because the credibility of everything else depends on it.", FOOT)
    bullets(s, 0.80, 2.15, 11.70, [
        "Certificate logs prove a NAME, never a service. Owning them transforms discovery and "
        "history. It does not remove the need for banner data, and this deck does not pretend it "
        "does.",
        "Zone-file access is granted under a programme with terms and an approval step. It is "
        "routine, but it is a dependency on somebody else's decision and it is not instant.",
        "Cloud storage and identity checks touch third-party platforms rather than the customer. "
        "That is lawful and normal, and it still needs the same care about rate, attribution and "
        "written scope that the rest of the engine already applies.",
        "Peer benchmarking needs volume before a percentile means anything. Publishing one early "
        "would be exactly the kind of confidently-wrong number this product exists to avoid.",
        "The active Verify tier stays off unless a written authorisation reference is recorded in "
        "the run. That is not a configuration flag we will quietly relax.",
        "Market sizing is absent from this deck on purpose. We do not have a defensible number "
        "and an invented one would discredit the measured ones beside it."],
        gap=0.60, dot=AMBER, size=11)

    # ================================================================================= 17 CLOSE ===
    s = d.slide("the ask", "One year, four", " pillars",
                "", FOOT, hero=False)
    _rect(s, 0.55, 2.20, 12.23, 2.05, INK, LINE)
    _rect(s, 0.55, 2.20, 12.23, 0.06, CYAN, None)
    _tb(s, 0.85, 2.50, 11.60, 1.55,
        "By the end of 2027 a customer should be able to say: they found assets our own team did "
        "not know about, including our cloud and our AI stack, they told us which one actually "
        "mattered and why, they proved the fix landed, and they did it again this quarter without "
        "being asked.", 15, WHITE, TEXT, space=1.28)
    for i, (v, lab, col) in enumerate([
            ("OWN", "the collection\nnot rent it", CYAN),
            ("SEE", "cloud, identity, AI\nnot only ports", VIOLET),
            ("ADVISE", "paths and proof\nnot lists", INDIGO),
            ("RECUR", "subscription\nnot a one-off", GREEN)]):
        x = 0.55 + i * 3.10
        _rect(s, x, 4.55, 2.88, 1.75, INK, LINE)
        _rect(s, x, 4.55, 2.88, 0.06, col, None)
        _tb(s, x + 0.18, 4.80, 2.52, 0.42, v, 19, col, DISPLAY, True)
        _tb(s, x + 0.18, 5.32, 2.52, 0.90, lab, 10, BODY, TEXT, space=1.2)
    _tb(s, 0.55, 6.50, 12.23, 0.30,
        "feranicus@s4biz.io  ·  cybergod.ai  ·  every figure on these slides is measured in our "
        "own systems", 9.5, MUTED, MONO)

    d.save(out)
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--template",
                    default=os.path.join(here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=os.path.join(here, "S4biz_Cybergod_Roadmap_2027.pptx"))
    a = ap.parse_args()
    if not os.path.exists(a.template):
        raise SystemExit("[X] template not found: %s" % a.template)
    print("built:", build(a.template, a.out))


if __name__ == "__main__":
    main()
