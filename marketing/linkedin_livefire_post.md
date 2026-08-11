# LinkedIn: live fire post

> FACT CHECK. Every figure below comes from `python analyse_attacks.py` reading colt-web's own
> event log on 10 Aug 2026. 156,511 http events, 2,253 distinct sources, 604 scanner-like.
> Class counts: wordpress 483, php_probe 481, admin_panel 162, shell_rce 113, template 100,
> env_secrets 96, backup_file 45, api_docs 28, iot_router 6, traversal 6, docs_leak 3.
> 48/48 corpus coverage after the fix, 29/48 before, so 19 gaps. 106 tests passing.
>
> NOT CLAIMED, deliberately: that any of the 604 were stopped. They were detected over the period
> the log covers. The shield shipped afterwards. On a security post, a number you cannot support
> is worse than no number.
>
> STYLE: no long dashes anywhere. See the standing rule in CLAUDE.md.

---

I pointed our own security product at our own server and found 604 strangers already having a look around.

None of it was a breach. It is just what the public internet does to anything with a DNS record. What bothered me was that I had never actually read the logs. 156,511 lines sitting there, and I had been assuming.

So, what was knocking:

483 sources hunting for WordPress. We do not run WordPress. 162 trying admin panels, 113 dropping shell and RCE chains, 96 asking very politely for .env, .git and .aws/credentials.

One cluster in France spent days fingerprinting Next.js internals. We have never run Next.js. I hope they billed someone for the time. 🙂

My favourite was a webshell campaign spread across four different cloud providers, uploading files called alfa.php, lock360.php and, I promise this is real, this_is_a_new_hello_world.php.

Now the part I did not enjoy writing.

Before we measured, our detection recognised 29 of 48 known attack path classes. I had built the rules from a single incident in the morning and assumed that was the job done. Reading the actual log found 19 gaps in an afternoon.

It gets worse. Two of the loudest addresses in the data were not attackers. A visitor in Germany and one in Israel, 439 and 362 "not found" responses between them, both entirely legitimate. On a naive 404 threshold I would have locked both of them out of the product.

What separates those two from a scanner is not volume. It is variety. A person misses the same three stale links over and over. A scanner misses hundreds of different ones. That is now a rule, and it is why the count of real visitors blocked is zero.

How it runs today:

Detection is deterministic. Pure arithmetic, microseconds, sitting inline. The strongest signal we have is one address presenting several different browsers within a few seconds, because no real visitor ever does that. If you rotate your user agent to dodge rate limiting, the rotation itself convicts you.

Four models from four vendors (deepseek, llama, gemma, kimi) review every block after the fact, write the incident report to my Telegram, and are allowed to adjust six thresholds within limits that live in committed code.

They are not in the request path, and that is deliberate. A model call takes anywhere from 300ms to a minute. Put one in front of an incoming request and you have not built a defence, you have built a very expensive way to take your own site down.

Code decides. The models explain, argue, and get overruled by arithmetic. 106 tests gate every deploy and each safety rail is proven by breaking it on purpose and watching the build fail.

Anyway. Read your own logs. Mine were more interesting than I expected and considerably less flattering.

Evgeny Vainshtein, S4biz Group / Cybergod LLC

#CyberSecurity #AI #ThreatDetection #DevSecOps #AppSec

---

## Posting notes

- 2,600 characters, inside LinkedIn's 3,000 limit.
- Link to cybergod.ai/demo goes in the FIRST COMMENT. LinkedIn suppresses reach on posts with
  outbound links in the body.
- Tue to Thu, 08:00 to 10:00 CET.
- **Leave the 19 gaps and the two nearly-blocked visitors in.** Admitting the miss is the only
  reason a reader believes the rest. Every vendor post claims detection works; almost none says
  what it missed last week.
- Two emojis total, one of them optional. If it feels like a lot, cut the smiley.
