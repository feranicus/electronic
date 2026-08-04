#!/usr/bin/env python3
"""
scope_deny.py — apexes that may NEVER enter a customer's assessment scope.

WHY THIS EXISTS (the abakus-tk.de incident, 2026-08)
----------------------------------------------------
abakus-tk.de is a 20-person Lubeck telecoms reseller with ONE shared IONOS webhosting VIP and
everything else in Microsoft 365. The delivered deck claimed 401 IPs across 42 ASNs and 49
countries. 236 of the 348 inventoried hosts -- 68% -- were Meta Platforms.

The whole estate came from ONE href in the site footer:

    <a href="https://wa.me/01702206960">Chat</a>

`wa.me` is WhatsApp's click-to-chat shortener. It was harvested as a "subsidiary", promoted to a
first-class seed, and `hostname:".wa.me"` returned Meta's global edge.

Two separate defects let it through, and the second is the reason this module exists:

  1. group_discovery.STRUCTURE_HINTS matched `struktur` as a bare substring, so the path
     `/it-infrastruktur/` -- the single most likely page on a TELECOMS provider's website --
     was read as a corporate group-structure page. Fixed there.
  2. The suppression list lived inside group_discovery and named `whatsapp.com` and `t.me`
     but not `wa.me`. A denylist that exists in exactly one module protects exactly one code
     path. `wa.me` could equally have arrived from a certificate SAN, a CT record or an
     operator's refine answer, and nothing downstream would have objected.

So the list lives here, and BOTH group_discovery (at harvest time) and shodan_recon (at the
ownership gate, ahead of every other test including the group-structure assertion) consult it.

THE RULE
--------
These domains are shared infrastructure operated by somebody else on behalf of millions of
unrelated parties. A customer LINKING to one is not evidence of ownership -- it is evidence
that the customer, like everyone else, uses the internet. Scanning them puts Meta's, Google's
or Bitly's estate into a customer deck.

Fails CLOSED: when in doubt the apex is denied. A denied apex costs recall on a domain the
customer almost certainly does not own; an admitted one costs the engagement.

USAGE
    from scope_deny import is_denied, why_denied
    is_denied("wa.me")            -> True
    why_denied("wa.me")           -> "URL shortener / click-to-chat"
    is_denied("abakus-tk.de")     -> False
"""
import re

# ---------------------------------------------------------------- categories
# URL shorteners and click-to-chat. These resolve into a provider's global edge and are the
# highest-yield poison: one link in a footer, thousands of a stranger's hosts.
SHORTENERS = {
    "wa.me", "api.whatsapp.com", "chat.whatsapp.com", "wa.link",
    "t.me", "telegram.me", "telegram.dog",
    "bit.ly", "bitly.com", "goo.gl", "tinyurl.com", "ow.ly", "buff.ly", "rebrand.ly",
    "cutt.ly", "shorturl.at", "rb.gy", "is.gd", "s.id", "lnkd.in", "fb.me", "m.me",
    "youtu.be", "amzn.to", "spoti.fi", "linktr.ee", "linkin.bio", "bio.link", "taplink.cc",
    "qr.link", "qrco.de", "short.io", "tiny.cc", "trib.al", "dlvr.it", "ift.tt",
}

# Social, video and community platforms.
SOCIAL = {
    "facebook.com", "fb.com", "instagram.com", "threads.net", "whatsapp.com", "whatsapp.net",
    "twitter.com", "x.com", "t.co", "linkedin.com", "xing.com", "kununu.com",
    "youtube.com", "vimeo.com", "tiktok.com", "snapchat.com", "pinterest.com", "pinterest.de",
    "reddit.com", "tumblr.com", "flickr.com", "twitch.tv", "discord.com", "discord.gg",
    "mastodon.social", "bsky.app", "vk.com", "ok.ru", "weibo.com", "wechat.com", "line.me",
    "signal.org", "skype.com", "viber.com",
}

# Booking, forms, marketing and generic SaaS a company merely USES. Note these are distinct
# from shodan_recon.TENANT_APEX, where <brand>.<vendor> IS the customer's own instance and is
# deliberately in scope. Nothing here has that property: calendly.com/jsmith is not an estate.
SAAS_TOOLS = {
    "calendly.com", "doodle.com", "eventbrite.com", "eventbrite.de", "meetup.com",
    "typeform.com", "surveymonkey.com", "jotform.com", "forms.gle", "google.com",
    "docs.google.com", "drive.google.com", "maps.google.com", "goo.maps",
    "mailchimp.com", "sendinblue.com", "brevo.com", "hubspot.com", "salesforce.com",
    "zoom.us", "teams.microsoft.com", "webex.com", "gotomeeting.com",
    "trustpilot.com", "provenexpert.com", "google.de", "bing.com", "yelp.com",
    "paypal.com", "paypal.me", "stripe.com", "klarna.com", "sofort.com",
    "wordpress.org", "wordpress.com", "elementor.com", "wix.com", "squarespace.com",
    "shopify.com", "jimdo.com", "webflow.com", "typo3.org", "joomla.org", "drupal.org",
}

# Platform, CDN, cloud, tooling and standards infrastructure.
INFRA = {
    "google.com", "gstatic.com", "googleapis.com", "googletagmanager.com", "google-analytics.com",
    "doubleclick.net", "gmail.com", "apple.com", "icloud.com", "microsoft.com", "office.com",
    "office365.com", "live.com", "outlook.com", "windows.net", "azure.com", "amazonaws.com",
    "aws.amazon.com", "cloudflare.com", "cloudfront.net", "akamai.com", "akamaized.net",
    "fastly.net", "jsdelivr.net", "unpkg.com", "jquery.com", "bootstrapcdn.com",
    "adobe.com", "typekit.net", "fontawesome.com", "gravatar.com", "cookiebot.com",
    "usercentrics.eu", "onetrust.com", "consentmanager.net", "borlabs.io",
    "github.com", "gitlab.com", "bitbucket.org", "sourceforge.net", "npmjs.com",
    "w3.org", "schema.org", "creativecommons.org", "mozilla.org", "whatwg.org",
    "ietf.org", "iana.org", "unicode.org", "openstreetmap.org", "wikipedia.org",
    "wikimedia.org", "archive.org", "europa.eu", "bund.de", "bsi.bund.de", "gesetze-im-internet.de",
    "yahoo.com", "duckduckgo.com", "ecosia.org", "gmx.net", "web.de", "t-online.de",
}

# Media. A structure or holding page routinely links a press mention. A newspaper is never a
# Mittelstand subsidiary. spiegel.de reached the live angermann.de run exactly this way.
MEDIA = {
    "spiegel.de", "handelsblatt.com", "faz.net", "welt.de", "zeit.de", "sueddeutsche.de",
    "manager-magazin.de", "wiwo.de", "immobilien-zeitung.de", "iz.de", "thomas-daily.de",
    "bloomberg.com", "reuters.com", "ft.com", "wsj.com", "forbes.com", "cnbc.com",
    "n-tv.de", "ard.de", "zdf.de", "dpa.com", "presseportal.de", "finanzen.net",
    "heise.de", "golem.de", "computerwoche.de", "crn.de", "funkschau.de", "channelpartner.de",
}

DENY_APEX = SHORTENERS | SOCIAL | SAAS_TOOLS | INFRA | MEDIA

_REASON = [
    (SHORTENERS, "URL shortener / click-to-chat"),
    (SOCIAL,     "social or messaging platform"),
    (SAAS_TOOLS, "third-party SaaS the customer merely uses"),
    (INFRA,      "platform, CDN or standards infrastructure"),
    (MEDIA,      "media outlet"),
]

# Shape-based catch-all for shorteners this list has not met yet: a ONE- or TWO-character label
# on a ccTLD that the shortener industry lives on (wa.me, t.me, t.co, rb.gy, is.gd, ow.ly).
# Deliberately narrow. An earlier draft allowed three characters and .io/.ai/.it, which would have
# denied a real startup's domain -- and a false denial silently shrinks a customer's estate, which
# is the failure mode this whole engine exists to avoid. Anything longer must be named explicitly.
_SHORT_SHAPE = re.compile(r"^[a-z0-9]{1,2}\.(me|ly|gy|gd|co|to|cc)$")


def is_denied(apex):
    """True if this registrable apex may never enter scope. Fails closed on junk input."""
    a = (apex or "").strip().lower().rstrip(".")
    if not a or "." not in a:
        return True
    if a in DENY_APEX:
        return True
    if _SHORT_SHAPE.match(a):
        return True
    return False


def why_denied(apex):
    """Human-readable reason, for the log line and for clarify.py. '' if not denied."""
    a = (apex or "").strip().lower().rstrip(".")
    if not a or "." not in a:
        return "not a registrable domain"
    for bucket, reason in _REASON:
        if a in bucket:
            return reason
    if _SHORT_SHAPE.match(a):
        return "URL shortener (short label on a shortener ccTLD)"
    return ""


def filter_apexes(apexes):
    """(kept, [(apex, reason), ...]) — convenience for callers that log what they dropped."""
    kept, dropped = [], []
    for a in apexes or []:
        if is_denied(a):
            dropped.append((a, why_denied(a) or "denied"))
        else:
            kept.append(a)
    return kept, dropped


if __name__ == "__main__":
    import sys
    for a in sys.argv[1:] or ["wa.me", "t.me", "abakus-tk.de", "netbid.com", "spiegel.de", "rb.gy"]:
        print("%-24s %-7s %s" % (a, "DENIED" if is_denied(a) else "ok", why_denied(a)))
