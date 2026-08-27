#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hostpath — where does a path INSIDE a container live on the HOST? One implementation.

WHY THIS FILE EXISTS (2026-08-27)
    This question has now been answered wrongly twice, in two different agents, on the same
    docker volume, thirteen days apart:

      * dbbackup (2026-08-14) looked up the volume `colt_events` by name. Docker Compose PREFIXES
        volumes with the project name, so the real name is `colt-stack_colt_events`, nothing was
        found, and the very first production run backed up NOTHING and exited 0.
      * logship (2026-08-27) read `/var/log/colt/events.log` directly. That is the path inside
        colt-web; the agent runs on the HOST, where the file is under the volume's mountpoint. It
        printed "no events log yet - nothing to ship" on every run since it was installed, so the
        off-box security archive - the copy that exists precisely because an attacker who owns the
        box owns Loki - has never contained a single byte.

    dbbackup was fixed by asking the CONTAINER for its own mount table. That fix was correct and it
    was not carried across, because it lived inside dbbackup's agent instead of somewhere logship
    could reach. Two homes for one decision is the defect this repository has paid for more than
    any other (ENRICH_MODELS had four; the document language had six). So the resolution lives here
    now, once, and both agents import it.

IMPORT PATH, deliberately without a fallback copy
    Both installers place this file at /opt/cybergod/hostpath.py and the agents add that directory
    to sys.path. In a repo checkout the agents also add their own parent (deploy/), so the same
    import works on the operator's machine with no environment variable. A local fallback
    implementation would recreate the exact defect this file exists to remove, so there is none:
    if the import fails, the agent fails loudly.
"""
import os
import subprocess


def sh(cmd, timeout=120):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def container_running(name):
    rc, out, _ = sh("docker inspect -f '{{.State.Running}}' %s 2>/dev/null" % name)
    return rc == 0 and out.strip() == "true"


def mount_root(container, inside):
    """(destination, host source) of the mount that CONTAINS `inside`, or None.

    Returned even when the file itself does not exist yet, because a caller that wants to WRITE
    under the volume (a state file, a snapshot) needs the directory before the file is there.
    Longest matching destination wins, so a nested mount beats its parent.
    """
    rc, out, _ = sh("docker inspect -f '{{range .Mounts}}{{.Destination}}|{{.Source}}{{\"\\n\"}}"
                    "{{end}}' %s 2>/dev/null" % container)
    if rc != 0 or not out:
        return None
    best = None
    for line in out.splitlines():
        if "|" not in line:
            continue
        dest, src = line.split("|", 1)
        dest, src = dest.strip(), src.strip()
        # the mount is a DIRECTORY; the file sits under it
        if dest and src and (inside == dest or inside.startswith(dest.rstrip("/") + "/")):
            if best is None or len(dest) > len(best[0]):
                best = (dest, src)
    return best


def volume_path(container, inside, vol, must_exist=True):
    """Where does `inside` live on the HOST?

    Ask the CONTAINER for its own mount table first. That is prefix-agnostic, so Compose naming
    (`colt-stack_colt_events`) cannot break it - which is exactly what broke dbbackup's first run.
    Falls back to matching a volume whose name ENDS WITH the logical name, so it still works when
    the container is stopped.

    `must_exist=False` returns the computed path even when the file is not there yet. Use it for
    something you are about to CREATE; leave it True when you are looking for existing data, so a
    wrong answer cannot be mistaken for a right one.
    """
    best = mount_root(container, inside)
    if best:
        dest, src = best
        p = os.path.join(src, os.path.relpath(inside, dest))
        if os.path.exists(p) or not must_exist:
            return p

    # FALLBACK: the container may be stopped. Match the volume by SUFFIX, because Compose prefixes
    # every volume with the project name and the unprefixed name matches nothing.
    rc, out, _ = sh("docker volume ls --format '{{.Name}}'")
    if rc != 0:
        return None
    for v in [x for x in out.split() if x == vol or x.endswith("_" + vol)]:
        rc, mp, _ = sh("docker volume inspect -f '{{.Mountpoint}}' %s" % v)
        if rc == 0 and mp:
            p = os.path.join(mp, os.path.basename(inside))
            if os.path.exists(p) or not must_exist:
                return p
    return None
