"""Temporary QBO OAuth callback route — used once to capture production tokens."""

import json
import os
from datetime import datetime, timedelta

import requests
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
TOKENS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "qbo_tokens.json")


@router.get("/api/qbo/callback", response_class=HTMLResponse, include_in_schema=False)
def qbo_callback(code: str, realmId: str, state: str = ""):
    client_id = os.getenv("QBO_CLIENT_ID", "")
    client_secret = os.getenv("QBO_CLIENT_SECRET", "")
    redirect_uri = "https://accounting.precisionpros.com/api/qbo/callback"

    resp = requests.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={"Accept": "application/json"},
    )

    if resp.status_code != 200:
        return HTMLResponse(f"<h2>Token exchange failed: {resp.status_code}</h2><pre>{resp.text}</pre>")

    data = resp.json()
    tokens = {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "realm_id": realmId,
        "expires_at": (datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))).isoformat(),
        "refresh_expires_at": (datetime.utcnow() + timedelta(seconds=data.get("x_refresh_token_expires_in", 8726400))).isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }

    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

    return HTMLResponse(
        f"<h2>QBO Authorization Successful!</h2>"
        f"<p>Realm ID: <strong>{realmId}</strong></p>"
        f"<p>Tokens saved to server. You can close this tab.</p>"
        f"<p>Refresh token expires: {tokens['refresh_expires_at']}</p>"
    )
