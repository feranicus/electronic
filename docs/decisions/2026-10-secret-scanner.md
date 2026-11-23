# The secret scanner had been red for two months — 16 October 2026

Moved verbatim out of CLAUDE.md on 23 Nov 2026 because that file re-enters the model's context on
every turn and had reached its size budget. Nothing here was changed; the RULE it earned stays in
CLAUDE.md and this is the evidence behind it, read on demand.

**THE SECRET SCANNER HAD BEEN RED FOR TWO MONTHS AND NOBODY SAW IT.** The first run that actually
blocked a merge (PR #19) reported 5 gitleaks findings; the oldest has been in the tree since
2026-08-22. The bypass made a failing scanner invisible — "an alert nobody gets is not an alert",
proven on this repo. All 5 are code ABOUT secrets (the delimiters `ci_key.py` matches on, synthetic key fixtures, the
token list the LLM guard must redact), so they are PATH-allowlisted in `.gitleaks.toml` — never
obfuscated, because hiding from the scanner teaches the next person to do it too. **An allowlist
is a new hole, so it ships with its own guard**: `tests/test_secret_scan.py` hands every PEM block
in each allowlisted file to `ssh-keygen -y` — OpenSSH decides, not a regex — and fails if one
PARSES, if a token is undocumented, if an entry is stale, or if the list grows. Two of my versions
could not fail: a greedy `.*?` returned ONE 25 KB "block" (class 13), and re-wrapping every body
in OPENSSH armour made a real RSA PEM unparseable for the WRONG reason. Keep the armour label;
handle the one-line escaped form a service-account JSON uses. **AND THE GUARD ITSELF STAYS UNDER THE SCANNER** — twice gitleaks
flagged it (the synthetic PAT written literally; a BEGIN/END pair in a COMMENT, since the rule
spans everything between). Allowlisting the guard was the tempting fix and the wrong one: who
guards the guard. Pin the token as `SYNTHETIC_SHA256`, describe armour in prose, and
`test_this_file_is_not_itself_a_finding` asserts it against gitleaks' OWN regexes so it fails
locally, not in CI. All four mutations caught. **BUT IT READ ONE FILE — ITS OWN**, so when I wrote
an armour pair into test_gate_diagnostics.py the laptop saw nothing (`ship.py --test` runs no
gitleaks) and run #8 died at the gate, skipping build/scan/staging/production behind it. A rule
enforced on one file is an exception. The sweep now covers every TRACKED file, allowlist derived
from the config, no binary needed — proved by re-introducing the verbatim run-#8 armour.
[2026-10-16]
