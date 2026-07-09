# KEB Automation KG — Attack-Surface Recon Brief & Top Shodan Filters

**Prepared for:** Pre-engagement screening (CISO Mr. Zauner consented)
**Target:** KEB Automation KG / Karl E. Brinkmann GmbH, Südstraße 38, 32683 Barntrup, Germany
**Date:** 11 June 2026
**Method:** Passive OSINT only (DNS-over-HTTPS, RIPE/RDAP, BGP, CT). No active scanning performed.

> Scope note: Use these filters only for the agreed KEB screening. Shodan itself is passive (it queries an existing index, it does not scan the target), so running these queries does not touch KEB systems. Keep findings inside the engagement.

---

## 1. Confirmed footprint (the facts behind the filters)

**Organisation / RIPE allocation — the anchor**

| Field | Value |
|---|---|
| Assigned netblock | **212.184.104.224/27** (32 addresses, .224–.255) |
| RIPE netname | **KARL-BRINKMANN-BARNTRUP-NET** |
| RIPE descr | "TDG fuer Karl E. Brinkmann GmbH" |
| Upstream / ASN | **AS3320 Deutsche Telekom AG** (this is the "HQ connected via DTAG") |
| Status | ASSIGNED PA, mnt-by DTAG-NIC |

KEB does **not** own an ASN. Their public IPv4 lives entirely inside this single Deutsche Telekom-assigned /27. That makes `net:212.184.104.224/27` the master filter — it captures essentially their whole on-prem internet edge.

**Primary domains** (all resolve to 212.184.104.246)

- `keb.de` (primary)
- `keb-automation.com`
- `kebautomation.com`
- `kebamerica.com` (US subsidiary — hosted separately, US)

**Known edge hosts**

| IP | Role | Notes |
|---|---|---|
| 212.184.104.246 | Web / edge | Hosts keb.de, keb-automation.com, kebautomation.com |
| 212.184.104.253 | Mail egress | Listed in `_spf.keb.de` — likely on-prem mail/iQ.Suite gateway |

**Email & DNS**

- Inbound mail: **Microsoft 365** (`keb-de.mail.protection.outlook.com`)
- On-prem mail security: **GBS iQ.Suite** (`a:portal.iqsuite.com` in SPF)
- DNS authoritative: **Deutsche Telekom** (`ns1.telekom-domains.de`)
- A 2nd SPF sender (`188.172.118.133`, WiTCOM Wiesbaden, PTR `meffert.youlogic.de`) is a **third-party relay**, not KEB infrastructure.

**SaaS / vendor stack revealed in DNS TXT + SPF** (useful for phishing-surface and supply-chain context)

Salesforce CRM · SAP SuccessFactors (HR) · AEB (export/customs compliance) · TeamViewer SSO · CleverReach (email marketing) · Apple Business · Google · cloud4partner · iQ.Suite.

> Note on Shodan org facets: because the /27 sits under Deutsche Telekom, Shodan's `org:`/`isp:` facet for these hosts usually reads "Deutsche Telekom AG", not "KEB". The reliable pivots are the **net block, SSL cert names, and hostnames** — not `org:`.

---

## 2. Top 10 Shodan filters (ranked)

Copy-paste ready. Run logged in; some facets (`vuln`, `tag`) need a paid plan.

**1 — Master: the entire KEB public block**
```
net:212.184.104.224/27
```
Everything KEB exposes on-prem. Start here, then facet by `port`, `product`, `org`, `tag` in the left sidebar.

**2 — Known edge hosts (web + mail), all ports/services**
```
net:212.184.104.224/27 ip:212.184.104.246,212.184.104.253
```
Focus on the two confirmed live hosts to see every open port and banner.

**3 — SSL/TLS certificates naming KEB (catches cloud assets outside the block)**
```
ssl.cert.subject.CN:"keb.de" ssl:"keb-automation.com" ssl:"KEB"
```
Pivot variants — run each separately if combined returns nothing:
```
ssl.cert.subject.CN:keb.de
ssl.cert.subject.O:"KEB"
ssl:"keb-automation.com"
```

**4 — Hostname pivot (finds KEB-named services on any IP, incl. hosters/CDN)**
```
hostname:keb.de,keb-automation.com,kebautomation.com,kebamerica.com
```

**5 — Remote access / VPN / firewall management exposure**
```
net:212.184.104.224/27 port:443,4433,8443,10443,4443,500,4500,1194
```
Then facet `product` for Fortinet / SonicWall / Sophos / Citrix / Pulse / Cisco ASA. Edge-VPN appliances are the #1 ransomware entry vector — directly relevant to the suspected breach 6 weeks ago.

**6 — Industrial / OT & ICS protocols (KEB builds drives, PLCs, HMIs — OT exposure is the core ISO/NIS2 question)**
```
net:212.184.104.224/27 port:102,502,4840,44818,20000,1911,47808,789,9600,2404
```
Covers Siemens S7 (102), Modbus (502), OPC-UA (4840), EtherNet/IP (44818), DNP3 (20000), Tridium Fox (1911), BACnet (47808), Red Lion Crimson (789), IEC-104 (2404). Add `tag:ics` or `tag:scada` to confirm. **Any hit here is a high-severity finding for the IT/OT ISO readiness conversation.**

**7 — Windows remote management / RDP exposure**
```
net:212.184.104.224/27 port:3389,3390,5985,5986,5900,5800
```
RDP/WinRM/VNC directly reachable from the internet — common audit failure and breach vector.

**8 — On-prem mail / Exchange / OWA / iQ.Suite gateway**
```
net:212.184.104.224/27 port:25,587,465,143,993,110,995
```
And to catch an on-prem Exchange/OWA portal:
```
net:212.184.104.224/27 http.title:"Outlook","Exchange","iQ.Suite","Anmeldung"
```

**9 — Exposed web logins, admin panels & legacy apps**
```
net:212.184.104.224/27 http.title:"login","Anmelden","Dashboard","phpMyAdmin","Webmin","Router","Camera"
```
Surfaces forgotten admin UIs, default pages, and management interfaces that shouldn't face the internet.

**10 — Known vulnerabilities & weak TLS on KEB hosts**
```
net:212.184.104.224/27 has_vuln:true
```
Companion checks (paste separately):
```
net:212.184.104.224/27 ssl.cert.expired:true
net:212.184.104.224/27 ssl.version:sslv3,tlsv1,tlsv1.1
```
Expired certs, deprecated TLS, and CVE-flagged services are the easiest, most defensible evidence to put in front of the COO to justify investment.

---

## 3. Bonus / contextual filters

```
net:212.184.104.224/27 port:5938                      # TeamViewer (they use TeamViewer SSO)
net:212.184.104.224/27 product:"OpenSSH"              # SSH version/exposure inventory
net:212.184.104.224/27 -ssl port:80,8080             # plain-HTTP services (no TLS)
net:212.184.104.224/27 country:DE                     # sanity-confirm geography
```

---

## 4. How to run the screening (suggested 20-min flow)

1. Open filter **#1** in Shodan → read the left-sidebar facets (Ports, Products, Vulns, Tags). This alone gives the exposure shape.
2. Drill **#5 (VPN)**, **#6 (OT)**, **#7 (RDP)**, **#10 (vulns)** — these produce the headline findings for the workshop with the Head of IT.
3. Pivot **#3 (SSL)** and **#4 (hostname)** to catch shadow/cloud assets the /27 misses.
4. Screenshot each hit for the findings deck. Frame OT/VPN/vuln results against NIS2 Art. 21 (risk management) and ISO 27001 A.8 (asset/vuln management) — Mr. Zauner's certification driver.

---

## 5. Verification notes / caveats

- The /27 ownership, ASN, domains, MX, SPF and SaaS records were confirmed live (RIPE Stat, dns.google DoH, bgp.he.net) on 11 Jun 2026.
- Common admin subdomains (vpn, remote, owa, fw, portal, sslvpn, teamviewer) on keb.de returned **NXDOMAIN** — KEB does not publish them in DNS. That does **not** mean nothing is exposed; Shodan indexes by IP, so the `net:` filters remain the authoritative check.
- Certificate Transparency (crt.sh) was unreachable during prep — re-run `crt.sh/?q=keb.de` manually for the full subdomain/SAN list before the workshop.
- `org:`/`isp:` facets read "Deutsche Telekom AG" for these hosts; rely on `net:`, `ssl:`, `hostname:`.
