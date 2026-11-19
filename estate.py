#!/usr/bin/env python3
"""estate.py — WHICH SITES EXIST. One home, because this value had nine of them.

WHY THIS FILE EXISTS (19 Nov 2026)
    jev.best and the two klimaanlage domains were retired. Finding every place that still
    believed in them took a derived sweep across 63 tracked files, and the list of live sites
    turned out to be written down independently in: the uptime workflow, caddyguard's probe loop,
    caddyguard's certificate loop, the vhost roster in the caddy agent, authz_audit's route map,
    fleet.py's project table, webapp/backend/app/fleet.py's project table, perseus's rollout
    targets, and perseus/hub.py's log sources.

    Nine homes for one fact. Class 32 says the newer one always loses, and it did: the uptime
    workflow kept alerting on a site nobody runs, while observemove.py refused to start because
    its own copy of the list said jev.best should answer 200. It answers 502, and has for weeks,
    because the project is gone.

    A retired site is not deleted from history here. It moves to RETIRED with the date, so the
    next person reading a 2026-10 incident about jev.best can tell "this was ours and is gone"
    from "this was never ours".

HOW TO RETIRE A SITE
    Move its entry from LIVE to RETIRED, with the date. Then `python observemove.py --apply`
    takes the vhost off the shared proxy, and every list above follows from this file.
"""

# host -> (url to probe, codes that mean healthy). The probe is part of the definition: a site
# nobody checks is a site that can die quietly, which is how klimaanlage sat at 502.
LIVE = {
    "cybergod.ai":        ("https://cybergod.ai/", ("200",)),
    "www.cybergod.ai":    ("https://www.cybergod.ai/", ("200", "301", "302", "308")),
    "jobhuntwow.com":     ("https://jobhuntwow.com/", ("200", "301", "302", "308")),
    "www.jobhuntwow.com": ("https://www.jobhuntwow.com/", ("200", "301", "302", "308")),
    "s4biz.io":           ("https://s4biz.io/api/health", ("200",)),
    "www.s4biz.io":       ("https://www.s4biz.io/", ("200", "301", "302", "308")),
}

# Routes that are not their own host but must still answer. Grafana moved here from godeyes.ai.
LIVE_PATHS = {
    "cybergod.ai/api/me":  ("https://cybergod.ai/api/me", ("401",)),
    "cybergod.ai/observe": ("https://cybergod.ai/observe/", ("200", "301", "302")),
}

# name -> (date retired, why). Kept, not deleted: it is the difference between "gone" and
# "never ours", and every diagnostic that reads a stale roster needs to be able to tell them apart.
RETIRED = {
    "godeyes.ai":                   ("2026-11-21", "domain not renewed; Grafana moved to "
                                                   "cybergod.ai/observe"),
    "jev.best":                     ("2026-11-19", "project ended"),
    "www.jev.best":                 ("2026-11-19", "project ended"),
    "klimaanlage-preise.de":        ("2026-11-19", "project ended"),
    "www.klimaanlage-preise.de":    ("2026-11-19", "project ended"),
    "klimaanlage-montieren.de":     ("2026-11-19", "project ended"),
    "www.klimaanlage-montieren.de": ("2026-11-19", "project ended"),
}

# The projects that still stamp events and still get a perseus sidecar. `service` is what the
# project writes on its OWN event lines, never the container name: jev-api was the container and
# it stamped service=jev-web, and looking for the container name is why fleet.py once reported a
# live project as silent.
PROJECTS = [
    {"key": "colt-web", "name": "cybergod.ai",    "service": "colt-web"},
    {"key": "jhw-web",  "name": "jobhuntwow.com", "service": "jhw-web"},
    {"key": "s4biz-web", "name": "s4biz.io",      "service": "s4biz-web", "own_log": "s4biz_events"},
]


def watch_list():
    """[(label, url, acceptable codes)] for every live host AND path. Used by observemove and by
    anything else that needs a baseline, so a retired site can never block a deploy again."""
    out = [(h, u, c) for h, (u, c) in sorted(LIVE_PATHS.items())]
    out += [(h, u, c) for h, (u, c) in sorted(LIVE.items())]
    return out


def expected_vhosts():
    """The hostnames the shared proxy should be serving. A name here and absent on the box is a
    FAILURE; a name on the box and absent here is a WARNING that names its fragment."""
    return sorted(LIVE)


def is_retired(host):
    return host.lower().lstrip("*.") in RETIRED


if __name__ == "__main__":
    print("LIVE (%d):" % len(LIVE))
    for h in expected_vhosts():
        print("   %-24s %s" % (h, LIVE[h][0]))
    print("\nPATHS (%d):" % len(LIVE_PATHS))
    for k, (u, c) in sorted(LIVE_PATHS.items()):
        print("   %-24s %-34s %s" % (k, u, "|".join(c)))
    print("\nRETIRED (%d):" % len(RETIRED))
    for h, (when, why) in sorted(RETIRED.items()):
        print("   %-30s %s  %s" % (h, when, why))
