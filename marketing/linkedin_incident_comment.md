# LinkedIn: comment thread on the live fire post

> LIMIT: LinkedIn comments cap at 1,250 characters (verified 2026). A deep dive does not fit in
> one, so this is a thread of three, posted as replies to your own comment. That is also what a
> person actually does when they have more to say, which is the point.
>
> FACT CHECK. Source: colt-web event log and the operator's own Telegram alerts, 10 Aug 2026.
> 195.178.110.199, geolocated AD. 19:05:55 to 19:05:57 UTC. Six client fingerprints. Paths /,
> //slug, /DOCS.md, /IAM.md, /[workspace]/. Brute-force rule counted 12 x 404 in 300s.
> 156,511 http events, 2,253 sources, 604 scanner-like, 19 detection classes missing before.
>
> NOT CLAIMED: that this scan would have led to a breach. It would not have, on its own. Saying
> otherwise is the kind of unsupported claim the whole post argues against.
>
> STYLE: no long dashes.

---

## Comment 1 of 3

A few people asked what the actual attack looked like, so here is the whole thing.

One address in Andorra. Two seconds. Six different browsers.

19:05:55 UTC it asks for /, then //slug, then /DOCS.md, /IAM.md and /[workspace]/. Every request from the same IP, each announcing a different client: Safari on macOS, Chrome on Linux, Chrome on macOS, Edge on Windows, Firefox on Windows, Firefox on macOS.

Look at those paths for a second. //slug and /[workspace]/ are template placeholders. DOCS.md and IAM.md are files that live in repositories, not on websites. This was not someone trying to break in. It was someone checking whether we had accidentally published our own internal documentation, our identity and access model, and our workspace layout.

That is a very 2026 thing to scan for. AI coding assistants and CI pipelines leave those files lying around constantly, and a surprising number of teams deploy them straight to production without noticing.

We had nothing there. It got six 404s and moved on.

(2 of 3 below)

---

## Comment 2 of 3

The postmortem is where it gets uncomfortable.

Our brute force rule fired correctly, 12 not-found responses inside five minutes, flagged HIGH. Good.

Then the platform sent me six separate alerts, each headed "A person just opened cybergod.ai", and each closing with the line "bots are served a 404 and never reach this alert".

One scanner. We told ourselves the opposite six times, in writing.

The bug was an assumption. We were identifying visitors partly by their browser, so an attacker rotating user agents did not look like one visitor evading detection, it looked like six separate people arriving. The evasion was reading as innocence.

That is now inverted. One address showing several browsers within seconds is treated as a scanner, because no real visitor ever does that. The evasion itself became the evidence.

Then we went and read all 156,511 lines of the log properly, which we had never done. 604 sources behaving like scanners. And our detection recognised 29 of 48 known attack classes. We had built the rules from one incident and assumed the job was finished.

(3 of 3 below)

---

## Comment 3 of 3

Honest answer to "what if you had done nothing": nothing, that day. They were hunting files we do not publish.

But that is the wrong question, and it is how organisations get caught.

Scanning is the survey, not the attack. It is free, automated, and the results get filed. A scan that finds nothing moves on. A scan that finds one leaked config, one forgotten staging host, produces a target with a name on it. What comes back is not a scanner. It is quiet, shaped around what was found, weeks later, from other addresses, looking like ordinary traffic.

By then your only evidence is the boring log line from a Tuesday that nobody read.

The part I did not expect: two of the noisiest addresses in that log were real visitors, in Germany and Israel, 439 and 362 not-found responses between them. On a naive threshold I would have locked both out of my own product while feeling rather pleased about the security.

Which is the actual lesson. Attacker tooling updates weekly. Your product grows new routes every sprint. Rules that were right in July go quietly wrong in August and nothing tells you.

Read your own logs.

---

## Posting notes

- Post comment 1 as a comment on your own post, then 2 and 3 as replies to it. Keeps the thread
  tidy and each one lands as a separate notification for anyone following.
- Character counts are verified below the 1,250 limit. Do not merge two of them.
- The line about nearly blocking two real users is the most valuable sentence in the thread.
  It is the one thing here that a competitor's marketing would never say.
