"""shield_tuning.py — the ONLY thing the model panel is allowed to change, and only within bounds.

The operator's decision (10 Aug 2026) was that the panel may auto-tune thresholds "within committed
bounds". That is a real side effect for a model, so the design is deliberately narrow:

  · the panel may propose values for the SIX numeric keys in shield.BOUNDS. Nothing else. It cannot
    add a key, disable the shield, change the blast cap, or touch the allowlist.
  · the bounds themselves live in shield.py, in git, and are enforced by shield.cfg() on every READ.
    A corrupt, hand-edited or hostile tuning file therefore cannot push the shield out of range --
    the worst it can do is choose a different point inside a range the operator already accepted.
  · a change of more than MAX_STEP_PCT in one cycle is clamped. Adaptation should be gradual;
    a model that has misread one incident must not be able to swing the whole policy in one step.
  · every write is logged as an event with the before, the after and the reason, so Grafana shows
    exactly when a threshold moved and why.

This file holds NO model logic. It is storage with a contract.
"""
import json
import os
import time

PATH = os.environ.get("SHIELD_TUNING", "/var/log/colt/shield_tuning.json")
MAX_STEP_PCT = 25          # no single cycle may move a value by more than a quarter

_cache = {"mtime": 0.0, "data": {}}


def _load():
    try:
        st = os.stat(PATH)
        if st.st_mtime != _cache["mtime"]:
            with open(PATH, encoding="utf-8") as fh:
                d = json.load(fh)
            _cache["data"] = d.get("values", {}) if isinstance(d, dict) else {}
            _cache["mtime"] = st.st_mtime
    except Exception:
        # No file, unreadable file, or malformed JSON -> the committed defaults apply. A tuning
        # store that cannot be read must never take the shield down with it.
        _cache["data"] = _cache["data"] or {}
    return _cache["data"]


def get(key, default):
    v = _load().get(key, default)
    return v if isinstance(v, int) else default


def all_values():
    return dict(_load())


def propose(new_values, reason, agreed_by):
    """Apply a panel proposal. Returns (applied_dict, rejected_list). Never raises.

    Refuses anything outside shield.BOUNDS, anything that is not one of the six known keys, and
    any step larger than MAX_STEP_PCT of the current value.
    """
    from . import shield
    applied, rejected = {}, []
    cur = {k: shield.cfg(k) for k in shield.BOUNDS}
    for k, v in (new_values or {}).items():
        if k not in shield.BOUNDS:
            rejected.append("%s: not a tunable key" % k)
            continue
        try:
            v = int(v)
        except Exception:
            rejected.append("%s: not an integer (%r)" % (k, v))
            continue
        lo, hi = shield.BOUNDS[k]
        if not (lo <= v <= hi):
            rejected.append("%s=%d outside the committed bounds %d..%d" % (k, v, lo, hi))
            continue
        step = abs(v - cur[k]) * 100.0 / max(1, cur[k])
        if step > MAX_STEP_PCT:
            rejected.append("%s=%d is a %.0f%% step from %d (max %d%%)"
                            % (k, v, step, cur[k], MAX_STEP_PCT))
            continue
        applied[k] = v

    if applied:
        merged = dict(_load())
        merged.update(applied)
        try:
            os.makedirs(os.path.dirname(PATH), exist_ok=True)
            tmp = PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"values": merged, "reason": str(reason)[:500],
                           "agreed_by": list(agreed_by or []),
                           "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, fh, indent=2)
            os.replace(tmp, PATH)
            _cache["mtime"] = 0.0
        except Exception as e:
            return {}, rejected + ["could not persist: %s" % e]
        try:
            from . import notify
            notify._log(evt="shield_tuned", changed=applied, before={k: cur[k] for k in applied},
                        reason=str(reason)[:300], agreed_by=list(agreed_by or []))
        except Exception:
            pass
    return applied, rejected


def reset():
    """Back to the committed defaults."""
    try:
        os.remove(PATH)
    except Exception:
        pass
    _cache["data"], _cache["mtime"] = {}, 0.0
