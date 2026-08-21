# -*- coding: utf-8 -*-
"""01 - Reseller framework agreement, objectale GmbH (CH) -> byon gmbh (DE).

THREE THINGS IN HERE ARE NOT IN THE HEAD DOCUMENTS, and they are the reason this is a new draft
rather than a search-and-replace of the operator's Master Partner Agreement.

1. THE CHAIN OF RIGHTS (clause 3). objectale is not the platform owner. It can grant byon only what
   the operator granted objectale, and if that head agreement ends, everything downstream ends with
   it. A reseller agreement that stays silent on this promises rights the seller may not hold, and
   the first person to discover it is byon's end customer.

2. THE FLOW-DOWN (clause 6 and Schedule 4). byon contracts with its own customers in its own name.
   objectale has no contract with them and cannot enforce anything against them directly, so the
   restrictions that protect the platform (passive only, no penetration test, no benchmarking) have
   to arrive in byon's own customer terms or they do not exist at all.

3. GERMAN LAW CHANGES THE LIABILITY AND DEFECT ARCHITECTURE. The parties chose German law and
   Frankfurt am Main. That means Sections 305 to 310 BGB apply to any pre-formulated term, so a
   flat cap or a broad exclusion is void rather than merely aggressive. Clause 17 uses the
   structure German courts accept: unlimited for intent and gross negligence, limited to the
   foreseeable contract-typical damage for breach of a cardinal duty, and untouched for the Product
   Liability Act and for injury to life, body or health. Clause 16 excludes the strict liability
   for initial defects under Section 536a(1) BGB, because German courts classify software provided
   as a service as a lease and that liability applies without fault.
"""
from common import BYON, OBJECTALE, DATE_DE, DATE_EN, LIST_PRICES, LIST_PRICES_DE, NOTE_DE, \
    NOTE_EN, OPERATOR, PLATFORM, VERSION

TITLE_EN = "RESELLER FRAMEWORK AGREEMENT"
TITLE_DE = "WIEDERVERKÄUFER-RAHMENVERTRAG"

EN = [
    ("h1", TITLE_EN),
    ("meta", "%s and %s  ·  Version %s  ·  %s  ·  German law, Frankfurt am Main"
     % (OBJECTALE["name"], BYON["name"], VERSION, DATE_EN)),

    ("p", "This Reseller Framework Agreement (the \"Agreement\") takes effect on [effective date] "
          "(the \"Effective Date\") between:"),
    ("p", "%s, a limited liability company incorporated in Switzerland, %s, registered under %s "
          "(\"objectale\"); and" % (OBJECTALE["name"], OBJECTALE["addr"], OBJECTALE["reg"])),
    ("p", "%s, a limited liability company incorporated in Germany, %s, registered with the %s, "
          "VAT identification number %s, represented by its managing directors %s (\"byon\"), an "
          "operating company of %s."
     % (BYON["name"], BYON["addr"], BYON["reg"], BYON["vat"], BYON["mgmt"], BYON["group"])),
    ("p", "Each a \"party\" and together the \"parties\"."),
    ("note", NOTE_EN),

    ("h2", "Background"),
    ("p", "A. objectale is a boutique consultancy for telecommunications and IT infrastructure and "
          "is an authorised partner for %s, an external cyber-risk and EU regulatory-compliance "
          "assessment platform operated by %s (the \"Operator\")." % (PLATFORM, OPERATOR)),
    ("p", "B. The platform has two modules. The assess module answers what of an organisation is "
          "exposed to the internet, what an incident would cost and who would plausibly attack it. "
          "The compliance module grades an organisation against the regulatory regimes of a chosen "
          "jurisdiction. Both produce presentation decks and an animated HTML report."),
    ("p", "C. The platform reads public sources only. It is not a penetration test. It performs no "
          "port scanning, no vulnerability probing and no authentication attempt against the "
          "organisation being assessed, and it sends no packet to that organisation."),
    ("p", "D. byon is a managed service provider for IT services and unified communications and "
          "wishes to resell the platform to its own customers, in its own name and for its own "
          "account, alongside its own managed services."),
    ("p", "E. The parties wish to record the terms on which objectale supplies and byon resells."),

    ("h2", "1. Interpretation"),
    ("num", "1.1", "\"Include\" and \"including\" are to be read without limitation."),
    ("num", "1.2", "Clause headings are for convenience and do not affect interpretation."),
    ("num", "1.3", "A reference to a statute is a reference to it as amended or re-enacted."),
    ("num", "1.4", "A reference to writing includes e-mail to the addresses in Schedule 1. Where "
                   "this Agreement requires written form for a variation, that means text form "
                   "within the meaning of Section 126b BGB unless stated otherwise."),
    ("num", "1.5", "The Schedules form part of this Agreement. Where a Schedule conflicts with the "
                   "clauses, the clauses prevail unless the Schedule says expressly that it varies "
                   "a numbered clause."),

    ("h2", "2. Structure of the Agreement"),
    ("num", "2.1", "This Agreement is the framework. Individual transactions are agreed by Order "
                   "Form in the form of Schedule 3, and each Order Form incorporates this "
                   "Agreement."),
    ("num", "2.2", "The following documents may supplement this Agreement and, where signed, form "
                   "part of it: the White-Label / OEM Agreement, the Service Level Agreement and "
                   "the Data Processing Agreement."),
    ("num", "2.3", "Order of precedence, highest first: a signed Order Form for the transaction it "
                   "governs; the Data Processing Agreement for data-protection matters; the "
                   "White-Label / OEM Agreement for white-label matters; the Service Level "
                   "Agreement for service levels; this Agreement; the Schedules."),
    ("num", "2.4", "byon's general terms and conditions do not apply, including where objectale "
                   "does not object to them and performs without reservation."),

    ("h2", "3. Chain of rights"),
    ("p", "This clause is the honest description of what objectale is able to sell. It is not "
          "boilerplate and the parties have read it."),
    ("num", "3.1", "objectale's rights in the platform are derived. objectale holds a partner "
                   "agreement with the Operator (the \"Head Agreement\") and grants byon rights "
                   "under this Agreement only to the extent the Head Agreement permits objectale "
                   "to grant them."),
    ("num", "3.2", "objectale warrants that on the Effective Date the Head Agreement is in force "
                   "and permits objectale to appoint resellers on the terms of this Agreement, and "
                   "that objectale will not agree any variation of the Head Agreement that reduces "
                   "the rights granted to byon during the term without byon's prior written "
                   "consent."),
    ("num", "3.3", "objectale will notify byon in writing without undue delay if the Head "
                   "Agreement is terminated, suspended or materially varied in a way that affects "
                   "byon, and in any event within five business days of objectale becoming aware."),
    ("num", "3.4", "If the Head Agreement ends for any reason, objectale will use its best efforts "
                   "to procure that the Operator offers byon a direct agreement on terms no less "
                   "favourable for the remainder of the then-current term of byon's own customer "
                   "contracts. Where the Operator does not do so, clause 20.4 applies."),
    ("num", "3.5", "byon acknowledges that objectale does not own the platform, does not control "
                   "its roadmap and cannot grant rights in the underlying software beyond the "
                   "rights of use described in this Agreement."),

    ("h2", "4. Appointment, territory and exclusivity"),
    ("num", "4.1", "objectale appoints byon as a non-exclusive reseller of the platform in the "
                   "Territory, and byon accepts the appointment."),
    ("num", "4.2", "The Territory is [Germany, Austria and Switzerland] unless Schedule 1 states "
                   "otherwise. byon may serve a customer headquartered in the Territory in respect "
                   "of that customer's group companies outside the Territory."),
    ("num", "4.3", "The appointment is non-exclusive. objectale may appoint other resellers and "
                   "may sell directly, subject to clause 4.4."),
    ("num", "4.4", "Deal registration. Where byon registers a named prospect in writing and "
                   "objectale confirms the registration, objectale will not solicit that prospect "
                   "for the platform for six months from confirmation, and will refer inbound "
                   "enquiries from that prospect to byon during that period. Confirmation is not "
                   "to be unreasonably withheld or delayed. A registration lapses if no Order Form "
                   "is placed within six months."),
    ("num", "4.5", "byon acts as an independent undertaking in its own name and for its own "
                   "account. Nothing in this Agreement creates an agency, a commercial agency "
                   "relationship within the meaning of Sections 84 ff. HGB, a partnership or a "
                   "joint venture, and byon has no authority to bind objectale or the Operator."),

    ("h2", "5. Resale to end customers"),
    ("num", "5.1", "byon may resell the platform to end customers in the Territory, in its own "
                   "name, for its own account and at prices byon determines."),
    ("num", "5.2", "byon may bundle the platform with its own managed services, its own reporting "
                   "and its own consultancy, and may present the combination as a byon service."),
    ("num", "5.3", "byon may not appoint sub-resellers without objectale's prior written consent. "
                   "Consent may be given for a named category of partner in Schedule 1, in which "
                   "case byon remains fully responsible for that partner's compliance with this "
                   "Agreement as if it were byon's own."),
    ("num", "5.4", "byon is responsible for its own customer relationships, including credit risk, "
                   "invoicing, first-line support and the performance of its own obligations. Non-"
                   "payment by an end customer does not relieve byon of its obligation to pay "
                   "objectale."),

    ("h2", "6. Minimum end-customer terms"),
    ("p", "objectale has no contract with byon's customers and cannot enforce anything against "
          "them. The protections below therefore have to appear in byon's own customer terms."),
    ("num", "6.1", "byon will contract with each end customer on terms that, as a minimum, include "
                   "the provisions in Schedule 4, and that are no less protective of objectale and "
                   "the Operator than this Agreement."),
    ("num", "6.2", "byon will procure that each end customer is told, in writing and before first "
                   "use, that the platform reads public sources only, that it is not a penetration "
                   "test and that a deliverable is an assessment and not a guarantee of security."),
    ("num", "6.3", "byon will not make any representation or warranty about the platform beyond "
                   "the documentation objectale supplies, and will not commit objectale or the "
                   "Operator to a service level, a functionality or a delivery date."),
    ("num", "6.4", "Where byon's customer is a public body, an operator of critical infrastructure "
                   "or a regulated financial institution, byon will tell objectale before the "
                   "Order Form is placed, so that any additional regulatory requirement can be "
                   "addressed before commitments are made."),
    ("num", "6.5", "byon will pass through, without material change, any restriction the Operator "
                   "notifies to objectale in respect of a third-party data source."),

    ("h2", "7. byon's obligations"),
    ("num", "7.1", "byon will use the platform, and procure that its customers use it, only for "
                   "organisations that have instructed byon, or that byon is otherwise lawfully "
                   "entitled to assess."),
    ("num", "7.2", "byon will not use the platform to assess an organisation as a pretext for "
                   "competitive intelligence, and will not publish an assessment of a third party "
                   "without that party's consent."),
    ("num", "7.3", "byon will not benchmark the platform against a competing product for "
                   "publication, decompile it, attempt to derive its source code, or use it to "
                   "build a competing service."),
    ("num", "7.4", "byon will keep credentials confidential, will not share a named user account "
                   "between individuals, and will notify objectale without undue delay of any "
                   "suspected compromise."),
    ("num", "7.5", "byon will provide first-line support to its own customers, will maintain at "
                   "least two trained contacts, and will escalate to objectale only after "
                   "first-line triage."),
    ("num", "7.6", "byon will comply with all applicable law, including export control and "
                   "sanctions law, and will not make the platform available to a person or in a "
                   "territory where that would be unlawful."),

    ("h2", "8. objectale's obligations"),
    ("num", "8.1", "objectale will make the platform available to byon in accordance with the "
                   "Service Level Agreement, subject to clause 8.4."),
    ("num", "8.2", "objectale will provide second-line support to byon's nominated contacts and "
                   "will escalate to the Operator where the cause lies in the platform."),
    ("num", "8.3", "objectale will provide reasonable enablement at no charge: onboarding for "
                   "byon's contacts, current documentation, and the materials byon needs to sell."),
    ("num", "8.4", "objectale's obligations are back-to-back. objectale does not owe byon a "
                   "service level, an update or a correction that objectale does not itself receive "
                   "under the Head Agreement. objectale will pursue the Operator diligently and "
                   "will pass on to byon whatever remedy it obtains."),
    ("num", "8.5", "objectale will notify byon of a planned change that alters a deliverable's "
                   "structure or an interface, with the notice periods in the Service Level "
                   "Agreement."),

    ("h2", "9. Access and named users"),
    ("num", "9.1", "Access is by named individual user. A named user is one natural person and may "
                   "not be shared. A named user may be replaced when a person leaves a role."),
    ("num", "9.2", "byon will keep the list of named users in Schedule 1 current and will notify "
                   "objectale within five business days of a change."),
    ("num", "9.3", "objectale may suspend an account immediately where it reasonably believes it "
                   "has been compromised or is being used in breach of clause 7, and will tell "
                   "byon the reason without undue delay."),

    ("h2", "10. Prices, ordering and payment"),
    ("num", "10.1", "Prices and byon's discount are in Schedule 2. All amounts are in euro and "
                    "exclusive of value added tax and any other applicable tax."),
    ("num", "10.2", "byon orders by Order Form. An Order Form binds when signed by both parties or "
                    "when objectale confirms it in writing."),
    ("num", "10.3", "Payment is due within 30 days of the invoice date, without deduction."),
    ("num", "10.4", "On late payment, objectale is entitled to default interest at nine percentage "
                    "points above the base rate under Section 288(2) BGB and to the lump sum under "
                    "Section 288(5) BGB. The right to claim further damage is unaffected."),
    ("num", "10.5", "byon may set off only against claims that are undisputed or that have been "
                    "finally determined by a court, and may exercise a right of retention only "
                    "where the counterclaim arises from the same contractual relationship."),
    ("num", "10.6", "objectale may adjust list prices once per contract year on three months' "
                    "written notice. byon's discount percentage is not reduced by a price "
                    "adjustment. Where an adjustment exceeds five per cent, byon may terminate the "
                    "affected Order Form with effect from the date the adjustment takes effect."),
    ("num", "10.7", "Prices already agreed in a signed Order Form apply unchanged for the term of "
                    "that Order Form."),

    ("h2", "11. Fair use and usage records"),
    ("num", "11.1", "A report subscription seat includes the number of assessment runs stated in "
                    "Schedule 2. Runs beyond that number are charged as consumed."),
    ("num", "11.2", "objectale may record the number of runs, the number of active seats and the "
                    "identity of the ordering user, for billing, capacity and abuse prevention. "
                    "Those records are the reference measurement for invoicing."),
    ("num", "11.3", "byon may raise a discrepancy in writing within 20 business days of an "
                    "invoice. The parties will resolve it in good faith before the invoice is "
                    "treated as overdue."),
    ("num", "11.4", "objectale may audit byon's compliance with this Agreement once per contract "
                    "year, on 20 business days' notice, during business hours, at objectale's "
                    "cost. Where the audit shows an underpayment above five per cent, byon bears "
                    "the reasonable cost of the audit."),

    ("h2", "12. Intellectual property"),
    ("num", "12.1", "The platform, its software, its templates, its methodology and all "
                    "intellectual property in them remain with the Operator or its licensors. "
                    "Nothing in this Agreement transfers ownership."),
    ("num", "12.2", "byon receives a non-exclusive, non-transferable right, limited to the term "
                    "and the Territory, to use the platform and to resell rights of use to end "
                    "customers on the terms of this Agreement."),
    ("num", "12.3", "A deliverable generated for an end customer, and the analysis it contains, "
                    "may be used by that customer without restriction for its own internal "
                    "purposes and in its dealings with its own auditors, insurers and regulators."),
    ("num", "12.4", "Feedback byon gives about the platform may be used by objectale and the "
                    "Operator without obligation and without payment. This does not extend to "
                    "byon's own confidential information or customer data."),

    ("h2", "13. Trade marks"),
    ("num", "13.1", "Each party grants the other a non-exclusive, revocable, royalty-free licence "
                    "to use its name and logo for the term, solely to describe the partnership, "
                    "and in accordance with any brand guidelines the owner supplies."),
    ("num", "13.2", "Neither party will register, or attempt to register, a mark or a domain that "
                    "is identical or confusingly similar to the other's."),
    ("num", "13.3", "A press release or a public case study naming the other party requires that "
                    "party's prior written approval, not to be unreasonably withheld."),
    ("num", "13.4", "On termination each party will cease use of the other's marks within 30 days, "
                    "except in archived material that is not publicly distributed."),

    ("h2", "14. Data protection"),
    ("num", "14.1", "The parties enter into the Data Processing Agreement, which governs any "
                    "processing of personal data under this Agreement and satisfies Article 28 "
                    "GDPR."),
    ("num", "14.2", "In respect of the platform, byon is the controller for its own users' account "
                    "data. objectale acts as processor for that data and the Operator acts as "
                    "sub-processor. Where byon runs an assessment on behalf of its own customer, "
                    "byon determines whether it does so as controller or as processor for that "
                    "customer, and byon is responsible for the corresponding agreement with that "
                    "customer."),
    ("num", "14.3", "The platform is hosted in Frankfurt am Main. Transfers of personal data from "
                    "the European Union to objectale in Switzerland rely on the adequacy decision "
                    "the European Commission adopted for Switzerland on 15 January 2024, so no "
                    "additional transfer safeguard is required for that leg."),
    ("num", "14.4", "Each party will notify the other without undue delay of a personal data "
                    "breach affecting the other's data, with the detail required for that party to "
                    "meet its own notification duties."),

    ("h2", "15. Confidentiality"),
    ("num", "15.1", "Each party will keep the other's confidential information secret, will use it "
                    "only for the purpose of this Agreement, and will disclose it only to those of "
                    "its personnel and advisers who need it and who are bound by equivalent "
                    "duties."),
    ("num", "15.2", "Each party will apply reasonable steps to keep that information secret within "
                    "the meaning of Section 2 no. 1(b) of the German Trade Secrets Act "
                    "(Geschäftsgeheimnisgesetz), including access control and marking."),
    ("num", "15.3", "The duty does not apply to information that is public without breach, that "
                    "the receiving party already held without a duty of confidence, that it "
                    "develops independently, or that it must disclose by law, in which case it "
                    "will tell the other party in advance where lawful."),
    ("num", "15.4", "The duty survives termination for three years. Trade secrets remain protected "
                    "for as long as they qualify as such."),
    ("num", "15.5", "Where the parties have signed a separate mutual non-disclosure agreement, "
                    "that agreement continues to apply and this clause supplements it."),

    ("h2", "16. Quality, defects and availability"),
    ("num", "16.1", "objectale provides the platform as a service. The parties agree that German "
                    "lease law applies to the provision of the platform."),
    ("num", "16.2", "The strict liability for defects existing at the beginning of the contract "
                    "under Section 536a(1) first alternative BGB is excluded. objectale is liable "
                    "for such defects only where it is at fault."),
    ("num", "16.3", "The agreed quality of the platform is that described in the documentation "
                    "current at the date of the Order Form and in the Service Level Agreement. A "
                    "public statement, an advertisement or a demonstration does not form part of "
                    "the agreed quality unless expressly confirmed in writing."),
    ("num", "16.4", "The platform reads public sources. objectale does not warrant that an "
                    "assessment identifies every exposure, that a public source is complete or "
                    "accurate, or that a deliverable is free of a finding that later proves not to "
                    "apply. objectale warrants that the platform performs materially in accordance "
                    "with the documentation."),
    ("num", "16.5", "A deliverable does not constitute legal advice, regulatory certification, an "
                    "audit opinion or an insurance assessment, and byon will not present it as "
                    "such."),
    ("num", "16.6", "Where the platform is defective, byon will notify objectale with enough "
                    "detail for the defect to be reproduced, and objectale will remedy it within "
                    "the times in the Service Level Agreement. Service credits under the Service "
                    "Level Agreement are byon's exclusive financial remedy for unavailability."),

    ("h2", "17. Liability"),
    ("p", "This clause follows the structure German courts accept for pre-formulated terms. A flat "
          "cap on all liability, or an exclusion of gross negligence, would be void under Sections "
          "307 ff. BGB and would leave objectale with no limitation at all."),
    ("num", "17.1", "Each party is liable without limitation for intent and gross negligence, for "
                    "injury to life, body or health, under the German Product Liability Act, and "
                    "where it has given a guarantee or fraudulently concealed a defect."),
    ("num", "17.2", "For simple negligence, each party is liable only where it breaches a material "
                    "contractual obligation, meaning an obligation whose performance makes the "
                    "proper performance of this Agreement possible in the first place and on whose "
                    "observance the other party regularly relies. In that case liability is "
                    "limited to the damage that is foreseeable and typical for this type of "
                    "contract."),
    ("num", "17.3", "Subject to clauses 17.1 and 17.2, aggregate liability for simple negligence "
                    "in any contract year is limited to the fees paid by byon to objectale under "
                    "this Agreement in the twelve months preceding the event giving rise to the "
                    "claim, and to [EUR 250,000] in total, whichever is lower."),
    ("num", "17.4", "Any further liability is excluded, in particular for loss of profit, loss of "
                    "anticipated savings and indirect damage, save where clause 17.1 applies."),
    ("num", "17.5", "The above limitations apply equally to the personal liability of the parties' "
                    "employees, representatives, bodies and vicarious agents."),
    ("num", "17.6", "byon is responsible for the decisions it and its customers take on the basis "
                    "of a deliverable. objectale is not liable for a security incident at an "
                    "organisation that has been assessed, whether or not the assessment identified "
                    "the vector."),
    ("num", "17.7", "The limitation period for claims for defects is one year from the statutory "
                    "commencement, save for claims under clause 17.1, for which the statutory "
                    "period applies."),

    ("h2", "18. Indemnity"),
    ("num", "18.1", "objectale will indemnify byon against third-party claims that byon's use of "
                    "the platform in accordance with this Agreement infringes an intellectual "
                    "property right, provided byon notifies objectale without undue delay, gives "
                    "objectale control of the defence and does not settle without consent."),
    ("num", "18.2", "Where such a claim is made, objectale may at its option procure the right to "
                    "continue use, modify the platform so that it no longer infringes, or "
                    "terminate the affected Order Form and refund fees paid for the unexpired "
                    "term."),
    ("num", "18.3", "byon will indemnify objectale against third-party claims arising from byon's "
                    "use of the platform in breach of clause 7, from a representation byon makes "
                    "beyond clause 6.3, or from an assessment byon runs against an organisation it "
                    "was not entitled to assess."),
    ("num", "18.4", "Clause 17 does not limit an indemnity under this clause 18."),

    ("h2", "19. Term and termination"),
    ("num", "19.1", "This Agreement runs for an initial term of 24 months from the Effective Date "
                    "and renews automatically for successive periods of 12 months unless either "
                    "party gives three months' written notice before the end of the then-current "
                    "term."),
    ("num", "19.2", "Either party may terminate for good cause without notice within the meaning "
                    "of Section 314 BGB, in particular where the other commits a material breach "
                    "and does not remedy it within 30 days of a written demand, where insolvency "
                    "proceedings are opened over the other's assets or their opening is refused "
                    "for want of assets, or where the other is subject to sanctions."),
    ("num", "19.3", "objectale may terminate for good cause where byon's use materially threatens "
                    "the security or the integrity of the platform, after giving byon the "
                    "opportunity to stop within a period appropriate to the risk."),
    ("num", "19.4", "Termination of this Agreement terminates every Order Form, unless the parties "
                    "agree otherwise in writing."),

    ("h2", "20. Consequences of termination"),
    ("num", "20.1", "On termination byon will cease to use the platform, will cease to market it, "
                    "and will not place further Order Forms."),
    ("num", "20.2", "Fees accrued to the date of termination remain payable. Where objectale "
                    "terminates for good cause, fees for the remainder of the term of each Order "
                    "Form fall due immediately."),
    ("num", "20.3", "byon may download the deliverables generated for it for 60 days after "
                    "termination. After that objectale is not obliged to retain them."),
    ("num", "20.4", "Run-off for live end customers. Where this Agreement ends other than for "
                    "byon's material breach, byon may continue to serve end customers under "
                    "contracts existing at the date of termination until those contracts expire, "
                    "for a maximum of 12 months, on the commercial terms then in force, provided "
                    "byon pays for that use and does not sign new end customers. This applies only "
                    "to the extent the Head Agreement permits it, and clause 3.4 applies where it "
                    "does not."),
    ("num", "20.5", "Clauses 12, 14, 15, 17, 18, 20, 21, 23 and 24 survive termination."),

    ("h2", "21. Non-solicitation"),
    ("num", "21.1", "During the term and for 12 months after it, neither party will actively "
                    "solicit an employee of the other who has been materially involved in the "
                    "performance of this Agreement."),
    ("num", "21.2", "This does not apply to a public job advertisement, to a response to an "
                    "unsolicited application, or where the employee approaches the other party on "
                    "their own initiative."),

    ("h2", "22. Escalation"),
    ("num", "22.1", "A dispute is escalated first to the operational contacts in Schedule 1, then "
                    "within ten business days to the commercial owners, then within a further ten "
                    "business days to a member of each party's management."),
    ("num", "22.2", "Neither party will commence proceedings before that escalation has been "
                    "completed or 30 business days have passed since the first escalation, except "
                    "for interim relief, for a claim for payment, or where a limitation period "
                    "would otherwise expire."),

    ("h2", "23. Final provisions"),
    ("num", "23.1", "Variations of this Agreement, including of this clause, require text form. "
                    "There are no oral side agreements."),
    ("num", "23.2", "Neither party may assign this Agreement without the other's prior written "
                    "consent, not to be unreasonably withheld. Section 354a HGB is unaffected. "
                    "Assignment to an affiliate or in connection with a transfer of the whole "
                    "business does not require consent but must be notified."),
    ("num", "23.3", "objectale may use subcontractors and remains responsible for their "
                    "performance as for its own."),
    ("num", "23.4", "Neither party is liable for a failure to perform caused by an event beyond "
                    "its reasonable control, for as long as that event continues and provided it "
                    "notifies the other and mitigates. Where the event continues for more than 60 "
                    "days, either party may terminate the affected Order Form."),
    ("num", "23.5", "If a provision is or becomes invalid, the validity of the remainder is "
                    "unaffected. The parties will replace the invalid provision with a valid one "
                    "that comes closest to its commercial purpose."),
    ("num", "23.6", "This Agreement is executed in German and in English. In the event of a "
                    "discrepancy, the [German] version prevails."),
    ("num", "23.7", "The parties may sign in counterparts and by qualified or advanced electronic "
                    "signature."),

    ("h2", "24. Governing law and jurisdiction"),
    ("num", "24.1", "This Agreement is governed by the laws of the Federal Republic of Germany, "
                    "excluding its conflict of laws rules and excluding the United Nations "
                    "Convention on Contracts for the International Sale of Goods."),
    ("num", "24.2", "The exclusive place of jurisdiction for all disputes arising out of or in "
                    "connection with this Agreement is Frankfurt am Main, Germany. Both parties "
                    "are merchants within the meaning of the German Commercial Code."),
    ("num", "24.3", "objectale remains entitled to bring proceedings at byon's general place of "
                    "jurisdiction."),

    ("pagebreak",),
    ("h2", "Schedule 1 - Party details and nominated contacts"),
    ("table", ["Item", "objectale", "byon"], [
        ["Legal entity", OBJECTALE["name"], BYON["name"]],
        ["Registered office", OBJECTALE["addr"], BYON["addr"]],
        ["Register", OBJECTALE["reg"], BYON["reg"]],
        ["VAT identification number", "[CHE-___.___.___ MWST]", BYON["vat"]],
        ["Represented by", "[name, function]", BYON["mgmt"]],
        ["Commercial contact", "[name] · [e-mail] · [telephone]", "[name] · [e-mail] · [telephone]"],
        ["Operational contact", "[name] · [e-mail] · [telephone]", "[name] · [e-mail] · [telephone]"],
        ["Notices address", OBJECTALE["mail"], BYON["mail"]],
        ["Territory", "[Germany, Austria and Switzerland]", "-"],
        ["Sub-resellers permitted", "[none / named category]", "-"],
    ]),
    ("h3", "Named users on signature"),
    ("table", ["#", "Name", "Role", "E-mail"], [
        ["1", "[name]", "[role]", "[e-mail]"],
        ["2", "[name]", "[role]", "[e-mail]"],
        ["3", "[name]", "[role]", "[e-mail]"],
        ["4", "[name]", "[role]", "[e-mail]"],
    ]),

    ("pagebreak",),
    ("h2", "Schedule 2 - Prices and discount"),
    ("p", "The list prices below are the platform list prices. byon's price is the list price less "
          "the discount recorded in this Schedule. All amounts are in euro and exclusive of VAT."),
    ("table", ["Item", "List price, EUR ex VAT"], [[a, b] for a, b in LIST_PRICES]),
    ("h3", "byon's discount"),
    ("table", ["Item", "Detail"], [
        ["Discount on list", "[__]% for the initial term"],
        ["Basis of the discount", "[volume commitment / white-label tier / other]"],
        ["Minimum commitment", "[none / __ seats / __ runs per quarter]"],
        ["Runs included per subscription seat per month", "[__]"],
        ["Price of a run beyond the included number", "[EUR __]"],
        ["Review of the discount", "Annually, on the anniversary of the Effective Date"],
    ]),
    ("note", "objectale cannot grant a discount that takes byon's price below objectale's own cost "
             "under the Head Agreement. The percentage above is agreed against that constraint and "
             "is the one commercial figure the parties should settle before signature."),

    ("pagebreak",),
    ("h2", "Schedule 3 - Form of Order Form"),
    ("table", ["Item", "Detail"], [
        ["Order Form number", "[ ]"],
        ["Effective date", "[ ]"],
        ["End customer, where the order is for a named customer", "[ ]"],
        ["Term of this Order Form", "[ ]"],
        ["Discount applied", "[ ]"],
        ["Billing frequency", "[monthly in advance / on delivery]"],
    ]),
    ("table", ["Line", "Item", "Quantity", "Unit price, EUR ex VAT", "Total per period"], [
        ["1", "Report subscription seats", "[ ]", "[ ]", "[ ]"],
        ["2", "Assessment runs beyond the included number", "As consumed", "[ ]", "[ ]"],
        ["3", "Findings review hours", "[ ]", "[ ]", "[ ]"],
        ["4", "Workshops", "[ ]", "[ ]", "[ ]"],
        ["5", "Other", "[ ]", "[ ]", "[ ]"],
    ]),

    ("pagebreak",),
    ("h2", "Schedule 4 - Minimum terms for byon's end-customer contracts"),
    ("p", "byon will include terms to at least the following effect in every end-customer contract "
          "under which the platform is supplied."),
    ("num", "A", "The customer confirms that it is entitled to instruct an assessment of each "
                 "organisation and each domain it submits."),
    ("num", "B", "The platform reads public sources only. It performs no port scanning, no "
                 "vulnerability probing and no authentication attempt, and sends no packet to the "
                 "organisation being assessed."),
    ("num", "C", "A deliverable is an assessment based on public information at a point in time. "
                 "It is not a guarantee of security, not legal advice, not a certification and not "
                 "an audit opinion."),
    ("num", "D", "The customer will not decompile the platform, will not attempt to derive its "
                 "source code, will not benchmark it for publication and will not use it to build "
                 "a competing service."),
    ("num", "E", "The customer will not publish an assessment of a third party without that third "
                 "party's consent."),
    ("num", "F", "Access is by named individual user and credentials may not be shared."),
    ("num", "G", "Intellectual property in the platform remains with its owner. The customer "
                 "receives a right of use for the term, and may use the deliverables generated for "
                 "it without restriction for its own purposes."),
    ("num", "H", "The customer's liability provisions, and any limitation of byon's liability, do "
                 "not purport to bind objectale or the Operator."),
    ("num", "I", "Where personal data is processed, the customer and byon enter into an agreement "
                 "satisfying Article 28 GDPR."),

    ("pagebreak",),
    ("h2", "Signatures"),
    ("p", "The parties sign this Agreement on the dates shown."),
    ("sig", "For %s" % OBJECTALE["name"], "For %s" % BYON["name"],
     ["Name:", "Function:", "Place:", "Date:"]),
]

DE = [
    ("h1", TITLE_DE),
    ("meta", "%s und %s  ·  Version %s  ·  %s  ·  Deutsches Recht, Frankfurt am Main"
     % (OBJECTALE["name"], BYON["name"], VERSION, DATE_DE)),

    ("p", "Dieser Wiederverkäufer-Rahmenvertrag (der \"Vertrag\") tritt am [Datum des "
          "Inkrafttretens] (das \"Datum des Inkrafttretens\") in Kraft zwischen:"),
    ("p", "%s, einer Gesellschaft mit beschränkter Haftung schweizerischen Rechts, %s, eingetragen "
          "unter %s (\"objectale\"); und"
     % (OBJECTALE["name"], OBJECTALE["addr_de"], OBJECTALE["reg"])),
    ("p", "%s, einer Gesellschaft mit beschränkter Haftung deutschen Rechts, %s, eingetragen beim "
          "%s, USt-IdNr. %s, vertreten durch die Geschäftsführer %s (\"byon\"), einem Unternehmen "
          "der %s."
     % (BYON["name"], BYON["addr_de"], BYON["reg"], BYON["vat"], BYON["mgmt"], BYON["group_de"])),
    ("p", "Jeweils eine \"Partei\" und gemeinsam die \"Parteien\"."),
    ("note", NOTE_DE),

    ("h2", "Präambel"),
    ("p", "A. objectale ist eine Boutique-Beratung für Telekommunikation und IT-Infrastruktur und "
          "autorisierter Partner für %s, eine Plattform zur Bewertung externer Cyber-Risiken und "
          "der EU-Regulierungs-Compliance, die von %s (der \"Betreiber\") betrieben wird."
     % (PLATFORM, OPERATOR)),
    ("p", "B. Die Plattform besteht aus zwei Modulen. Das Assess-Modul beantwortet, welche Teile "
          "eines Unternehmens aus dem Internet erreichbar sind, welche Kosten ein Vorfall "
          "verursachen würde und wer plausibel angreifen würde. Das Compliance-Modul bewertet ein "
          "Unternehmen gegen die Regulierungsregime einer gewählten Jurisdiktion. Beide erzeugen "
          "Präsentationen und einen animierten HTML-Bericht."),
    ("p", "C. Die Plattform wertet ausschließlich öffentliche Quellen aus. Sie ist kein "
          "Penetrationstest. Sie führt keinen Portscan, keine Schwachstellenprüfung und keinen "
          "Anmeldeversuch gegen das bewertete Unternehmen durch und sendet an dieses Unternehmen "
          "kein Datenpaket."),
    ("p", "D. byon ist Managed Service Provider für IT-Services und Unified Communications und "
          "beabsichtigt, die Plattform im eigenen Namen und auf eigene Rechnung neben den eigenen "
          "Managed Services an eigene Kunden weiterzuverkaufen."),
    ("p", "E. Die Parteien wollen die Bedingungen festhalten, zu denen objectale liefert und byon "
          "weiterverkauft."),

    ("h2", "1. Auslegung"),
    ("num", "1.1", "\"Einschließlich\" und \"insbesondere\" sind ohne Beschränkung zu verstehen."),
    ("num", "1.2", "Überschriften dienen der Übersicht und beeinflussen die Auslegung nicht."),
    ("num", "1.3", "Die Bezugnahme auf eine Vorschrift erfasst diese in ihrer jeweils geltenden "
                   "Fassung."),
    ("num", "1.4", "Die Bezugnahme auf Schriftlichkeit umfasst E-Mail an die in Anlage 1 "
                   "genannten Adressen. Soweit dieser Vertrag für eine Änderung Schriftform "
                   "verlangt, ist Textform im Sinne des § 126b BGB gemeint, sofern nichts anderes "
                   "bestimmt ist."),
    ("num", "1.5", "Die Anlagen sind Bestandteil dieses Vertrages. Bei Widersprüchen zwischen einer "
                   "Anlage und den Klauseln gehen die Klauseln vor, sofern die Anlage nicht "
                   "ausdrücklich bestimmt, dass sie eine bezifferte Klausel ändert."),

    ("h2", "2. Vertragsstruktur"),
    ("num", "2.1", "Dieser Vertrag ist der Rahmen. Einzelgeschäfte werden durch Bestellformular "
                   "nach dem Muster der Anlage 3 vereinbart; jedes Bestellformular bezieht diesen "
                   "Vertrag ein."),
    ("num", "2.2", "Folgende Dokumente können diesen Vertrag ergänzen und werden, soweit "
                   "unterzeichnet, Bestandteil: der White-Label-/OEM-Vertrag, das Service Level "
                   "Agreement und der Auftragsverarbeitungsvertrag."),
    ("num", "2.3", "Rangfolge, beginnend mit dem höchsten Rang: ein unterzeichnetes "
                   "Bestellformular für das von ihm geregelte Geschäft; der "
                   "Auftragsverarbeitungsvertrag für datenschutzrechtliche Fragen; der "
                   "White-Label-/OEM-Vertrag für White-Label-Fragen; das Service Level Agreement "
                   "für Service Levels; dieser Vertrag; die Anlagen."),
    ("num", "2.4", "Allgemeine Geschäftsbedingungen von byon finden keine Anwendung, auch dann "
                   "nicht, wenn objectale ihnen nicht widerspricht und vorbehaltlos leistet."),

    ("h2", "3. Rechtekette"),
    ("p", "Diese Klausel beschreibt zutreffend, was objectale überhaupt verkaufen kann. Sie ist "
          "keine Formelklausel und die Parteien haben sie gelesen."),
    ("num", "3.1", "Die Rechte von objectale an der Plattform sind abgeleitet. objectale unterhält "
                   "einen Partnervertrag mit dem Betreiber (der \"Hauptvertrag\") und räumt byon "
                   "Rechte nach diesem Vertrag nur insoweit ein, als der Hauptvertrag objectale "
                   "deren Einräumung gestattet."),
    ("num", "3.2", "objectale sichert zu, dass der Hauptvertrag am Datum des Inkrafttretens "
                   "besteht und objectale gestattet, Wiederverkäufer zu den Bedingungen dieses "
                   "Vertrages zu bestellen, und dass objectale ohne vorherige schriftliche "
                   "Zustimmung von byon keiner Änderung des Hauptvertrages zustimmen wird, die die "
                   "byon eingeräumten Rechte während der Laufzeit einschränkt."),
    ("num", "3.3", "objectale wird byon unverzüglich schriftlich informieren, wenn der "
                   "Hauptvertrag beendet, ausgesetzt oder in einer byon betreffenden Weise "
                   "wesentlich geändert wird, in jedem Fall binnen fünf Arbeitstagen ab "
                   "Kenntnis."),
    ("num", "3.4", "Endet der Hauptvertrag aus welchem Grund auch immer, wird objectale sich nach "
                   "besten Kräften darum bemühen, dass der Betreiber byon einen unmittelbaren "
                   "Vertrag zu nicht ungünstigeren Bedingungen für die Restlaufzeit der eigenen "
                   "Kundenverträge von byon anbietet. Tut der Betreiber dies nicht, gilt Ziffer "
                   "20.4."),
    ("num", "3.5", "byon nimmt zur Kenntnis, dass objectale nicht Inhaberin der Plattform ist, "
                   "deren Weiterentwicklung nicht steuert und keine Rechte an der zugrunde "
                   "liegenden Software über die in diesem Vertrag beschriebenen Nutzungsrechte "
                   "hinaus einräumen kann."),

    ("h2", "4. Bestellung, Gebiet und Exklusivität"),
    ("num", "4.1", "objectale bestellt byon zum nicht ausschließlichen Wiederverkäufer der "
                   "Plattform im Gebiet; byon nimmt die Bestellung an."),
    ("num", "4.2", "Das Gebiet ist [Deutschland, Österreich und die Schweiz], sofern Anlage 1 "
                   "nichts anderes bestimmt. byon darf einen im Gebiet ansässigen Kunden auch in "
                   "Bezug auf dessen Konzerngesellschaften außerhalb des Gebietes betreuen."),
    ("num", "4.3", "Die Bestellung ist nicht ausschließlich. objectale darf weitere "
                   "Wiederverkäufer bestellen und unmittelbar verkaufen, vorbehaltlich Ziffer "
                   "4.4."),
    ("num", "4.4", "Projektschutz. Meldet byon einen namentlich benannten Interessenten "
                   "schriftlich an und bestätigt objectale die Anmeldung, wird objectale diesen "
                   "Interessenten für die Dauer von sechs Monaten ab Bestätigung nicht für die "
                   "Plattform ansprechen und eingehende Anfragen dieses Interessenten in diesem "
                   "Zeitraum an byon verweisen. Die Bestätigung darf nicht unbillig verweigert "
                   "oder verzögert werden. Die Anmeldung erlischt, wenn innerhalb von sechs "
                   "Monaten kein Bestellformular erteilt wird."),
    ("num", "4.5", "byon handelt als selbständiges Unternehmen im eigenen Namen und auf eigene "
                   "Rechnung. Dieser Vertrag begründet keine Stellvertretung, kein "
                   "Handelsvertreterverhältnis im Sinne der §§ 84 ff. HGB, keine Gesellschaft und "
                   "kein Joint Venture; byon ist nicht berechtigt, objectale oder den Betreiber zu "
                   "verpflichten."),

    ("h2", "5. Weiterverkauf an Endkunden"),
    ("num", "5.1", "byon darf die Plattform an Endkunden im Gebiet weiterverkaufen, im eigenen "
                   "Namen, auf eigene Rechnung und zu von byon bestimmten Preisen."),
    ("num", "5.2", "byon darf die Plattform mit eigenen Managed Services, eigener Berichterstattung "
                   "und eigener Beratung bündeln und die Kombination als byon-Leistung anbieten."),
    ("num", "5.3", "byon darf ohne vorherige schriftliche Zustimmung von objectale keine "
                   "Untervertriebspartner bestellen. Die Zustimmung kann in Anlage 1 für eine "
                   "benannte Partnerkategorie erteilt werden; in diesem Fall bleibt byon für die "
                   "Einhaltung dieses Vertrages durch diesen Partner wie für eigenes Handeln "
                   "verantwortlich."),
    ("num", "5.4", "byon ist für die eigenen Kundenbeziehungen verantwortlich, einschließlich "
                   "Kreditrisiko, Rechnungsstellung, First-Level-Support und Erfüllung der eigenen "
                   "Pflichten. Der Zahlungsausfall eines Endkunden befreit byon nicht von der "
                   "Zahlungspflicht gegenüber objectale."),

    ("h2", "6. Mindestbedingungen für Endkundenverträge"),
    ("p", "objectale unterhält keinen Vertrag mit den Kunden von byon und kann diesen gegenüber "
          "nichts durchsetzen. Die nachstehenden Schutzbestimmungen müssen daher in den eigenen "
          "Kundenbedingungen von byon enthalten sein."),
    ("num", "6.1", "byon wird mit jedem Endkunden zu Bedingungen kontrahieren, die mindestens die "
                   "Regelungen der Anlage 4 enthalten und objectale und den Betreiber nicht "
                   "schlechter stellen als dieser Vertrag."),
    ("num", "6.2", "byon wird sicherstellen, dass jeder Endkunde vor der ersten Nutzung schriftlich "
                   "darauf hingewiesen wird, dass die Plattform ausschließlich öffentliche Quellen "
                   "auswertet, kein Penetrationstest ist und ein Ergebnisdokument eine Bewertung "
                   "und keine Sicherheitsgarantie darstellt."),
    ("num", "6.3", "byon wird über die von objectale bereitgestellte Dokumentation hinaus keine "
                   "Zusicherungen oder Garantien zur Plattform abgeben und objectale oder den "
                   "Betreiber nicht auf ein Service Level, eine Funktionalität oder einen "
                   "Liefertermin verpflichten."),
    ("num", "6.4", "Ist der Kunde von byon eine öffentliche Stelle, ein Betreiber kritischer "
                   "Infrastrukturen oder ein beaufsichtigtes Finanzinstitut, wird byon objectale "
                   "vor Erteilung des Bestellformulars informieren, damit zusätzliche "
                   "aufsichtsrechtliche Anforderungen vor der Eingehung von Verpflichtungen "
                   "berücksichtigt werden können."),
    ("num", "6.5", "byon wird jede Beschränkung, die der Betreiber objectale in Bezug auf eine "
                   "Drittdatenquelle mitteilt, ohne wesentliche Änderung weitergeben."),

    ("h2", "7. Pflichten von byon"),
    ("num", "7.1", "byon wird die Plattform nur für Unternehmen nutzen und die Nutzung durch seine "
                   "Kunden nur für Unternehmen zulassen, die byon beauftragt haben oder zu deren "
                   "Bewertung byon sonst rechtmäßig berechtigt ist."),
    ("num", "7.2", "byon wird die Plattform nicht zum Zwecke der Wettbewerbsbeobachtung einsetzen "
                   "und keine Bewertung eines Dritten ohne dessen Einwilligung veröffentlichen."),
    ("num", "7.3", "byon wird die Plattform nicht zu Veröffentlichungszwecken mit Wettbewerbs"
                   "produkten vergleichen, sie nicht dekompilieren, nicht versuchen, ihren "
                   "Quellcode abzuleiten, und sie nicht zum Aufbau eines Konkurrenzdienstes nutzen."),
    ("num", "7.4", "byon wird Zugangsdaten vertraulich behandeln, ein benanntes Nutzerkonto nicht "
                   "zwischen Personen teilen und objectale unverzüglich über jeden Verdacht einer "
                   "Kompromittierung informieren."),
    ("num", "7.5", "byon erbringt den First-Level-Support für die eigenen Kunden, hält mindestens "
                   "zwei geschulte Ansprechpartner vor und eskaliert an objectale erst nach eigener "
                   "Erstqualifizierung."),
    ("num", "7.6", "byon wird das anwendbare Recht einhalten, einschließlich Exportkontroll- und "
                   "Sanktionsrecht, und die Plattform keiner Person und in keinem Gebiet zugänglich "
                   "machen, in dem dies rechtswidrig wäre."),

    ("h2", "8. Pflichten von objectale"),
    ("num", "8.1", "objectale stellt byon die Plattform nach Maßgabe des Service Level Agreements "
                   "zur Verfügung, vorbehaltlich Ziffer 8.4."),
    ("num", "8.2", "objectale erbringt Second-Level-Support für die benannten Ansprechpartner von "
                   "byon und eskaliert an den Betreiber, soweit die Ursache in der Plattform "
                   "liegt."),
    ("num", "8.3", "objectale stellt angemessene Befähigung unentgeltlich bereit: Einweisung der "
                   "Ansprechpartner von byon, aktuelle Dokumentation und die für den Vertrieb "
                   "erforderlichen Unterlagen."),
    ("num", "8.4", "Die Pflichten von objectale gelten spiegelbildlich. objectale schuldet byon "
                   "kein Service Level, kein Update und keine Fehlerbeseitigung, die objectale "
                   "nicht selbst aus dem Hauptvertrag erhält. objectale wird den Betreiber "
                   "sorgfältig in Anspruch nehmen und byon den erlangten Ausgleich weitergeben."),
    ("num", "8.5", "objectale wird byon über geplante Änderungen informieren, die den Aufbau eines "
                   "Ergebnisdokuments oder eine Schnittstelle verändern, mit den Fristen des "
                   "Service Level Agreements."),

    ("h2", "9. Zugänge und benannte Nutzer"),
    ("num", "9.1", "Der Zugang erfolgt über benannte Einzelnutzer. Ein benannter Nutzer ist eine "
                   "natürliche Person; eine Mehrfachnutzung ist unzulässig. Ein benannter Nutzer "
                   "darf bei einem Rollenwechsel ersetzt werden."),
    ("num", "9.2", "byon hält die Nutzerliste in Anlage 1 aktuell und meldet Änderungen binnen "
                   "fünf Arbeitstagen."),
    ("num", "9.3", "objectale darf ein Konto unverzüglich sperren, wenn sie berechtigterweise von "
                   "einer Kompromittierung oder einer Nutzung entgegen Ziffer 7 ausgeht, und teilt "
                   "byon den Grund unverzüglich mit."),

    ("h2", "10. Preise, Bestellung und Zahlung"),
    ("num", "10.1", "Preise und der Rabatt von byon ergeben sich aus Anlage 2. Alle Beträge "
                    "verstehen sich in Euro zuzüglich Umsatzsteuer und sonstiger anfallender "
                    "Steuern."),
    ("num", "10.2", "byon bestellt per Bestellformular. Ein Bestellformular wird verbindlich mit "
                    "beiderseitiger Unterzeichnung oder mit schriftlicher Bestätigung durch "
                    "objectale."),
    ("num", "10.3", "Die Zahlung ist innerhalb von 30 Tagen ab Rechnungsdatum ohne Abzug fällig."),
    ("num", "10.4", "Bei Zahlungsverzug stehen objectale Verzugszinsen in Höhe von neun "
                    "Prozentpunkten über dem Basiszinssatz gemäß § 288 Abs. 2 BGB sowie die "
                    "Pauschale nach § 288 Abs. 5 BGB zu. Die Geltendmachung eines weitergehenden "
                    "Schadens bleibt unberührt."),
    ("num", "10.5", "byon kann nur mit unbestrittenen oder rechtskräftig festgestellten "
                    "Forderungen aufrechnen und ein Zurückbehaltungsrecht nur ausüben, soweit der "
                    "Gegenanspruch auf demselben Vertragsverhältnis beruht."),
    ("num", "10.6", "objectale darf die Listenpreise einmal je Vertragsjahr mit einer Frist von "
                    "drei Monaten schriftlich anpassen. Der Rabattsatz von byon wird durch eine "
                    "Preisanpassung nicht verringert. Übersteigt eine Anpassung fünf Prozent, kann "
                    "byon das betroffene Bestellformular zum Wirksamwerden der Anpassung kündigen."),
    ("num", "10.7", "Bereits in einem unterzeichneten Bestellformular vereinbarte Preise gelten "
                    "für dessen Laufzeit unverändert."),

    ("h2", "11. Faire Nutzung und Nutzungsnachweise"),
    ("num", "11.1", "Ein Report-Abonnement-Seat umfasst die in Anlage 2 genannte Anzahl von "
                    "Assessment-Läufen. Darüber hinausgehende Läufe werden nach Verbrauch "
                    "abgerechnet."),
    ("num", "11.2", "objectale darf die Anzahl der Läufe, die Anzahl aktiver Seats und die "
                    "Identität des bestellenden Nutzers zu Zwecken der Abrechnung, der "
                    "Kapazitätsplanung und der Missbrauchsverhinderung aufzeichnen. Diese "
                    "Aufzeichnungen sind für die Rechnungsstellung maßgeblich."),
    ("num", "11.3", "byon kann eine Abweichung binnen 20 Arbeitstagen ab Rechnung schriftlich "
                    "rügen. Die Parteien klären sie nach Treu und Glauben, bevor die Rechnung als "
                    "überfällig behandelt wird."),
    ("num", "11.4", "objectale darf die Einhaltung dieses Vertrages einmal je Vertragsjahr mit "
                    "einer Ankündigungsfrist von 20 Arbeitstagen während der Geschäftszeiten auf "
                    "eigene Kosten prüfen. Ergibt die Prüfung eine Unterzahlung von mehr als fünf "
                    "Prozent, trägt byon die angemessenen Prüfkosten."),

    ("h2", "12. Schutzrechte"),
    ("num", "12.1", "Die Plattform, ihre Software, ihre Vorlagen, ihre Methodik und sämtliche "
                    "daran bestehenden Schutzrechte verbleiben beim Betreiber oder seinen "
                    "Lizenzgebern. Dieser Vertrag überträgt kein Eigentum."),
    ("num", "12.2", "byon erhält ein nicht ausschließliches, nicht übertragbares, auf die Laufzeit "
                    "und das Gebiet beschränktes Recht, die Plattform zu nutzen und Nutzungsrechte "
                    "zu den Bedingungen dieses Vertrages an Endkunden weiterzuverkaufen."),
    ("num", "12.3", "Ein für einen Endkunden erzeugtes Ergebnisdokument und die darin enthaltene "
                    "Analyse dürfen von diesem Kunden für eigene interne Zwecke sowie im Verkehr "
                    "mit seinen Prüfern, Versicherern und Aufsichtsbehörden uneingeschränkt genutzt "
                    "werden."),
    ("num", "12.4", "Rückmeldungen von byon zur Plattform dürfen objectale und der Betreiber ohne "
                    "Verpflichtung und ohne Vergütung nutzen. Dies erstreckt sich nicht auf "
                    "vertrauliche Informationen oder Kundendaten von byon."),

    ("h2", "13. Marken"),
    ("num", "13.1", "Jede Partei räumt der anderen ein nicht ausschließliches, widerrufliches und "
                    "unentgeltliches Recht ein, ihren Namen und ihr Logo für die Laufzeit "
                    "ausschließlich zur Beschreibung der Partnerschaft und nach Maßgabe etwaiger "
                    "Markenrichtlinien zu verwenden."),
    ("num", "13.2", "Keine Partei wird ein Zeichen oder eine Domain anmelden oder anzumelden "
                    "versuchen, das oder die mit der Kennzeichnung der anderen identisch oder "
                    "verwechslungsfähig ähnlich ist."),
    ("num", "13.3", "Eine Pressemitteilung oder eine öffentliche Fallstudie, die die andere Partei "
                    "nennt, bedarf deren vorheriger schriftlicher Zustimmung, die nicht unbillig "
                    "verweigert werden darf."),
    ("num", "13.4", "Nach Vertragsende stellt jede Partei die Nutzung der Kennzeichen der anderen "
                    "binnen 30 Tagen ein, ausgenommen in archiviertem, nicht öffentlich "
                    "verbreitetem Material."),

    ("h2", "14. Datenschutz"),
    ("num", "14.1", "Die Parteien schließen den Auftragsverarbeitungsvertrag, der jede Verarbeitung "
                    "personenbezogener Daten aus diesem Vertrag regelt und Art. 28 DSGVO genügt."),
    ("num", "14.2", "In Bezug auf die Plattform ist byon Verantwortlicher für die Kontodaten der "
                    "eigenen Nutzer. objectale handelt insoweit als Auftragsverarbeiter, der "
                    "Betreiber als Unterauftragsverarbeiter. Führt byon ein Assessment für einen "
                    "eigenen Kunden durch, bestimmt byon, ob dies als Verantwortlicher oder als "
                    "Auftragsverarbeiter dieses Kunden geschieht; byon ist für die entsprechende "
                    "Vereinbarung mit diesem Kunden verantwortlich."),
    ("num", "14.3", "Die Plattform wird in Frankfurt am Main gehostet. Übermittlungen "
                    "personenbezogener Daten aus der Europäischen Union an objectale in der "
                    "Schweiz stützen sich auf den Angemessenheitsbeschluss, den die Europäische "
                    "Kommission am 15. Januar 2024 für die Schweiz erlassen hat; für diesen "
                    "Übermittlungsschritt ist daher keine zusätzliche Garantie erforderlich."),
    ("num", "14.4", "Jede Partei informiert die andere unverzüglich über eine Verletzung des "
                    "Schutzes personenbezogener Daten, die Daten der anderen betrifft, mit den "
                    "Angaben, die diese Partei zur Erfüllung eigener Meldepflichten benötigt."),

    ("h2", "15. Vertraulichkeit"),
    ("num", "15.1", "Jede Partei wird die vertraulichen Informationen der anderen geheim halten, "
                    "sie nur zum Zweck dieses Vertrages verwenden und nur solchen Mitarbeitern und "
                    "Beratern offenlegen, die sie benötigen und die gleichwertigen Pflichten "
                    "unterliegen."),
    ("num", "15.2", "Jede Partei trifft angemessene Geheimhaltungsmaßnahmen im Sinne des § 2 Nr. 1 "
                    "lit. b GeschGehG, einschließlich Zugriffsbeschränkung und Kennzeichnung."),
    ("num", "15.3", "Die Pflicht gilt nicht für Informationen, die ohne Pflichtverletzung "
                    "öffentlich sind, die die empfangende Partei bereits ohne Geheimhaltungspflicht "
                    "besaß, die sie unabhängig entwickelt oder die sie aufgrund Gesetzes offenlegen "
                    "muss; im letzteren Fall wird sie die andere Partei vorab informieren, soweit "
                    "zulässig."),
    ("num", "15.4", "Die Pflicht besteht drei Jahre über das Vertragsende hinaus fort. "
                    "Geschäftsgeheimnisse bleiben geschützt, solange sie diese Eigenschaft "
                    "besitzen."),
    ("num", "15.5", "Haben die Parteien eine gesonderte gegenseitige Geheimhaltungsvereinbarung "
                    "geschlossen, gilt diese fort; die vorliegende Ziffer ergänzt sie."),

    ("h2", "16. Beschaffenheit, Mängel und Verfügbarkeit"),
    ("num", "16.1", "objectale stellt die Plattform als Dienst bereit. Die Parteien sind sich "
                    "einig, dass auf die Überlassung der Plattform Mietrecht Anwendung findet."),
    ("num", "16.2", "Die verschuldensunabhängige Haftung für anfängliche Mängel nach § 536a Abs. 1 "
                    "Alt. 1 BGB wird ausgeschlossen. objectale haftet für solche Mängel nur bei "
                    "Verschulden."),
    ("num", "16.3", "Die vereinbarte Beschaffenheit der Plattform ergibt sich aus der bei "
                    "Erteilung des Bestellformulars aktuellen Dokumentation und aus dem Service "
                    "Level Agreement. Öffentliche Äußerungen, Werbung oder Vorführungen sind nicht "
                    "Bestandteil der vereinbarten Beschaffenheit, sofern sie nicht ausdrücklich "
                    "schriftlich bestätigt wurden."),
    ("num", "16.4", "Die Plattform wertet öffentliche Quellen aus. objectale sichert nicht zu, dass "
                    "ein Assessment jede Exposition erkennt, dass eine öffentliche Quelle "
                    "vollständig oder zutreffend ist oder dass ein Ergebnisdokument frei von "
                    "Feststellungen ist, die sich später als nicht einschlägig erweisen. objectale "
                    "sichert zu, dass die Plattform im Wesentlichen der Dokumentation entspricht."),
    ("num", "16.5", "Ein Ergebnisdokument stellt keine Rechtsberatung, keine aufsichtsrechtliche "
                    "Zertifizierung, kein Prüfungsurteil und keine versicherungstechnische "
                    "Bewertung dar; byon wird es nicht als solche darstellen."),
    ("num", "16.6", "Ist die Plattform mangelhaft, wird byon objectale mit hinreichenden Angaben "
                    "zur Reproduktion des Mangels informieren; objectale beseitigt ihn innerhalb "
                    "der Fristen des Service Level Agreements. Service-Gutschriften nach dem "
                    "Service Level Agreement sind der ausschließliche finanzielle Ausgleich von "
                    "byon für Nichtverfügbarkeit."),

    ("h2", "17. Haftung"),
    ("p", "Diese Klausel folgt der Struktur, die deutsche Gerichte für vorformulierte Bedingungen "
          "anerkennen. Eine pauschale Haftungsbegrenzung oder ein Ausschluss grober Fahrlässigkeit "
          "wäre nach §§ 307 ff. BGB unwirksam und würde objectale ohne jede Begrenzung "
          "zurücklassen."),
    ("num", "17.1", "Jede Partei haftet unbeschränkt für Vorsatz und grobe Fahrlässigkeit, für "
                    "Schäden aus der Verletzung des Lebens, des Körpers oder der Gesundheit, nach "
                    "dem Produkthaftungsgesetz sowie bei Übernahme einer Garantie oder arglistigem "
                    "Verschweigen eines Mangels."),
    ("num", "17.2", "Bei einfacher Fahrlässigkeit haftet jede Partei nur bei Verletzung einer "
                    "wesentlichen Vertragspflicht, also einer Pflicht, deren Erfüllung die "
                    "ordnungsgemäße Durchführung dieses Vertrages überhaupt erst ermöglicht und auf "
                    "deren Einhaltung die andere Partei regelmäßig vertraut. In diesem Fall ist die "
                    "Haftung auf den vertragstypischen, vorhersehbaren Schaden begrenzt."),
    ("num", "17.3", "Vorbehaltlich der Ziffern 17.1 und 17.2 ist die Gesamthaftung für einfache "
                    "Fahrlässigkeit je Vertragsjahr auf die von byon an objectale in den zwölf "
                    "Monaten vor dem schadensauslösenden Ereignis gezahlten Entgelte, höchstens "
                    "jedoch auf [EUR 250.000] begrenzt, je nachdem welcher Betrag niedriger ist."),
    ("num", "17.4", "Eine weitergehende Haftung ist ausgeschlossen, insbesondere für entgangenen "
                    "Gewinn, entgangene Einsparungen und mittelbare Schäden, soweit nicht Ziffer "
                    "17.1 eingreift."),
    ("num", "17.5", "Die vorstehenden Beschränkungen gelten auch zugunsten der persönlichen "
                    "Haftung der Mitarbeiter, Vertreter, Organe und Erfüllungsgehilfen der "
                    "Parteien."),
    ("num", "17.6", "byon trägt die Verantwortung für Entscheidungen, die byon und seine Kunden "
                    "auf Grundlage eines Ergebnisdokuments treffen. objectale haftet nicht für "
                    "einen Sicherheitsvorfall bei einem bewerteten Unternehmen, unabhängig davon, "
                    "ob das Assessment den Angriffsweg erkannt hat."),
    ("num", "17.7", "Die Verjährungsfrist für Mängelansprüche beträgt ein Jahr ab dem gesetzlichen "
                    "Verjährungsbeginn; für Ansprüche nach Ziffer 17.1 gilt die gesetzliche Frist."),

    ("h2", "18. Freistellung"),
    ("num", "18.1", "objectale stellt byon von Ansprüchen Dritter frei, die geltend machen, die "
                    "vertragsgemäße Nutzung der Plattform durch byon verletze ein Schutzrecht, "
                    "sofern byon objectale unverzüglich informiert, objectale die Führung der "
                    "Verteidigung überlässt und ohne Zustimmung keinen Vergleich schließt."),
    ("num", "18.2", "Im Fall eines solchen Anspruchs kann objectale nach eigener Wahl das Recht "
                    "zur weiteren Nutzung beschaffen, die Plattform so ändern, dass keine "
                    "Verletzung mehr vorliegt, oder das betroffene Bestellformular kündigen und "
                    "die für die ungenutzte Restlaufzeit gezahlten Entgelte erstatten."),
    ("num", "18.3", "byon stellt objectale von Ansprüchen Dritter frei, die auf einer Nutzung der "
                    "Plattform entgegen Ziffer 7, auf einer über Ziffer 6.3 hinausgehenden "
                    "Erklärung von byon oder auf einem Assessment gegen ein Unternehmen beruhen, "
                    "zu dessen Bewertung byon nicht berechtigt war."),
    ("num", "18.4", "Ziffer 17 begrenzt eine Freistellung nach dieser Ziffer 18 nicht."),

    ("h2", "19. Laufzeit und Kündigung"),
    ("num", "19.1", "Dieser Vertrag läuft 24 Monate ab dem Datum des Inkrafttretens und verlängert "
                    "sich automatisch um jeweils 12 Monate, sofern nicht eine Partei mit einer "
                    "Frist von drei Monaten zum Ende der jeweiligen Laufzeit schriftlich kündigt."),
    ("num", "19.2", "Jede Partei kann aus wichtigem Grund im Sinne des § 314 BGB fristlos kündigen, "
                    "insbesondere wenn die andere eine wesentliche Pflicht verletzt und diese nicht "
                    "binnen 30 Tagen nach schriftlicher Aufforderung behebt, wenn über ihr Vermögen "
                    "ein Insolvenzverfahren eröffnet oder dessen Eröffnung mangels Masse abgelehnt "
                    "wird oder wenn sie Sanktionen unterliegt."),
    ("num", "19.3", "objectale kann aus wichtigem Grund kündigen, wenn die Nutzung durch byon die "
                    "Sicherheit oder die Integrität der Plattform erheblich gefährdet, nachdem byon "
                    "Gelegenheit erhalten hat, dies innerhalb einer dem Risiko angemessenen Frist "
                    "abzustellen."),
    ("num", "19.4", "Die Beendigung dieses Vertrages beendet sämtliche Bestellformulare, sofern die "
                    "Parteien nichts anderes schriftlich vereinbaren."),

    ("h2", "20. Folgen der Beendigung"),
    ("num", "20.1", "Mit Beendigung stellt byon die Nutzung und die Vermarktung der Plattform ein "
                    "und erteilt keine weiteren Bestellformulare."),
    ("num", "20.2", "Bis zur Beendigung angefallene Entgelte bleiben geschuldet. Kündigt objectale "
                    "aus wichtigem Grund, werden die Entgelte für die Restlaufzeit jedes "
                    "Bestellformulars sofort fällig."),
    ("num", "20.3", "byon kann die für byon erzeugten Ergebnisdokumente 60 Tage nach Beendigung "
                    "herunterladen. Danach ist objectale zu ihrer Aufbewahrung nicht verpflichtet."),
    ("num", "20.4", "Auslauf für bestehende Endkunden. Endet dieser Vertrag aus einem anderen "
                    "Grund als einer wesentlichen Pflichtverletzung von byon, darf byon Endkunden "
                    "aus im Zeitpunkt der Beendigung bestehenden Verträgen bis zu deren Ablauf "
                    "weiter betreuen, höchstens jedoch 12 Monate, zu den dann geltenden "
                    "kommerziellen Bedingungen, sofern byon diese Nutzung vergütet und keine neuen "
                    "Endkunden gewinnt. Dies gilt nur, soweit der Hauptvertrag dies zulässt; "
                    "andernfalls gilt Ziffer 3.4."),
    ("num", "20.5", "Die Ziffern 12, 14, 15, 17, 18, 20, 21, 23 und 24 gelten über die Beendigung "
                    "hinaus fort."),

    ("h2", "21. Abwerbeverbot"),
    ("num", "21.1", "Während der Laufzeit und für 12 Monate danach wird keine Partei einen "
                    "Mitarbeiter der anderen aktiv abwerben, der an der Durchführung dieses "
                    "Vertrages wesentlich beteiligt war."),
    ("num", "21.2", "Dies gilt nicht für öffentliche Stellenausschreibungen, für die Reaktion auf "
                    "eine Initiativbewerbung oder wenn der Mitarbeiter von sich aus an die andere "
                    "Partei herantritt."),

    ("h2", "22. Eskalation"),
    ("num", "22.1", "Eine Streitigkeit wird zunächst an die operativen Ansprechpartner nach Anlage "
                    "1 eskaliert, sodann binnen zehn Arbeitstagen an die kommerziell "
                    "Verantwortlichen und sodann binnen weiterer zehn Arbeitstage an je ein "
                    "Mitglied der Geschäftsleitung beider Parteien."),
    ("num", "22.2", "Keine Partei wird ein gerichtliches Verfahren einleiten, bevor diese "
                    "Eskalation abgeschlossen ist oder 30 Arbeitstage seit der ersten Eskalation "
                    "vergangen sind; ausgenommen sind einstweiliger Rechtsschutz, Zahlungsklagen "
                    "und Fälle drohender Verjährung."),

    ("h2", "23. Schlussbestimmungen"),
    ("num", "23.1", "Änderungen dieses Vertrages, auch dieser Ziffer, bedürfen der Textform. "
                    "Mündliche Nebenabreden bestehen nicht."),
    ("num", "23.2", "Keine Partei darf diesen Vertrag ohne vorherige schriftliche Zustimmung der "
                    "anderen abtreten; die Zustimmung darf nicht unbillig verweigert werden. § 354a "
                    "HGB bleibt unberührt. Eine Abtretung an ein verbundenes Unternehmen oder im "
                    "Zusammenhang mit einer Übertragung des gesamten Geschäftsbetriebs bedarf "
                    "keiner Zustimmung, ist aber anzuzeigen."),
    ("num", "23.3", "objectale darf Subunternehmer einsetzen und bleibt für deren Leistung wie für "
                    "eigene verantwortlich."),
    ("num", "23.4", "Keine Partei haftet für eine Leistungsstörung, die auf einem Ereignis außerhalb "
                    "ihres zumutbaren Einflussbereichs beruht, solange dieses Ereignis andauert und "
                    "sie die andere informiert und den Schaden mindert. Dauert das Ereignis länger "
                    "als 60 Tage an, kann jede Partei das betroffene Bestellformular kündigen."),
    ("num", "23.5", "Ist oder wird eine Bestimmung unwirksam, bleibt die Wirksamkeit der übrigen "
                    "unberührt. Die Parteien ersetzen die unwirksame Bestimmung durch eine "
                    "wirksame, die ihrem wirtschaftlichen Zweck am nächsten kommt."),
    ("num", "23.6", "Dieser Vertrag wird in deutscher und in englischer Sprache ausgefertigt. Bei "
                    "Abweichungen ist die [deutsche] Fassung maßgeblich."),
    ("num", "23.7", "Die Parteien können in Ausfertigungen und mittels qualifizierter oder "
                    "fortgeschrittener elektronischer Signatur unterzeichnen."),

    ("h2", "24. Anwendbares Recht und Gerichtsstand"),
    ("num", "24.1", "Dieser Vertrag unterliegt dem Recht der Bundesrepublik Deutschland unter "
                    "Ausschluss seiner Kollisionsnormen und unter Ausschluss des UN-Kaufrechts."),
    ("num", "24.2", "Ausschließlicher Gerichtsstand für alle Streitigkeiten aus oder im "
                    "Zusammenhang mit diesem Vertrag ist Frankfurt am Main, Deutschland. Beide "
                    "Parteien sind Kaufleute im Sinne des Handelsgesetzbuchs."),
    ("num", "24.3", "objectale bleibt berechtigt, am allgemeinen Gerichtsstand von byon zu klagen."),

    ("pagebreak",),
    ("h2", "Anlage 1 - Parteiangaben und benannte Ansprechpartner"),
    ("table", ["Angabe", "objectale", "byon"], [
        ["Rechtsträger", OBJECTALE["name"], BYON["name"]],
        ["Sitz", OBJECTALE["addr_de"], BYON["addr_de"]],
        ["Register", OBJECTALE["reg"], BYON["reg"]],
        ["USt-IdNr.", "[CHE-___.___.___ MWST]", BYON["vat"]],
        ["Vertreten durch", "[Name, Funktion]", BYON["mgmt"]],
        ["Kaufmännischer Kontakt", "[Name] · [E-Mail] · [Telefon]", "[Name] · [E-Mail] · [Telefon]"],
        ["Operativer Kontakt", "[Name] · [E-Mail] · [Telefon]", "[Name] · [E-Mail] · [Telefon]"],
        ["Zustelladresse", OBJECTALE["mail"], BYON["mail"]],
        ["Gebiet", "[Deutschland, Österreich und die Schweiz]", "-"],
        ["Untervertriebspartner zulässig", "[keine / benannte Kategorie]", "-"],
    ]),
    ("h3", "Benannte Nutzer bei Unterzeichnung"),
    ("table", ["#", "Name", "Rolle", "E-Mail"], [
        ["1", "[Name]", "[Rolle]", "[E-Mail]"],
        ["2", "[Name]", "[Rolle]", "[E-Mail]"],
        ["3", "[Name]", "[Rolle]", "[E-Mail]"],
        ["4", "[Name]", "[Rolle]", "[E-Mail]"],
    ]),

    ("pagebreak",),
    ("h2", "Anlage 2 - Preise und Rabatt"),
    ("p", "Die nachstehenden Listenpreise sind die Listenpreise der Plattform. Der Preis von byon "
          "ist der Listenpreis abzüglich des in dieser Anlage festgehaltenen Rabatts. Alle Beträge "
          "in Euro zuzüglich Umsatzsteuer."),
    ("table", ["Position", "Listenpreis, EUR zzgl. USt."], [[a, b] for a, b in LIST_PRICES_DE]),
    ("h3", "Rabatt von byon"),
    ("table", ["Angabe", "Detail"], [
        ["Rabatt auf Liste", "[__]% für die Erstlaufzeit"],
        ["Grundlage des Rabatts", "[Mengenzusage / White-Label-Stufe / sonstiges]"],
        ["Mindestabnahme", "[keine / __ Seats / __ Läufe je Quartal]"],
        ["Enthaltene Läufe je Abonnement-Seat und Monat", "[__]"],
        ["Preis eines Laufs über die enthaltene Anzahl hinaus", "[EUR __]"],
        ["Überprüfung des Rabatts", "Jährlich zum Jahrestag des Inkrafttretens"],
    ]),
    ("note", "objectale kann keinen Rabatt gewähren, der den Preis von byon unter die eigenen "
             "Kosten von objectale aus dem Hauptvertrag senkt. Der vorstehende Prozentsatz wird vor "
             "diesem Hintergrund vereinbart und ist die eine kommerzielle Größe, die die Parteien "
             "vor Unterzeichnung festlegen sollten."),

    ("pagebreak",),
    ("h2", "Anlage 3 - Muster eines Bestellformulars"),
    ("table", ["Angabe", "Detail"], [
        ["Nummer des Bestellformulars", "[ ]"],
        ["Datum des Inkrafttretens", "[ ]"],
        ["Endkunde, sofern die Bestellung einen benannten Kunden betrifft", "[ ]"],
        ["Laufzeit dieses Bestellformulars", "[ ]"],
        ["Angewandter Rabatt", "[ ]"],
        ["Abrechnungsintervall", "[monatlich im Voraus / bei Lieferung]"],
    ]),
    ("table", ["Pos.", "Position", "Menge", "Einzelpreis, EUR zzgl. USt.", "Summe je Periode"], [
        ["1", "Report-Abonnement-Seats", "[ ]", "[ ]", "[ ]"],
        ["2", "Assessment-Läufe über die enthaltene Anzahl hinaus", "Nach Verbrauch", "[ ]", "[ ]"],
        ["3", "Findings-Review-Stunden", "[ ]", "[ ]", "[ ]"],
        ["4", "Workshops", "[ ]", "[ ]", "[ ]"],
        ["5", "Sonstiges", "[ ]", "[ ]", "[ ]"],
    ]),

    ("pagebreak",),
    ("h2", "Anlage 4 - Mindestbedingungen für Endkundenverträge von byon"),
    ("p", "byon wird in jedem Endkundenvertrag, unter dem die Plattform bereitgestellt wird, "
          "mindestens Regelungen folgenden Inhalts aufnehmen."),
    ("num", "A", "Der Kunde bestätigt, dass er berechtigt ist, ein Assessment für jedes von ihm "
                 "benannte Unternehmen und jede von ihm benannte Domain zu beauftragen."),
    ("num", "B", "Die Plattform wertet ausschließlich öffentliche Quellen aus. Sie führt keinen "
                 "Portscan, keine Schwachstellenprüfung und keinen Anmeldeversuch durch und sendet "
                 "an das bewertete Unternehmen kein Datenpaket."),
    ("num", "C", "Ein Ergebnisdokument ist eine Bewertung auf Basis öffentlicher Informationen zu "
                 "einem Zeitpunkt. Es ist keine Sicherheitsgarantie, keine Rechtsberatung, keine "
                 "Zertifizierung und kein Prüfungsurteil."),
    ("num", "D", "Der Kunde wird die Plattform nicht dekompilieren, nicht versuchen, ihren "
                 "Quellcode abzuleiten, sie nicht zu Veröffentlichungszwecken mit "
                 "Wettbewerbsprodukten vergleichen und sie nicht zum Aufbau eines "
                 "Konkurrenzdienstes nutzen."),
    ("num", "E", "Der Kunde wird keine Bewertung eines Dritten ohne dessen Einwilligung "
                 "veröffentlichen."),
    ("num", "F", "Der Zugang erfolgt über benannte Einzelnutzer; Zugangsdaten dürfen nicht geteilt "
                 "werden."),
    ("num", "G", "Die Schutzrechte an der Plattform verbleiben bei ihrem Inhaber. Der Kunde erhält "
                 "ein Nutzungsrecht für die Laufzeit und darf die für ihn erzeugten "
                 "Ergebnisdokumente für eigene Zwecke uneingeschränkt nutzen."),
    ("num", "H", "Die Haftungsregelungen des Kunden und eine Haftungsbegrenzung von byon binden "
                 "objectale oder den Betreiber nicht."),
    ("num", "I", "Soweit personenbezogene Daten verarbeitet werden, schließen der Kunde und byon "
                 "eine Vereinbarung, die Art. 28 DSGVO genügt."),

    ("pagebreak",),
    ("h2", "Unterschriften"),
    ("p", "Die Parteien unterzeichnen diesen Vertrag zu den angegebenen Daten."),
    ("sig", "Für %s" % OBJECTALE["name"], "Für %s" % BYON["name"],
     ["Name:", "Funktion:", "Ort:", "Datum:"]),
]
