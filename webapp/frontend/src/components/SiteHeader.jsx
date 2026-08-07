import { Link, useLocation } from "react-router-dom";
import { LangToggle } from "../legal";
import { useT } from "../i18n";

/* SiteHeader — the one navigation bar, on every public page.
 *
 * WHY IT EXISTS: only the landing page had a header. /demo, /contact, /privacy and /impressum were
 * dead ends — the only way out was the browser back button, which on an installed PWA is not even
 * on screen. A visitor who arrived on /demo from LinkedIn had no route to anything else.
 *
 * The section anchors (#edge, #demo, ...) only exist on the landing page, so on every OTHER page
 * they are rendered as links back to "/#edge" rather than in-page jumps that would do nothing.
 *
 * The language toggle lives here, which is what makes the switch site-wide: it writes the same
 * localStorage key the legal pages read, so the whole site and the privacy text move together.
 */
export default function SiteHeader({ onLanding = false }) {
  const [lang, setLang, t] = useT();
  const { pathname } = useLocation();
  const p = (hash) => (onLanding ? hash : "/" + hash);

  return (
    <header id="hd"><div className="wrap">
      <Link className="brand" to="/" aria-label={t("nav.home")}>
        <span className="chev">&#10095;</span> cybergod.ai
      </Link>
      <nav>
        <a href={p("#edge")}>{t("nav.why")}</a>
        <a href={p("#map")}>{t("nav.machine")}</a>
        <a href={p("#secure")}>{t("nav.secure")}</a>
        <Link to="/experience">{t("nav.about")}</Link>
        <Link to="/contact">{t("nav.contact")}</Link>
        {/* Demo must be a .btn: the phone rule `#hd nav a:not(.btn){display:none}` hides plain
            links, and this is the one entry point an anonymous visitor can actually use. */}
        {pathname !== "/demo" && <Link className="btn sm ghost" to="/demo">{t("nav.demo")}</Link>}
        <LangToggle lang={lang} setLang={setLang} />
        <Link className="btn sm" to="/login">{t("nav.open")}</Link>
      </nav>
    </div></header>
  );
}
