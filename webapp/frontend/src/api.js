// All requests carry the session cookie.
const opts = (method, body) => ({
  method,
  credentials: "include",
  headers: { "Content-Type": "application/json" },
  ...(body ? { body: JSON.stringify(body) } : {}),
});

export async function getJSON(path) {
  const r = await fetch(path, { credentials: "include" });
  if (r.status === 401) { const e = new Error("unauthorized"); e.status = 401; throw e; }
  return r.json();
}
export async function postJSON(path, body) {
  const r = await fetch(path, opts("POST", body));
  let data = {};
  try { data = await r.json(); } catch { /* empty body ok */ }
  return { ok: r.ok, status: r.status, data };
}
// DELIBERATELY THE SAME SHAPE AS postJSON: { ok, status, data }. A third return contract is a third
// thing to remember, and api_contract.mjs exists because this file already had two. The gate is
// taught to treat delJSON as postJSON-backed, so its callers are checked the same way.
export async function delJSON(path) {
  const r = await fetch(path, opts("DELETE"));
  let data = {};
  try { data = await r.json(); } catch { /* empty body ok */ }
  return { ok: r.ok, status: r.status, data };
}

// ---- Auth ----
export const authBegin  = (email, password) => postJSON("/api/auth/begin",  { email, password });
export const authVerify = (email, code)     => postJSON("/api/auth/verify", { email, code });
export const authLogout = ()                => postJSON("/api/auth/logout", {});
// getJSON-backed: returns the PARSED BODY { email, is_admin, must_change }, not { ok, data }.
export const getMe      = ()                => getJSON("/api/me");
export const changePassword = (currentPassword, newPassword) =>
  postJSON("/api/auth/change-password", { current_password: currentPassword, new_password: newPassword });

// ---- Administration (server-side gated on colt_auth.ADMIN_EMAILS; the nav item is cosmetic) ----
// getJSON-backed: the parsed body { users, store_ok, min_password_len, shared_password_active }.
export const adminUsers = () => getJSON("/api/admin/users");
// postJSON-backed: { ok, status, data }. data.password is the plaintext, returned ONCE.
export const adminSetUser = (email, password, mustChange = true, note = "") =>
  postJSON("/api/admin/users", { email, password, must_change: mustChange, note });
export const adminDisable = (email, disabled = true) =>
  postJSON(`/api/admin/users/${encodeURIComponent(email)}/disable?disabled=${disabled ? "true" : "false"}`, {});
export const adminDeleteUser = (email) => delJSON(`/api/admin/users/${encodeURIComponent(email)}`);

// ---- Assessment ----
export const startAssess = (company, lang = "en", zoneSurvey = false) =>
  postJSON("/api/assess", { company, lang, zone_survey: zoneSurvey });
export const assessEventsUrl = (jobId) => `/api/assess/${encodeURIComponent(jobId)}/events`;
// records that the Art.13 notice was shown+accepted (accountability, Art. 5(2))
export const assessStatus = (jobId) => getJSON(`/api/assess/${encodeURIComponent(jobId)}/status`);
export const ackPrivacy = () => postJSON("/api/privacy/ack", {});
// post-run clarification loop (jobhuntwow gap->answer model)
export const assessClarify = (jobId) => getJSON(`/api/assess/${encodeURIComponent(jobId)}/clarify`);
export const assessRefine = (jobId, answers, lang = "en") =>
  postJSON(`/api/assess/${encodeURIComponent(jobId)}/refine`, { answers, lang });

// ---- Compliance (regime set follows the JURISDICTION) ----
// Shares the assess streaming/status/clarify/deck endpoints (engine-agnostic); only start + refine
// are compliance-specific. `jurisdiction` MUST be carried on the refine call too, or the child run
// re-grades against the wrong regime set the moment the operator answers a question.
export const startCompliance = (company, lang = "en", jurisdiction = "") =>
  postJSON("/api/compliance", { company, lang, jurisdiction });
export const complianceRefine = (jobId, answers, lang = "en", jurisdiction = "") =>
  postJSON(`/api/compliance/${encodeURIComponent(jobId)}/refine`, { answers, lang, jurisdiction });

// ---- Assistant ----
export const assist = (message) => postJSON("/api/assist", { message });

// ---- History ----
export const getHistory = () => getJSON("/api/history");

// Which languages the UI ships in vs which the DECK ENGINE can actually render. See the /api/langs
// docstring: these are different sets, and defaulting the document language from the SITE language
// was silently sending `--lang it` to an engine that only has an English and a German dictionary.
export const getLangs = () => getJSON("/api/langs");
// getJSON-backed: returns the PARSED BODY, not {ok,data}. (api_contract.mjs enforces this — the
// docLangs hook once destructured {ok,data} from a getJSON call and the language list silently
// collapsed to English-only.)
export const getJurisdictions = () => getJSON("/api/jurisdictions");
