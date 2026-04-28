#!/usr/bin/env python3
"""
QBO OAuth 2.0 Authorization Helper
Run this once to authorize access to your QBO company and save tokens.

Usage:
    python3 qbo_oauth.py

Reads QBO_CLIENT_ID and QBO_CLIENT_SECRET from backend/.env
Saves tokens to backend/qbo_tokens.json
"""

import json
import os
import secrets
import sys
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("QBO_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("QBO_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8080/callback"
TOKENS_FILE = os.path.join(os.path.dirname(__file__), "qbo_tokens.json")

AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
SCOPE = "com.intuit.quickbooks.accounting"

_auth_code = None
_realm_id = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code, _realm_id
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            params = parse_qs(parsed.query)
            _auth_code = params.get("code", [None])[0]
            _realm_id = params.get("realmId", [None])[0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Authorization successful! You can close this tab.</h2>")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress access logs


def exchange_code_for_tokens(code, realm_id):
    resp = requests.post(
        TOKEN_URL,
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()

    tokens = {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "realm_id": realm_id,
        "expires_at": (
            datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))
        ).isoformat(),
        "refresh_expires_at": (
            datetime.utcnow() + timedelta(seconds=data.get("x_refresh_token_expires_in", 8726400))
        ).isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }
    return tokens


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: QBO_CLIENT_ID and QBO_CLIENT_SECRET must be set in backend/.env")
        sys.exit(1)

    state = secrets.token_hex(16)
    auth_params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": SCOPE,
        "redirect_uri": REDIRECT_URI,
        "state": state,
    }
    auth_link = f"{AUTH_URL}?{urlencode(auth_params)}"

    print("Opening browser for QBO authorization...")
    print(f"\nIf the browser doesn't open, go to:\n{auth_link}\n")
    webbrowser.open(auth_link)

    print("Waiting for authorization callback on http://localhost:8080/callback ...")
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.handle_request()

    if not _auth_code or not _realm_id:
        print("ERROR: Did not receive authorization code or realm ID.")
        sys.exit(1)

    print(f"Received auth code. Company Realm ID: {_realm_id}")
    print("Exchanging code for tokens...")

    tokens = exchange_code_for_tokens(_auth_code, _realm_id)
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

    print(f"\nTokens saved to: {TOKENS_FILE}")
    print(f"Access token expires: {tokens['expires_at']}")
    print(f"Refresh token expires: {tokens['refresh_expires_at']}")
    print("\nSetup complete. You can now run qbo_import.py")


if __name__ == "__main__":
    main()
