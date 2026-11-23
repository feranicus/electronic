#!/usr/bin/env python3
"""roles.py — WHO MAY DO WHAT. One home, because authorisation with two homes is a breach.

    python roles.py            print the matrix, so the policy can be read rather than inferred

THE MODEL, AND WHERE IT COMES FROM
    Every platform that sells through a channel converges on the same three things, and this is
    the smallest version of them: a TENANT, a MEMBERSHIP with a ROLE, and a role that is a named
    BUNDLE OF PERMISSIONS rather than a list of screens. SecurityScorecard, Bitsight and Pipedrive
    all let a customer administer their own users without ever seeing another customer's, and all
    three make "can create users" a permission held by some roles and not others. That is the
    whole idea, and it is worth copying exactly because the alternative - an `if email ==` ladder -
    is how a partner ends up able to read another partner's deals.

    TENANT IS THE EMAIL DOMAIN, deliberately. The platform already decides trust that way:
    `colt_auth.PARTNER_DOMAINS` admits a whole domain. Inventing a second notion of "company"
    beside the one the login gate already uses would give the same fact two homes (class 32), and
    the newer one always loses. A person at colt.net is in the colt.net tenant; nothing to
    configure, nothing to keep in step. `ORG_OF` overrides it only where a real exception exists.

WHAT A PERMISSION IS
    A verb, never a screen. "assess.run", not "can see the Assess tab". Hiding a nav item is
    presentation; the server asks for the verb. CLAUDE.md has carried that rule since the admin
    routes were written, and this file is what makes it enforceable beyond `_require_admin`.

WHY THE ROLES ARE ORDERED
    Seniority decides who may create whom. A company admin who could mint a platform admin is a
    privilege-escalation hole with a friendly name, so `may_grant()` refuses upward and sideways
    grants by construction rather than by a list somebody has to maintain.
"""
import os
import sys

# ---------------------------------------------------------------------------------------------
# PERMISSIONS. Each is a verb a route can demand. Adding a route means picking one of these or
# adding one here; it never means inventing a check at the call site.
# ---------------------------------------------------------------------------------------------
PERMISSIONS = {
    "assess.run":        "start a security assessment or a compliance run",
    "assess.read.own":   "open assessments this person started",
    "assess.read.org":   "open any assessment started by their own company",
    "assess.read.all":   "open any assessment on the platform",
    "brand.manage":      "set the white-label branding used on their company's documents",
    "pipeline.view":     "open the channel pipeline",
    "pipeline.edit":     "move a deal, write an update, attach a file",
    "pipeline.admin":    "read the connected mailboxes into the board, and re-file a message by "
                         "hand onto a different deal",
    # DEAL REGISTRATION. Four verbs, because "register a deal", "see your own", "see everyone's"
    # and "decide" are four different powers and collapsing any two of them is a leak.
    #
    # `dealreg.view.all` IS THE SENSITIVE ONE. A registration names an end customer, the expected
    # value, the close date and the incumbent competitor, submitted by a reseller who competes with
    # the other resellers. Granting it to a partner would make US the channel through which one
    # reseller learns a rival's pipeline — competitor-to-competitor disclosure via the vendor,
    # which is the exposure dual distribution is judged on. So it goes to S4biz roles only, which
    # is also exactly what the operator asked for: every S4biz account sees every registration,
    # because you cannot adjudicate "who got here first" from a partial view, and an S4biz seller
    # must know an account is spoken for before promising it to somebody else.
    "dealreg.submit":    "register a deal and ask for protection, a discount and deal support",
    "dealreg.view.own":  "open the deal registrations this person submitted",
    "dealreg.view.all":  "open EVERY deal registration on the platform (S4biz only — a "
                         "registration is a rival reseller's pipeline)",
    "dealreg.decide":    "approve, return, reject or expire a registration, and extend protection",
    "users.invite.org":  "create and disable accounts INSIDE their own company",
    "users.invite.any":  "create accounts in any company, and create companies",
    "users.manage.all":  "create, disable and delete any account anywhere",
    "fleet.read":        "the operational fleet page",
    "platform.admin":    "everything, including the parts that can break the platform",
}

# ---------------------------------------------------------------------------------------------
# ROLES, most senior first. The ORDER IS THE POLICY: may_grant() reads it.
# ---------------------------------------------------------------------------------------------
_R = [
    ("admin", "Platform administrator", "S4biz. Everything.", set(PERMISSIONS)),

    ("s4biz_power", "S4biz power user",
     "S4biz staff. The whole product and the whole pipeline, but not the controls that can break "
     "the platform.",
     {"assess.run", "assess.read.own", "assess.read.org", "assess.read.all", "brand.manage",
      "pipeline.view", "pipeline.edit", "pipeline.admin", "users.invite.any", "fleet.read",
      "dealreg.submit", "dealreg.view.own", "dealreg.view.all", "dealreg.decide"}),

    ("reseller_admin", "Reseller administrator",
     "A distributor. Administers their own people AND the companies they sell to.",
     {"assess.run", "assess.read.own", "assess.read.org", "brand.manage",
      "pipeline.view", "pipeline.edit", "users.invite.any",
      # A distributor REGISTERS deals and sees their own. NOT view.all: that would hand one
      # reseller the pipeline of every other reseller, through us.
      "dealreg.submit", "dealreg.view.own"}),

    ("company_admin", "Company administrator",
     "Administers their own company's people. Sees nothing outside it.",
     {"assess.run", "assess.read.own", "assess.read.org", "brand.manage", "users.invite.org",
      "dealreg.submit", "dealreg.view.own"}),

    ("presales", "Pre-sales engineer",
     "Runs assessments and reads every assessment their company ran.",
     {"assess.run", "assess.read.own", "assess.read.org"}),

    ("sales_rep", "Sales representative",
     "Runs assessments and works the pipeline. Reads their own work.",
     {"assess.run", "assess.read.own", "pipeline.view", "pipeline.edit",
      "dealreg.submit", "dealreg.view.own"}),

    ("user", "User", "Runs assessments and reads their own.",
     {"assess.run", "assess.read.own"}),
]

ROLES = {k: {"rank": i, "label": lab, "about": ab, "perms": p}
         for i, (k, lab, ab, p) in enumerate(_R)}
DEFAULT_ROLE = "user"

# THE ROLE THAT CANNOT BE ABSENT. If nobody holds platform.admin the platform has locked itself
# out, so colt_auth.ADMIN_EMAILS keeps its meaning: those addresses are admin whatever the store
# says. A role row can only ever ADD, exactly as an enabled account can only ever add (CLAUDE.md).
try:                                                        # pragma: no cover - import guard
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from colt_auth import ADMIN_EMAILS
except Exception:
    ADMIN_EMAILS = set()

# A tenant that is NOT the email domain. Empty by design: every entry is a fact that can go stale.
ORG_OF = {}


def org_of(email):
    """The tenant an address belongs to. The domain, unless an exception is recorded."""
    e = (email or "").strip().lower()
    if e in ORG_OF:
        return ORG_OF[e]
    return e.split("@", 1)[1] if "@" in e else ""


def role_of(email, stored=None):
    """The effective role. `stored` is the role column, passed in so this file never reads a
    database and can be tested without one."""
    e = (email or "").strip().lower()
    if e in {a.lower() for a in ADMIN_EMAILS}:
        return "admin"                        # the floor: never lockable-out by a bad row
    r = (stored or "").strip().lower()
    return r if r in ROLES else DEFAULT_ROLE


def perms_of(role):
    return set(ROLES.get(role, ROLES[DEFAULT_ROLE])["perms"])


def can(perm, role):
    """The ONE question every route asks. Unknown permission answers NO.

    An unknown verb must not be a silent yes: a typo in a route decorator would otherwise open
    it to everybody, which is the deny-by-default rule the authz audit exists to enforce."""
    if perm not in PERMISSIONS:
        return False
    return perm in perms_of(role)


def may_grant(actor_role, target_role):
    """May someone holding `actor_role` create or change an account to `target_role`?

    STRICTLY DOWNWARD. Equal rank is refused too: a company admin minting a second company admin
    is how one compromised account becomes two, and the platform admin can always do it. Only a
    role that holds an invite permission may grant at all."""
    a, t = ROLES.get(actor_role), ROLES.get(target_role)
    if not a or not t:
        return False
    if not ({"users.invite.org", "users.invite.any", "users.manage.all"} & a["perms"]):
        return False
    if actor_role == "admin":
        return True                            # the platform admin may grant any role, including admin
    return t["rank"] > a["rank"]


def may_touch(actor_role, actor_email, target_email):
    """May the actor administer this particular account? Rank is not enough: scope decides.

    A company administrator with users.invite.org is confined to their OWN tenant. That is the
    single rule that keeps one customer out of another customer's user list, so it is here rather
    than in a route."""
    p = perms_of(actor_role)
    if "users.manage.all" in p or "users.invite.any" in p:
        return True
    if "users.invite.org" in p:
        return org_of(actor_email) == org_of(target_email) and org_of(actor_email) != ""
    return False


def describe():
    out = ["PERMISSIONS (%d)" % len(PERMISSIONS)]
    for k in sorted(PERMISSIONS):
        out.append("  %-18s %s" % (k, PERMISSIONS[k]))
    out.append("")
    out.append("ROLES, most senior first")
    for k, v in sorted(ROLES.items(), key=lambda kv: kv[1]["rank"]):
        out.append("  %d  %-15s %s" % (v["rank"], k, v["label"]))
        out.append("     %s" % v["about"])
        out.append("     %s" % ", ".join(sorted(v["perms"])))
    out.append("")
    out.append("WHO MAY CREATE WHOM (strictly downward; admin may grant anything)")
    names = [k for k, _ in sorted(ROLES.items(), key=lambda kv: kv[1]["rank"])]
    out.append("     actor \\ target   " + " ".join("%-14s" % n for n in names))
    for a in names:
        out.append("     %-16s " % a + " ".join(
            "%-14s" % ("yes" if may_grant(a, t) else "-") for t in names))
    return "\n".join(out)


if __name__ == "__main__":
    print(describe())
