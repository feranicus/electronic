# MEDDPICC STEP UP — deploy on the Ubuntu 24.04 droplet (Docker + Gmail API)

A tiny always-on container in your existing stack that, **every Monday & Friday at 09:00**,
sends **individual** emails to your 37 AEs via the **Gmail API** — from `feranicus@s4biz.io`,
**Reply-To `jevgenijs.vainsteins@colt.net`** (so replies land in your Colt inbox), **CC**
Stephan + Alex + you, with the **deck attached**, in beautiful HTML. No drafts, no SMTP app
password, no man-in-the-middle. Your PC does not need to be on.

```
cron (Mon & Fri 09:00) ──► send.py ──► Gmail API (users.messages.send) ──► 37 AEs
                                        token.json (OAuth, gmail.send scope)
```

## Files in this folder
| File | Role |
|------|------|
| `send.py` | Builds each MIME email (Reply-To, CC, attachment, HTML) and sends via Gmail API |
| `get_token.py` | One-time: turns `credentials.json` → `token.json` (run on your laptop) |
| `recipients.json` | The 37 AEs (edit freely) |
| `Dockerfile`, `docker-compose.yml`, `crontab` | The container + Mon/Fri schedule |
| `.env.example` | Config → copy to `.env` |

---

## Step 1 — Google Cloud: enable Gmail API + get an OAuth client
You likely already did most of this for your existing Gmail API on the droplet — reuse it.

1. https://console.cloud.google.com → pick (or create) a project.
2. **APIs & Services → Library → Gmail API → Enable.**
3. **APIs & Services → OAuth consent screen:**
   - If `s4biz.io` is **Google Workspace** → set **User type = Internal**. *(Best: tokens
     never expire, no verification.)*
   - If it's a normal Gmail → User type = External, and **add `feranicus@s4biz.io` as a Test
     user**. ⚠️ In "Testing" mode refresh tokens expire after 7 days — to run long-term,
     click **Publish app** (for the `gmail.send` scope Google may ask you to verify).
   - Add the scope `https://www.googleapis.com/auth/gmail.send`.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID → Desktop app.**
   Download the JSON and save it as **`credentials.json`** next to `get_token.py`.

## Step 2 — Mint the token (once, on your laptop)
Do this where a browser is available (your laptop), not the headless droplet:
```bash
pip install google-auth-oauthlib
python get_token.py            # browser opens → sign in as feranicus@s4biz.io → allow "Send email"
```
This writes **`token.json`**. That's the only secret the droplet needs.

> Alternative (Workspace admins): use a **service account with domain-wide delegation**
> (delegate scope `gmail.send`, impersonate `feranicus@s4biz.io`) instead of OAuth — then no
> `token.json`/browser at all. Ask if you want that variant; the OAuth path above is simplest.

## Step 3 — Copy everything to the droplet
```bash
# from your laptop, in this folder:
scp -r "DropletDocker" root@<droplet-ip>:/opt/meddpicc
scp token.json root@<droplet-ip>:/opt/meddpicc/secrets/token.json
scp "..\Richard account review\Stephan_Security_Report_09Jul2026_v2.pptx" \
    root@<droplet-ip>:/opt/meddpicc/data/
```
On the droplet:
```bash
ssh root@<droplet-ip>
cd /opt/meddpicc
mkdir -p secrets data                 # (if scp didn't create them)
cp .env.example .env                  # review values; keep GO_LIVE=false for now
nano .env
```

## Step 4 — Build & test
```bash
docker compose build
# one-off test send to yourself (uses the same code path):
docker compose run --rm meddpicc python send.py test
```
Open **evgeny@s4biz.io** → hit **Reply** → the To field must show
`jevgenijs.vainsteins@colt.net`, deck attached, HTML correct. ✅

## Step 5 — Go live (24/7 cron container)
```bash
# in .env set GO_LIVE=true  (sends to all 37 AEs)
docker compose up -d
docker compose logs -f meddpicc       # watch; it fires Mon & Fri 09:00
```
`restart: unless-stopped` keeps it alive across reboots. Done — fully automatic.

## Manage
```bash
docker compose run --rm meddpicc python send.py monday   # send this week's Monday mail now
docker compose run --rm meddpicc python send.py friday   # send the Friday nudge now
docker compose restart meddpicc                          # after editing recipients.json/.env
docker compose down                                      # stop
```

## Edit content / list
- **Recipients:** `recipients.json` (mounted read-only; `docker compose restart` to pick up).
- **Wording / design:** the `html()` function in `send.py` (rebuild: `docker compose build`).
- **CC / Reply-To / times:** `.env` and `crontab`.

## Notes & gotchas
- **Token longevity:** with Workspace **Internal** consent screen the refresh token doesn't
  expire. On an **External app left in "Testing"** it expires every 7 days — publish the app
  (or switch to Internal) so you don't have to re-mint `token.json`.
- **Quota:** Gmail API send limit is generous (Workspace ~1,500–2,000 recipients/day); 37×2/wk
  is nothing.
- **Secrets:** `secrets/token.json` and `.env` are sensitive — don't commit them. `.dockerignore`
  already keeps them out of the image; they're mounted read-only at runtime.
- **Timezone:** set in `.env` (`TZ=Europe/Berlin`) so 09:00 means your 09:00.
