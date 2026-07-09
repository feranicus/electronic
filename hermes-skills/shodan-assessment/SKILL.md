---
name: shodan-assessment
description: Cyber security / Shodan / attack-surface assessment of a company. Trigger on any request to assess, scan, or run Shodan/security/exposure on a company name, domain, URL, or ASN.
---

# Shodan assessment — run one command, attach 3 decks

You were asked to assess a company (the argument is a company name, domain, URL, or ASN).

**Do exactly this — one shell command, nothing else:**

```
shodan-assessment <ARGUMENT>
```

Example: `shodan-assessment keb.de`

Then:
1. Wait for it to print `ASSESSMENT COMPLETE`. It writes 3 files to `/root/work`:
   `*_Shodan_Findings.pptx`, `*_C-BIQ.pptx`, `*_GEOPOL.pptx`.
2. **Attach those 3 .pptx files** and post the printed summary.

DO NOT: search for skills, list skills, `find` for scripts, install whois/dig/nmap,
browse shodan.io, or gather info by hand. The `shodan-assessment` command already does
recon + Shodan + C-BIQ + GEOPOL. It exists on PATH. Just run it.

Behind a CDN / few results? Re-run: `shodan-assessment <company> --asn AS<N> --net <CIDR>`.
