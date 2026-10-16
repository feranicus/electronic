#!/usr/bin/env python3
"""ghcr.py — the ONE HOME for "what is this image called, and why can't we pull it".

THE INCIDENT, 2026-10-16. The staging job died on:

    Image ghcr.io/feranicus/colt-web:c6d051e729cc Pulling
    failed to resolve reference "ghcr.io/feranicus/colt-web:c6d051e729cc": not found

and the gate reported `[!] staging build failed (exit 1)`. Four words, no subject. The cause was
not in the log at all, because the log printed the name it ASKED for and never the name CI had
PUSHED. Those were different:

    pipeline.yml      IMAGE_OWNER = ghcr.io/${{ github.repository }}
                      -> pushes  ghcr.io/feranicus/electronic/colt-web:<tag>
    docker-compose.web.yml
                      -> pulls   ghcr.io/feranicus/colt-web:<tag>

Only WEB_TAG was ever threaded from CI to the droplet. The REPOSITORY half was hardcoded in three
places that disagreed (compose, web-deploy.yml, deploy_web_direct.py). Defect class 32: a value
with several homes drifts, and the newer one always loses.

**AND "not found" DOES NOT MEAN NOT FOUND.** GHCR answers an unauthenticated request for a PRIVATE
package with 404, not 401 — deliberately, so a stranger cannot enumerate private packages. So the
one error message covers two unrelated faults with two unrelated repairs:

    the tag genuinely is not in the registry      -> the build did not push what the deploy wants
    the tag is there and we are not allowed in    -> the package is private / we never logged in

Docker cannot tell them apart and neither could we, which is how one wrong name survived a full
pipeline run. `report()` below asks the registry BOTH ways — anonymously and with a token — and
the difference between those two answers is the diagnosis. Nothing here guesses: every line is an
HTTP status this function received, and where it received nothing it says so and concludes nothing
(defect class 1).

No credential is ever printed. The repo is public and so are its CI logs.
"""
import json
import os
import urllib.error
import urllib.request

# ONE HOME. Every other spelling of the image name must DERIVE from these, and
# tests/test_image_ref.py fails the build if any file hardcodes a different one.
REGISTRY = "ghcr.io"
NAMESPACE = os.environ.get("IMAGE_OWNER", "ghcr.io/feranicus").strip().rstrip("/")
WEB_IMAGE = "colt-web"
TIMEOUT = 20


def ref(image=WEB_IMAGE, tag="latest", namespace=None):
    """The full image reference, assembled in exactly one place."""
    ns = (namespace or NAMESPACE).strip().rstrip("/")
    if not ns.startswith(REGISTRY):
        ns = "%s/%s" % (REGISTRY, ns.lstrip("/"))
    return "%s/%s:%s" % (ns, image, tag)


def split(reference):
    """`ghcr.io/feranicus/electronic/colt-web:abc` -> ('feranicus/electronic/colt-web', 'abc').

    The REPOSITORY is everything after the registry host and before the tag. GHCR allows any
    depth, which is the whole reason this bug was possible: `feranicus/colt-web` and
    `feranicus/electronic/colt-web` are two different packages that read almost identically.
    """
    s = reference.strip()
    if s.startswith(REGISTRY + "/"):
        s = s[len(REGISTRY) + 1:]
    if ":" in s.rsplit("/", 1)[-1]:
        repo, tag = s.rsplit(":", 1)
    else:
        repo, tag = s, "latest"
    return repo, tag


def _get(url, headers, fetch=None):
    """Return (status, body). A transport failure is a status of 0 and is never read as a 404."""
    if fetch is not None:
        return fetch(url, headers)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.getcode(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode("utf-8", "replace") if e.fp else "")
    except Exception:                                    # noqa: BLE001 - reported by the caller
        return 0, ""


def _bearer(repo, token, fetch=None):
    """GHCR hands out a short-lived pull token. Anonymous works only for a PUBLIC package, which
    is precisely the distinction this module exists to measure."""
    url = "https://%s/token?scope=repository:%s:pull&service=%s" % (REGISTRY, repo, REGISTRY)
    headers = {}
    if token:
        import base64
        headers["Authorization"] = "Basic " + base64.b64encode(
            ("x:" + token).encode()).decode()
    st, body = _get(url, headers, fetch)
    if st != 200:
        return None
    try:
        return json.loads(body).get("token")
    except Exception:                                    # noqa: BLE001
        return None


def manifest(repo, tag, token=None, fetch=None):
    """The HTTP status GHCR gives for this exact tag. 200 = pullable, 404 = absent OR forbidden."""
    bearer = _bearer(repo, token, fetch)
    headers = {"Accept": "application/vnd.oci.image.index.v1+json,"
                         "application/vnd.docker.distribution.manifest.list.v2+json,"
                         "application/vnd.docker.distribution.manifest.v2+json"}
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    st, _ = _get("https://%s/v2/%s/manifests/%s" % (REGISTRY, repo, tag), headers, fetch)
    return st


def tags(repo, token=None, fetch=None, limit=100):
    """Which tags DO exist. An empty list is not proof of an empty package - it is also what a
    refused listing looks like - so the caller must report the manifest status beside it."""
    bearer = _bearer(repo, token, fetch)
    headers = {}
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    st, body = _get("https://%s/v2/%s/tags/list?n=%d" % (REGISTRY, repo, limit), headers, fetch)
    if st != 200:
        return []
    try:
        return list(json.loads(body).get("tags") or [])
    except Exception:                                    # noqa: BLE001
        return []


def report(reference, token=None, fetch=None):
    """The diagnosis: WHY this reference could not be pulled, measured, as a list of lines.

    The method is the point. `anon` and `auth` are the same question asked with and without a
    credential, and their DIFFERENCE is the answer docker's single "not found" throws away:

        anon 404, auth 200  -> the package is PRIVATE. The puller must log in.
        anon 404, auth 404  -> the tag really is not there. Look at what the build pushed.
        anon 200            -> public and present; the failure is not the registry at all.
    """
    repo, tag = split(reference)
    out = ["  GHCR could not serve %s. What was measured, just now:" % reference,
           "    repository    %s" % repo,
           "    tag           %s" % tag]

    anon = manifest(repo, tag, token=None, fetch=fetch)
    out.append("    anonymous     HTTP %s%s" % (anon or "no answer",
                                                "" if anon else " (transport failure)"))
    auth = None
    if token:
        auth = manifest(repo, tag, token=token, fetch=fetch)
        out.append("    with token    HTTP %s%s" % (auth or "no answer",
                                                    "" if auth else " (transport failure)"))
    else:
        out.append("    with token    NOT TESTED - no token was given to this check, so "
                   "'private' and 'absent' cannot be told apart here")

    present = tags(repo, token=token, fetch=fetch)
    if present:
        out.append("    tags present  %s%s" % (", ".join(present[:12]),
                                               " ... (%d total)" % len(present)
                                               if len(present) > 12 else ""))
        if tag not in present:
            out.append("    => the repository EXISTS and this tag is NOT in it. The build pushed "
                       "under a different name or a different tag than the deploy asked for - "
                       "compare IMAGE_OWNER in the build job against WEB_IMAGE in the pull.")
    else:
        out.append("    tags present  the tag list could not be read (private, absent, or the "
                   "credential cannot list) - nothing concluded from this line alone")

    if anon == 200 or auth == 200:
        out.append("    => the image IS pullable with the credentials tested here, so the failure "
                   "is on the PULLING host: it is not logged in to %s." % REGISTRY)
    elif token and anon in (401, 403, 404) and auth in (401, 403, 404):
        out.append("    => neither anonymous nor authenticated access can see this tag. The most "
                   "likely cause is that it was never pushed under this name.")
    elif token and anon != 200 and auth == 200:
        out.append("    => the package is PRIVATE. Either `docker login ghcr.io` on the pulling "
                   "host, or make the package public (a one-time console job).")
    elif not anon:
        out.append("    => the registry could not be reached at all. Nothing is concluded about "
                   "the image.")
    return "\n".join(out)
