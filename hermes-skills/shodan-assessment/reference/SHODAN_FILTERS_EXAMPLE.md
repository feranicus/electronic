# Top 10 Shodan Filters — UBS AG (incl. legacy Credit Suisse)

> **Scope / authorization note.** These queries are for **external attack-surface mapping (ASM)** of assets owned by or authorized by UBS. Shodan only indexes already-public, internet-facing data. Only run active follow-up (scans, logins, exploitation) against assets you are explicitly authorized to test.

**Identity data used** (from bgp.he.net):

| Entity | ASNs | Key netblocks |
|---|---|---|
| UBS AG / Group / Card Center | AS8883, AS8729, AS21994, AS209848, AS17071, AS17070, AS10615, AS10100 | 94.154.164.0/22 (164–167) |
| Credit Suisse Group (legacy) | AS3083–AS3109, AS3412–AS3415, AS4405–AS4430 | 198.240.128.0/17, 198.240.209–249.0/24, 199.53.27.0/24, 200.9.148.0/24 |
| Banco Credit Suisse (Brasil) | AS264044 | 200.9.148.0/24 |

---

## 1. Full ASN sweep — UBS estate
The broadest single net. Every host announced from UBS-owned autonomous systems.
```
asn:AS8883,AS8729,AS21994,AS209848,AS17071,AS17070,AS10615,AS10100
```

## 2. Full ASN sweep — Credit Suisse legacy estate
Post-acquisition, these still route to UBS. Often the most neglected / forgotten assets.
```
asn:AS4405,AS4406,AS4407,AS4408,AS4409,AS4410,AS4411,AS4412,AS4413,AS4414,AS4415,AS4416,AS4417,AS4418,AS4419,AS4420,AS4421,AS4422,AS4423,AS4424,AS4425,AS4426,AS4427,AS4428,AS4429,AS4430,AS3412,AS3413,AS3414,AS3415,AS264044
```

## 3. Organization name match
Catches hosts whose WHOIS/netname maps to the org but may sit outside the ASNs above (cloud, hosting, subsidiaries).
```
org:"UBS AG"
org:"UBS Group AG"
org:"UBS Card Center AG"
org:"Credit Suisse Group"
```

## 4. Netblock / CIDR sweep
Direct prefix targeting — useful when ASN attribution is incomplete.
```
net:94.154.164.0/22,198.240.128.0/17,199.53.27.0/24,200.9.148.0/24
```

## 5. TLS certificate subject (domain in cert)
Finds hosts presenting UBS/CS certificates anywhere on the internet — including shadow IT on third-party hosting.
```
ssl.cert.subject.cn:"ubs.com"
ssl.cert.subject.cn:"credit-suisse.com"
ssl.cert.subject.cn:"credit-suisse.net"
```

## 6. TLS certificate organization / free-text SSL
Catches wildcard and SAN certs where the CN isn't the apex domain.
```
ssl:"UBS"
ssl:"Credit Suisse"
ssl.cert.subject.o:"UBS AG"
```

## 7. Hostname / domain match
Reverse-DNS and HTTP host attribution.
```
hostname:".ubs.com"
hostname:".credit-suisse.com"
```

## 8. Exposed remote-access & database ports
High-risk management services that should not face the internet. Repeat per identity selector.
```
asn:AS8883,AS8729 port:3389,22,23,5900,3306,1433,5432,6379,27017,21
org:"Credit Suisse Group" port:3389,22,23,5900,3306,1433
```
- 3389 RDP · 22 SSH · 23 Telnet · 5900 VNC · 3306 MySQL · 1433 MSSQL · 5432 Postgres · 6379 Redis · 27017 Mongo · 21 FTP

## 9. Known-vulnerable & end-of-life services
Hosts Shodan has flagged with CVEs, plus expired/self-signed TLS (config-hygiene red flags).
```
org:"UBS AG" has_vuln:true
asn:AS8883,AS8729 ssl.cert.expired:true
org:"Credit Suisse Group" ssl.cert.expired:true
```
> `vuln:` and `has_vuln` require a Shodan paid/enterprise plan.

## 10. Exposed web logins, panels & dev/staging surfaces
Admin consoles, VPN portals and non-prod environments that leak via title/banner.
```
asn:AS8883,AS8729 http.title:"login","admin","portal","vpn"
org:"UBS AG" http.title:"dev","staging","test","uat"
asn:AS8883,AS8729 product:"Citrix","Fortinet","Pulse Secure","Palo Alto"
```

---

## Quick-use tips
- Combine any filter with `country:CH` / `country:US` to localize (UBS is CH + US heavy).
- Add `-honeypot:true` to drop honeypot noise.
- Prefix a term with `-` to exclude (e.g. `-port:443` to skip standard HTTPS).
- Save the high-value ones as **Shodan Monitors** for continuous alerting on new exposed hosts.
- Export results via the Shodan CLI: `shodan download ubs_asn 'asn:AS8883,AS8729'` then `shodan parse`.

*ASNs and prefixes sourced from bgp.he.net (UBS search screenshot + Credit Suisse PDF). Verify current ownership before action — BGP attribution drifts over time.*
