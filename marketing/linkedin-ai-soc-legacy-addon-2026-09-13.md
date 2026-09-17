# LinkedIn post — the legacy blue team, and what an Automated AI SOC adds on top (2026-09-13)

EVERY NUMBER TRACED BEFORE WRITING (standing rule):
  42,369 attack-shaped requests / 14 days ............ attack_digest 2026-09-13 07:01 UTC
  ~3,000 a day ....................................... 42,369 / 14 = 3,026, arithmetic shown
  551 distinct paths, 143 user agents, 96 unnamed .... same digest, actor 34.148.208.255
  5 rules retired this week .......................... perseus weekly 2026-09-13 05:20 UTC
  /@fs/ now matches 99 paths we serve ................ same weekly, RETIRED line
  ^/wp-.* 79 hostile / 134 clean, refused ............ same weekly, PROMOTION GATE
  "not one packet" ................................... committed engine claim, /partners + ToU

VENDOR NAMES ARE DESCRIPTIVE, NEVER COMPARATIVE. No claim that this is better than any named
product (UWG s6 / UCP Directive, and we have benchmarked nothing). The argument is ARCHITECTURE:
what the appliance was designed for, and what changed in the traffic.

Character count: ~2,900 of LinkedIn's 3,000.

---

Three years ago, if you ran a 50-person company, your security looked like this, and it was a reasonable thing to buy.

A FortiGate or a Check Point at the edge. Sophos or SonicWall if the budget was tighter, WatchGuard or a Cisco Meraki if your MSP had a preference. Palo Alto if you had grown. An EDR agent on the laptops. Microsoft 365 with MFA switched on, eventually. A pen test once a year, a PDF, and a quiet twelve months.

All of it rested on one assumption. Attacks arrive at human speed, and somebody at the vendor writes the signature before it reaches you.

That assumption is what broke.

Our own small sites logged 42,369 attack-shaped requests in the last fourteen days. Roughly 3,000 a day, against companies nobody has heard of, holding nothing a nation state would want. We are not a target. We are an address range. So are you.

Volume is not even the interesting part. One single address tried 551 different paths on us, using 143 different user agents. People do not do that. Nobody changes their browser identity 143 times before lunch. That is software, written by someone who has never heard of us and never will.

Ninety-six of those 551 paths are shapes our own detection corpus cannot name yet. New this week.

Which brings me to the appliance in your rack.

Your firewall is not the problem. It does what it was designed to do and it still does it. The difficulty is that its rules move on the vendor's schedule, and your applications move on yours.

Our system retired five of its own blocking rules this week. Not because the attackers went away. Because our sites changed underneath them. A rule matching /@fs/ was a clean attack signature in July. Today it matches 99 paths our own build output serves. Nobody would have spotted that until customers started seeing errors.

An automated SOC sits on top of the box you already own and does the part the box was never built for:

reads your traffic instead of a global feed
proposes new rules nightly from what actually hit you
retires its own rules weekly when your app moves
refuses outright any rule that would touch a real customer

That last one is the hard part, and it is where most automation quietly fails. This week the system had a candidate rule for /wp-*, with 79 hostile hits behind it. It also had 134 hits from real visitors. Refused, permanently. Four models from four vendors proposed it. Deterministic code killed it. A tired human at 2am ships that rule and spends Wednesday explaining the outage.

If your defences change once a quarter and the attacks against you change every day, you are not running a risk any more. You are running a countdown.

Fifty people or five thousand, the arithmetic is the same. Keep the firewall. Add something that adapts at the speed the attackers already do.

Want to see what the internet already knows about your estate? cybergod.ai. Not one packet is sent at your systems, and you get the report either way.
