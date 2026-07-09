# Hermes Agent — local test (Docker)

Runs the real NousResearch Hermes Agent in a container, using **your DigitalOcean Qwen**
as the model (OpenAI-compatible endpoint). Config/memory persist in the `hermes_data` volume.

## 1. Build
    cd hermes-local
    docker build -t hermes-local .

## 2. First-time setup (interactive wizard) — configures the model
    docker run -it --rm ^
      -e OPENAI_API_KEY=doo_v1_YOURKEY ^
      -e OPENAI_BASE_URL=https://inference.do-ai.run/v1 ^
      -v hermes_data:/root/.hermes ^
      hermes-local hermes setup

In the wizard:
- Provider: choose the **OpenAI (custom / OpenAI-compatible)** option
  (it uses OPENAI_API_KEY + OPENAI_BASE_URL you passed above).
- Model: type  `qwen3.5-397b-a17b`
- Skip Telegram/voice for now (we add the gateway after the model works).

## 3. Chat
    docker run -it --rm ^
      -e OPENAI_API_KEY=doo_v1_YOURKEY ^
      -e OPENAI_BASE_URL=https://inference.do-ai.run/v1 ^
      -v hermes_data:/root/.hermes ^
      hermes-local

Type a message. If it replies — Hermes is really running on your Qwen. 🎉

## Notes
- `^` is the PowerShell line-continuation; or put it all on one line.
- Secrets are passed with `-e` at run time, never baked into the image.
- Once the model works, next steps: `hermes gateway setup` (Telegram/WhatsApp) and
  our JobHuntWOW skills (job-scout, apply-driver). Then deploy the same image to the droplet.
