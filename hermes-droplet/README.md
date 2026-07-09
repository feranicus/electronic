# Hermes Agent — 24/7 gateway on the droplet

Runs the real Hermes Agent as an always-on messaging concierge (Telegram now,
WhatsApp after Meta onboarding), using your DO Qwen as the model.

## 0. Copy this folder to the droplet and set the key
    scp -r hermes-droplet root@64.225.108.200:/opt/
    ssh root@64.225.108.200
    cd /opt/hermes-droplet
    cp .env.example .env    # put your doo_v1_... key in OPENAI_API_KEY
    nano .env

## 1. Build + configure once (model + gateway)
    docker compose build
    # model (custom endpoint = your DO Qwen, model qwen3.5-397b-a17b):
    docker compose run --rm hermes hermes setup
    # gateway (Telegram token now; WhatsApp creds if you have Meta Cloud API):
    docker compose run --rm hermes hermes setup gateway

## 2. Start the 24/7 gateway (daemon, survives reboot)
    docker compose up -d
    docker compose logs -f hermes     # watch it connect; Ctrl+C to stop watching

Message your Telegram bot -> Hermes answers. It stays online even when your PC is off.

## 3. WhatsApp (Meta Cloud API) — needs a public webhook
- Create a Meta Business app + WhatsApp product; get phone number id, a permanent
  token, and pick a verify token. Enter them in `hermes setup gateway`.
- Note the webhook port Hermes prints; set it in docker-compose (ports) if != 8099.
- Add the block from Caddy-snippet.txt to /opt/videodead/Caddyfile, `caddy reload`.
- DNS: A hermes -> 64.225.108.200. Set Meta's webhook URL to https://hermes.jobhuntwow.com/...

## Manage
    docker compose restart hermes     # after config changes
    docker compose run --rm hermes hermes doctor   # diagnose
