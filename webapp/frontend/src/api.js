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

// ---- Auth ----
export const authBegin  = (email, password) => postJSON("/api/auth/begin",  { email, password });
export const authVerify = (email, code)     => postJSON("/api/auth/verify", { email, code });
export const authLogout = ()                => postJSON("/api/auth/logout", {});
export const getMe      = ()                => getJSON("/api/me");

// ---- Assessment ----
export const startAssess = (company, lang = "en") => postJSON("/api/assess", { company, lang });
export const assessEventsUrl = (jobId) => `/api/assess/${encodeURIComponent(jobId)}/events`;
// records that the Art.13 notice was shown+accepted (accountability, Art. 5(2))
export const assessStatus = (jobId) => getJSON(`/api/assess/${encodeURIComponent(jobId)}/status`);
export const ackPrivacy = () => postJSON("/api/privacy/ack", {});

// ---- Assistant ----
export const assist = (message) => postJSON("/api/assist", { message });

// ---- History ----
export const getHistory = () => getJSON("/api/history");
