# Counting visitors against bots, and wiring every alarm to Telegram

> A portable reference. Everything here is running in production on cybergod.ai, jobhuntwow.com,
> jev.best, klimaanlage-preise.de and s4biz.io. The code is standard library only and assumes
> nothing about your framework beyond "you can run something per request".
>
> Version 1.1 · 21 September 2026

---

## 0. The one idea, before any code

**A claim is evidence only when contradicting it costs the attacker something.**

Everything below follows from that sentence. A `User-Agent` header costs nothing to fake, so it can
never be the thing that convinces you a human arrived. Making a Python or Go HTTP client actually
emit the header set a real browser emits costs real engineering work. That asymmetry is the whole
game.

The second idea, which is less obvious and matters more in practice:

**Never use two buckets. Use three.** Visitor, bot, and *not determinable*. The moment you force
every request into human-or-robot you start inventing answers for requests you did not measure, and
a dashboard that confidently reports a wrong number is worse than one that admits a gap.

---

## PART 1: COUNTING VISITORS AGAINST BOTS

## 1. How most people get this wrong

Here is the defect, in the shape it usually takes:

```python
visitors = len({line["ip"] for line in http_lines_last_24h})
```

That counts distinct source addresses and calls the answer "visitors". One `curl` is one visitor. A
scanner is one visitor. An AI training crawler is one visitor. This exact line was in production on
our own admin page for months while the operator looked at the number and wondered why it felt
wrong.

The fix is not to add a user-agent filter. The user-agent is the thing you cannot trust.

## 2. The evidence hierarchy

Rank your signals by what it costs an attacker to fake them. Use the cheap ones for labelling and
the expensive ones for judgement.

| Tier | Signal | Cost to fake | Use it for |
|---|---|---|---|
| 0 | User-Agent string | Zero. One header | Labelling honest clients only |
| 1 | Requested path | Zero, but reveals intent | Attack detection. This is your best single signal |
| 2 | Fetch-metadata headers | Low but non-zero. Must be researched and added | Browser-vs-script |
| 3 | HTTP protocol version | Moderate. Needs a real HTTP/2 stack | Browser-vs-script |
| 4 | Asset-fetch pattern | High. Costs bandwidth and a real parser | Browser-vs-script |
| 5 | TLS fingerprint (JA3/JA4) | High. Needs a patched TLS stack | Strong, but needs proxy support |

A useful property of tiers 2 to 4: they are all **server-side**. No JavaScript, no client
cooperation, no privacy escalation, no new open port.

## 3. The three buckets

```
VISITOR    the record carries evidence, and nothing contradicted itself
CLIENT     self-identified bot, OR the record contradicted itself
UNJUDGED   the record did not carry the fields to look at
```

**Precedence runs one way only.** An address seen once as a bot, or once contradicting itself, is a
client for the whole window even if its other requests looked like a browser. A scanner that also
fetches your homepage with a clean header set must not buy itself a place in the visitor count. The
reverse promotion is never done.

```python
browsers = browsers_seen - clients_seen
unjudged = unjudged_seen - clients_seen - browsers
```

## 4. What to log per request

Log these fields on every request. They are the raw material for everything else.

| Field | Value | Why |
|---|---|---|
| `ip` | Client address, from `CF-Connecting-IP`, then first `X-Forwarded-For`, then `X-Real-IP`, then the socket peer | Identity for the window |
| `path` | Path only, truncated | Tier 1 evidence |
| `status` | Response code | 404 variety is the scanner tell |
| `method` | Verb | `PUT`/`DELETE`/`TRACE` on a read-only site is a signal |
| `ua` | Raw User-Agent, truncated to about 220 chars | Tier 0, for labelling only |
| `bot` | Boolean from the UA table below | Honest clients |
| `sf` | Bitmask of which fetch-metadata headers were present | Tier 2 |
| `hv` | HTTP protocol version | Tier 3 |
| `hvs` | **Whose** version `hv` describes. See section 7, this field is the trap | Tier 3 |
| `av` | Distinct static assets this address fetched recently. One-way positive, see section 8 | Tier 4 |
| `ref` | Referer, truncated | Referrer spam detection |
| `ts` | Timestamp | Use **milliseconds**, not seconds. See section 11 |

Two rules on this record:

- **Presence, never values, for the fetch-metadata headers.** You want to know the client sent
  `Sec-Fetch-Mode`, not what it said. The values carry navigation context you have no business
  keeping next to an IP address.
- **`sf` absent and `sf == 0` are different facts.** Absent means the line predates your change and
  you never looked. Zero means you looked and the client sent none of them. Collapsing the two is
  the same confident wrong number you are trying to eliminate.
- **The same rule applies to `av`**, with one difference worth knowing: `av == 0` is not a signal
  in either direction, because asset correlation only ever confirms. See section 8.

## 5. Tier 0: the honest-client table

This catches clients that are not pretending. It is not a security control, it is a courtesy to
clients that identify themselves.

```python
_BOTS = (
    ("googlebot", "Googlebot"), ("bingbot", "bingbot"), ("duckduckbot", "DuckDuckBot"),
    ("yandexbot", "YandexBot"), ("baiduspider", "Baiduspider"), ("slurp", "Yahoo Slurp"),
    ("applebot", "Applebot"), ("linkedinbot", "LinkedInBot"), ("twitterbot", "Twitterbot"),
    ("facebookexternalhit", "Facebook"), ("slackbot", "Slackbot"), ("telegrambot", "TelegramBot"),
    ("whatsapp", "WhatsApp"), ("discordbot", "Discordbot"),
    ("gptbot", "GPTBot"), ("claudebot", "ClaudeBot"), ("ccbot", "CCBot"),
    ("perplexitybot", "PerplexityBot"), ("bytespider", "Bytespider"),
    ("ahrefsbot", "AhrefsBot"), ("semrushbot", "SemrushBot"), ("mj12bot", "MJ12bot"),
    ("dotbot", "DotBot"), ("petalbot", "PetalBot"),
    ("curl", "curl"), ("wget", "wget"), ("python-requests", "python-requests"),
    ("python-urllib", "urllib"), ("go-http-client", "Go"), ("java/", "Java"),
    ("okhttp", "OkHttp"), ("axios", "axios"), ("node-fetch", "node-fetch"),
    ("headlesschrome", "HeadlessChrome"), ("phantomjs", "PhantomJS"),
    ("masscan", "masscan"), ("nmap", "nmap"), ("zgrab", "zgrab"), ("nuclei", "nuclei"),
)

_BROWSER = ("edg/", "opr/", "chrome/", "crios/", "firefox/", "fxios/", "safari/")
_OS = ("windows", "macintosh", "mac os", "linux", "android", "iphone", "ipad", "cros")


def classify_ua(ua):
    """-> dict. Labelling only. The header is attacker-controlled."""
    u = (ua or "").lower()
    if not u.strip():
        return {"bot": True, "bot_name": "no-user-agent"}
    for token, name in _BOTS:
        if token in u:
            return {"bot": True, "bot_name": name}
    has_browser = any(t in u for t in _BROWSER)
    has_os = any(t in u for t in _OS)
    # A string claiming neither an engine nor a platform is not a browser, whatever it says.
    if not has_browser and not has_os:
        return {"bot": True, "bot_name": "unknown-client"}
    return {"bot": False, "bot_name": ""}
```

Two details worth keeping: an **empty** User-Agent is a bot, and a string carrying **neither an
engine token nor an OS token** is a bot. Those two catch a surprising share of lazy scrapers.

## 6. Tier 2: fetch metadata, the signal that does the work today

Every current browser sends `Sec-Fetch-Site`, `Sec-Fetch-Mode` and `Sec-Fetch-Dest` on a
navigation. Scripted HTTP clients almost never do unless someone deliberately added them.

```python
SF_SITE, SF_MODE, SF_DEST, SF_CHUA = 1, 2, 4, 8
FETCH_METADATA_BITS = SF_SITE | SF_MODE | SF_DEST

_SF_HEADERS = (("sec-fetch-site", SF_SITE), ("sec-fetch-mode", SF_MODE),
               ("sec-fetch-dest", SF_DEST), ("sec-ch-ua", SF_CHUA))


def sf_mask(get_header):
    """-> int bitmask of which headers were PRESENT. Never raises."""
    mask = 0
    try:
        for name, bit in _SF_HEADERS:
            if get_header(name) is not None:
                mask |= bit
    except Exception:
        return 0
    return mask
```

**`sec-ch-ua` is deliberately excluded from the required set.** It is a Client Hint, Chromium only,
and Firefox and Safari never send it. Requiring it would flag every Firefox user on your site.
Record it as a fourth bit because it is free and it is positive corroboration when present.

**Per-engine floors, because the feature shipped on different dates.** Below its floor a browser
genuinely did not send these headers, and you must say nothing at all.

```python
FETCH_METADATA_SINCE = {
    "chrome": 76,      # Aug 2019
    "edge": 79,        # Jan 2020, the first Chromium Edge
    "opera": 63,       # Chromium 76
    "firefox": 90,     # Jul 2021
    "safari": (16, 4), # Mar 2023, the late one, and why Safari needs a (major, minor) tuple
}
```

**Fire on none of the three, not on fewer than three.** A middlebox that strips one header must not
convict a real person.

## 7. Tier 3: the HTTP version trap, and this is the one that will catch you

The idea is sound: a client claiming Chrome 131 that speaks HTTP/1.1 to a TLS endpoint offering h2
is contradicting itself, because real browsers negotiate h2.

**The trap:** if you sit behind a reverse proxy, the protocol version your application sees is the
**proxy-to-application** hop, not the client. Caddy and nginx terminate TLS and open a fresh
upstream connection, and most Python application servers implement no HTTP/2 at all. So your
framework reports `1.1` for a Chrome user, a Firefox user and a Go program alike.

A check built on that fires on 100% of real browsers. It looks like a working check and it is a
check that cannot fail, pointed the wrong way. We wrote exactly that and caught it in review.

**The fix is to record whose version it is:**

```python
HV_FROM_CLIENT = "p"   # a proxy that actually saw the client told us
HV_FROM_HOP    = "s"   # the local hop only. Says NOTHING about the client
HV_CLIENT_HEADER = "x-client-proto"
```

Have the proxy tell you. One line in Caddy:

```
reverse_proxy app:8000 {
    header_up X-Client-Proto {http.request.proto}
}
```

nginx:

```
proxy_set_header X-Client-Proto $server_protocol;
```

Until that line exists, the check must report **not determinable** rather than inventing a verdict.
Ours ships dormant and says so in its own docstring.

## 8. Tier 4: asset correlation, and this one only ever points in a single direction

A browser that opens your page then pulls the JS bundle, the stylesheet, the manifest and the icons
within a second or two is doing something an HTTP client that fetches the HTML and stops cannot
imitate without becoming a browser. That is the strongest server-side proof of a rendering engine
you can get without JavaScript, and most people throw it away, because the first thing everybody
does is filter static assets out of the request log.

Filtering them out of the LOG is right. A subresource is not a page visit, and logging every icon
drowns the file. What is wrong is discarding the fact along with the line.

### The rule, and it is not negotiable

**This signal is one-way positive. It may confirm that a browser engine rendered the page. It may
never be used to conclude that something is a script.**

Three legitimate populations sit at zero assets, and between them they cover most real traffic:

- The **first navigation** from any address has no assets behind it yet. The subresources arrive
  after you already logged the navigation.
- A **cached repeat visit** fetches nothing. Warm disk cache, or a service worker answering from
  its own cache, means zero requests for a bundle the browser already has.
- A **page served fully inline** fetches nothing. So does a redirect, a 404, a JSON route, and
  anybody who pasted a URL to something that is not an HTML page.

So `assets >= threshold` is evidence of a browser, and `assets == 0` is evidence of nothing at all.
This is the same absence-of-evidence rule as everywhere else in this document, and it is the one
place where getting it backwards would hurt real people at scale: invert it and you start filing
most first-time visitors as scripts.

The useful consequence of the constraint is that the signal **cannot produce a false positive
against a real person by construction**. The worst a wrong answer can do is leave an address in the
unjudged bucket, which is where it already was. That asymmetry is why it is worth having.

### What it is actually worth, without the sales pitch

It confirms a **browser engine**, not a human. A full headless browser driven by Playwright or
Puppeteer fetches the CSS, the bundle and the icons exactly as Chrome does, because it is Chrome,
and this signal will confirm it. Combine it with tier 0, which already flags the automation user
agents, and with tier 1, which is where a scraper's intent shows up.

What it does defeat is the large and cheap population of scrapers built on a plain HTTP client:
requests, urllib, Go's net/http, curl in a loop. Those fetch the HTML and stop, because parsing the
document and resolving subresources is work nobody writes unless they have to. That population is
most of what hits a small site, so the gain is real. It is not a bot-proof test and you should not
describe it as one.

### The ledger

An in-memory map, standard library only, no persistence, no background thread.

```python
import threading, time

# How long after a navigation an asset still counts. Be generous: slow connections, lazy
# loading, deferred fonts, a service worker registering after first paint. Every error in the
# generous direction costs nothing; every error in the tight direction deletes the signal for
# exactly the visitors who most deserve the benefit of the doubt.
WINDOW_S = 120

# The floor that confirms a browser. MEASURE THIS, do not guess it: open your own built page and
# count the distinct same-origin subresources a cold view actually pulls. Ours pulls six (bundle,
# stylesheet, manifest, favicon, SVG icon, service worker), so three is comfortably below what a
# real page produces and comfortably above the one or two an opportunistic scraper reaches by
# following the first script tag it sees.
MIN_ASSETS = 3

# Hard ceiling on addresses held. A source-rotating flood is the expected attack on any in-memory
# map keyed by IP, and this must not become the outage. Evict oldest-touched first.
MAX_TRACKED = 4096

# Ceiling on distinct paths per address. The only question ever asked is "at or above the floor",
# so more than a handful buys nothing. Keep it several times the floor so the cap can never hide
# a confirmation.
MAX_PATHS_PER_IP = 16

_LOCK = threading.Lock()
_SEEN = {}        # ip -> {path: last_seen_ts}
_LAST = {}        # ip -> last_seen_ts, so eviction never scans the inner dicts
_SWEPT = [0.0]


def _prune(now):
    """Expiry, then the ceiling. Caller holds the lock."""
    pressure = len(_SEEN) > MAX_TRACKED
    if not pressure and (now - _SWEPT[0]) < 30:
        return
    _SWEPT[0] = now
    for ip in [k for k, t in _LAST.items() if (now - t) >= WINDOW_S]:
        _SEEN.pop(ip, None); _LAST.pop(ip, None)
    if len(_SEEN) > MAX_TRACKED:
        keep = MAX_TRACKED - (MAX_TRACKED // 8)          # evict in batches, not one at a time
        for ip, _t in sorted(_LAST.items(), key=lambda kv: kv[1])[:len(_SEEN) - keep]:
            _SEEN.pop(ip, None); _LAST.pop(ip, None)


def note(ip, path, now=None):
    """Called for every request whose path is a static asset. WRITES NOTHING. Never raises."""
    try:
        if not ip or not path:
            return
        now = time.time() if now is None else float(now)
        key, who = str(path)[:160], str(ip)[:64]
        with _LOCK:
            paths = _SEEN.setdefault(who, {})
            paths[key] = now                              # DISTINCT paths, or one image on a
            _LAST[who] = now                              # retry loop confirms a browser alone
            for p in [p for p, t in paths.items() if (now - t) >= WINDOW_S]:
                paths.pop(p, None)
            if len(paths) > MAX_PATHS_PER_IP:
                excess = len(paths) - MAX_PATHS_PER_IP
                for p, _t in sorted(paths.items(), key=lambda kv: kv[1])[:excess]:
                    paths.pop(p, None)
            _prune(now)
    except Exception:
        return                                            # fail open, always


def evidence(ip, now=None):
    """-> distinct assets inside the window. Never raises, 0 on any error.

    ZERO IS NOT A FINDING. The only permitted reading is `>= MIN_ASSETS -> a browser engine
    rendered the page`."""
    try:
        now = time.time() if now is None else float(now)
        with _LOCK:
            paths = _SEEN.get(str(ip)[:64])
            return sum(1 for t in paths.values() if (now - t) < WINDOW_S) if paths else 0
    except Exception:
        return 0
```

Four things about that code are load-bearing:

- **Prune on write, never on a timer.** A background thread is a thread to leak, and a leaked
  thread in the request path of every site you run is a worse failure than the memory it saves.
- **Batch the eviction.** Dropping one entry at a time means a sustained flood pays for a sort on
  every single request. Dropping an eighth of the table at once amortises it.
- **Take the lock.** Both callers are concurrent. The insert itself is safe under CPython's GIL;
  the read-modify-write inside the prune is not, and an unlocked build leaves the ceiling exceeded
  or raises mid-iteration. We measured it: zero violations locked, several hundred unlocked, over
  the same workload.
- **Never raise.** This runs inside the observer of every request. An error here is a fact about
  you, not about the client.

### Wiring it in

At the exact point where your emitter currently drops a static asset, record it first, then drop
the line as before.

```python
if SKIP_PATH_RE.search(path):
    asset_trace.note(client_ip(request), path)
    return                       # still no log line. That is the whole affordability argument.
```

And on a navigation that you do log, carry the derived count:

```python
ev["av"] = asset_trace.evidence(ip)      # omit the key entirely if the ledger is unavailable
```

`av` absent and `av == 0` are different facts, exactly as `sf` already distinguishes them. Absent
means nobody looked. Never default it, or every line you wrote before today silently changes
meaning.

### Where it goes in the precedence

Tier 4 adds one rung, and the order matters more than the rung does:

```
1. self-identified bot, or a contradiction recorded  ->  CLIENT, wins over everything
2. av >= MIN_ASSETS                                  ->  BROWSER, confirmed
3. fetch metadata determinable, no contradiction     ->  BROWSER, inferred
4. otherwise                                         ->  UNJUDGED
```

Rung 1 stays on top: a crawler that renders pages in a real engine and says so is still a client,
and asset evidence buys it nothing. Rung 2 sits above rung 3 because it is the stronger fact, and
worth distinguishing in your payload so a dashboard can say which half of the visitor count was
proved rather than inferred.

**A low or zero `av` moves nothing.** It never takes an address out of the browser bucket and it
never puts one into the client bucket. All it does is shrink the unjudged bucket, which is the
entire point: it makes the other two numbers honest without making either of them larger.

Two things to assert in your tests, because they are the two that go wrong:

- An HTTP client that fetched only the HTML lands in **unjudged**, not in clients. Name the bucket
  in the assertion.
- A self-identified bot that also fetched every asset is still a **client**. Precedence holds.

## 9. Putting it together

```python
REASON_HTTP11 = "claims_h2_browser_but_spoke_http11"
REASON_NO_FETCH_METADATA = "claims_modern_browser_but_sent_no_fetch_metadata"
EXEMPT_PREFIXES = ("/api/", "/.well-known/")


def evaluate(ev):
    """-> (reasons, determinable). Reads one logged record. Never raises, never enforces."""
    try:
        if not isinstance(ev, dict):
            return (), False
        path = ev.get("path") or ""
        if path.startswith(EXEMPT_PREFIXES):
            return (), False
        # Already counted once. An honest curl is a client by tier 0; do not double-count it.
        if ev.get("bot"):
            return (), False

        engine = claimed_engine(ev.get("ua"))      # -> ("chrome", 131) or None
        if engine is None:
            return (), False

        name, version = engine
        reasons = []
        determinable = False

        sf = ev.get("sf")
        if sf is not None and _at_or_above(name, version, FETCH_METADATA_SINCE):
            determinable = True
            if not (int(sf) & FETCH_METADATA_BITS):
                reasons.append(REASON_NO_FETCH_METADATA)

        hv, hvs = ev.get("hv"), ev.get("hvs")
        if hv and hvs == HV_FROM_CLIENT and _at_or_above(name, version, H2_EXPECTED_SINCE):
            determinable = True
            if str(hv).startswith("1."):
                reasons.append(REASON_HTTP11)

        return tuple(reasons), determinable
    except Exception:
        return (), False        # fail open, always
```

Then the counting:

```python
for ev in last_24h:
    ip = ev.get("ip")
    if not ip:
        continue
    addresses.add(ip)
    if ev.get("bot"):
        clients.add(ip); continue
    reasons, determinable = evaluate(ev)
    if reasons:
        clients.add(ip)
    elif determinable:
        browsers.add(ip)
    else:
        unjudged.add(ip)

visitors = browsers - clients
unjudged = unjudged - clients - visitors
```

## 10. Order matters: parse the User-Agent in the right sequence

Edge's UA contains `Chrome/`. Opera's contains both. iOS Chrome calls itself `CriOS`. Matching
`Chrome/` first files every Edge user as Chrome and compares them against the wrong floor.

```
Edge (edg/)  ->  Opera (opr/)  ->  Chrome (chrome/|crios/)  ->  Firefox  ->  Safari
```

Legacy `Edge/18` is EdgeHTML, a different engine that sends no fetch metadata. Match `edg/` only,
so legacy Edge falls through unmatched and gets no verdict.

Also refuse to judge anything matching `headless|phantomjs|electron/|puppeteer|playwright|selenium`.
Those are already bots by tier 0.

## 11. What NOT to do. Each of these cost us a cycle

- **Do not log timestamps in whole seconds.** It destroys inter-arrival timing, which is one of the
  strongest human-vs-script signals you will ever have. Use milliseconds.
- **Do not filter static assets out of your log before correlating them.** Dropping the LINE is
  right, a subresource is not a page visit. Dropping the FACT is the mistake: the same address
  fetching the HTML and then the bundle and the icons is the best server-side proof of a browser
  engine you can get. Section 8 is the in-memory ledger that keeps the fact at zero log cost.
- **Do not let a zero asset count accuse anybody.** This is the same mistake one sign over, and it
  is worse, because it fires on a first navigation, on a cached repeat visit and on any page served
  inline. Asset correlation confirms; it never convicts.
- **Do not let a contradiction block anything.** These are weak signals with a large legitimate
  population behind them. Corporate middleboxes, old browsers, privacy extensions. Label, never
  enforce.
- **Do not let a rate limit convict.** Automation on legitimate paths is not an attack. A
  monitoring check hitting your health endpoint every ten seconds is not a scanner.
- **Do not count a refused request as a visitor.** If you serve bots a 404, those requests are
  still in your log. We counted them for months.

### The privacy line, and it is not optional in the EU

An IP address is personal data (GDPR; CJEU C-582/14 *Breyer*). Everything above is derived from
requests the client sent you voluntarily, which is defensible under legitimate interest for
security purposes with a notice.

**Techniques that unmask a user behind a VPN are a different category.** WebRTC STUN/TURN
disclosure and QUIC/UDP leak checks deliberately reveal an address the user chose to hide. If you
are tempted: they need JavaScript to run, so they never see scripted clients at all; they flag
corporate networks that block UDP, Safari, and anyone using a privacy extension; and they require
you to run a TURN relay, which is new infrastructure and new attack surface. We evaluated it and
rejected it. The header-based signals above cost nothing and unmask nobody.

If you want correlation without the identifier, store a salted hash of the address rather than the
address.

---

## PART 2: TELEGRAM ALERTS

## 12. Getting the two values you need

**The bot token.** Message `@BotFather` on Telegram, send `/newbot`, pick a name and a username
ending in `bot`. It replies with a token shaped like `8123456789:AAH...`. That token is a
credential. It goes in an environment file with mode 600, never in git.

**Your chat id.** Three ways, easiest first:

1. Message `@userinfobot`. It replies with your numeric id.
2. Send any message to your new bot, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and read
   `result[0].message.chat.id`.
3. For a group: add the bot to the group, send a message, call `getUpdates` the same way. **Group
   ids are negative**, for example `-1001234567890`. Keep the minus sign.

A bot cannot message you first. **You must send it one message before it can ever reach you.** This
is the single most common reason a correctly configured alert pipeline is silent.

## 13. Environment

```bash
# /opt/yourapp/.env   (chmod 600)
BOT_TOKEN=8123456789:AAH...
ALERT_TG_CHAT=123456789              # comma-separated for several recipients
ALERTS_ENABLED=1
ALERT_COOLDOWN=900                   # seconds, per rule per subject
ALERT_STORM_CAP=12                   # maximum alerts per hour, all rules
```

| Variable | Default | What it does |
|---|---|---|
| `BOT_TOKEN` | none | BotFather token. No token means no Telegram, silently |
| `ALERT_TG_CHAT` | none | Comma-separated chat ids. Explicit always wins |
| `ALERTS_ENABLED` | `1` | Global off switch |
| `ALERT_COOLDOWN` | `900` | One alert per rule per subject per this many seconds |
| `ALERT_STORM_CAP` | `12` | Hard ceiling per hour across every rule |

## 14. The sender. Standard library, no dependencies

```python
import json, os, time, urllib.parse, urllib.request

TG_TOKEN = os.environ.get("BOT_TOKEN", "")
ALERT_CHAT = os.environ.get("ALERT_TG_CHAT", "")
API = "https://api.telegram.org/bot%s/sendMessage"


def _chats():
    return [c.strip() for c in ALERT_CHAT.split(",") if c.strip()]


def telegram(text, reply_markup=None):
    """Send to every configured chat. Returns True if at least one delivery succeeded."""
    if not TG_TOKEN:
        return False
    ok = False
    for chat in _chats():
        try:
            payload = {"chat_id": chat, "text": text[:3900],
                       "disable_web_page_preview": "true"}
            if reply_markup is None:
                payload["parse_mode"] = "Markdown"
            else:
                # MARKDOWN IS DROPPED WHEN A KEYBOARD IS ATTACHED. An attacker-supplied path can
                # contain _ or *, Telegram then rejects the whole message as malformed entities,
                # and the alert that matters most is the one that silently never arrives.
                payload["reply_markup"] = json.dumps(reply_markup)
            data = urllib.parse.urlencode(payload).encode()
            req = urllib.request.Request(API % TG_TOKEN, data=data)
            with urllib.request.urlopen(req, timeout=12) as r:
                ok = (r.status == 200) or ok
        except Exception as exc:
            print(json.dumps({"evt": "alert_delivery", "channel": "telegram",
                              "chat": str(chat), "result": "error",
                              "err": repr(exc)[:160]}), flush=True)
    return ok
```

Four things in there that were each paid for:

- **`text[:3900]`.** Telegram's limit is 4096 and it rejects the whole message if you exceed it.
- **`parse_mode` only when there is no keyboard.** An attacker controls the path string that ends
  up in your alert. A stray `_` makes Telegram reject the message. You lose exactly the alert you
  needed.
- **`timeout=12`.** Never make a network call from an alert path without one.
- **Log the failure.** An alert nobody receives is not an alert, and a silent `except: pass` here
  means you will believe you are covered when you are not.

## 15. Cooldown and storm cap. Do not skip this

An alert that fires on every request trains you to ignore the one that matters.

```python
from collections import deque

COOLDOWN = int(os.environ.get("ALERT_COOLDOWN", 900))
STORM_CAP = int(os.environ.get("ALERT_STORM_CAP", 12))
ENABLED = os.environ.get("ALERTS_ENABLED", "1") != "0"

_sent = {}
_storm = deque()


def fire(rule, subject, title, lines, severity="HIGH"):
    """Send once per COOLDOWN per (rule, subject), never more than STORM_CAP per hour."""
    if not ENABLED:
        return False
    now = time.time()
    key = "%s|%s" % (rule, subject)
    if now - _sent.get(key, 0) < COOLDOWN:
        return False
    while _storm and _storm[0] < now - 3600:
        _storm.popleft()
    if len(_storm) >= STORM_CAP:
        print(json.dumps({"evt": "alert_suppressed", "rule": rule,
                          "reason": "storm cap %d/h reached" % STORM_CAP}), flush=True)
        return False
    _sent[key] = now
    _storm.append(now)

    stamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now))
    body = "\n".join(str(x) for x in lines)
    full = "%s\n\nWhen : %s\nRule : %s\n\n%s" % (title, stamp, rule, body)
    print(json.dumps({"evt": "security_alert", "rule": rule, "severity": severity,
                      "subject": str(subject)[:120]}), flush=True)
    return telegram("*%s*\n\n%s" % (title, full))
```

**Key the cooldown on (rule, subject), not on rule alone.** Otherwise one noisy address silences
the alert for a different address that matters.

**Emit a structured log line for every alert AND every suppression.** When somebody asks "why
didn't I get an alert", the suppression line is the answer.

## 16. The rule set, with the thresholds we actually run

Eleven rules. Every threshold is an environment variable so it can be tuned without a deploy.

| Rule | Fires when | Window | Env override |
|---|---|---|---|
| Failed logins | 3 failures from one address | 600 s | `ALERT_FAIL_LOGIN_N` |
| Password spray | 3 distinct emails tried from one address | 900 s | `ALERT_SPRAY_EMAILS_N` |
| OTP brute force | 4 wrong one-time codes | 600 s | `ALERT_OTP_FAIL_N` |
| Job burst | 6 expensive operations from one user | 900 s | `ALERT_ASSESS_N` |
| Distributed flood | 300 requests from 40 distinct addresses | 60 s | `ALERT_DDOS_REQ_N` |
| Single-address burst | 120 requests from one address | 60 s | `ALERT_BURST_IP_N` |
| Path probing | 12 distinct 404s from one address | 300 s | `ALERT_PROBE_404_N` |
| Authorisation probing | 5 responses of 401 or 403 | 300 s | `ALERT_DENY_N` |
| Download burst | 25 file downloads from one user | 600 s | `ALERT_DOWNLOAD_N` |
| Session from many addresses | one session on 3 distinct addresses | 1800 s | `ALERT_SESSION_IP_N` |
| New address for a known user | first sighting | n/a | n/a |

The probe-path list that feeds the probing rule:

```python
_PROBE_PATHS = ("/.env", "/.git", "/wp-", "/wordpress", "/phpmyadmin", "/admin.php",
                "/.aws", "/config.json", "/actuator", "/vendor/", "/xmlrpc.php",
                "/shell", "/cgi-bin", "/.ssh", "/backup", "/.docker",
                "/api/v1/pods", "/solr/", "/struts")
```

**Count distinct paths, not requests.** A real person reloads the same stale bookmark. A scanner
misses hundreds of different paths. Our two heaviest genuine visitors had 439 and 362 404s each,
every one on real routes. Volume alone would have banned two real people.

## 17. A sliding window in six lines

```python
from collections import defaultdict, deque

_w = defaultdict(deque)


def hit(bucket, key, window_s):
    """-> count of events in this bucket for this key inside the window."""
    now = time.time()
    q = _w["%s|%s" % (bucket, key)]
    q.append(now)
    while q and q[0] < now - window_s:
        q.popleft()
    return len(q)


# usage
if hit("fail_login", ip, 600) >= 3:
    fire("fail_login", ip, "Repeated failed logins", [f"Address: {ip}"])
```

Cap the dictionary size or prune it periodically, or a distributed flood turns your alerting into
the outage.

## 18. Buttons, if you want to act from the phone

```python
markup = {"inline_keyboard": [[
    {"text": "Hold 24h", "callback_data": "hold|%s|86400" % ip},
    {"text": "False alarm", "callback_data": "clear|%s" % ip},
]]}
telegram("Scanner active: %s\n%d distinct paths in 5 min" % (ip, n), reply_markup=markup)
```

Three rules if you do this:

- **Authorise the callback.** Check the originating chat id against your allow-list and fail closed.
  Anyone who learns your bot username can press buttons otherwise.
- **Expire unanswered actions.** Ours expire after two hours. Nothing waits on a person forever.
- **Read the confirmation back out of live state.** After the action, re-read the actual expiry and
  the actual list size and report those. Silence after a tap is indistinguishable from success.

## 19. Never put these behind a button

Scanning back, connecting to the attacker's host, any form of hack-back. Criminal under German
StGB §202a, §202b, §303a, §303b and §202c (which covers creating the tooling), EU Directive
2013/40, US CFAA §1030 and Canadian Criminal Code s.342.1.

The attacking address is usually a compromised third party anyway, so the lawful answer and the
effective answer are the same answer: a complaint to the hosting provider.

---

## PART 3: THE CHECKLIST

Counting:

- [ ] Log `ip`, `path`, `status`, `ua`, `bot`, `sf`, `hv`, `hvs`, `av`, `ref`, `ts` in milliseconds
- [ ] Three buckets, never two. Unjudged is a real answer
- [ ] Precedence runs one way: bot-or-contradicted wins for the window
- [ ] Per-engine version floors for fetch metadata, Safari on `(16, 4)`
- [ ] `sec-ch-ua` recorded but never required
- [ ] Fire on none of the three headers, not on fewer than three
- [ ] `X-Client-Proto` set at the proxy before trusting any protocol-version check
- [ ] `/api/` and `/.well-known/` exempt from everything
- [ ] Asset correlation is one-way: it confirms a browser engine and never accuses anything
- [ ] A zero or absent `av` moves no address into the client bucket, asserted across every path
- [ ] The asset ledger is bounded, prunes on write, and writes no log line
- [ ] Every path fails open
- [ ] Nothing here blocks anything

Telegram:

- [ ] Token in a 600-mode env file, never in git
- [ ] You have sent your bot a message at least once
- [ ] Group ids keep their minus sign
- [ ] `text[:3900]`
- [ ] No `parse_mode` when a keyboard is attached
- [ ] `timeout=` on the request
- [ ] Delivery failures logged, never swallowed
- [ ] Cooldown keyed on `(rule, subject)`
- [ ] Storm cap, and suppressions logged
- [ ] Callbacks authorised against an allow-list, failing closed
- [ ] Send yourself one test alert and confirm it arrives

## 20. Test it end to end

```bash
curl -s "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
  -d chat_id="$ALERT_TG_CHAT" \
  -d text="alert pipeline test $(date -u +%H:%M:%S)"
```

If that returns `{"ok":true,...}` and nothing arrives, you are sending to the wrong chat id. If it
returns `{"ok":false,"error_code":403}`, you have not messaged the bot yet, or you blocked it.

Then break something on purpose. Point a scanner at your own staging host and confirm the alert
arrives, once, with a cooldown, and that the suppression line appears in your log when it fires
again. A check that has never been observed working is off.
