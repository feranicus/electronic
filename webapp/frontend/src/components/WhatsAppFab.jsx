import { OPERATOR } from "../legal";

/* Floating WhatsApp button.
 *
 * WHY A FAB AND NOT A TAB: the phone tab bar already carries six items (Why / Live / Machine /
 * Deep / Secure / Open). A seventh makes every target too small to hit reliably, and contact is
 * not a place in the page — it is an action. So it floats above the bar, always reachable, on
 * every screen. Before this there was NO way to contact anyone from the installed PWA at all.
 *
 * `bottom` clears the fixed tab bar plus the iPhone home indicator via env(safe-area-inset-bottom).
 */
const TEXT = "Hi — I sell cyber security and I would like access to cybergod.ai.";

export default function WhatsAppFab() {
  const href = `${OPERATOR.whatsapp}?text=${encodeURIComponent(TEXT)}`;
  return (
    <a className="wa-fab" href={href} target="_blank" rel="noreferrer"
       aria-label="Message us on WhatsApp">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M20.5 11.6a8.5 8.5 0 0 1-12.4 7.5L3.5 20.5l1.5-4.4a8.5 8.5 0 1 1 15.5-4.5z" />
        <path d="M8.8 8.2c.3-.1.6 0 .8.3l.8 1.3c.1.2.1.5 0 .7l-.5.7c.6 1.1 1.5 2 2.6 2.6l.7-.5c.2-.1.5-.2.7 0l1.3.8c.3.2.4.5.3.8-.3.9-1.2 1.5-2.1 1.3-2.9-.5-5.3-2.9-5.9-5.9-.2-.9.4-1.8 1.3-2.1z" />
      </svg>
      <span>WhatsApp</span>
    </a>
  );
}
