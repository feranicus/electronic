// Native-app style bottom tab bar for the landing page on phones.
// Ported from the jev.best pattern: fixed grid docked to the bottom, height + padding driven by the
// safe-area inset (so it clears the iPhone home indicator), translucent blur, and a glowing 2px bar
// along the TOP edge of the active tab. Desktop never sees it (CSS: display:none above 720px).
const ICONS = {
  edge:   (<><path d="M13 2L4.5 13H11l-1 9 8.5-11H12z" /></>),
  demo:   (<><rect x="3" y="4" width="18" height="14" rx="2.5" /><path d="M10.5 8.5l4.5 2.6-4.5 2.6z" /><path d="M8 21h8" /></>),
  map:    (<><circle cx="5.5" cy="6" r="2.2" /><circle cx="18.5" cy="6" r="2.2" /><circle cx="12" cy="18" r="2.2" /><path d="M7.4 7.3L10.9 16M16.6 7.3L13.1 16M7.7 6h8.6" /></>),
  deep:   (<><path d="M12 3l9 4.5-9 4.5-9-4.5z" /><path d="M3 12l9 4.5 9-4.5" /><path d="M3 16.5L12 21l9-4.5" /></>),
  secure: (<><path d="M12 3l8 3.5v5c0 5-3.5 8.5-8 9.5-4.5-1-8-4.5-8-9.5v-5z" /><path d="M9 12l2 2 4-4" /></>),
  app:    (<><path d="M14 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5" /><path d="M10 17l5-5-5-5" /><path d="M15 12H3" /></>),
};

export default function TabBar({ tabs, active, onGo }) {
  return (
    <nav className="tabbar" aria-label="Sections">
      {tabs.map((t) => (
        <button key={t.id} type="button"
          className={active === t.id ? "tb on" : "tb"}
          aria-current={active === t.id ? "true" : undefined}
          onClick={() => onGo(t)}>
          <svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[t.id]}</svg>
          {t.label}
        </button>
      ))}
    </nav>
  );
}
