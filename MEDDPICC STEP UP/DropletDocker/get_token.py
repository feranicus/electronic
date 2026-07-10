#!/usr/bin/env python3
"""
One-time: turn credentials.json (OAuth client) into token.json (refresh token) for gmail.send.
Run this ONCE on a machine with a browser (your laptop is easiest), then copy token.json to the droplet.

  pip install google-auth-oauthlib
  python get_token.py            # opens a browser; sign in as feranicus@s4biz.io; grant "send email"
  -> writes token.json next to this script
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0)   # opens browser, one consent
open("token.json", "w").write(creds.to_json())
print("Wrote token.json — copy it to the droplet's secrets folder.")
