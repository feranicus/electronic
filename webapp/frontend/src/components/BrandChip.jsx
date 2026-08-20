import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getBrand } from "../api.js";
import { useT } from "../i18n";

// One line on Assess and Compliance saying which branding the artifacts will carry.
//
// WHY A COMPONENT AND NOT TWO COPIES: the same sentence pasted into two pages is the drift this
// codebase keeps paying for (creed.js, legal.jsx, de.json all exist for that reason). It is also
// the only place a partner finds out, BEFORE spending an assessment, that their White Label upload
// did not take — which is a far better moment than opening the finished deck.
//
// Fails SILENT, deliberately: a brand lookup that errors must not put an error banner on the page
// somebody came to run an assessment from. Worst case the chip does not appear.
export default function BrandChip() {
  const [, , t] = useT();
  const [b, setB] = useState(null);

  useEffect(() => {
    let live = true;
    getBrand()                                   // getJSON-backed: the parsed body
      .then((d) => { if (live) setB(d); })
      .catch(() => { /* not a reason to break the page */ });
    return () => { live = false; };
  }, []);

  if (!b) return null;
  const on = b.active && b.brand;
  return (
    <p className="brandchip">
      {on && b.brand.has_logo
        ? <img className="brandchip-logo" src="/api/brand/logo" alt="" />
        : null}
      <span>{on ? t("wl.chip").replace("{name}", b.brand.name || "") : t("wl.chipNone")}</span>
      <Link to="/app/brand">{t("wl.chipEdit")}</Link>
    </p>
  );
}
