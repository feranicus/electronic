# Hermes + shodan-assessment skill BAKED IN. On start, the skill is synced into the
# volume-mounted skills dir so Hermes registers `/shodan-assessment` AND the files exist.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates git build-essential ffmpeg nodejs npm python3-pip \
 && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
ENV PATH="/root/.local/bin:${PATH}"
RUN mkdir -p /opt/node && cd /opt/node && npm init -y >/dev/null 2>&1 && npm install pptxgenjs@^4 --no-audit --no-fund
ENV NODE_PATH=/opt/node/node_modules
RUN pip3 install --no-cache-dir --break-system-packages shodan
RUN mkdir -p /root/work
# bake the skill
COPY hermes-skills/shodan-assessment /opt/shodan-skill
# one-word PATH command
RUN printf '#!/usr/bin/env bash\nexec python3 /opt/shodan-skill/scripts/run_assessment.py --seed "$1" --outdir /root/work "${@:2}"\n' > /usr/local/bin/shodan-assessment \
 && chmod +x /usr/local/bin/shodan-assessment
# entrypoint: sync baked skill into ~/.hermes/skills (the volume) so Hermes registers it, then run
RUN printf '#!/usr/bin/env bash\nset -e\nmkdir -p /root/.hermes/skills\nrm -rf /root/.hermes/skills/shodan-assessment\ncp -r /opt/shodan-skill /root/.hermes/skills/shodan-assessment\nexec "$@"\n' > /usr/local/bin/entrypoint.sh \
 && chmod +x /usr/local/bin/entrypoint.sh
ENV OPENAI_BASE_URL="https://inference.do-ai.run/v1"
WORKDIR /root
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["hermes"]
