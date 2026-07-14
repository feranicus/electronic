🚦 I lost a day to a single "502 Bad Gateway." The bug wasn't my app. It was me not understanding my reverse proxy. Here's the debug playbook — and why I'm now all-in on Caddy. 🧵👇

The setup: a fresh app behind a shared Caddy in Docker. Config looked *perfect*. Browser said 502. Every. Single. Time. 😤

🔎 What actually bites you (save this):

1️⃣ **Reload ≠ reload.** `caddy reload` hashes the new config against the running one. If they match, it *skips* the reload and quietly keeps the OLD config → pointing at your dead/changed upstream → 502. The fix is one flag: `caddy reload --force`. ⚡

2️⃣ **Docker single-file mounts.** Mount `./Caddyfile:/etc/caddy/Caddyfile` and Docker pins the file's *inode*. Editors save-and-swap (new inode), so the container literally never sees your change → "config unchanged." The fix: mount the **directory**, not the file. 📁

3️⃣ **Container-to-container networking.** Inside a container, `127.0.0.1:PORT` is the container's own loopback — NOT the host. Reverse-proxy to the service **name** on a shared network (`reverse_proxy app:8000`), and keep the upstream on **one** network. A container on two networks hands the proxy two IPs and it happily dials the unreachable one. 🕸️

The moment I fixed those? `401 Unauthorized` instead of `502`. In this context, 401 = "auth is working." Chef's kiss. 👨‍🍳💋

💚 Now the love letter to Caddy:

✅ **Written in Go — memory-safe.** An entire class of bugs (buffer/heap overflows) simply *can't* happen. Contrast nginx **CVE-2021-23017**: a 1-byte heap overwrite in the DNS resolver that lived in the codebase from **v0.6.18 (2009) to 2021 — ~12 years** — with likely RCE. That's the quiet tax of a 20-year-old C codebase. 🧨

✅ **Automatic HTTPS.** Let's Encrypt issuance + renewal, on by default. No certbot cron, no expired-cert pages at 3am. 🔐

✅ **One static binary + one readable config** (or a clean admin API). No module soup.

🇷🇺 Bonus governance note: nginx's origin story is genuinely messy — built by Igor Sysoev *while at Rambler*, sold to F5 for $670M in 2019, then Russian police raided the Moscow office over an ownership claim. Not FUD — just a reminder to **know your software supply chain**.

🚀 TL;DR: learn your proxy's reload + networking model, and pick tools that make the dangerous stuff *impossible by design*. Caddy does exactly that.

What's your worst reverse-proxy war story? 👇

#Caddy #DevOps #Nginx #Golang #WebSecurity #Docker #SRE #ReverseProxy #InfoSec #Cybersecurity
