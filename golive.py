#!/usr/bin/env python3
"""DEPRECATED — superseded by CI (.github/workflows/web-deploy.yml) + ship_web.py.
Neutralised so it can never re-inject the old 127.0.0.1:8090 Caddy target or a GitHub-Pages CNAME.
Use: python ship_web.py   (single source of truth; see webapp/DEPLOY.md)."""
import sys
sys.exit("DEPRECATED: run `python ship_web.py` instead (CI single source of truth).")
