"""brand.py — White Label storage: one partner brand per user, shared by the web app and the bots.

WHERE IT LIVES, AND WHY THERE
-----------------------------
`/var/log/colt/brands/<safe-email>/` on the PERSISTENT, SHARED `colt_events` volume — the same
volume, and the same reasoning, as cost_ledger.sqlite and users.sqlite. colt-web, colt-assessbot and
colt-cassandra all mount it read-write, so an assessment started from Telegram renders in exactly
the same branding as one started from the cabinet. `colt_webdata` would have been the obvious home
and is wrong: only colt-web mounts it, so the bots would silently produce unbranded decks and the
partner would have no idea which door produced which artifact.

The directory holds exactly two files:
    theme.json   what the builders read (BRAND_THEME points at it)
    logo.png     the validated image, re-written by us, never the uploaded bytes under their name

WHAT IS DELIBERATELY NOT KEPT: the uploaded .pptx. It is a partner's own commercial material, we
have taken everything we need from it (a palette, two font names, one image), and keeping customer
files we have no use for is storage we have to defend, disclose and delete on request. Extract,
then discard.
"""
import json
import os
import re
import shutil
import sys
import time

# The engine tree is COPYed into every image at /opt/shodan-skill; proteus lives there so that the
# bots can use it too. Same path handling as the rest of the engine imports in this app.
_SKILL = os.environ.get("SHODAN_SKILL", "/opt/shodan-skill")
for _p in (os.path.join(_SKILL, "scripts"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
               os.path.dirname(os.path.abspath(__file__))))),
               "hermes-skills", "shodan-assessment", "scripts")):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import proteus                                                          # noqa: E402

# The shared events volume. EVENTS_LOG already points into it everywhere else in this app, so the
# brand directory is derived from it rather than being a second hardcoded path that can drift.
def root():
    base = os.path.dirname(os.environ.get("EVENTS_LOG", "/var/log/colt/events.log"))
    return os.environ.get("BRAND_DIR", os.path.join(base, "brands"))


def _safe(email):
    """The same transformation _job_dir uses, so one identity is one directory everywhere."""
    return re.sub(r"[^a-z0-9._-]", "_", (email or "").strip().lower())


def dir_for(email):
    e = _safe(email)
    if not e or e in (".", ".."):
        raise ValueError("bad identity")
    return os.path.join(root(), e)


def theme_path(email):
    """Absolute path to this user's theme.json, or None. This is what becomes BRAND_THEME."""
    p = os.path.join(dir_for(email), "theme.json")
    return p if os.path.isfile(p) else None


def get(email):
    p = theme_path(email)
    if not p:
        return None
    try:
        t = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        return {"broken": repr(e)[:120]}
    t["has_logo"] = os.path.isfile(os.path.join(dir_for(email), "logo.png"))
    return t


def logo_path(email):
    p = os.path.join(dir_for(email), "logo.png")
    return p if os.path.isfile(p) else None


def delete(email):
    d = dir_for(email)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
        return True
    return False


def precheck(template=None, logo=None):
    """The CHEAP refusals, in milliseconds, so an obviously wrong file never becomes a job.

    Called synchronously by the endpoint AND again by save(). One implementation, two callers: an
    endpoint that validated separately would drift from what save() actually accepts, and a save()
    that trusted the endpoint would be unsafe when called from anywhere else.

    Everything here is a parse or a header read. The SLOW part — four models deciding which colour
    is the brand — is what the job and its progress feed exist for, and it cannot fail this way.
    """
    if template is not None:
        proteus.extract(template)                 # raises ValueError: not a zip, not a deck, bomb
    if logo:
        ok, why, _meta = proteus.logo_ok(logo)
        if not ok:
            raise ValueError("logo rejected: " + why)


def save(email, template=None, logo=None, name=None, powered_by=None, use_panel=True, on=None):
    """Extract a theme from the partner's own deck and store it. Returns (theme, problems).

    ORDER MATTERS: everything is validated and the theme is fully built BEFORE anything is written.
    A half-written brand directory — a theme.json whose logo never arrived, or a logo with no theme —
    renders as a broken deck for every assessment that user starts afterwards, and they would have
    no way to tell why.
    """
    say = on or (lambda pct, msg: None)
    precheck(template, logo)
    if template:
        say(4, "reading the file")
        facts = proteus.extract(template)                # raises ValueError on anything not a deck
        say(14, "%d theme colours, %d fonts, %d image(s) inside"
            % (len(facts.get("colors") or {}), len(facts.get("fonts") or {}),
               len(facts.get("media") or [])))
        if use_panel:
            say(18, "asking %d models which colour is the brand" % len(proteus.PANEL))
            judgement = proteus.judge(facts, on=say)
        else:
            judgement = proteus._heuristic(facts)
        say(74, judgement.get("decided_by", "decided"))
    else:
        # No new template: re-editing the name or the logo on an existing brand.
        old = get(email)
        if not old:
            raise ValueError("upload a PowerPoint template first")
        facts = {"colors": (old.get("source") or {}).get("colors") or {},
                 "fonts": {"major": (old.get("fonts") or {}).get("heading"),
                           "minor": (old.get("fonts") or {}).get("body")},
                 "company": old.get("name"), "media": [],
                 "sha256": (old.get("source") or {}).get("sha256")}
        judgement = {"brand": old["palette"]["brandDark"] if
                     proteus.luminance(old["palette"]["brandDark"]) > 0.4 else
                     old["palette"]["brandMid"],
                     "name": old.get("name"), "logo": "", "mode": old.get("mode", "light"),
                     "decided_by": old.get("decided_by", ""), "votes": []}

    # The logo: either one the partner uploaded explicitly, or the one the panel picked out of the
    # template. An explicit upload WINS — they know which image is their logo and we are guessing.
    say(80, "checking the logo")
    blob, wh = None, None
    if logo:
        ok, why, meta = proteus.logo_ok(logo)
        if not ok:
            raise ValueError("logo rejected: " + why)
        blob, wh = logo, (meta.get("w"), meta.get("h"))
    elif template and judgement.get("logo"):
        try:
            cand = proteus.read_media(template, judgement["logo"])
            ok, _why, meta = proteus.logo_ok(cand)
            if ok:
                blob, wh = cand, (meta.get("w"), meta.get("h"))
        except Exception:
            blob = None                                  # a logo we cannot use is not a failure

    theme = proteus.build_theme(facts, judgement, logo_name="logo.png" if blob else None,
                                powered_by=powered_by, logo_wh=wh)
    if name and str(name).strip():
        theme["name"] = str(name).strip()[:80]
        theme["wordmark"] = theme["name"][:40]
        theme["warnings"] = [w for w in theme.get("warnings", [])
                             if "does not say which company" not in w]
    say(88, "building the colour ramp and measuring contrast")
    problems = proteus.verify(theme)
    if problems:
        # A theme that does not verify is never written. The partner sees why instead of receiving
        # unreadable decks for a week.
        raise ValueError("; ".join(problems))
    theme["updated_ts"] = time.time()
    theme["owner"] = (email or "").strip().lower()

    d = dir_for(email)
    os.makedirs(d, exist_ok=True)
    if blob:
        with open(os.path.join(d, "logo.png"), "wb") as fh:
            fh.write(blob)
    elif not (template is None and logo is None):
        # A new template with no usable logo replaces the old one rather than leaving a stale mark
        # from a previous upload sitting on the partner's new brand.
        try:
            os.remove(os.path.join(d, "logo.png"))
        except OSError:
            pass
    tmp = os.path.join(d, "theme.json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(theme, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, os.path.join(d, "theme.json"))       # atomic: never a half-written theme
    say(100, "saved — future artifacts will carry this branding")
    return theme, theme.get("warnings") or []


def env_for(email):
    """The env addition that makes an engine run use this partner's brand, or {}."""
    try:
        p = theme_path(email)
    except Exception:
        return {}
    return {"BRAND_THEME": p} if p else {}
