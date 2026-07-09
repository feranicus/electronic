# Hermes Agent (Nous) + deps for the shodan-assessment skill (Node/pptxgenjs + Python shodan).
# Native Windows isn't supported; this Linux container runs fine under Docker Desktop (WSL2).
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates git build-essential ffmpeg \
      nodejs npm python3-pip \
 && rm -rf /var/lib/apt/lists/*
# Hermes Agent (official installer: uv venv + `hermes` in ~/.local/bin)
RUN curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
ENV PATH="/root/.local/bin:${PATH}"
# --- skill deps ---
RUN mkdir -p /opt/node && cd /opt/node && npm init -y >/dev/null 2>&1 && npm install pptxgenjs@^4 --no-audit --no-fund
ENV NODE_PATH=/opt/node/node_modules
RUN pip3 install --no-cache-dir --break-system-packages shodan
RUN mkdir -p /root/work
# DO Qwen as an OpenAI-compatible custom endpoint (key passed at RUN time)
ENV OPENAI_BASE_URL="https://inference.do-ai.run/v1"
WORKDIR /root
CMD ["hermes"]
