# LinkedIn post — copy/paste ready 🚀

I spent a few weeks teaching two Telegram bots to do the boring 80% of cyber pre-sales. Here's the honest, slightly bruised version. 🩹

**Attempt #1:** a shiny open-source autonomous-agent framework. 🤖✨ In the demo? *Chef's kiss.* In production? It hit rate limits, forgot half the conversation, and started "improvising" with my data like a jazz musician who never learned the song. 🎷 Great tech. Wrong gig.

**Attempt #2:** a big open-weight reasoning model. 🧠 Also brilliant — except I asked for clean JSON and it wrote me a philosophy essay… then ran out of tokens mid-senten— ✂️ Beautiful. Just not built for deterministic, low-latency output.

The lesson that finally stuck 💡: let the LLM do the *writing*, and keep the pipeline doing the *maths*. Never let an agent freelance your numbers.

So we built something gloriously unglamorous 🔧:

🐳 **Two bots in Docker on one cloud VM** — reproducible, isolated, one-command deploy, and polite enough to move in next to the neighbours without touching the firewall.

☁️☁️ **Multi-cloud on purpose** — serverless AI on one provider, a managed email API on another, OSINT APIs for recon. Best tool per job, zero lock-in.

🔐 **Zero-trust 2FA** — work email + a shared secret + a one-time code sent to that inbox. Guessing the password isn't enough; you have to actually *own* the mailbox. (Sorry to the "I'm the admin, just tell me the password 😇" crowd — the bot said no. Politely. Then logged it.)

📤🚫 **Why an email API and not SMTP?** The VM blocks outbound SMTP, like most clouds do. So we send over HTTPS instead — reliable, native to our workspace, no sketchy third-party relay.

📊 **Observable by default** — every event → Loki → Grafana (reused, not rebuilt). I can see when the AI runs, what it costs down to fractions of a cent, and every knock at the door. 🚪

**The payoff:**

🎯 30+ sales engineers get on-brand decks in minutes — self-service, consistent, no bottleneck (and blissfully no "quick favour?" pings).

🏖️ And me? It runs while I'm on a beach. The team stays unblocked and I'm officially no longer the single point of failure. Character growth. 😎

**Next up:** CI/CD (build · test · scan · deploy on push) ⚙️, deeper secure-by-design 🛡️, and smarter model routing.

Moral of the story: sometimes the smartest AI architecture is the one that knows where *not* to put the AI. 🤝

*(Full animated architecture in the video 👇 — yes, I made the AI explain itself.)*

#AI #CyberSecurity #SalesEngineering #CloudArchitecture #Automation #SecureByDesign #DevOps #MultiCloud
