# LinkedIn post — Automated AI SOC (2026-09-13)

SOURCE FOR EVERY NUMBER (traced before writing, per the standing rule):
  42,369 / 0 blocked / 2,685 distinct unserved paths ...... attack_digest 2026-09-13 07:01 UTC
  14,897 env secrets · 6,336 wordpress · 4,867 backup ..... same digest, "what they went looking for"
  5 rules retired, /@fs/ matching 99 served paths ......... perseus weekly cycle 2026-09-13 05:20 UTC
  ^/wp-.* 79 hostile / 134 clean, REFUSED OUTRIGHT ........ same weekly, PROMOTION GATE
  2 blocking · 7 detecting · 0 ready ...................... same weekly
  panel 0 of 4 answered ................................... same weekly + digest
  2 AbuseIPDB submissions, 2 held (no RDAP abuse contact) . same weekly, CONSEQUENCE section
  "not one packet" ........................................ committed engine claim, /partners + ToU

Character count: ~2,850 of LinkedIn's 3,000.

---

Somebody rattled 42,369 door handles on our buildings in the last fourteen days.

Our automated rule engine blocked none of them, and that was the correct outcome. Stay with me, because the reason is the whole argument for an AI SOC.

Every thriller has the scene where a man in a long coat walks the perimeter and tries each door in turn. Nobody sends a man any more. They send a script, it tries 2,685 different doors, and most of those doors have never existed on your building. Ours spent the fortnight hunting .env files 14,897 times, WordPress 6,336 times, and backup archives 4,867 times. We do not run WordPress.

Your firewall is fine. Your WAF is fine. The problem is that somebody wrote those rules on a Tuesday in 2023 and nothing has re-read them since.

Two things happened on our own estate this week that show what that costs.

First, the system retired five of its own blocking rules. Not because they stopped catching attackers. Because the sites changed underneath them. One rule matched anything starting with /@fs/, a clean attack signature back in July. Today it matches 99 paths our own build output serves. Left alone, that rule would have quietly broken our website while the dashboard stayed green.

Then the good bit. The system had a candidate rule for /wp-*, and the evidence was tempting: 79 hostile hits. It also had 134 hits from real visitors. Refused outright, permanently. A tired human at 2am ships that rule and spends Wednesday morning wondering why customers are getting errors.

That is what an automated SOC actually buys you, and it has little to do with catching more.

How ours decides, because "AI-powered" means nothing on its own:

Four models from four different vendors look at each incident and propose. They install nothing. Deterministic code decides. A proposed rule sits in detection for at least 24 hours. Three of the four must agree. It needs one genuine hostile match, and exactly zero matches against traffic we really serve. One legitimate hit kills it forever.

This week that produced two rules blocking, seven still soaking, zero promoted.

Not a bad week. The gate doing its job.

One more thing worth saying out loud. During that same week the model panel answered zero times out of four. Vendors were down or rate-limited. Nothing broke, because the models advise and the code decides. If your security stops working when a language model is unavailable, you have built a single point of failure with a friendly personality.

Two abuse reports went to the offending providers automatically. Two more are sitting unsent, because those providers publish no abuse contact at all. Make of that what you will.

Curious what the internet can already see of your company, before somebody starts trying your doors? That is what we do at cybergod.ai. We send not one packet at your systems, and you get the report either way.
