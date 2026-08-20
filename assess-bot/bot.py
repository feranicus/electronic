#!/usr/bin/env python3
"""cybergod.ai assessment Telegram bot — deterministic engine + ONE controlled
DeepSeek enrichment call. Zero-trust gate: every user must authenticate with an approved
email (name.familyname@yourcompany.com) + a shared 99-char access password BEFORE using /assess.
Streams live phase progress, shows when the AI takes over (tokens + est cost), and re-emits
structured JSON events (incl. auth audit) for the Loki/Grafana observability stack."""
import os, re, json, time, asyncio, colt_auth
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN   = os.environ["BOT_TOKEN"]
ALLOWED = {x.strip() for x in os.environ.get("ALLOWED_USERS", "").split(",") if x.strip()}
OUTDIR  = os.environ.get("OUTDIR", "/root/work")
ENGINE  = "/opt/shodan-skill/scripts/run_assessment.py"
EVENTS  = os.environ.get("EVENTS_LOG", os.path.join(OUTDIR, "events.log"))
try: os.makedirs(os.path.dirname(EVENTS), exist_ok=True)
except Exception: pass

# ---------------- zero-trust auth (email + password + email OTP 2FA — shared module) ----------------
AUTHFILE   = os.environ.get("AUTH_STORE", os.path.join(os.path.dirname(EVENTS), "authorized.json"))
QWEN_EVT_A = '"evt": "qwen"'; QWEN_EVT_B = '"evt":"qwen"'
BOT_NAME   = "colttechbot"
def _evfile(line):
    try:
        with open(EVENTS, "a") as fh: fh.write(line + "\n")
    except Exception: pass
def _evfile_json(line):
    # tag subprocess JSON events (qwen/phase/assess_done) with the bot for observability
    try:
        o = json.loads(line)
        if isinstance(o, dict):
            o.setdefault("bot", BOT_NAME); line = json.dumps(o)
    except Exception: pass
    _evfile(line)
def _log(**k):
    k.setdefault("bot", BOT_NAME)
    line = json.dumps(k); print(line, flush=True); _evfile(line)

AUTH = colt_auth.Auth(BOT_NAME, AUTHFILE, log=_log)   # email + password + email OTP 2FA

# ------------------------------------------- INTERFACE language vs DOCUMENT language -------------
# These are TWO DIFFERENT THINGS and conflating them ships a lie.
#   * the INTERFACE language is how this bot talks to the operator — six of them, same set as the site;
#   * the DOCUMENT language is what the generated decks are written in — and the ENGINE only ships two.
# A deck language needs `scripts/i18n/<lang>.json` + the i18n.py post-pass + a LANG_* prompt block in
# enrich.py (per-company PROSE, which no dictionary can ever cover). So "the bot speaks Polish" does
# NOT imply "the decks speak Polish". Before this split, `/lang it` would have sent `--lang it` to the
# engine, the engine would have silently fallen back to English, and the operator would have received
# an English deck out of an Italian conversation with nothing saying so.
#
# The website remembers the reader's language in localStorage. A Telegram chat has no access to that,
# so "switch them together" cannot mean one shared switch — the honest equivalent is: each surface
# defaults to the SAME signal (the user's own client language) and remembers a per-user override.
# Telegram hands us `language_code` on every update, so a German user gets German without asking.
LANGS = ("en", "de", "it", "fr", "es", "pl")     # INTERFACE languages (what the bot speaks)
_LANG = {}                       # telegram uid -> interface code   (persisted alongside the auth store)
_LANGFILE = os.path.join(os.path.dirname(AUTHFILE), "lang.json")
try:
    _LANG.update({int(k): v for k, v in json.load(open(_LANGFILE, encoding="utf-8")).items()})
except Exception:
    pass


def _save_lang():
    try:
        json.dump(_LANG, open(_LANGFILE, "w", encoding="utf-8"))
    except Exception:
        pass


def lang_of(update):
    """This user's INTERFACE language: explicit choice first, else their Telegram client's setting."""
    u = update.effective_user
    if u and u.id in _LANG and _LANG[u.id] in LANGS:
        return _LANG[u.id]
    code = str(getattr(u, "language_code", "") or "").lower()
    for c in LANGS:                      # "de-AT" -> de, "en-GB" -> en; no prefix collisions in LANGS
        if code.startswith(c):
            return c
    return "en"


# ---- what the DECK ENGINE can ACTUALLY render — asked, never assumed ----------------------------
# deck_langs.doc_langs() derives the answer from the dictionaries on disk, so adding `it.json` +
# an enrich prompt block lights Italian up here with no change to this bot. Imported defensively:
# in the container the engine lives at /opt/shodan-skill/scripts, locally at the repo path. A
# capability probe must never take the bot down — on any failure we claim English only, which is
# always true.
def _load_deck_langs():
    import importlib.util as _ilu
    _here = os.path.dirname(os.path.abspath(__file__))
    for base in (os.path.dirname(ENGINE),
                 os.path.join(os.path.dirname(_here), "hermes-skills", "shodan-assessment", "scripts")):
        try:
            path = os.path.join(base, "deck_langs.py")
            if not os.path.exists(path):
                continue
            spec = _ilu.spec_from_file_location("deck_langs", path)
            mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        except Exception:
            continue
    return None


_DECK_LANGS = _load_deck_langs()
_DOC_NAME = {"en": "English", "de": "Deutsch", "it": "Italiano",
             "fr": "Français", "es": "Español", "pl": "Polski"}
_DOC_FLAG = {"en": "\U0001f1ec\U0001f1e7", "de": "\U0001f1e9\U0001f1ea", "it": "\U0001f1ee\U0001f1f9",
             "fr": "\U0001f1eb\U0001f1f7", "es": "\U0001f1ea\U0001f1f8", "pl": "\U0001f1f5\U0001f1f1"}


def doc_langs():
    """Languages the deck engine can genuinely produce (today: en, de)."""
    try:
        out = [str(c).lower() for c in _DECK_LANGS.doc_langs()]
        return out or ["en"]
    except Exception:
        return ["en"]


def doc_supported(lang):
    """Coerce ANY requested code down to one the engine can really write. Fail-closed to English."""
    try:
        return _DECK_LANGS.supported(lang)
    except Exception:
        code = str(lang or "en").strip().lower()[:2]
        return code if code in doc_langs() else "en"


def _doc_name(code):
    return _DOC_NAME.get(code, str(code).upper())


def _doc_names():
    """'English, Deutsch' — endonyms, so the sentence reads the same in every interface language."""
    return ", ".join(_doc_name(c) for c in doc_langs())


def _doc_keyboard():
    """The document-language buttons, BUILT FROM doc_langs() — never a hardcoded pair."""
    btns = [InlineKeyboardButton("%s  %s" % (_DOC_FLAG.get(c, "\U0001f310"), _doc_name(c)),
                                 callback_data="lang:" + c) for c in doc_langs()]
    return InlineKeyboardMarkup([btns[i:i + 2] for i in range(0, len(btns), 2)])


def _split_lang_flag(extra):
    """Pull `--lang xx` / `--lang=xx` out of the extra args -> (requested_code_or_None, rest).

    Everything that reaches the engine is re-emitted through doc_supported(), so an unsupported code
    can never arrive at `--lang` unchallenged — including via the power-user shortcut."""
    rest, req, i = [], None, 0
    while i < len(extra):
        tok = str(extra[i])
        if tok == "--lang":
            if i + 1 < len(extra):
                req = str(extra[i + 1]).strip().lower()
            i += 2
            continue
        if tok.lower().startswith("--lang="):
            req = tok.split("=", 1)[1].strip().lower()
            i += 1
            continue
        rest.append(extra[i])
        i += 1
    return req, rest


def _md(s):
    """Telegram legacy-Markdown escape for interpolated user input (a company name may hold _ or *)."""
    out = str(s)
    for ch in ("\\", "_", "*", "`", "["):
        out = out.replace(ch, "\\" + ch)
    return out


T = {
 "start": {
  "en": ("\U0001f512 cybergod.ai Cyber Assessment bot — zero-trust access.\n\n"
         "To use this bot you must authenticate with your approved identity:\n"
         "  /auth name.familyname@yourcompany.com <access-password>\n\n"
         "After authentication:\n"
         "  /assess <company / domain / ASN>\n"
         "  e.g.  /assess keb.de\n"
         "  Behind a CDN?  /assess <company> --asn AS1234 --net 1.2.3.0/24\n"
         "  I will ask which language the documents should be written in;\n"
         "  skip the question with  /assess <company> --lang de\n\n"
         "  /lang en | de | it | fr | es | pl  sets the language I speak to you in.\n\n"
         "2-step: after /auth I email a 6-digit code to that address; reply /verify <code>.\n"
         "\u26a0 Your /auth message contains a secret — delete it from this chat afterwards."),
  "de": ("\U0001f512 cybergod.ai Cyber-Assessment-Bot — Zero-Trust-Zugang.\n\n"
         "Zur Nutzung müssen Sie sich mit Ihrer freigegebenen Identität authentifizieren:\n"
         "  /auth name.nachname@ihrefirma.de <Zugangspasswort>\n\n"
         "Nach der Authentifizierung:\n"
         "  /assess <Firma / Domain / ASN>\n"
         "  z. B.  /assess keb.de\n"
         "  Hinter einem CDN?  /assess <Firma> --asn AS1234 --net 1.2.3.0/24\n"
         "  Ich frage, in welcher Sprache die Dokumente erstellt werden sollen;\n"
         "  überspringen mit  /assess <Firma> --lang de\n\n"
         "  /lang en | de | it | fr | es | pl  legt fest, in welcher Sprache ich mit Ihnen spreche.\n\n"
         "2 Schritte: nach /auth sende ich einen 6-stelligen Code per E-Mail; antworten Sie /verify <Code>.\n"
         "\u26a0 Ihre /auth-Nachricht enthält ein Geheimnis — bitte anschließend aus dem Chat löschen."),
  "it": ("\U0001f512 Bot di Cyber Assessment cybergod.ai — accesso zero-trust.\n\n"
         "Per usare questo bot deve autenticarsi con la Sua identità approvata:\n"
         "  /auth nome.cognome@azienda.it <password-di-accesso>\n\n"
         "Dopo l'autenticazione:\n"
         "  /assess <azienda / dominio / ASN>\n"
         "  es.  /assess keb.de\n"
         "  Dietro una CDN?  /assess <azienda> --asn AS1234 --net 1.2.3.0/24\n"
         "  Le chiederò in quale lingua redigere i documenti;\n"
         "  per saltare la domanda:  /assess <azienda> --lang de\n\n"
         "  /lang en | de | it | fr | es | pl  imposta la lingua in cui Le parlo.\n\n"
         "Due passaggi: dopo /auth invio un codice di 6 cifre a quell'indirizzo; risponda /verify <codice>.\n"
         "\u26a0 Il Suo messaggio /auth contiene un segreto — lo elimini dalla chat subito dopo."),
  "fr": ("\U0001f512 Bot d'évaluation cyber cybergod.ai — accès zero-trust.\n\n"
         "Pour utiliser ce bot, vous devez vous authentifier avec votre identité approuvée :\n"
         "  /auth prenom.nom@votreentreprise.fr <mot-de-passe-d-acces>\n\n"
         "Après l'authentification :\n"
         "  /assess <entreprise / domaine / ASN>\n"
         "  ex.  /assess keb.de\n"
         "  Derrière un CDN ?  /assess <entreprise> --asn AS1234 --net 1.2.3.0/24\n"
         "  Je vous demanderai dans quelle langue rédiger les documents ;\n"
         "  pour sauter la question :  /assess <entreprise> --lang de\n\n"
         "  /lang en | de | it | fr | es | pl  définit la langue dans laquelle je vous parle.\n\n"
         "Deux étapes : après /auth, j'envoie un code à 6 chiffres à cette adresse ; "
         "répondez /verify <code>.\n"
         "\u26a0 Votre message /auth contient un secret — supprimez-le ensuite de cette conversation."),
  "es": ("\U0001f512 Bot de evaluación cibernética cybergod.ai — acceso zero-trust.\n\n"
         "Para usar este bot debe autenticarse con su identidad aprobada:\n"
         "  /auth nombre.apellido@suempresa.es <contraseña-de-acceso>\n\n"
         "Tras la autenticación:\n"
         "  /assess <empresa / dominio / ASN>\n"
         "  p. ej.  /assess keb.de\n"
         "  ¿Detrás de una CDN?  /assess <empresa> --asn AS1234 --net 1.2.3.0/24\n"
         "  Le preguntaré en qué idioma deben redactarse los documentos;\n"
         "  para omitir la pregunta:  /assess <empresa> --lang de\n\n"
         "  /lang en | de | it | fr | es | pl  fija el idioma en el que le hablo.\n\n"
         "Dos pasos: tras /auth envío un código de 6 dígitos a esa dirección; responda /verify <código>.\n"
         "\u26a0 Su mensaje /auth contiene un secreto — elimínelo después de este chat."),
  "pl": ("\U0001f512 Bot Cyber Assessment cybergod.ai — dostęp zero-trust.\n\n"
         "Aby korzystać z bota, należy uwierzytelnić się zatwierdzoną tożsamością:\n"
         "  /auth imie.nazwisko@twojafirma.pl <hasło-dostępu>\n\n"
         "Po uwierzytelnieniu:\n"
         "  /assess <firma / domena / ASN>\n"
         "  np.  /assess keb.de\n"
         "  Za CDN-em?  /assess <firma> --asn AS1234 --net 1.2.3.0/24\n"
         "  Zapytam, w jakim języku mają powstać dokumenty;\n"
         "  aby pominąć pytanie:  /assess <firma> --lang de\n\n"
         "  /lang en | de | it | fr | es | pl  ustawia język, w którym prowadzę rozmowę.\n\n"
         "Dwa kroki: po /auth wysyłam 6-cyfrowy kod na ten adres; w odpowiedzi należy wpisać /verify <kod>.\n"
         "\u26a0 Wiadomość /auth zawiera sekret — trzeba ją potem usunąć z czatu."),
 },
 "auth_usage": {"en": "Usage: /auth name.familyname@yourcompany.com <access-password>",
                "de": "Verwendung: /auth name.nachname@ihrefirma.de <Zugangspasswort>",
                "it": "Uso: /auth nome.cognome@azienda.it <password-di-accesso>",
                "fr": "Utilisation : /auth prenom.nom@votreentreprise.fr <mot-de-passe-d-acces>",
                "es": "Uso: /auth nombre.apellido@suempresa.es <contraseña-de-acceso>",
                "pl": "Użycie: /auth imie.nazwisko@twojafirma.pl <hasło-dostępu>"},
 "auth_warn":  {"en": "\n⚠ Delete your /auth message — it contains the password.",
                "de": "\n⚠ Löschen Sie Ihre /auth-Nachricht — sie enthält das Passwort.",
                "it": "\n⚠ Elimini il Suo messaggio /auth — contiene la password.",
                "fr": "\n⚠ Supprimez votre message /auth — il contient le mot de passe.",
                "es": "\n⚠ Elimine su mensaje /auth — contiene la contraseña.",
                "pl": "\n⚠ Należy usunąć wiadomość /auth — zawiera hasło."},
 "verify_usage": {"en": "Usage: /verify <6-digit code from your email>",
                  "de": "Verwendung: /verify <6-stelliger Code aus Ihrer E-Mail>",
                  "it": "Uso: /verify <codice di 6 cifre ricevuto via e-mail>",
                  "fr": "Utilisation : /verify <code à 6 chiffres reçu par e-mail>",
                  "es": "Uso: /verify <código de 6 dígitos recibido por correo>",
                  "pl": "Użycie: /verify <6-cyfrowy kod z wiadomości e-mail>"},
 "not_authed": {"en": ("\U0001f512 Not authenticated. Run:\n"
                       "  /auth name.familyname@yourcompany.com <access-password>\n"
                       "then /verify <code> from the email I send you."),
                "de": ("\U0001f512 Nicht authentifiziert. Bitte:\n"
                       "  /auth name.nachname@ihrefirma.de <Zugangspasswort>\n"
                       "danach /verify <Code> aus der E-Mail, die ich Ihnen sende."),
                "it": ("\U0001f512 Non autenticato. Esegua:\n"
                       "  /auth nome.cognome@azienda.it <password-di-accesso>\n"
                       "poi /verify <codice> dall'e-mail che Le invio."),
                "fr": ("\U0001f512 Non authentifié. Lancez :\n"
                       "  /auth prenom.nom@votreentreprise.fr <mot-de-passe-d-acces>\n"
                       "puis /verify <code> reçu dans l'e-mail que je vous envoie."),
                "es": ("\U0001f512 Sin autenticar. Ejecute:\n"
                       "  /auth nombre.apellido@suempresa.es <contraseña-de-acceso>\n"
                       "y después /verify <código> del correo que le envío."),
                "pl": ("\U0001f512 Brak uwierzytelnienia. Należy wykonać:\n"
                       "  /auth imie.nazwisko@twojafirma.pl <hasło-dostępu>\n"
                       "a następnie /verify <kod> z wiadomości e-mail.")},
 "not_authed_short": {"en": "\U0001f512 Not authenticated.",
                      "de": "\U0001f512 Nicht authentifiziert.",
                      "it": "\U0001f512 Non autenticato.",
                      "fr": "\U0001f512 Non authentifié.",
                      "es": "\U0001f512 Sin autenticar.",
                      "pl": "\U0001f512 Brak uwierzytelnienia."},
 "assess_usage": {"en": "Usage: /assess <company / domain / ASN>",
                  "de": "Verwendung: /assess <Firma / Domain / ASN>",
                  "it": "Uso: /assess <azienda / dominio / ASN>",
                  "fr": "Utilisation : /assess <entreprise / domaine / ASN>",
                  "es": "Uso: /assess <empresa / dominio / ASN>",
                  "pl": "Użycie: /assess <firma / domena / ASN>"},
 # %s = the company (Markdown-escaped). Sent with parse_mode="Markdown".
 # The deck names stay English by rule, so they live outside the translated sentence.
 "ask_docs": {"en": "\U0001f30d In which language should I write the documents for *%s*?",
              "de": "\U0001f30d In welcher Sprache soll ich die Dokumente für *%s* erstellen?",
              "it": "\U0001f30d In quale lingua devo redigere i documenti per *%s*?",
              "fr": "\U0001f30d Dans quelle langue dois-je rédiger les documents pour *%s* ?",
              "es": "\U0001f30d ¿En qué idioma debo redactar los documentos de *%s*?",
              "pl": "\U0001f30d W jakim języku mam przygotować dokumenty dla *%s*?"},
 "ask_tip": {"en": "_Tip: add --lang de to /assess to skip this question._",
             "de": "_Tipp: --lang de an /assess anhängen überspringt diese Frage._",
             "it": "_Suggerimento: aggiunga --lang de a /assess per saltare questa domanda._",
             "fr": "_Astuce : ajoutez --lang de à /assess pour sauter cette question._",
             "es": "_Consejo: añada --lang de a /assess para omitir esta pregunta._",
             "pl": "_Wskazówka: dodanie --lang de do /assess pomija to pytanie._"},
 # %s = the document languages the ENGINE can really render (endonyms, e.g. "English, Deutsch").
 # This is THE sentence that stops an Italian conversation quietly producing an English deck.
 "doc_only": {"en": "ℹ The documents can be written in %s only.",
              "de": "ℹ Die Dokumente können nur in %s erstellt werden.",
              "it": "ℹ I documenti possono essere redatti solo in %s.",
              "fr": "ℹ Les documents ne peuvent être rédigés qu'en %s.",
              "es": "ℹ Los documentos solo pueden redactarse en %s.",
              "pl": "ℹ Dokumenty mogą powstać wyłącznie w tych językach: %s."},
 # %s = the document language actually used after coercion.
 "doc_coerced": {"en": "ℹ That document language is not available — I will write them in %s.",
                 "de": "ℹ Diese Dokumentsprache gibt es nicht — ich erstelle sie in %s.",
                 "it": "ℹ Quella lingua dei documenti non è disponibile — li redigerò in %s.",
                 "fr": "ℹ Cette langue de document n'est pas disponible : je les rédigerai en %s.",
                 "es": "ℹ Ese idioma de documento no está disponible: los redactaré en %s.",
                 "pl": "ℹ Ten język dokumentów nie jest dostępny — powstaną w tym języku: %s."},
 "lang_set": {"en": "✅ Interface language: English. I will speak to you in it from now on.",
              "de": "✅ Oberflächensprache: Deutsch. Ab jetzt spreche ich Sie in dieser Sprache an.",
              "it": "✅ Lingua dell'interfaccia: italiano. D'ora in poi Le parlerò in questa lingua.",
              "fr": "✅ Langue de l'interface : français. Je vous parlerai désormais dans cette langue.",
              "es": "✅ Idioma de la interfaz: español. A partir de ahora le hablaré en este idioma.",
              "pl": "✅ Język interfejsu: polski. Od teraz prowadzę rozmowę w tym języku."},
 "lang_usage": {"en": "Usage: /lang en | de | it | fr | es | pl",
                "de": "Verwendung: /lang en | de | it | fr | es | pl",
                "it": "Uso: /lang en | de | it | fr | es | pl",
                "fr": "Utilisation : /lang en | de | it | fr | es | pl",
                "es": "Uso: /lang en | de | it | fr | es | pl",
                "pl": "Użycie: /lang en | de | it | fr | es | pl"},
 "expired": {"en": "That request expired — send /assess <company> again.",
             "de": "Diese Anfrage ist abgelaufen — senden Sie /assess <Firma> erneut.",
             "it": "Questa richiesta è scaduta — invii di nuovo /assess <azienda>.",
             "fr": "Cette demande a expiré — renvoyez /assess <entreprise>.",
             "es": "Esa solicitud ha caducado — envíe de nuevo /assess <empresa>.",
             "pl": "Ta prośba wygasła — należy ponownie wysłać /assess <firma>."},
 # %s x3 = flag, DOCUMENT-language name, company.
 "starting": {"en": "%s Documents in %s — starting the assessment for %s ...",
              "de": "%s Dokumente in %s — starte das Assessment für %s ...",
              "it": "%s Documenti in %s — avvio la valutazione di %s ...",
              "fr": "%s Documents en %s — je lance l'évaluation de %s ...",
              "es": "%s Documentos en %s — inicio la evaluación de %s ...",
              "pl": "%s Dokumenty w tym języku: %s — rozpoczynam analizę: %s ..."},
 "working": {"en": "⏳ Assessing %s ...",
             "de": "⏳ Assessment für %s läuft ...",
             "it": "⏳ Valutazione di %s in corso ...",
             "fr": "⏳ Évaluation de %s en cours ...",
             "es": "⏳ Evaluando %s ...",
             "pl": "⏳ Trwa analiza: %s ..."},
 "done": {"en": "✅ Done.", "de": "✅ Fertig.", "it": "✅ Fatto.",
          "fr": "✅ Terminé.", "es": "✅ Listo.", "pl": "✅ Gotowe."},
 "failed": {"en": "❌ Failed:", "de": "❌ Fehlgeschlagen:", "it": "❌ Non riuscita:",
            "fr": "❌ Échec :", "es": "❌ Ha fallado:", "pl": "❌ Niepowodzenie:"},
}


def tl(lang, key):
    """Look a string up by language CODE. A missing translation falls back to English, never KeyError."""
    d = T.get(key, {})
    return d.get(lang, d.get("en", key))


def t(update, key):
    return tl(lang_of(update), key)


async def lang_cmd(update, ctx):
    """/lang <code> — sets the INTERFACE language only (all six of them).

    The DOCUMENT language is a SEPARATE question, because the deck engine ships fewer languages than
    the interface does. Setting Italian here must never imply an Italian deck."""
    arg = (ctx.args[0].lower() if ctx.args else "")
    if arg not in LANGS:
        await update.message.reply_text(t(update, "lang_usage")); return
    _LANG[update.effective_user.id] = arg
    _save_lang()
    # Confirmation in the NEW language, and say plainly that the documents are a shorter list.
    await update.message.reply_text(T["lang_set"][arg] + "\n" + (tl(arg, "doc_only") % _doc_names()))


async def start(update, ctx):
    """The help text, in the operator's own language, plus what the DOCUMENTS can actually be."""
    await update.message.reply_text(
        t(update, "start") + "\n\n" + (t(update, "doc_only") % _doc_names()))


async def auth(update, ctx):
    uid = update.effective_user.id
    if len(ctx.args) < 2:
        await update.message.reply_text(t(update, "auth_usage"))
        return
    email = ctx.args[0].strip(); pw = " ".join(ctx.args[1:]).strip()
    _, msg = AUTH.begin(uid, email, pw)               # validates, then emails a 6-digit code
    await update.message.reply_text(msg + t(update, "auth_warn"))

async def verify(update, ctx):
    uid = update.effective_user.id
    if not ctx.args:
        await update.message.reply_text(t(update, "verify_usage")); return
    _, msg = AUTH.verify(uid, ctx.args[0].strip())
    await update.message.reply_text(msg)

async def assess(update, ctx):
    """Collect the company, then ask which language the DOCUMENTS should be in.

    The document languages are whatever the engine can really render (deck_langs.doc_langs()) — a
    SHORTER list than the six the bot speaks. Power users skip the prompt with
    `/assess <company> --lang de`, and even that goes through doc_supported()."""
    uid = update.effective_user.id
    if not AUTH.is_authed(uid, ALLOWED):
        await update.message.reply_text(
t(update, "not_authed"))
        _log(evt="assess_denied", user=str(uid), ts=int(time.time())); return
    if not ctx.args:
        await update.message.reply_text(t(update, "assess_usage"))
        return
    _args = list(ctx.args)
    _i = next((k for k, tok in enumerate(_args) if tok.startswith('--')), len(_args))
    seed = ' '.join(_args[:_i]).strip(); extra = _args[_i:]   # multi-word company names -> one seed
    if not seed:
        await update.message.reply_text(t(update, "assess_usage")); return

    ui = lang_of(update)
    requested, rest = _split_lang_flag(extra)

    # explicit --lang xx -> run straight away, no question — but never pass it through unchecked.
    if requested:
        doc = doc_supported(requested)
        if doc != requested:
            await update.message.reply_text(t(update, "doc_coerced") % _doc_name(doc))
        await _run_assessment(update.message, ctx, uid, seed, rest + ["--lang", doc], ui); return

    # A user who has already chosen an interface language the ENGINE can also write has answered
    # this question for good — do not ask again. If it CANNOT write it, we must ask.
    if update.effective_user.id in _LANG and ui in doc_langs():
        await _run_assessment(update.message, ctx, uid, seed, rest + ["--lang", ui], ui); return

    # otherwise ask. The pending run is parked per-user (never global: two AEs can assess at once).
    ctx.user_data["pending"] = {"seed": seed, "extra": rest}
    body = [t(update, "ask_docs") % _md(seed), "_Findings · C-BIQ · GEOPOL · DELTAS_"]
    if ui not in doc_langs():
        # Say it plainly, in their language: the decks do not come in Italian/French/Spanish/Polish.
        body.append(t(update, "doc_only") % _doc_names())
    body.append(t(update, "ask_tip"))
    await update.message.reply_text("\n".join(body),
                                    reply_markup=_doc_keyboard(), parse_mode="Markdown")


async def on_lang(update, ctx):
    """Document-language button pressed -> start the parked assessment."""
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    ui = lang_of(update)
    if not AUTH.is_authed(uid, ALLOWED):
        await q.edit_message_text(t(update, "not_authed_short")); return
    lang = doc_supported(q.data.split(":", 1)[-1])       # the button can only ever offer a real one
    pending = (ctx.user_data or {}).pop("pending", None)
    if not pending:
        await q.edit_message_text(t(update, "expired")); return
    await q.edit_message_text(t(update, "starting") % (
        _DOC_FLAG.get(lang, "\U0001f310"), _doc_name(lang), pending["seed"]))
    await _run_assessment(q.message, ctx, uid, pending["seed"],
                          pending["extra"] + ["--lang", lang], ui)


def _brand_env(email):
    """White Label: point the engine at this partner's theme, if they have one.

    ONE derivation of the path, matching webapp/backend/app/brand.py — both read it from
    EVENTS_LOG's directory, which is the shared colt_events volume every container already mounts.
    Importing colt-web's app package instead is not an option (this image does not have it), and
    hardcoding a second copy of the path would be the "two homes for one value" defect again.
    Fails SILENT: a branding lookup must never be the reason a Telegram assessment does not start.
    """
    try:
        base = os.path.dirname(os.environ.get("EVENTS_LOG", "/var/log/colt/events.log"))
        root = os.environ.get("BRAND_DIR", os.path.join(base, "brands"))
        safe = re.sub(r"[^a-z0-9._-]", "_", (email or "").strip().lower())
        if not safe or safe in (".", ".."):
            return {}
        p = os.path.join(root, safe, "theme.json")
        return {"BRAND_THEME": p} if os.path.isfile(p) else {}
    except Exception:
        return {}


async def _run_assessment(msg, ctx, uid, seed, extra, ui="en"):
    # `ui` is the INTERFACE language (how we narrate); `lang` is the DOCUMENT language the engine
    # was actually given. They are deliberately allowed to differ.
    _req, _ = _split_lang_flag(extra)
    lang = doc_supported(_req)
    _log(evt="assess_start", company=seed, user=str(uid), lang=lang,
         email=AUTH.authed.get(str(uid), {}).get("email", ""), ts=int(time.time()))

    _who = AUTH.authed.get(str(uid), {}).get("email", "")

    # PER-USER QUOTA. The web app counts its own jobs table, which this process cannot see, so the
    # bot counts the durable cost ledger on the shared colt_events volume instead. Without this the
    # Telegram front door would simply be the way around an evaluation cap. Both look up the same
    # allowance in colt_auth, so the two can never disagree about who is limited.
    try:
        import colt_auth as _CA
        _cap = _CA.quota_for(_who)
        if _cap:
            import sys as _sys
            _sys.path.insert(0, os.path.dirname(ENGINE))
            import cost_ledger as _CL
            _used = _CL.count_for_user(_who)
            if _used >= _cap:
                _log(evt="quota_exceeded", user=_who, used=_used, cap=_cap)
                await msg.reply_text(
                    "Assessment limit reached: %d of %d used. This is an evaluation account.\n"
                    "Contact feranicus@s4biz.io to raise the limit." % (_used, _cap))
                return
    except Exception:
        pass                       # a quota lookup must never take an assessment down

    status = await msg.reply_text(tl(ui, "working") % seed)
    steps = []

    cmd = ["python3", ENGINE, "--seed", seed, "--outdir", OUTDIR] + list(extra)
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        # COLT_USER: same requester attribution as the web path.
        # BRAND_THEME: White Label. The brand store lives on the SHARED colt_events volume for
        # exactly this reason — a partner who uploaded their template in the cabinet gets the same
        # branding from Telegram, and a run started here is indistinguishable from one started
        # there. Reading it directly rather than importing colt-web's app package: this container
        # does not have that package, and duplicating the path string would be a second home for it.
        env={**os.environ, "COLT_USER": _who, **_brand_env(_who)})

    lines = []
    async for raw in proc.stdout:
        line = raw.decode("utf-8", "ignore").rstrip()
        if not line:
            continue
        lines.append(line)
        print(line, flush=True)
        if line.startswith("{"): _evfile_json(line)   # -> events.log -> promtail -> Loki -> Grafana
        if line.startswith("PROGRESS:"):
            steps.append("- " + line[len("PROGRESS:"):].strip())
            try:
                await status.edit_text(("⏳ %s\n" % seed) + "\n".join(steps[-8:]))
            except Exception:
                pass
    await proc.wait()
    out = "\n".join(lines)

    if "ASSESSMENT COMPLETE" not in out:
        _log(evt="error", company=seed, msg="pipeline failed")
        await msg.reply_text(tl(ui, "failed") + "\n" + (out[-1500:] or "no output"))
        return

    summary = "\n".join(l for l in lines
                        if any(k in l for k in ("Company:", "Findings:", "Priced", "Threat actors", "QA:")))
    qwen = None
    for l in lines:
        if QWEN_EVT_A in l or QWEN_EVT_B in l:
            try:
                qwen = json.loads(l)
            except Exception:
                pass
    stat = ""
    if qwen:
        if qwen.get("status") == "ok":
            tok = qwen.get("tokens_in", 0) + qwen.get("tokens_out", 0)
            stat = "\n\U0001f9e0 AI enrichment: ON - %s - %s tokens - ~$%.4f (DO serverless)" % (
                qwen.get("model", ""), tok, qwen.get("cost_usd", 0))
        else:
            stat = "\n\U0001f9e0 AI enrichment: %s [%s] (templated text used - deck still valid)" % (
                qwen.get("status", "off"), (qwen.get("error", "") or "")[:120])
    await msg.reply_text(tl(ui, "done") + "\n" + summary + stat)

    decks = [l.split("OK", 1)[1].strip() for l in lines
             if l.strip().startswith("OK") and l.strip().endswith(".pptx")]
    for path in decks:
        if os.path.exists(path):
            with open(path, "rb") as fh:
                await msg.reply_document(fh, filename=os.path.basename(path))

SHIELD_DIR = os.environ.get("SHIELD_STATE_DIR", "/var/log/colt")


async def shield_decide(update, ctx):
    """The operator tapped an escalation on a shield alert.

    THE BOT OWNS THE CALLBACK because it already long-polls Telegram; a second getUpdates consumer
    in colt-web would steal messages from this one. It writes the answer to the shared colt_events
    volume (which both containers already mount read-write) and colt-web applies it on its next
    pass. No new port, no second Telegram consumer, no direct call between the two containers.

    IT ONLY RECORDS THE CHOICE. Nothing here blocks, unblocks or reports anything itself: the
    authorisation and the action stay in separate processes, so a bug in the bot cannot enforce.
    """
    q = update.callback_query
    try:
        await q.answer()
    except Exception:
        pass
    try:
        _, incident, action = (q.data or "").split(":", 2)
    except ValueError:
        return
    uid = q.from_user.id if q.from_user else 0
    if not AUTH.is_authed(uid, ALLOWED):
        # AUTHORISATION IS NOT OPTIONAL HERE. Anyone who learns a chat id could otherwise tap a
        # button and change the site's defensive posture.
        try:
            await q.edit_message_text((q.message.text or "") + "\n\n[X] Not authorised — /auth first.")
        except Exception:
            pass
        return
    email = AUTH.authed.get(str(uid), {}).get("email", "")
    try:
        path = os.path.join(SHIELD_DIR, "shield_decisions.json")
        cur = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                cur = json.load(fh)
        cur[incident] = {"action": action, "by": email, "ts": time.time()}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cur, fh, indent=2)
        os.replace(tmp, path)
        await q.edit_message_text((q.message.text or "")
                                  + "\n\n>> %s authorised by %s.\nRecorded. The platform "
                                    "confirms with the resulting state within ~20s. If NO "
                                    "confirmation arrives, colt-web is not running and nothing "
                                    "was applied." % (action, email))
    except Exception as e:
        _log(evt="shield_decide_error", err=repr(e)[:160])


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CallbackQueryHandler(shield_decide, pattern=r"^sh:"))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auth", auth))
    app.add_handler(CommandHandler("verify", verify))
    app.add_handler(CommandHandler("assess", assess))
    app.add_handler(CommandHandler("lang", lang_cmd))
    # the keyboard is built from doc_langs(), so the pattern must not hardcode the pair either;
    # on_lang() re-checks the code through doc_supported() before anything reaches the engine.
    app.add_handler(CallbackQueryHandler(on_lang, pattern=r"^lang:[a-z]{2}$"))
    print("assessment bot polling (zero-trust auth enabled)...", flush=True)
    app.run_polling()

if __name__ == "__main__":
    main()
