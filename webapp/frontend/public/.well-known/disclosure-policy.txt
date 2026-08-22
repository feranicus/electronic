# Security Policy — Coordinated Vulnerability Disclosure

Cybergod LLC (S4Biz Group) operates cybergod.ai. We welcome reports of security
vulnerabilities and will work with you in good faith to resolve them.

This is a real coordinated vulnerability disclosure (CVD) process, published to meet the
expectations of the EU Cyber Resilience Act (Regulation (EU) 2024/2847), Annex I Part II,
and aligned with ISO/IEC 29147 (vulnerability disclosure) and ISO/IEC 30111 (handling).

## Scope

In scope:

- `cybergod.ai` and its subdomains
- the assessment engine, the web cabinet, and the Telegram bots
- the container images we publish (`ghcr.io/feranicus/colt-web` and the bot images)

Out of scope, and please do not test these:

- the other services that share our host (a VPN, unrelated sites). We run on shared
  infrastructure; testing a neighbour is testing someone who did not consent.
- denial of service, traffic flooding, or resource-exhaustion testing against the live site
- social engineering of our staff, partners or customers
- physical attacks

## How to report

Email **feranicus@s4biz.io** with:

- what you found and where (a URL, an endpoint, an image tag)
- how to reproduce it, ideally with a minimal proof of concept
- what an attacker could do with it

If you need to send us something sensitive, say so in a first message and we will arrange an
encrypted channel. Please do not open a public GitHub issue for a security report.

## What you can expect from us

- **Acknowledgement within 3 working days** that we received your report.
- **An initial assessment within 10 working days**, telling you whether we have reproduced
  it and our view of the severity.
- **Progress updates** at least every 14 days until it is resolved.
- **Credit**, if you would like it, when we publish a fix. We will not name you without your
  consent.

## What we ask of you

- Give us a reasonable time to fix the issue before disclosing it publicly. We aim to
  remediate and disclose within **90 days**; if we need longer we will tell you why.
- Do not access, modify or delete data that is not yours, and do not degrade our service for
  others while testing.
- Stay within the scope above.

Acting in good faith within this policy, we will not pursue or support legal action against
you for your research. This is our commitment; it is not a waiver of any third party's rights.

## Our own transparency

When a vulnerability in a product we publish is actively exploited, or when a severe incident
affects our service, we report it as required by CRA Article 14 (applicable from 11 September
2026): an early warning to the relevant national CSIRT and ENISA within 24 hours, a
notification within 72 hours, and a final report within 14 days (or one month for a severe
incident). We publish an advisory once a fix is available.

_Last reviewed: 2026-08-22. Contact: feranicus@s4biz.io_
