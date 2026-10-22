# A package name on a RUN line is a version nobody wrote down — 2026-10-22

## What happened

Pipeline run #12 failed at the scan gate. Two of three images passed; one did not:

```
scan the artifacts (CRITICAL stops the promotion) (colttechbot)
certifi (METADATA)  GHSA-6q48-6c7w-9gw2  CRITICAL
  installed 2026.7.22   fixed 2026.10.19
  "certifi bundles emSign root CAs with compromised intermediate CA keys"
```

The gate was right and the finding was real. The interesting part is that colt-web, built from the
same commit in the same run, held **certifi 2026.10.19** and passed. Same repo, same minute,
opposite answers about a dependency neither image names.

## Why the two images disagreed

`assess-bot/Dockerfile` installed its dependencies by name:

```dockerfile
RUN pip3 install --no-cache-dir --break-system-packages shodan python-telegram-bot mmh3
RUN pip3 install --no-cache-dir --break-system-packages google-auth requests
```

and `pipeline.yml` builds that image with `cache-from: type=gha,scope=bot`.

A RUN line that never changes is a cache key that never changes. That layer had not re-resolved
since the day it was first built, and a cache hit does not consult PyPI — so the versions inside
it were frozen at whatever "latest" meant on that day. colt-web's equivalent layer sits behind
`COPY webapp/backend/requirements.txt`, which changes, so it re-resolves.

The same scan shows the second witness: `xlsxwriter` is **3.2.9** in colttechbot and **3.3.0** in
colt-web. One commit, one run, two dependency sets.

`webapp/backend/requirements.txt` already argues this case at length, for starlette and
python-multipart — *"a floor defeats the immutability guarantee... pip resolves independently in
each build"*. The engine's own packages were simply never held to it, and they were installed by
name in **four** Dockerfiles at once (defect class 32: one home).

## Why nothing caught it for six weeks

Every mechanism that exists to catch this was pointed somewhere with no effect:

| Mechanism | What it watched | Effect |
|---|---|---|
| Dependabot (`pip`) | `/` — the root `requirements.txt` | No Dockerfile installed that file. Every bump it could offer changed nothing that ships. |
| `pip-audit` in security.yml | the same root file | Audited a dependency set nothing shipped. |
| `scripts/gen_sbom.py` | named `hermes-skills/shodan-assessment/requirements.txt` | That file **did not exist**, so the engine's dependencies were absent from our own CRA SBOM. |

And the root file opened with the line `# Runtime deps ... Dockerfiles install these.` Nothing
installed them. A declared home that nothing reads is the same class as the jobhuntwow vhost whose
authoritative fragment CI could not see: the document is right, the path to it is not there.

## The repair

Not "bump certifi". Every image installs `-r` a committed, pinned manifest, and nothing installs a
bare name. A pin cannot be frozen by a cache, because changing the pin changes the COPY and the
layer with it.

- **`hermes-skills/shodan-assessment/requirements.txt`** (new) — the engine's runtime
  dependencies, exactly pinned: `shodan==1.31.0`, `mmh3==5.3.1`, `requests==2.34.2`,
  `google-auth==2.62.0`, `certifi==2026.10.19`. One home, for every image that carries the engine:
  webapp, webapp/backend, assess-bot, hermes-local, hermes-droplet, and `Dockerfile.ci` so the
  gate's interpreter holds the versions the images ship.
- **`assess-bot/requirements.txt`** (new) — `python-telegram-bot==22.8`.
- **`cassandra-bot/requirements.txt`** (new) — `python-telegram-bot==21.11` (the `<22` cap is
  deliberate and predates this; bumping it is a separate decision), `playwright==1.64.0`,
  `google-auth`, `requests`, `certifi`.
- **certifi is pinned by name in every manifest**, even though it is transitive via requests. A
  trust store whose entire purpose is to be current is the last thing that should be resolved by
  accident.
- Root `requirements.txt` **retired**. Dependabot, pip-audit and the SBOM now all name the four
  manifests the images really install.

Every pinned version was measured on 2026-10-22: each is what a clean resolve produces today,
which is what colt-web shipped and passed the scan with. Pinning changes no behaviour; it makes
the next build produce the same bytes as this one. Resolution was verified for each manifest and
for every combination an image installs (`webapp + engine`, `engine + bot`, cassandra), so the
pins do not conflict with `webapp/backend/requirements.txt`'s existing ranges.

## The guard

`tests/test_image_dependencies.py`, five properties, the last two **derived** so the list cannot
go stale the way the original one did:

1. No Dockerfile installs a python package by name. (`ruff` and `pytest` in `Dockerfile.ci` are
   the only exemption — not in any shipped artifact, no scanner reads them, and pinning a linter
   would let a new rule release block a ship. The allowlist is asserted to stay exactly those two.)
2. Every `-r` resolves to a file that Dockerfile COPIES in and that git will carry — gitignored
   manifests fail, because a file only the operator's machine can see is the jobhuntwow shape.
3. Every pip command's manifests, together, pin certifi exactly.
4. `.github/dependabot.yml`'s pip directories **equal** the directories of those manifests.
5. `gen_sbom.PY_MANIFESTS` **equals** those manifests.

Baseline run first (class 14), then six mutations, all caught:

| Mutation | Caught by |
|---|---|
| a bare `shodan` back on the assess-bot pip line | 1 |
| `certifi==2026.10.19` → `certifi` | 3 |
| a directory removed from dependabot.yml | 4 |
| a manifest removed from `PY_MANIFESTS` | 5 |
| `-r` pointed at a path nothing COPIES | 2 |
| a manifest COPIED from a gitignored path | 2 |

## What is still true after this

The cache is not the villain and was not disabled. The rule is narrower: a cached layer may hold
anything as long as a committed file says what it holds. Keeping those files current is
Dependabot's job, and this is the first change in which Dependabot is pointed at a file that
reaches an artifact.
