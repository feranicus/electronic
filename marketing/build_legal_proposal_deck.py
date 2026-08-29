#!/usr/bin/env python3
"""build_legal_proposal_deck.py — proposal to a LAW FIRM, in the S4biz template, cyan-led.

    python marketing/build_legal_proposal_deck.py [--out PATH] [--template PATH] [--firm NAME]

THIS IS NOT THE EXISTING legal.pptx. That deck sells law firms as a CHANNEL: the firm resells
assessments to its own clients, and it is organised by country and NIS2 deadline. This deck sells
TO the firm, about the firm's own estate, and it combines the three things we actually deliver:

    1. cybergod.ai   the outside view, with no packets sent to the firm
    2. BAS           the inside view, blast radius once someone is already in
    3. the stack     the managed remediation that closes what the two views find

TEMPLATE: imported from build_consensus_deck.py, which read every coordinate and colour off
S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx. Four decks now share one implementation.

CYAN-LED, ON REQUEST. The template's title tail is violet by default; here it is recoloured to
cyan after the slide is built, so the shared implementation is not forked for a colour preference.
Severity colours are NOT rebranded: red still means a refusal and amber still means a caution.
Those are enums, and this repository has already paid for renaming an enum.

HONESTY RULES APPLIED HERE (the audience is lawyers, so this matters more than usual):
  * The peer-firm evidence is REAL and comes from an assessment we ran, presented ANONYMISED.
    No client is named, which is both the professional norm and our own rule for partner material.
  * Statute references are to the provisions themselves. Nothing is characterised as legal advice,
    and the deck says so, because telling a law firm what the law says is a bad way to open.
  * Commercials are the real list prices from the existing partner material. BAS and stack are
    marked scoped-per-engagement rather than given an invented number.
  * No named competitor, no invented benchmark, no CVE identifiers, no em dashes.
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


def build(template, out, firm):
    # The title guard and the cyan tail pass live in deck_chrome.py, shared with the roadmap and
    # accounting decks. They used to be copied into each builder, which is the duplication this
    # repository has paid for more than any other defect class.
    d = guarded(Deck(template), tail=CYAN)
    FOOT = "S4biz Group · Cybergod LLC · proposal · confidential · not legal advice"

    # ================================================================================ 01 TITLE ===
    s = d.slide("proposal · %s · external, internal and managed" % firm,
                [("YOUR CLIENTS' SECRETS", WHITE), ("ARE YOUR", WHITE),
                 ("ATTACK SURFACE.", CYAN)],
                footer=FOOT, hero=True)
    _tb(s, 0.55, 1.35, 9.60, 0.32,
        "> assess --outside 0-packets  |  bas --inside blast-radius  |  close --managed",
        12, CYAN, MONO)
    _tb(s, 0.57, 4.45, 11.60, 0.45,
        "A law firm concentrates other people's worst secrets in one estate. This is what the "
        "internet can already see, what an intruder would reach, and how both get closed.",
        12, BODY, TEXT)
    for i, (v, lab, col) in enumerate([
            ("0", "packets sent to you\nduring assessment", CYAN),
            ("5 min", "from company name\nto finished report", CYAN),
            ("24/7", "attack simulation\nnot once a year", INDIGO),
            ("GPLv3", "the simulation engine\nis open source", GREEN),
            ("EU", "all data in Frankfurt\nno replication out", VIOLET)]):
        x = 0.55 + i * 2.49
        _rect(s, x, 5.45, 2.29, 1.35, INK, LINE)
        _rect(s, x, 5.45, 2.29, 0.06, col, None)
        _tb(s, x + 0.16, 5.61, 1.99, 0.50, v, 20, col, DISPLAY, True)
        _tb(s, x + 0.16, 6.07, 1.99, 0.66, lab, 9.5, WHITE, TEXT, True, space=1.15)

    # ==================================================================== 02 WHY A FIRM IS TARGET ===
    s = d.slide("the target profile", "Why a firm is worth", " more",
                "An attacker does not breach a law firm to reach the law firm.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("CONCENTRATION", CYAN, "Many clients, one estate",
             "Transaction data, litigation strategy, board minutes, investigation files and "
             "intellectual property, for every client at once. One firm is a shortcut to the "
             "confidential material of everyone it acts for."),
            ("TIMING", INDIGO, "Value with a clock on it",
             "A deal, a filing deadline or a hearing date gives material a precise window in "
             "which it is worth the most. Extortion works best against a party that cannot afford "
             "to wait, and a firm rarely can."),
            ("LEVERAGE", VIOLET, "Publication is the threat",
             "Modern extortion does not need to encrypt anything. Copying privileged material and "
             "threatening to publish it is enough, and it defeats every backup strategy the firm "
             "may have.")]):
        card(s, X3[i], 2.05, W3, 2.55, k, kc, h, b)
    _rect(s, 0.55, 4.90, 12.23, 1.60, INK, LINE)
    _rect(s, 0.55, 4.90, 12.23, 0.06, CYAN, None)
    _tb(s, 0.80, 5.12, 11.70, 0.30, "THE CONSEQUENCE THAT IS DIFFERENT HERE", 9, CYAN, MONO, True)
    _tb(s, 0.80, 5.45, 11.70, 0.90,
        "For most businesses a breach is a regulatory and commercial problem. For a firm it is "
        "also a professional one, and in the worst case a criminal one. That changes which "
        "controls are worth having, and it changes who has to sign off on them.",
        12.5, BODY, TEXT, space=1.25)

    # ========================================================================== 03 LEGAL EXPOSURE ===
    s = d.slide("the obligation", "The exposure is", " criminal",
                "Provisions cited so the firm can check them. Nothing here is legal advice.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("PROFESSIONAL SECRECY", RED, "Personal liability",
             "Unauthorised disclosure of a secret entrusted to a lawyer is a criminal offence in "
             "Germany under section 203 of the Criminal Code and in Switzerland under article 321. "
             "The duty falls on individuals, not only on the entity."),
            ("SERVICE PROVIDERS", AMBER, "It follows the data",
             "German law extends the same duty to the people and firms brought in to support the "
             "practice, and the professional code governs how such providers are engaged. Your IT "
             "supply chain is inside the secrecy perimeter, not outside it."),
            ("DATA PROTECTION", CYAN, "Article 32 and 33",
             "Appropriate technical measures, plus notification within seventy two hours. Firms "
             "routinely process the special categories and criminal-offence data that attract the "
             "closest scrutiny when something goes wrong.")]):
        card(s, X3[i], 2.05, W3, 2.85, k, kc, h, b, bsize=9.5)
    _tb(s, 0.55, 5.20, 12.23, 1.30,
        "Why this belongs on slide three rather than in an appendix: it decides the buying "
        "criteria. A control that cannot be evidenced afterwards is worth very little when the "
        "question is whether appropriate measures were in place on the day, and that question is "
        "asked after the incident, by somebody hostile.", 11, MUTED, TEXT, space=1.25)

    # ============================================================================ 04 NIS2 PUSHDOWN ===
    s = d.slide("the commercial driver", "You are not in scope. Your",
                " clients are",
                "Which is why the requirement arrives from a client, not from a regulator.", FOOT)
    card(s, X2[0], 2.05, W2, 2.35, "THE MECHANISM", CYAN, "Supply chain, pushed down",
         "The current EU cyber regime obliges in-scope organisations to manage security in their "
         "supplier relationships. Their advisers are suppliers. The obligation does not land on "
         "the firm directly; it arrives as a questionnaire, a contractual clause or an audit "
         "request from a client the firm cannot afford to disappoint.")
    card(s, X2[1], 2.05, W2, 2.35, "WHAT THAT LOOKS LIKE", INDIGO, "A form you must pass",
         "Financial-sector clients are under a separate resilience regime with its own testing "
         "expectations, and they pass those expectations on. The practical effect is the same: "
         "the firm is asked to demonstrate, in writing and on a schedule, that it tests its own "
         "defences. Assertion stops being sufficient.")
    _rect(s, 0.55, 4.70, 12.23, 1.85, INK, LINE)
    _rect(s, 0.55, 4.70, 12.23, 0.06, GREEN, None)
    _tb(s, 0.80, 4.92, 11.70, 0.30, "TURN IT AROUND", 9, GREEN, MONO, True)
    _tb(s, 0.80, 5.25, 11.70, 1.15,
        "A firm that can answer the questionnaire on the day it arrives, with dated evidence "
        "rather than a policy document, is easier to keep on a panel than one that cannot. The "
        "same three layers that reduce the risk also produce the paperwork, which is the part "
        "most security spending fails to deliver.", 12.5, BODY, TEXT, space=1.25)

    # =========================================================================== 05 REAL EVIDENCE ===
    s = d.slide("evidence", "What we found at a", " peer firm",
                "A mid-sized German firm. No contact, no access, no credentials, no packets sent.",
                FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("FINDING", RED, "The mail archive",
             "An archive server holding years of correspondence, reachable from the internet on "
             "the mail port, presenting a self-signed certificate that had already expired. For a "
             "practice under professional secrecy that is the client file, exposed."),
            ("FINDING", AMBER, "The case system",
             "A case-file application and a hypervisor management interface, both externally "
             "resolvable. Neither is something an outside party has any reason to reach, and "
             "neither had been noticed internally."),
            ("METHOD", CYAN, "How we knew",
             "Public certificate logs, public routing and DNS records the firm publishes itself. "
             "The whole picture came from records anyone can read, which is exactly why an "
             "attacker starts there too.")]):
        card(s, X3[i], 2.05, W3, 2.70, k, kc, h, b, bsize=9.5)
    _rect(s, 0.55, 5.05, 12.23, 1.40, INK, LINE)
    _tb(s, 0.80, 5.28, 11.70, 1.00,
        "The firm is not named here and will not be named to anyone else, which is the same "
        "answer you will get about your own assessment. The point of the example is that none of "
        "it required cleverness. It required looking.", 12, BODY, TEXT, space=1.25)

    # ============================================================================ 06 THREE LAYERS ===
    s = d.slide("the proposal", "Outside, inside,", " closed",
                "Three layers. Each answers a question the other two cannot.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("LAYER 1 · CYBERGOD", CYAN, "What can be seen",
             "The external estate as an attacker enumerates it, with no packets sent to you. "
             "Findings, priced risk, threat profile and a full evidence log. Five to seven "
             "minutes per run, repeatable on a schedule."),
            ("LAYER 2 · BAS", INDIGO, "How far they get",
             "Breach and attack simulation inside the network. Once a credential is phished or a "
             "laptop is compromised, what does it actually reach, and does it reach the document "
             "management system."),
            ("LAYER 3 · THE STACK", GREEN, "Close it, keep it closed",
             "Managed firewall, zero-trust access, email authentication, segmentation and backup "
             "validation. Then the outside view runs again and proves the finding is gone.")]):
        card(s, X3[i], 2.05, W3, 2.70, k, kc, h, b)
    _rect(s, 0.55, 5.05, 12.23, 1.45, INK, LINE)
    _rect(s, 0.55, 5.05, 12.23, 0.06, CYAN, None)
    _tb(s, 0.80, 5.30, 11.70, 1.00,
        "Layer one can start this week with nothing signed beyond a scope confirmation. Layer two "
        "needs an agreed window and a written authorisation. Layer three follows what the first "
        "two actually find, rather than a product list decided in advance.",
        12.5, BODY, TEXT, space=1.25)

    # ======================================================================= 07 LAYER 1 CYBERGOD ===
    s = d.slide("layer 1 · cybergod.ai", "The outside view in", " minutes",
                "One input: the firm's name. Four documents and a run log out.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("EXPOSURE", CYAN, "What is reachable",
             "Every externally visible weakness, ranked, each anchored to the specific evidence "
             "that produced it so it can be verified rather than believed."),
            ("COST", INDIGO, "Priced in euros",
             "Each finding converted to an annual loss figure using the same quantitative method "
             "insurers use, so the remediation conversation is a budget conversation."),
            ("THREAT", VIOLET, "Who is likely",
             "Named actor groups with sources and confidence grading, and why a practice of this "
             "profile fits what they select for."),
            ("RECORD", GREEN, "The methodology log",
             "A customer-safe log of what was queried, what was refused and why. It is the "
             "document that survives being challenged later.")]):
        card(s, X4[i], 2.05, W4, 2.60, k, kc, h, b, bsize=9.5)
    for i, (v, lab) in enumerate([("0", "packets sent to\nthe firm's systems"),
                                  ("3", "document languages\nEN, DE, RU"),
                                  ("33", "detector classes\nnot a generic scan"),
                                  ("5", "artifacts per run\nincluding the log"),
                                  ("EU", "processing stays\nin Frankfurt")]):
        stat(s, 0.55 + i * 2.49, 5.00, 2.29, v, lab)

    # ======================================================================== 08 WHY ZERO TOUCH ===
    s = d.slide("the objection, answered", "Why zero touch matters",
                " here", "This is the slide that matters to a general counsel more than any "
                "feature.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("EVALUATION", CYAN, "Try it with nothing signed",
             "Because the assessment reads only public records, evaluating us does not require "
             "network access, credentials, an installed agent or a data processing agreement. "
             "There is no confidentiality exposure in finding out whether it is any good."),
            ("PRIVILEGE", INDIGO, "Nothing privileged is read",
             "We do not see documents, mail content or matter data at any point in layer one. The "
             "inputs are certificate logs, routing records and DNS entries the firm already "
             "publishes to the world."),
            ("PROOF", GREEN, "It is checkable",
             "The methodology log lists every query. If a finding is disputed, the evidence "
             "anchor is in the report and can be reproduced by the firm's own IT provider without "
             "our involvement.")]):
        card(s, X3[i], 2.05, W3, 2.85, k, kc, h, b, bsize=9.5)
    _rect(s, 0.55, 5.20, 12.23, 1.30, INK, LINE)
    _rect(s, 0.55, 5.20, 12.23, 0.06, AMBER, None)
    _tb(s, 0.80, 5.42, 11.70, 0.95,
        "Stated plainly because it is the limit of layer one: reading public records cannot tell "
        "you what an intruder would reach once inside. That question needs layer two, and layer "
        "two is not zero touch. It is authorised, scheduled and scoped in writing.",
        11.5, BODY, TEXT, space=1.25)

    # ============================================================================== 09 BAS BASICS ===
    s = d.slide("layer 2 · bas", "A yearly test is a", " snapshot",
                "The estate changes every week. The test does not.", FOOT)
    card(s, X2[0], 2.05, W2, 2.55, "TODAY", MUTED, "Annual penetration test",
         "A skilled team, a fixed window, a report. It is genuinely useful and it is also a "
         "photograph. It reflects the estate on the week it ran, it is expensive enough that it "
         "happens once a year, and every change made in the following eleven months is untested "
         "until the next one.")
    card(s, X2[1], 2.05, W2, 2.55, "INSTEAD", CYAN, "Continuous simulation",
         "Automated attack simulation running on a schedule against the live estate, using real "
         "techniques mapped to the public attack framework. It does not replace human testers for "
         "creative work. It replaces the eleven months in which nothing is tested at all, and it "
         "produces dated evidence every time it runs.")
    for i, (v, lab, col) in enumerate([
            ("SNAPSHOT", "one week a year\nis measured", MUTED),
            ("CONTINUOUS", "every change\nis re-tested", CYAN),
            ("MAPPED", "to the public\nattack framework", INDIGO),
            ("EVIDENCE", "dated output for\nthe questionnaire", GREEN)]):
        x = 0.55 + i * 3.10
        _rect(s, x, 4.90, 2.88, 1.60, INK, LINE)
        _rect(s, x, 4.90, 2.88, 0.06, col, None)
        _tb(s, x + 0.18, 5.12, 2.52, 0.34, v, 13, col, DISPLAY, True)
        _tb(s, x + 0.18, 5.52, 2.52, 0.85, lab, 9.5, BODY, TEXT, space=1.2)

    # ========================================================================= 10 THE ONE QUESTION ===
    s = d.slide("layer 2 · what it answers", "Does reception reach the",
                " DMS?",
                "For a law firm this is the whole question, and almost nobody can answer it.",
                FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("SEGMENTATION", CYAN, "Prove the wall exists",
             "Simulation starts from an assumed compromise on an ordinary workstation and attempts "
             "to move. If it reaches the document management system, the matter archive or the "
             "finance system, you learn it from us rather than from an extortion note."),
            ("CREDENTIALS", INDIGO, "Reused and cached",
             "Shared local administrator passwords, cached domain credentials and service accounts "
             "with more rights than anyone remembers granting. These are what turn one "
             "compromised laptop into the whole practice."),
            ("REMOTE OFFICES", VIOLET, "The small sites",
             "Branch offices and home working are usually where segmentation quietly is not "
             "enforced. The simulation is run from there too, because that is where a real "
             "intruder would prefer to start.")]):
        card(s, X3[i], 2.05, W3, 2.85, k, kc, h, b, bsize=9.5)
    _rect(s, 0.55, 5.20, 12.23, 1.30, INK, LINE)
    _tb(s, 0.80, 5.42, 11.70, 0.95,
        "The output is not a score. It is a per-machine list of what moved where, and the "
        "specific change that stops it: this rule, this account, this segment. That is a work "
        "order, and it is what makes the next run measurably better than the last.",
        12, BODY, TEXT, space=1.25)

    # ============================================================================ 11 OPEN SOURCE ===
    s = d.slide("layer 2 · the engine", "Open source, and you can",
                " read it",
                "A profession built on confidentiality should not have to take this on trust.",
                FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("INSPECTABLE", CYAN, "Published source",
             "The simulation engine is open source under a public licence. Your own advisers can "
             "read exactly what it does before it runs inside your network, which is not possible "
             "with a closed commercial agent."),
            ("NO LOCK-IN", INDIGO, "No licence dependency",
             "There is no per-seat licence and no vendor whose commercial decisions can strand "
             "the capability. The approach is deliberately tool-agnostic: the engine can be "
             "replaced without changing the service around it."),
            ("SAFE BY DESIGN", GREEN, "Simulation, not payload",
             "The technique is exercised and the reachability is recorded. Nothing is encrypted, "
             "nothing is exfiltrated and nothing is destroyed. Scope, timing and stop conditions "
             "are agreed in writing before anything starts."),
            ("MANAGED", VIOLET, "We run it, you read it",
             "Deployment, scheduling, tuning and interpretation are ours. The firm receives the "
             "findings and the work orders, not another console to staff.")]):
        card(s, X4[i], 2.05, W4, 2.90, k, kc, h, b, bsize=9.5)
    _tb(s, 0.55, 5.25, 12.23, 1.10,
        "One honest note for the technical reviewer: the specific engine matters less than the "
        "discipline around it. We name the tool in the statement of work, we agree the version, "
        "and if the project behind it changes direction we replace it and say so.",
        11, MUTED, TEXT, space=1.25)

    # ================================================================================ 12 THE STACK ===
    s = d.slide("layer 3 · the stack", "Closing what the two views",
                " find",
                "Scoped from findings, not sold from a catalogue.", FOOT)
    rows = [("PERIMETER", "Managed next-generation firewall and rule review, driven by what the "
             "simulation actually walked through.", CYAN),
            ("ACCESS", "Zero-trust remote access replacing flat VPN reach, so a stolen credential "
             "opens one application rather than the network.", CYAN),
            ("IDENTITY", "Multi-factor coverage, privileged account cleanup and removal of the "
             "shared local administrator passwords the simulation finds.", INDIGO),
            ("MAIL", "Sender authentication so the firm's own domain cannot be used to invoice "
             "its clients fraudulently, which is the most common attack on this profession.",
             INDIGO),
            ("SEGMENTATION", "Separation of the document and matter systems from general office "
             "traffic, then re-tested rather than assumed.", VIOLET),
            ("RECOVERY", "Backup that is verified by restore, including the archive, because "
             "publication threats defeat backups and encryption does not.", GREEN)]
    y = 1.98
    for name, desc, col in rows:
        _rect(s, 0.55, y, 12.23, 0.70, INK, LINE)
        _rect(s, 0.55, y, 0.06, 0.70, col, None)
        _tb(s, 0.80, y + 0.14, 2.30, 0.30, name, 12, col, DISPLAY, True)
        _tb(s, 3.20, y + 0.13, 9.35, 0.52, desc, 10, BODY, TEXT, space=1.2)
        y += 0.78
    _tb(s, 0.55, 6.72, 12.23, 0.26,
        "Nothing on this slide is proposed until layer one or layer two has produced a reason for "
        "it.", 9, MUTED, MONO)

    # ============================================================================== 13 THE FLYWHEEL ===
    s = d.slide("how it compounds", "Find, prove, close,", " verify",
                "The loop is the product. A single report is not.", FOOT)
    for i, (n, k, kc, h, b) in enumerate([
            ("01", "FIND", CYAN, "Outside view",
             "The external assessment produces ranked findings with evidence anchors and a priced "
             "annual loss figure."),
            ("02", "PROVE", INDIGO, "Inside view",
             "Simulation shows which of those findings actually reaches something that matters, "
             "and which are noise."),
            ("03", "CLOSE", GREEN, "Managed change",
             "Only the changes the first two steps justified, delivered as managed service or "
             "handed to the firm's existing provider."),
            ("04", "VERIFY", VIOLET, "Re-run and date it",
             "Both views run again. The finding is shown closed, with a date. That artifact is "
             "what answers the client questionnaire.")]):
        x = X4[i]
        _rect(s, x, 2.05, W4, 2.90, INK, LINE)
        _rect(s, x, 2.05, W4, 0.06, kc, None)
        _tb(s, x + 0.22, 2.28, 0.60, 0.28, n, 11, kc, MONO, True)
        _tb(s, x + 0.22, 2.58, W4 - 0.44, 0.30, k, 9, kc, MONO, True)
        _tb(s, x + 0.22, 2.86, W4 - 0.44, 0.36, h, 14, WHITE, DISPLAY, True)
        _tb(s, x + 0.22, 3.32, W4 - 0.44, 1.50, b, 9.5, BODY, TEXT, space=1.28)
    _rect(s, 0.55, 5.25, 12.23, 1.25, INK, LINE)
    _rect(s, 0.55, 5.25, 12.23, 0.06, CYAN, None)
    _tb(s, 0.80, 5.48, 11.70, 0.90,
        "Step four is the one most security work never reaches, and it is the only step that "
        "produces something the firm can hand to a client, an insurer or a regulator.",
        12.5, BODY, TEXT, space=1.25)

    # ============================================================================== 14 ENGAGEMENT ===
    s = d.slide("delivery", "How the engagement", " runs",
                "Nothing in the first stage requires access, downtime or a change window.", FOOT)
    for i, (q, col, head, items) in enumerate([
            ("WEEK 1", CYAN, "Outside", ["Scope confirmed in writing",
                                         "External assessment run",
                                         "Findings walked through",
                                         "Priorities agreed"]),
            ("WEEK 2-3", INDIGO, "Inside", ["Authorisation signed",
                                            "Window and stop rules set",
                                            "Simulation deployed",
                                            "Blast radius mapped"]),
            ("WEEK 4", VIOLET, "Report", ["Combined findings",
                                          "Work orders, prioritised",
                                          "Half-day workshop",
                                          "Questionnaire evidence"]),
            ("ONGOING", GREEN, "Loop", ["Monthly external re-run",
                                        "Scheduled simulation",
                                        "Managed stack as agreed",
                                        "Dated verification"])]):
        x = X4[i]
        _rect(s, x, 2.05, W4, 3.35, INK, LINE)
        _rect(s, x, 2.05, W4, 0.06, col, None)
        _tb(s, x + 0.22, 2.28, W4 - 0.44, 0.30, q, 11, col, MONO, True)
        _tb(s, x + 0.22, 2.58, W4 - 0.44, 0.36, head, 15, WHITE, DISPLAY, True)
        bullets(s, x + 0.22, 3.10, W4 - 0.44, items, gap=0.46, dot=col, size=9.5, dotsize=0.09)
    _tb(s, 0.55, 5.65, 12.23, 0.85,
        "The firm can stop after week one and still hold something useful. That is deliberate: an "
        "engagement that only pays off if you buy all of it is a sales structure, not a plan.",
        11.5, BODY, TEXT, space=1.25)

    # ============================================================================ 15 COMMERCIALS ===
    s = d.slide("commercials", "What it", " costs",
                "List prices. Volume and partner terms are set in the agreement.", FOOT)
    rows = [("Single assessment", "one company, one point in time, four documents",
             "EUR 100", CYAN),
            ("Report subscription", "scheduled re-assessment with change history, per month",
             "EUR 200", CYAN),
            ("Findings review", "walkthrough and prioritisation with an engineer, per hour",
             "EUR 200", INDIGO),
            ("Workshop", "hands-on session with the firm's own estate, per day",
             "EUR 2 500", INDIGO),
            ("Breach and attack simulation", "deployment, scheduled runs and interpretation",
             "scoped", VIOLET),
            ("Managed stack", "only the components the findings justify",
             "scoped", GREEN)]
    y = 1.98
    for name, desc, price, col in rows:
        _rect(s, 0.55, y, 12.23, 0.70, INK, LINE)
        _rect(s, 0.55, y, 0.06, 0.70, col, None)
        _tb(s, 0.80, y + 0.14, 3.60, 0.30, name, 12, col, DISPLAY, True)
        _tb(s, 4.55, y + 0.16, 5.90, 0.42, desc, 10, BODY, TEXT)
        _tb(s, 10.60, y + 0.14, 1.95, 0.30, price, 13, WHITE, DISPLAY, True)
        y += 0.78
    _tb(s, 0.55, 6.72, 12.23, 0.26,
        "The two scoped lines are quoted after week one, because quoting them before means "
        "guessing what is wrong.", 9, MUTED, MONO)

    # =========================================================================== 16 WHAT WE WON'T ===
    s = d.slide("boundaries", "What we will not", " touch",
                "For this audience the refusals are more persuasive than the features.", FOOT)
    for i, (h, b) in enumerate([
            ("Your client files",
             "No matter data, no mail content, no documents. The external assessment reads public "
             "records only. The simulation measures reachability and records that it could reach "
             "a system. It does not read what is in it."),
            ("Anything offensive",
             "No action against a third party, no scanning of an attacker, no exploitation "
             "outside the agreed scope and window. Simulation stops at proving the path."),
            ("Unbounded access",
             "Layer two runs only with written authorisation naming the scope, the window and the "
             "stop conditions. The authorisation reference is recorded in the run itself, not "
             "filed and forgotten.")]):
        card(s, X3[i], 2.05, W3, 2.85, "REFUSED", RED, h, b, bsize=9.5)
    _rect(s, 0.55, 5.20, 12.23, 1.30, INK, LINE)
    _rect(s, 0.55, 5.20, 12.23, 0.06, CYAN, None)
    _tb(s, 0.80, 5.42, 11.70, 0.95,
        "We are also willing to be treated as what we are: a service provider inside your secrecy "
        "perimeter. Confidentiality undertakings, a data processing agreement and named personnel "
        "are expected, not resisted, and we will sign them before layer two begins.",
        12, BODY, TEXT, space=1.25)

    # ============================================================================== 17 OUR POSTURE ===
    s = d.slide("about us", "Where your data", " sits",
                "A security supplier that cannot answer this should not be in the building.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("LOCATION", CYAN, "Frankfurt, and only there",
             "The application, database, sessions, generated documents and logs run on "
             "infrastructure in Frankfurt with no replication outside the EU. The one named "
             "external processor is the mail gateway used to send one-time login codes."),
            ("OUR OWN BUILD", INDIGO, "Gated, not asserted",
             "Every release passes a fixed set of deterministic checks and an adversarial review "
             "by four independent models before it reaches production. Dependency scanning fails "
             "the build on critical findings rather than reporting them."),
            ("TRANSPARENCY", GREEN, "Published, not promised",
             "We publish a software bill of materials and a coordinated vulnerability disclosure "
             "policy, and the security logs of our own platform are archived off the machine that "
             "produces them.")]):
        card(s, X3[i], 2.05, W3, 2.85, k, kc, h, b, bsize=9.5)
    for i, (v, lab) in enumerate([("42", "release gates\nbefore production"),
                                  ("4", "model vendors\nreview every release"),
                                  ("388", "automated tests\nin the suite"),
                                  ("SBOM", "published\nper the German standard"),
                                  ("CVD", "disclosure policy\npublished")]):
        stat(s, 0.55 + i * 2.49, 5.25, 2.29, v, lab)

    # ==================================================================================== 18 CLOSE ===
    s = d.slide("next step", "What happens", " next", "", FOOT)
    _rect(s, 0.55, 2.05, 12.23, 1.95, INK, LINE)
    _rect(s, 0.55, 2.05, 12.23, 0.06, CYAN, None)
    _tb(s, 0.85, 2.35, 11.60, 1.45,
        "Confirm the scope in writing and we will run the external assessment on the firm's own "
        "name this week. You will hold four documents and an evidence log before anything is "
        "signed, bought or installed, and you will know by then whether the rest of this deck is "
        "worth reading twice.", 15, WHITE, TEXT, space=1.28)
    for i, (v, lab, col) in enumerate([
            ("THIS WEEK", "scope confirmed\nassessment run", CYAN),
            ("WEEK 2", "authorisation\nsimulation scoped", INDIGO),
            ("WEEK 4", "combined report\nand workshop", VIOLET),
            ("THEN", "the loop, monthly\nwith dated proof", GREEN)]):
        x = 0.55 + i * 3.10
        _rect(s, x, 4.30, 2.88, 1.70, INK, LINE)
        _rect(s, x, 4.30, 2.88, 0.06, col, None)
        _tb(s, x + 0.18, 4.55, 2.52, 0.38, v, 16, col, DISPLAY, True)
        _tb(s, x + 0.18, 5.02, 2.52, 0.85, lab, 10, BODY, TEXT, space=1.2)
    _tb(s, 0.55, 6.25, 12.23, 0.30,
        "feranicus@s4biz.io  ·  cybergod.ai  ·  this document is a commercial proposal and not "
        "legal advice", 9.5, MUTED, MONO)

    d.save(out)
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--template",
                    default=os.path.join(here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=os.path.join(here, "S4biz_Cybergod_Legal_Proposal.pptx"))
    ap.add_argument("--firm", default="law firms")
    a = ap.parse_args()
    if not os.path.exists(a.template):
        raise SystemExit("[X] template not found: %s" % a.template)
    print("built:", build(a.template, a.out, a.firm))


if __name__ == "__main__":
    main()
