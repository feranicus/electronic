🌐 I put a brand-new domain on the internet. No links. No announcement. Nobody knew it existed.

**It was scanned within hours.** 🕵️ My own 24-hour log, unedited 👇

```
20.63.63.128     Azure   → /wp-content/plugins/…/wp_filemanager.php
20.151.7.119     Azure   → /admin.php, /wp-includes/
216.144.249.201  Censys  → /.env, /.git/config
```

MITRE ATT&CK **T1595.003** — Active Scanning: Wordlist Scanning. Three sources, zero humans. Hunting webshells, admin panels, and my cloud keys in a `.env` file.

Nobody *targeted* me. I was **found** — by machines sweeping all of IPv4, throwing a wordlist at anything that answers on :443. 🎯

🛡️ **Layer 1 — WAF.** Every one of those requests dies on a single rule: block `/wp-`, `*.php`, `/.env`, `/.git`. Took me ten minutes. It killed 100% of that day's traffic. A WAF isn't clever — it's the cheapest control you will ever deploy, because **nothing legitimate on my host ends in .php.**

⚡ **Layer 2 — DDoS.** Recon is the cheap half. The same industrialised botnets run the volumetric side:

📊 **31.4 Tbps** — largest DDoS ever recorded (Aisuru, Dec 2025). Duration: **35 seconds**.
📊 Record was **3.8 Tbps** in Oct 2024 → **+700% in 14 months**.
📊 Cloudflare mitigated **47.1M** attacks in 2025 — ~**227,000 a day**.

Your firewall is irrelevant here. So is your load balancer. So is your beautifully-tuned nginx. If 31 Tbps hits a 10 Gbps circuit, **the circuit is the casualty** — the packets never reach anything you own. You cannot patch your way out of a bandwidth problem. It's physics, not skill. It has to be absorbed **upstream, in the carrier's network.**

🧠 **Layer 0 — and this is the one that matters: SASE from day zero.**

Notice I only needed that WAF rule because the service was **exposed in the first place**. Secure-by-design (CISA/BSI) says: don't bolt controls on afterwards — remove the exposure. **SASE/ZTNA means there is no public edge to scan.** No open panel. No internet-facing VPN appliance to become next quarter's KEV entry. An attacker can't wordlist a door that doesn't exist. 🚪

Bolt-on security is a tax you pay forever. Day-zero architecture is paid once.

🇩🇪 And in Germany this is no longer taste — it's law:
⚖️ NIS2 applies since **6 Dec 2025**, no transition.
⚖️ BSI registration was due **6 March 2026**.
⚖️ **Systematic BSI audits start H2 2026.**
⚖️ **Art. 21** demands availability + continuity. A 35-second flood that drops your service is a reportable incident.

"We'll deal with it if it happens" isn't a strategy. It's a finding. 📋

💚 That's the Colt stack, in the order I'd actually deploy it:
**SASE/ZTNA** (no exposed edge) → **Managed WAF** (kill the wordlists) → **IP Guardian / DDoS** (absorb the flood upstream, where the bandwidth is).

I got lucky — mine was only reconnaissance. It took hours to be found.

How long would your edge last? 👇

#SASE #ZeroTrust #WAF #DDoS #NIS2 #BSI #SecureByDesign #Colt #CISO #KRITIS
