#!/usr/bin/env python3
"""build_finance_proposal_deck.py — proposal to an ACCOUNTING, AUDIT or TAX firm. Cyan-led.

    python marketing/build_finance_proposal_deck.py [--out PATH] [--template PATH] [--firm NAME]

NOT A FIND-AND-REPLACE OF THE LEGAL DECK. The structure is deliberately the same because it works,
but the argument is different in four places, and those four are the reason this deck exists:

  1. A law firm holds secrets. AN ACCOUNTING PRACTICE HOLDS SECRETS AND CAN MOVE MONEY. Payroll
     runs, payment files and banking mandates make it an execution channel, not only a data
     target. That single fact reorders the whole risk model.
  2. THE ATTACK IS EMAIL, not ransomware. Payment redirection against a firm that clients trust to
     send instructions is the crown-jewel attack in this sector, and sender authentication is the
     control that stops it. We already measure that from DNS with no packets, so it is a real
     capability and not a promise.
  3. THE CALENDAR IS PUBLISHED. Year-end close and filing deadlines are a known window in which
     the practice is overloaded and least able to respond. Testing has to be scheduled around it,
     and the deck says so rather than pretending every week is equal.
  4. AUDIT WORK IS PRICE-SENSITIVE BEFORE PUBLICATION. That is a different category of exposure
     from client confidentiality and it belongs on its own line.

HONESTY RULES, same as the legal deck and for the same reason:
  * Peer evidence is real, from an assessment we ran, and anonymised. No client is named.
  * Statutes are cited so the reader can check them. Nothing is characterised as legal advice.
  * List prices are the real ones. Simulation and stack are marked scoped, not invented.
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
from deck_chrome import W3, W4, X3, X4, guarded  # noqa: E402  — shared guards and geometry


def build(template, out, firm):
    d = guarded(Deck(template), tail=CYAN)
    FOOT = "S4biz Group · Cybergod LLC · proposal · confidential · not legal or tax advice"

    # ================================================================================ 01 TITLE ===
    s = d.slide("proposal · %s · external, internal and managed" % firm,
                [("YOU DO NOT ONLY", WHITE), ("HOLD THE DATA.", WHITE),
                 ("YOU MOVE THE MONEY.", CYAN)],
                footer=FOOT, hero=True)
    _tb(s, 0.55, 1.35, 9.80, 0.32,
        "> assess --outside 0-packets  |  bas --inside payment-path  |  close --managed",
        12, CYAN, MONO)
    _tb(s, 0.57, 4.45, 11.60, 0.45,
        "A practice that runs payroll and payment files is not only a data target. It is an "
        "execution channel. This is what the internet can already see, what an intruder would "
        "reach, and how both get closed.", 12, BODY, TEXT)
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

    # ============================================================================== 02 THE TARGET ===
    s = d.slide("the target profile", "Why this practice is", " different",
                "Three things a general business does not have, all at once.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("EXECUTION", RED, "You can move money",
             "Payroll runs, payment files and banking mandates. A compromise here is not only a "
             "disclosure event, it is a funds transfer event, and the money leaves before anybody "
             "reads a log."),
            ("CONCENTRATION", CYAN, "Every client's books",
             "Ledgers, margins, salaries and tax positions for the whole client base in one "
             "estate, plus the personal data of every employee of every client."),
            ("TIMING", INDIGO, "Your calendar is public",
             "Year-end close and filing deadlines are known to everyone, including an attacker. "
             "They are the weeks when the practice is fully loaded, changes are frozen and nobody "
             "has capacity to investigate an anomaly.")]):
        card(s, X3[i], 2.05, W3, 2.55, k, kc, h, b)
    _rect(s, 0.55, 4.90, 12.23, 1.60, INK, LINE)
    _rect(s, 0.55, 4.90, 12.23, 0.06, RED, None)
    _tb(s, 0.80, 5.12, 11.70, 0.30, "AND ONE MORE, FOR AUDIT WORK", 9, RED, MONO, True)
    _tb(s, 0.80, 5.45, 11.70, 0.90,
        "Draft figures and working papers are price-sensitive before publication. That is a "
        "different category of exposure from client confidentiality, it attracts a different "
        "regulator, and it has a hard date attached to it in every engagement.",
        12.5, BODY, TEXT, space=1.25)

    # ============================================================================ 03 THE OBLIGATION ===
    s = d.slide("the obligation", "The exposure is", " criminal",
                "Provisions cited so the firm can check them. Nothing here is legal or tax advice.",
                FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("PROFESSIONAL SECRECY", RED, "Named in the statute",
             "Section 203 of the German Criminal Code names tax advisers, tax agents, auditors and "
             "sworn accountants explicitly. The duty is personal, and the professional codes for "
             "each of those roles impose their own confidentiality obligations on top."),
            ("SERVICE PROVIDERS", AMBER, "It follows the data",
             "The same duty extends to the people and firms brought in to support the practice. "
             "Your IT supplier, your hosting and anyone administering the systems that hold client "
             "books sit inside the secrecy perimeter, not outside it."),
            ("DATA PROTECTION", CYAN, "Article 32 and 33",
             "Appropriate technical measures, and notification within seventy two hours. Payroll "
             "processing puts the personal data of every client's workforce in scope, which "
             "multiplies the notification population well beyond the firm's own headcount.")]):
        card(s, X3[i], 2.05, W3, 2.85, k, kc, h, b, bsize=9.5)
    _tb(s, 0.55, 5.20, 12.23, 1.20,
        "This is on slide three rather than in an appendix because it sets the buying criteria. "
        "After an incident the question is whether appropriate measures were in place on the day, "
        "and it is asked by somebody hostile, in writing, about a date that has already passed.",
        11, MUTED, TEXT, space=1.25)

    # =========================================================================== 04 DORA PUSHDOWN ===
    s = d.slide("the commercial driver", "Your clients are regulated.",
                " You get audited",
                "Which is why this arrives as a contract clause, not as a regulator's letter.",
                FOOT)
    card(s, 0.55, 2.05, 6.00, 2.35, "THE MECHANISM", CYAN, "Third-party risk, pushed down",
         "Financial-sector clients operate under a digital resilience regime that obliges them to "
         "manage the risk of their information and communication technology suppliers, and to "
         "hold prescribed contractual terms with them. A practice that keeps their books is such "
         "a supplier. The obligation is theirs. The questionnaire is yours.")
    card(s, 6.78, 2.05, 6.00, 2.35, "WHAT IT ASKS FOR", INDIGO, "Evidence, not assurances",
         "Audit and access rights, incident cooperation with defined timescales, an exit plan, and "
         "a register entry describing exactly what you do and how it is tested. A policy document "
         "does not satisfy any of those. Dated output from a repeated test does.")
    _rect(s, 0.55, 4.70, 12.23, 1.85, INK, LINE)
    _rect(s, 0.55, 4.70, 12.23, 0.06, GREEN, None)
    _tb(s, 0.80, 4.92, 11.70, 0.30, "TURN IT AROUND", 9, GREEN, MONO, True)
    _tb(s, 0.80, 5.25, 11.70, 1.15,
        "Most practices treat the questionnaire as an annual irritation answered from memory. A "
        "firm that answers it on the day it arrives, with dated evidence and a named test "
        "schedule, is materially easier to keep on a client's approved supplier list. The same "
        "three layers that reduce the risk produce that paperwork as a by-product.",
        12.5, BODY, TEXT, space=1.25)

    # =========================================================================== 05 REAL EVIDENCE ===
    s = d.slide("evidence", "What we found at a", " peer group",
                "A German advisory group with transaction and leasing arms. No contact, no access, "
                "no packets.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("FINDING", RED, "The mail cluster",
             "The group's mail infrastructure was presenting an expired certificate across seven "
             "separate ports. For a practice whose clients act on emailed instructions, the mail "
             "path is the control surface, and it had been unattended long enough to lapse."),
            ("FINDING", AMBER, "The other companies",
             "The operating subsidiaries traded under names with no textual relationship to the "
             "parent. Nobody had ever assessed them together, so the group had never seen its own "
             "estate in one picture. The best findings were in the entities nobody thought to look at."),
            ("METHOD", CYAN, "Their own published data",
             "Certificate logs, routing records, DNS and the group structure page on the firm's "
             "own website. Everything came from records the group publishes itself, which is "
             "exactly the route an attacker takes.")]):
        card(s, X3[i], 2.05, W3, 2.85, k, kc, h, b, bsize=9.5)
    _rect(s, 0.55, 5.20, 12.23, 1.25, INK, LINE)
    _tb(s, 0.80, 5.42, 11.70, 0.95,
        "The group is not named here and will not be named to anyone else, which is the same "
        "answer you will get about your own assessment. The point is that none of it took "
        "cleverness. It took looking, at all of the entities rather than the main one.",
        12, BODY, TEXT, space=1.25)

    # ============================================================================ 06 THREE LAYERS ===
    s = d.slide("the proposal", "Outside, inside,", " closed",
                "Three layers. Each answers a question the other two cannot.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("LAYER 1 · CYBERGOD", CYAN, "What can be seen",
             "The external estate of every entity in the group as an attacker enumerates it, with "
             "no packets sent to you. Findings, priced risk, threat profile and a full evidence "
             "log, in five to seven minutes, repeatable on a schedule."),
            ("LAYER 2 · BAS", INDIGO, "How far they get",
             "Attack simulation inside the network. Once a credential is phished or a laptop is "
             "compromised, does it reach the payment environment, the payroll system and the tax "
             "platform, and how quickly."),
            ("LAYER 3 · THE STACK", GREEN, "Close it, keep it closed",
             "Sender authentication first, then access control, segmentation of the payment path "
             "and verified recovery. Then the outside view runs again and proves the finding is "
             "gone.")]):
        card(s, X3[i], 2.05, W3, 2.70, k, kc, h, b)
    _rect(s, 0.55, 5.05, 12.23, 1.45, INK, LINE)
    _rect(s, 0.55, 5.05, 12.23, 0.06, CYAN, None)
    _tb(s, 0.80, 5.30, 11.70, 1.00,
        "Layer one can start this week with nothing signed beyond a scope confirmation, and it "
        "covers every entity in the group, not only the trading name. Layer two needs a written "
        "authorisation and a window that avoids your close and filing peaks.",
        12.5, BODY, TEXT, space=1.25)

    # ====================================================================== 07 LAYER 1 CYBERGOD ===
    s = d.slide("layer 1 · cybergod.ai", "The outside view in", " minutes",
                "One input: the firm's name. Four documents and a run log out.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("EXPOSURE", CYAN, "What is reachable",
             "Every externally visible weakness across all group entities, ranked, each anchored "
             "to the evidence that produced it so it can be verified rather than believed."),
            ("COST", INDIGO, "Priced in euros",
             "Each finding converted to an annual loss figure using a recognised quantitative "
             "method, which is the language a partner group already argues in."),
            ("THREAT", VIOLET, "Who is likely",
             "Named actor groups with sources and confidence grading, and why a practice of this "
             "size and client base fits what they select for."),
            ("RECORD", GREEN, "The methodology log",
             "A customer-safe record of what was queried and what was deliberately refused. It is "
             "the document that survives a client's due diligence.")]):
        card(s, X4[i], 2.05, W4, 2.60, k, kc, h, b, bsize=9.5)
    for i, (v, lab) in enumerate([("0", "packets sent to\nthe firm's systems"),
                                  ("3", "document languages\nEN, DE, RU"),
                                  ("33", "detector classes\nnot a generic scan"),
                                  ("5", "artifacts per run\nincluding the log"),
                                  ("EU", "processing stays\nin Frankfurt")]):
        stat(s, 0.55 + i * 2.49, 5.00, 2.29, v, lab)

    # ======================================================================== 08 EMAIL / PAYMENT ===
    s = d.slide("layer 1 · the one that pays for itself", "Anyone can send as",
                " your firm",
                "Payment redirection is the attack that actually happens to this profession.",
                FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("THE ATTACK", RED, "A trusted instruction",
             "The client receives a message that appears to come from the practice, with changed "
             "bank details on a real invoice or payroll file. It is believed because the sender "
             "looks correct, and by the time anyone telephones, the payment has settled."),
            ("THE CONTROL", CYAN, "Three DNS records",
             "Sender policy, message signing and an enforcing policy that tells the world to "
             "reject anything that fails. Published correctly, the forged message does not arrive. "
             "Published loosely, which is the common case, it arrives looking legitimate."),
            ("WHAT WE DO", GREEN, "Measured, not assumed",
             "The assessment reads those records for every domain the group owns, including the "
             "ones nobody remembers registering, and reports which are enforcing, which are "
             "advisory only and which are absent. No packets, no access, no cost to check.")]):
        card(s, X3[i], 2.05, W3, 2.95, k, kc, h, b, bsize=9.5)
    _rect(s, 0.55, 5.30, 12.23, 1.20, INK, LINE)
    _rect(s, 0.55, 5.30, 12.23, 0.06, AMBER, None)
    _tb(s, 0.80, 5.52, 11.70, 0.90,
        "Firms usually believe this is already handled because a record exists. Existing and "
        "enforcing are different things, and only one of them stops the message. That distinction "
        "is the entire finding, and it is visible from outside in seconds.",
        12, BODY, TEXT, space=1.25)

    # ======================================================================== 09 WHY ZERO TOUCH ===
    s = d.slide("the objection, answered", "Why zero touch matters",
                " here",
                "The slide that matters to a managing partner more than any feature.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("EVALUATION", CYAN, "Try it with nothing signed",
             "Because the assessment reads only public records, evaluating us needs no network "
             "access, no credentials, no installed agent and no data processing agreement. There "
             "is no confidentiality exposure in finding out whether it is any good."),
            ("CLIENT DATA", INDIGO, "No books are opened",
             "We do not see ledgers, payroll files, tax returns or mail content at any point in "
             "layer one. The inputs are certificate logs, routing records and DNS entries the "
             "firm already publishes to the world."),
            ("PROOF", GREEN, "It is checkable",
             "The methodology log lists every query. A disputed finding can be reproduced by your "
             "own IT provider without our involvement, which is what makes it usable in a client "
             "due-diligence pack.")]):
        card(s, X3[i], 2.05, W3, 2.85, k, kc, h, b, bsize=9.5)
    _rect(s, 0.55, 5.20, 12.23, 1.30, INK, LINE)
    _rect(s, 0.55, 5.20, 12.23, 0.06, AMBER, None)
    _tb(s, 0.80, 5.42, 11.70, 0.95,
        "Stated plainly because it is the limit of layer one: public records cannot tell you what "
        "an intruder would reach once inside, and for this profession the thing that matters is "
        "inside. That needs layer two, which is authorised, scheduled and scoped in writing.",
        11.5, BODY, TEXT, space=1.25)

    # ============================================================================== 10 BAS BASICS ===
    s = d.slide("layer 2 · bas", "A yearly test is a", " snapshot",
                "The estate changes every week. The test does not.", FOOT)
    card(s, 0.55, 2.05, 6.00, 2.55, "TODAY", MUTED, "Annual penetration test",
         "A skilled team, a fixed window, a report. Genuinely useful, and also a photograph. It "
         "reflects the estate on the week it ran, it is expensive enough to happen once a year, "
         "and every change made in the following eleven months is untested until the next one.")
    card(s, 6.78, 2.05, 6.00, 2.55, "INSTEAD", CYAN, "Continuous simulation",
         "Automated attack simulation on a schedule against the live estate, using real techniques "
         "mapped to the public attack framework. It does not replace human testers for creative "
         "work. It replaces the eleven months in which nothing is tested at all, and it produces "
         "dated evidence every time it runs.")
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

    # ========================================================================= 11 THE ONE QUESTION ===
    s = d.slide("layer 2 · what it answers", "Does a laptop reach the",
                " payment run?",
                "For this profession that is the whole question, and almost nobody can answer it.",
                FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("SEGMENTATION", CYAN, "Prove the wall exists",
             "Simulation starts from an assumed compromise on an ordinary workstation and attempts "
             "to move. If it reaches the payment environment, the payroll system or the tax "
             "platform, you learn it from us and not from a reconciliation."),
            ("CREDENTIALS", INDIGO, "Reused and cached",
             "Shared local administrator passwords, cached domain credentials and service accounts "
             "with more rights than anyone remembers granting. These turn one compromised laptop "
             "into the whole practice."),
            ("APPROVALS", VIOLET, "Does the second person help",
             "Dual approval on a payment only works if the two approvers cannot be reached from "
             "the same compromised session. That is a technical question about segmentation, and "
             "it is testable rather than assumed.")]):
        card(s, X3[i], 2.05, W3, 2.85, k, kc, h, b, bsize=9.5)
    _rect(s, 0.55, 5.20, 12.23, 1.30, INK, LINE)
    _tb(s, 0.80, 5.42, 11.70, 0.95,
        "The output is not a score. It is a per-machine list of what moved where and the specific "
        "change that stops it: this rule, this account, this segment. That is a work order, and "
        "it makes the next run measurably better than the last.", 12, BODY, TEXT, space=1.25)

    # ============================================================================ 12 OPEN SOURCE ===
    s = d.slide("layer 2 · the engine", "Open source, and you can",
                " read it",
                "A practice built on confidentiality should not have to take this on trust.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("INSPECTABLE", CYAN, "Published source",
             "The simulation engine is open source under a public licence. Your own IT advisers "
             "can read exactly what it does before it runs inside your network, which is not "
             "possible with a closed commercial agent."),
            ("NO LOCK-IN", INDIGO, "No licence dependency",
             "No per-seat licence and no vendor whose commercial decisions can strand the "
             "capability. The approach is deliberately tool-agnostic: the engine can be replaced "
             "without changing the service around it."),
            ("SAFE BY DESIGN", GREEN, "Simulation, not payload",
             "The technique is exercised and reachability is recorded. Nothing is encrypted, "
             "exfiltrated or destroyed, and no live payment file is ever touched. Scope, timing "
             "and stop conditions are agreed in writing first."),
            ("MANAGED", VIOLET, "We run it, you read it",
             "Deployment, scheduling, tuning and interpretation are ours. The firm receives "
             "findings and work orders, not another console to staff.")]):
        card(s, X4[i], 2.05, W4, 2.90, k, kc, h, b, bsize=9.5)
    _tb(s, 0.55, 5.25, 12.23, 1.10,
        "One honest note for whoever reviews this technically: the specific engine matters less "
        "than the discipline around it. We name the tool and the version in the statement of "
        "work, and if the project behind it changes direction we replace it and say so.",
        11, MUTED, TEXT, space=1.25)

    # ================================================================================ 13 THE STACK ===
    s = d.slide("layer 3 · the stack", "Closing what the two views",
                " find", "Scoped from findings, not sold from a catalogue.", FOOT)
    rows = [("MAIL", "Enforcing sender authentication so nobody can invoice your clients in your "
             "name. First, because it is the attack that actually happens here.", CYAN),
            ("IDENTITY", "Multi-factor coverage on payment approvers, privileged account cleanup "
             "and removal of the shared local passwords the simulation finds.", CYAN),
            ("ACCESS", "Zero-trust remote access replacing flat VPN reach, so a stolen credential "
             "opens one application rather than the network.", INDIGO),
            ("SEGMENTATION", "Separation of the payment, payroll and tax-platform environment from "
             "general office traffic, then re-tested rather than assumed.", INDIGO),
            ("PERIMETER", "Managed firewall and rule review, driven by what the simulation "
             "actually walked through rather than by a template.", VIOLET),
            ("RECOVERY", "Backup verified by restore, including the archive, because an extortion "
             "threat to publish defeats a backup strategy and encryption does not.", GREEN)]
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

    # ============================================================================== 14 FLYWHEEL ===
    s = d.slide("how it compounds", "Find, prove, close,", " verify",
                "The loop is the product. A single report is not.", FOOT)
    for i, (n, k, kc, h, b) in enumerate([
            ("01", "FIND", CYAN, "Outside view",
             "External assessment across every group entity, producing ranked findings with "
             "evidence anchors and a priced annual loss figure."),
            ("02", "PROVE", INDIGO, "Inside view",
             "Simulation shows which findings actually reach the payment path and which are "
             "noise, so remediation money goes to the right place."),
            ("03", "CLOSE", GREEN, "Managed change",
             "Only the changes the first two steps justified, delivered as managed service or "
             "handed to the firm's existing IT provider."),
            ("04", "VERIFY", VIOLET, "Re-run and date it",
             "Both views run again. The finding is shown closed, with a date. That artifact "
             "answers the client's supplier questionnaire.")]):
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
        "produces something the firm can hand to a client, an insurer or a professional body.",
        12.5, BODY, TEXT, space=1.25)

    # ============================================================================== 15 ENGAGEMENT ===
    s = d.slide("delivery", "How the engagement", " runs",
                "Scheduled around your close and filing peaks, not through them.", FOOT)
    for i, (q, col, head, items) in enumerate([
            ("WEEK 1", CYAN, "Outside", ["Scope confirmed in writing",
                                         "All group entities listed",
                                         "External assessment run",
                                         "Mail posture reported"]),
            ("WEEK 2-3", INDIGO, "Inside", ["Authorisation signed",
                                            "Window avoids close",
                                            "Simulation deployed",
                                            "Payment path mapped"]),
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

    # ============================================================================ 16 COMMERCIALS ===
    s = d.slide("commercials", "What it", " costs",
                "List prices. Volume and partner terms are set in the agreement.", FOOT)
    rows = [("Single assessment", "one entity, one point in time, four documents",
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
        "A group is priced per entity assessed. The two scoped lines are quoted after week one, "
        "because quoting them before means guessing what is wrong.", 9, MUTED, MONO)

    # =========================================================================== 17 WHAT WE WON'T ===
    s = d.slide("boundaries", "What we will not", " touch",
                "For this audience the refusals are more persuasive than the features.", FOOT)
    for i, (h, b) in enumerate([
            ("Client books or payments",
             "No ledgers, no payroll files, no tax data, no mail content. The simulation records "
             "that it could reach a system. It does not read what is in it, and it never "
             "interacts with a live payment run."),
            ("Anything offensive",
             "No action against a third party, no scanning of an attacker, no exploitation outside "
             "the agreed scope and window. Simulation stops at proving the path exists."),
            ("Your busy season",
             "No inside testing during close or filing peaks unless you specifically ask for it. "
             "The window is named in the authorisation, along with the stop conditions and who "
             "can invoke them.")]):
        card(s, X3[i], 2.05, W3, 2.85, "REFUSED", RED, h, b, bsize=9.5)
    _rect(s, 0.55, 5.20, 12.23, 1.30, INK, LINE)
    _rect(s, 0.55, 5.20, 12.23, 0.06, CYAN, None)
    _tb(s, 0.80, 5.42, 11.70, 0.95,
        "We are also willing to be treated as what we are: a service provider inside your secrecy "
        "perimeter. Confidentiality undertakings, a data processing agreement and named personnel "
        "are expected rather than resisted, and signed before layer two begins.",
        12, BODY, TEXT, space=1.25)

    # ============================================================================== 18 OUR POSTURE ===
    s = d.slide("about us", "Where your data", " sits",
                "A security supplier that cannot answer this should not be in the building.", FOOT)
    for i, (k, kc, h, b) in enumerate([
            ("LOCATION", CYAN, "Frankfurt, and only there",
             "The application, database, sessions, generated documents and logs run on "
             "infrastructure in Frankfurt with no replication outside the EU. The one named "
             "external processor is the mail gateway that sends one-time login codes."),
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

    # ==================================================================================== 19 CLOSE ===
    s = d.slide("next step", "What happens", " next", "", FOOT)
    _rect(s, 0.55, 2.05, 12.23, 1.95, INK, LINE)
    _rect(s, 0.55, 2.05, 12.23, 0.06, CYAN, None)
    _tb(s, 0.85, 2.35, 11.60, 1.45,
        "Confirm the scope in writing and we will run the external assessment on every entity in "
        "the group this week, including the mail posture that decides whether somebody can invoice "
        "your clients in your name. You will hold four documents and an evidence log before "
        "anything is signed, bought or installed.", 15, WHITE, TEXT, space=1.28)
    for i, (v, lab, col) in enumerate([
            ("THIS WEEK", "scope confirmed\nassessment run", CYAN),
            ("WEEK 2", "authorisation\nwindow agreed", INDIGO),
            ("WEEK 4", "combined report\nand workshop", VIOLET),
            ("THEN", "the loop, monthly\nwith dated proof", GREEN)]):
        x = 0.55 + i * 3.10
        _rect(s, x, 4.30, 2.88, 1.70, INK, LINE)
        _rect(s, x, 4.30, 2.88, 0.06, col, None)
        _tb(s, x + 0.18, 4.55, 2.52, 0.38, v, 16, col, DISPLAY, True)
        _tb(s, x + 0.18, 5.02, 2.52, 0.85, lab, 10, BODY, TEXT, space=1.2)
    _tb(s, 0.55, 6.25, 12.23, 0.30,
        "feranicus@s4biz.io  ·  cybergod.ai  ·  a commercial proposal, not legal or tax advice",
        9.5, MUTED, MONO)

    d.save(out)
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--template",
                    default=os.path.join(here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--out", default=os.path.join(here, "S4biz_Cybergod_Accounting_Proposal.pptx"))
    ap.add_argument("--firm", default="accounting, audit and tax practices")
    a = ap.parse_args()
    if not os.path.exists(a.template):
        raise SystemExit("[X] template not found: %s" % a.template)
    print("built:", build(a.template, a.out, a.firm))


if __name__ == "__main__":
    main()
