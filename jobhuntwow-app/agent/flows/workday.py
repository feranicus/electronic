"""Deterministic Workday ATS driver (Playwright over CDP) — NO LLM, NO vision.

Workday tags every field with a stable `data-automation-id`, so the whole account + My-Information +
resume-upload flow is deterministic and fast. We drive it to the screening-questions / Review stage and
STOP; the LLM (agent.py) only finishes leftover custom questions. Never clicks the final Submit.

Returned dict: {ok, stage, filled[], note, needs_llm}. `needs_llm=True` means hand the CURRENT page to
the LLM to finish (questions/voluntary-disclosures), then a human submits in noVNC.
"""
from __future__ import annotations
import asyncio, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # /agent (for `import ask`)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # /agent/flows (for autofill)
from playwright.async_api import async_playwright
try:
    import ask
except Exception:
    ask = None
try:
    import autofill
except Exception:
    autofill = None

CDP_URL  = os.getenv("JHW_CDP_URL", "http://localhost:9222")
ACCOUNTS = os.path.join(os.getenv("JHW_OUT", "/agent/out"), "ats_accounts.json")


def _host(url: str) -> str:
    m = re.search(r"https?://([^/]+)", url or "")
    return m.group(1).lower() if m else ""


def _load_accounts() -> dict:
    try:
        return json.load(open(ACCOUNTS, encoding="utf-8"))
    except Exception:
        return {}


def _save_account(host, email, password):
    a = _load_accounts(); a[host] = {"email": email, "password": password}
    try:
        json.dump(a, open(ACCOUNTS, "w"), indent=2)
    except Exception:
        pass


async def _ask(q: str) -> str:
    if ask:
        try:
            return await ask.ask_human(q) or ""
        except Exception:
            return ""
    return ""

# --- Workday stable selectors (data-automation-id) -------------------------------------------------
S = {
    "cookie":        "#onetrust-accept-btn-handler, [data-automation-id='legalNoticeAcceptButton']",
    "apply":         "[data-automation-id='adventureButton'], a[data-automation-id='adventureButton']",
    "apply_manual":  "[data-automation-id='applyManually']",
    "email":         "[data-automation-id='email']",
    "password":      "[data-automation-id='password']",
    "verify_pw":     "[data-automation-id='verifyPassword']",
    "acct_checkbox": "[data-automation-id='createAccountCheckbox']",
    "create_link":   "[data-automation-id='createAccountLink']",
    "signin_link":   "[data-automation-id='signInLink']",
    "create_submit": "[data-automation-id='createAccountSubmitButton']",
    "signin_submit": "[data-automation-id='signInSubmitButton'], [data-automation-id='click_filter']",
    "first_name":    "[data-automation-id='legalNameSection_firstName']",
    "last_name":     "[data-automation-id='legalNameSection_lastName']",
    "addr1":         "[data-automation-id='addressSection_addressLine1']",
    "city":          "[data-automation-id='addressSection_city']",
    "postal":        "[data-automation-id='addressSection_postalCode']",
    "phone":         "[data-automation-id='phone-number']",
    "file_input":    "input[type='file'], input[data-automation-id='file-upload-input-ref']",
    "next":          "[data-automation-id='pageFooterNextButton'], [data-automation-id='bottom-navigation-next-button']",
    "error":         "[data-automation-id='errorMessage'], [data-automation-id='alertMessage']",
}


async def _connect(pw):
    browser = await pw.chromium.connect_over_cdp(CDP_URL)
    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
    # Use the MOST RECENT Workday tab (this run's), not the first stale one from earlier attempts.
    wd = [p for p in ctx.pages if re.search(r"myworkday|workday", (p.url or ""), re.I)]
    page = wd[-1] if wd else (ctx.pages[-1] if ctx.pages else await ctx.new_page())
    # close older stale Workday tabs so they can't confuse future runs
    for p in wd[:-1]:
        try: await p.close()
        except Exception: pass
    return browser, ctx, page


# probe JS (same as flows/probe.py) — dump real fields/buttons/ids so we write selectors from truth
_PROBE_JS = r"""
() => {
  const vis = (el)=>{const r=el.getBoundingClientRect();const s=getComputedStyle(el);
    return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none';};
  const lab=(el)=>{let t='';if(el.id){const l=document.querySelector(`label[for="${el.id}"]`);if(l)t=l.innerText;}
    if(!t){const l=el.closest('label');if(l)t=l.innerText;}return (t||'').replace(/\s+/g,' ').trim().slice(0,80);};
  const pick=(el)=>({tag:el.tagName.toLowerCase(),type:el.getAttribute('type')||'',
    dai:el.getAttribute('data-automation-id')||'',name:el.getAttribute('name')||'',id:el.id||'',
    ph:el.getAttribute('placeholder')||'',aria:el.getAttribute('aria-label')||'',label:lab(el),
    text:(el.innerText||'').replace(/\s+/g,' ').trim().slice(0,60)});
  return {url:location.href,
    inputs:[...document.querySelectorAll('input,textarea,select')].filter(vis).map(pick),
    buttons:[...document.querySelectorAll('button,[role=button],a')].filter(vis).map(pick).filter(b=>b.text||b.dai||b.aria),
    dais:[...new Set([...document.querySelectorAll('[data-automation-id]')].map(e=>e.getAttribute('data-automation-id')))].slice(0,150)};
}
"""


async def _dump(page, name: str):
    """Write the live DOM (fields/buttons/ids) of the current page to out/wd_<name>.json — ground truth."""
    try:
        import json as _j
        data = await page.evaluate(_PROBE_JS)
        outdir = os.getenv("JHW_OUT", "/agent/out")
        _j.dump(data, open(os.path.join(outdir, f"wd_{name}.json"), "w"), indent=2, ensure_ascii=False)
        print(f"[dump] wd_{name}.json  url={data.get('url','')[:80]}  inputs={len(data.get('inputs',[]))}", flush=True)
    except Exception as e:
        print(f"[dump] {name} failed: {e}", flush=True)


async def _has(page, sel, t=1500):
    try:
        return await page.locator(sel).first.is_visible(timeout=t)
    except Exception:
        return False


async def _click(page, sel, t=6000) -> bool:
    try:
        el = page.locator(sel).first
        await el.wait_for(state="visible", timeout=t)
        await el.click(); await page.wait_for_timeout(700)
        return True
    except Exception:
        return False


async def _fill(page, sel, value, t=5000) -> bool:
    if not value:
        return False
    try:
        el = page.locator(sel).first
        await el.wait_for(state="visible", timeout=t)
        await el.click(); await el.fill(""); await el.type(str(value), delay=15)
        return True
    except Exception:
        return False


async def _click_role(page, role, name_rx, t=4000) -> bool:
    """Click by ARIA role + visible name (robust when data-automation-id differs per tenant)."""
    try:
        el = page.get_by_role(role, name=re.compile(name_rx, re.I)).first
        await el.wait_for(state="visible", timeout=t); await el.click(); await page.wait_for_timeout(600)
        return True
    except Exception:
        return False


async def _check_consent(page) -> bool:
    """Tick the required consent / terms / privacy checkbox (the 'By clicking the checkbox I consent…'
       banner). This is the thing the old LLM kept fumbling — here it's deterministic."""
    if await _has(page, S["acct_checkbox"], 800):
        try:
            await page.locator(S["acct_checkbox"]).first.check(); return True
        except Exception:
            pass
    cbs = page.locator("input[type='checkbox']")
    try:
        n = await cbs.count()
    except Exception:
        n = 0
    for i in range(min(n, 12)):
        el = cbs.nth(i)
        try:
            if not await el.is_visible() or await el.is_checked():
                continue
            sig = ""
            eid = await el.get_attribute("id")
            if eid:
                lab = page.locator(f'label[for="{eid}"]')
                if await lab.count():
                    sig = await lab.first.inner_text()
            if not sig:
                try:
                    sig = await el.evaluate("e => (e.closest('label,div,fieldset')?.innerText) || ''")
                except Exception:
                    sig = ""
            if re.search(r"consent|agree|terms|privacy|acknowledge|certify", sig or "", re.I):
                await el.check(); return True
        except Exception:
            pass
    return False


def _split_address(addr: str):
    """'Hermann-J.-Bach-Weg 16, 61169 Friedberg (Hessen)' -> (line1, postal, city). Best-effort; human reviews."""
    line1, postal, city = addr, "", ""
    parts = [p.strip() for p in addr.split(",")]
    if parts:
        line1 = parts[0]
    rest = " ".join(parts[1:]) if len(parts) > 1 else ""
    m = re.search(r"\b(\d{4,6})\b", rest)
    if m:
        postal = m.group(1)
        city = rest.replace(postal, "").strip()
        city = re.sub(r"\(.*?\)", "", city).strip()   # drop "(Hessen)"
    return line1, postal, city


async def _past_gate(page) -> bool:
    """Through the gate only if the password field is gone AND no login error is showing."""
    await page.wait_for_timeout(500)
    if await _has(page, S["error"], 600):       # 'wrong email or password' etc. -> NOT past
        return False
    return not await _has(page, S["password"], 1200)


async def _is_review(page) -> bool:
    """Reached the final Review/Submit stage (we STOP here; a human submits)."""
    if "review" in (page.url or "").lower():
        return True
    try:
        if await page.get_by_role("button", name=re.compile(r"^\s*submit", re.I)).count() > 0:
            return True
    except Exception:
        pass
    return False


async def _answer_choices(page, profile, answer_fn) -> int:
    """Answer required radio-group questions (work auth, sponsorship, disclosures) via a text-only LLM,
       falling back to ask_human for anything the profile can't determine. Returns count answered."""
    if not answer_fn:
        return 0
    answered = 0
    groups = page.locator("[data-automation-id='radioGroup'], fieldset")
    try:
        n = await groups.count()
    except Exception:
        n = 0
    for i in range(min(n, 15)):
        g = groups.nth(i)
        try:
            if not await g.is_visible():
                continue
            radios = g.locator("input[type='radio']")
            rc = await radios.count()
            if rc == 0:
                continue
            if any([await radios.nth(j).is_checked() for j in range(rc)]):
                continue                                   # already answered
            qtext = (await g.inner_text())[:300]
            labs = g.locator("label")
            opts = []
            for j in range(min(await labs.count(), 8)):
                t = (await labs.nth(j).inner_text()).strip()
                if t:
                    opts.append(t)
            choice = await answer_fn(qtext, opts, profile)
            if choice and choice.strip().upper().startswith("UNKNOWN"):
                choice = await _ask(f"Application question needs your answer:\n{qtext}\nOptions: {opts}")
            if choice:
                for j in range(min(await labs.count(), 8)):
                    t = (await labs.nth(j).inner_text()).strip()
                    if t and (t.lower() in choice.lower() or choice.lower() in t.lower()):
                        await labs.nth(j).click(); answered += 1; break
        except Exception:
            pass
    return answered


async def _try_signin(page, email, password) -> bool:
    # switch from the Create-Account view to Sign-In (automation-id, else the visible "Sign In" link)
    if not await _click(page, S["signin_link"], t=1500):
        (await _click_role(page, "link", r"sign\s*in", t=1500)
         or await _click_role(page, "button", r"sign\s*in", t=1500))
    await page.wait_for_timeout(800)
    await _fill(page, S["email"], email)
    await _fill(page, S["password"], password)
    if not await _click(page, S["signin_submit"], t=2000):     # automation-id, else the visible button
        await _click_role(page, "button", r"^\s*sign\s*in\s*$")
    await page.wait_for_timeout(2800)
    return await _past_gate(page)


async def _account(page, host, email, proposed_pw, filled) -> bool:
    """Own the Workday account gate with STABLE per-host credentials. Returns True only when past it.
       create-once then sign-in-forever; if the account exists but we lack the password, ask the human."""
    accounts = _load_accounts()
    acc = accounts.get(host) or {}
    stored = acc.get("password")
    login_email = acc.get("email") or email        # the ACCOUNT login email (may differ from résumé email)

    # 1) Known account -> sign in with the stored login email + password.
    if stored:
        if await _try_signin(page, login_email, stored):
            filled.append("account:signin"); return True

    # 2) Fresh account -> Create Account (email, password, verify, consent) and persist the password.
    on_create = await _has(page, S["verify_pw"]) or await _has(page, S["acct_checkbox"])
    if on_create and not stored:
        await _fill(page, S["email"], email)
        await _fill(page, S["password"], proposed_pw)
        await _fill(page, S["verify_pw"], proposed_pw)
        await _check_consent(page)                              # tick the consent/terms banner FIRST
        if not await _click(page, S["create_submit"], t=2000):  # automation-id, else the visible button
            await _click_role(page, "button", r"create\s*account")
        await page.wait_for_timeout(2800)
        if await _past_gate(page):
            _save_account(host, email, proposed_pw); filled.append("account:create"); return True

    # 3) Account exists but our password is wrong/unknown -> ask the human once, then sign in + persist.
    pw = await _ask(f"JobHuntWOW is stuck at the Workday login for {host}. A candidate account for "
                    f"{login_email} seems to already exist. Reply with its PASSWORD (or use 'Forgot your "
                    f"password?' in the browser to reset it, then reply with the new one).")
    if pw and not pw.startswith("NO_ANSWER"):
        if await _try_signin(page, login_email, pw.strip()):
            _save_account(host, login_email, pw.strip()); filled.append("account:signin-human"); return True
    return False


async def drive(creds: dict, data: dict, resume_path: str = "", answer_fn=None) -> dict:
    """Deterministically drive Workday ALL THE WAY to the Review page. NO browser-use.
       autofill (password-manager engine) fills contact fields; answer_fn (a text-only LLM) answers
       required choice questions; we click Next page by page and STOP at Review. Never submits."""
    r = {"ok": False, "stage": "start", "filled": [], "note": "", "needs_llm": False}
    b = data.get("basics", {})
    legal = (b.get("legal_name") or b.get("name") or "").split()
    first = legal[0] if legal else ""
    last = " ".join(legal[1:]) if len(legal) > 1 else ""
    line1, postal, city = _split_address(b.get("address", ""))
    pw = await async_playwright().start(); browser = None
    try:
        browser, ctx, page = await _connect(pw)
        if not re.search(r"myworkday|workday", (page.url or ""), re.I):
            r["note"] = f"front tab is not Workday ({page.url}); letting LLM handle it."; return r
        await page.bring_to_front()
        r["stage"] = "cookie"
        await _click(page, S["cookie"], t=3000)                       # dismiss OneTrust banner

        r["stage"] = "apply"
        if await _has(page, S["apply"], 3000):                        # job-posting page -> start apply
            await _click(page, S["apply"])                            # adventureButton (confirmed)
            await page.wait_for_timeout(3000)                         # Workday navigates to the auth/method page
            await _click(page, S["apply_manual"], t=3000)             # 'Apply Manually' if a method dialog appears
            await page.wait_for_timeout(2500)
        await _dump(page, "after_apply")                              # ground truth: what page did Apply lead to?

        r["stage"] = "account"
        host = _host(page.url)
        # a signed-out Apply redirects to Sign In / Create Account — wait for a password field to render
        try:
            await page.wait_for_selector("input[type='password']", timeout=8000)
        except Exception:
            pass
        await _dump(page, "account")
        if await _has(page, "input[type='password']", 1500) or await _has(page, S["password"], 800):
            if not await _account(page, host, creds["email"], creds["password"], r["filled"]):
                r["needs_llm"] = False
                r["note"] = ("Could not get past the Workday account gate for " + host +
                             ". The account likely exists with a different password — reset it via "
                             "'Forgot your password?' in noVNC, or reply to the Telegram prompt, then re-run apply.")
                return r

        # PAGE LOOP — deterministic, no browser-use. Fill + answer + Next until Review.
        r["stage"] = "pages"
        for _i in range(9):
            await page.wait_for_timeout(1800)
            # wait for the SPA page body to actually render its fields before filling
            try:
                await page.wait_for_selector("input, [data-automation-id$='firstName'], "
                                             "[data-automation-id='fileUploadDropZone']", timeout=6000)
            except Exception:
                pass
            if _i == 0:
                await _dump(page, "form")                              # ground truth of the first form page
            if await _is_review(page):
                r["ok"] = True; r["stage"] = "review"
                r["note"] = ("Reached Review deterministically. Filled: " +
                             ", ".join(sorted(set(r["filled"]))) + ". Review in noVNC and Submit yourself.")
                return r
            # high-confidence Workday My-Information overlay (wait up to 6s for the fields to render)
            if await _has(page, S["first_name"], 6000):
                if await _fill(page, S["first_name"], first): r["filled"].append("first_name")
                if await _fill(page, S["last_name"], last):   r["filled"].append("last_name")
                if await _fill(page, S["addr1"], line1):      r["filled"].append("address")
                if await _fill(page, S["city"], city):        r["filled"].append("city")
                if await _fill(page, S["postal"], postal):    r["filled"].append("postal")
                if await _fill(page, S["phone"], b.get("phone", "")): r["filled"].append("phone")
            # generic autofill engine for everything else (email/linkedin/consent/etc.)
            if autofill:
                try:
                    rep = await autofill.fill_page(page, data)
                    r["filled"] += rep["filled"]
                except Exception as e:
                    r["note"] += f" autofill:{e};"
            # resume upload — file inputs are usually HIDDEN behind a drop-zone, so match by COUNT
            # (not visibility); set_input_files works on hidden inputs. Upload once.
            if resume_path and os.path.exists(resume_path) and "resume" not in r["filled"]:
                fi = page.locator("input[type='file']")
                try:
                    if await fi.count() > 0:
                        await fi.first.set_input_files(resume_path)
                        r["filled"].append("resume"); await page.wait_for_timeout(3000)
                except Exception as e:
                    r["note"] += f" upload:{e};"
            # answer required choice questions (work auth, sponsorship, disclosures) via text-only LLM
            try:
                a = await _answer_choices(page, data, answer_fn)
                if a:
                    r["filled"].append(f"answered:{a}")
            except Exception as e:
                r["note"] += f" answer:{e};"
            # advance to the next page
            if not await _click(page, S["next"], t=4000):
                r["note"] += " no Next button on this page — paused for the human."
                break
            await page.wait_for_timeout(1500)

        r["ok"] = True; r["stage"] = "paused"
        r["note"] = ("Deterministic fill advanced through the form (" +
                     ", ".join(sorted(set(r["filled"]))) + "). Stopped before Submit — finish/submit in noVNC.")
        return r
    except Exception as e:
        r["note"] = f"workday driver error: {e}"; return r
    finally:
        if browser:
            try: await browser.close()
            except Exception: pass
        await pw.stop()


if __name__ == "__main__":
    import json
    d = json.load(open(os.getenv("JHW_DATA", "/agent/templates/resume_data.json"), encoding="utf-8"))
    c = {"email": d["basics"]["email"], "password": "Test!Only1"}
    print(json.dumps(asyncio.run(drive(c, d, "/agent/out/resume.pdf")), indent=2))
