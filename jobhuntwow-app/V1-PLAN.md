# JobHuntWOW — V1 build plan (LinkedIn → Workday apply)

**Scope of V1:** one vertical slice, proven end-to-end against a real target:
Red Hat *EMEA AI Architect (m/f/d)* — LinkedIn job `4435446898` → Workday portal
`redhat.wd5.myworkdayjobs.com`. Ship the loop, then add ATS adapters one at a time.

Reference target (the V1 test fixture):
- LinkedIn: https://www.linkedin.com/jobs/view/4435446898/
- Workday: https://redhat.wd5.myworkdayjobs.com/jobs/job/Remote-Germany/EMEA-AI-Architect--m-f-d-_R-057546-2

---

## 1. The deciding constraint (why V1 is hybrid, not all-online)

The browser drives the candidate's **own authenticated LinkedIn session** and creates/uses
**their own Workday account**. LinkedIn and Workday both flag automation from datacenter IPs.
Running that browser in DigitalOcean = the candidate's LinkedIn gets restricted. So:

> The browser runs on the candidate's machine (residential IP, real session).
> The cloud does the thinking (LLM, tailoring, CRM, orchestration) but never touches the browser.

This is the same standing rule the repos already enforce — *"the LLM assists, it does not decide
side effects"* — applied to a new product.

```
CANDIDATE PC (Docker: jhw-agent)                     DO DROPLET (cloud, reuse cybergod stack)
┌────────────────────────────────────┐               ┌──────────────────────────────────────┐
│ Chromium + Playwright (stealth)     │  outbound WSS │ FastAPI backend (existing)           │
│  ├─ LinkedIn session (real cookies) │◄─────────────►│  ├─ /api/chat   Qwen (existing)      │
│  ├─ Workday adapter (fills form)    │   task/result │  ├─ /api/scout  → real LinkedIn scout │
│  └─ reports DOM + confirmations     │   messages    │  ├─ /api/apply  → dispatch to agent  │
│                                     │               │  ├─ tailor.py   resume/CL (LLM)      │
│ NO secrets decided here — executes  │               │  └─ store/CRM   Kanban + history     │
│ instructions, asks user to confirm  │               │ DeepSeek/Qwen via DO Serverless      │
└────────────────────────────────────┘               └──────────────────────────────────────┘
        residential IP, candidate's real browser              datacenter IP — text only
```

**Local agent packaging:** Docker (`docker compose up` on the candidate PC), matching existing
patterns. A friendlier installer can come later.

**AI approach:** reuse the cybergod SDK-free DeepSeek/DO client. Adapter-first filling; the LLM
only reads the JD, tailors the resume/cover letter, and resolves ambiguous fields. `page-agent`
stays as a *fallback* for ATS portals we haven't written an adapter for — not the foundation.

---

## 2. The V1 flow, walked through Red Hat

1. **Candidate logs into the cloud portal** and starts the local `jhw-agent` (Docker) once. The
   agent imports their real logged-in LinkedIn session (cookie file, like `linkedin_verifier.py`).
2. **Scout** — candidate pastes/searches the LinkedIn job. Agent opens `linkedin.com/jobs/view/4435446898`,
   scrapes the JD (title, company, description, requirements). Cloud stores it.
3. **Tailor** — cloud LLM reads the JD + the candidate's profile (the LinkedIn "Save to PDF"
   export, e.g. `Profile.pdf`) and produces a tailored `resume.pdf` + `cover_letter.pdf` that
   surface the stakeholder value the JD asks for. Grounded only in real profile facts.
4. **Apply click** — agent clicks *Apply* on LinkedIn. Red Hat routes to the Workday portal.
5. **Workday adapter** takes over (see §4): creates/uses the candidate's Red Hat Workday account,
   uploads the tailored resume, autofills My Information / Experience / Education / screening
   questions from the profile. Missing-but-required fields → agent pauses and asks the candidate.
6. **Human gate** — agent fills everything, then **stops at Review**. The candidate clicks Submit
   (existing rule: *never auto-submit without an explicit user action*). Agent captures the
   confirmation number.
7. **CRM** — the application lands as a card in the Kanban ("Applied" column) with company, role,
   date, confirmation #, and links.

---

## 3. Components — new vs. reused

| Component | Status | Source to reuse |
|---|---|---|
| Stealth Chromium + cookie-session login | **reuse** | `Linkedin Scraper/linkedin_verifier.py` (`create_stealth_context`, `load_cookies`, `human_*`, `detect_challenge`) |
| SDK-free DeepSeek/DO LLM client (+fallback/retry) | **reuse** | `Linkedin Scraper/webapp/backend/app/assistant.py` (`_post_model`, `_call_llm`) + existing `backend/app/qwen.py` |
| FastAPI + SSE + store skeleton | **reuse (exists)** | `jobhuntwow-app/backend/app/{main,store,scout}.py` |
| Zero-trust auth (email+pw+OTP), signed sessions | **reuse (V1.1)** | `Linkedin Scraper/colt_auth.py` + `webapp/backend/app/auth.py` (generalize `@colt.net` regex) |
| Retry/backoff state machine, per-item checkpoint | **reuse** | `oxford-dictionary-scraper/src/scraper.py` (`fetch_url`, checkpoint), `database.py` |
| Per-selector field mapping → **per-ATS adapter config** | **new (from pattern)** | Oxford `parse_page` selector approach, generalized to a per-vendor selector map |
| **jhw-agent** local runner (Docker, WS to cloud) | **new** | wraps the reused Playwright core |
| **Workday adapter** | **new** | §4 |
| Resume/cover-letter tailoring (`tailor.py`) | **new** | uses LLM client + `pdf` skill for output |
| CRM Kanban board | **reuse/adapt** | `jobhuntwow.com/docker-jobhuntwow/frontend` Kanban components; existing `Pipeline.jsx` |
| Docker/Caddy deploy, GHCR CI, obs | **reuse** | `webapp/Dockerfile`, `docker-compose.web.yml`, `ship_web.py`, `obs/` |

---

## 4. Workday adapter (V1's one adapter)

Workday application flow is consistent across tenants (`*.myworkdayjobs.com`), which is exactly
why it's the highest-ROI first adapter. Adapter = an ordered list of steps, each a selector map +
a fill/action, with the LLM only consulted for free-text/ambiguous answers.

Canonical Workday steps the adapter must handle:
1. **Job page → Apply** (`Autofill with Resume` vs `Apply Manually`). Prefer Autofill with the
   tailored resume, then correct fields.
2. **Account** — sign in or create account (email + generated password). *Credential is generated
   per-company and stored in the vault — see §5.*
3. **My Information** — name, address, phone, contact prefs, "how did you hear about us".
4. **Experience** — work history, education, skills, languages, resume/CV upload, LinkedIn URL.
5. **Application Questions** — work authorization, relocation, notice period, sponsorship — the
   screening questions. Deterministic from profile where known; LLM-drafted then user-confirmed
   where not.
6. **Voluntary Disclosures / Self-Identify** — leave to candidate (sensitive; do not auto-fill).
7. **Review → STOP.** Human gate. Candidate submits.

Real selectors get captured during build against the Red Hat URL and stored as
`agent/adapters/workday.yml` (a versioned selector map, so a Workday UI change is a config edit,
not a code change).

---

## 5. Credentials & secrets (design note)

Each candidate gets a **generated per-company Workday login**. These are real secrets, so:
- Never in git, never in the JSON store (existing rule).
- V1: encrypted-at-rest vault on the cloud, per-user key; the agent pulls the one credential it
  needs at apply time over the authenticated channel. (Simplest secure option; can move to
  local-only vault later if preferred.)
- The email-fetch CRM automation (auto-linking interview emails to applications) is **V2**.

---

## 6. Build sequence

1. **`agent/` local runner** — lift `linkedin_verifier.py` stealth core into a standalone
   `jhw-agent` Docker service that connects out to the backend and runs tasks. Prove it opens
   LinkedIn with the candidate session and scrapes job `4435446898`.
2. **Real scout** — replace `scout.py` sample data with the agent-driven LinkedIn scrape,
   keeping the `{query,count,jobs,note}` shape.
3. **`tailor.py`** — JD + profile PDF → tailored resume + cover letter PDF (LLM + `pdf` skill).
4. **Workday adapter** — build `agent/adapters/workday.yml` + runner against the Red Hat URL,
   through fill; stop at Review.
5. **Human-gate wiring** — `/api/apply` dispatches to the agent, streams steps over SSE, waits
   for the candidate's explicit Submit.
6. **CRM Kanban** — applied jobs → cards; adapt the existing Pipeline page.
7. **Package & deploy** — agent Docker image + cloud via existing `ship_web.py`/CI.

Multi-user auth (colt_auth) folds in at step 5/7 as V1.1.

---

## 7. Guardrails (carried from existing CLAUDE.md rules)

- Never auto-submit an application without an explicit user click.
- The LLM writes text; deterministic code decides what gets filled, stored, or submitted.
- Secrets only in the vault / env, never in git or the JSON store.
- Frontend coerces unknown backend values to text (no white-screen on a shape change).
