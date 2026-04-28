"""
QBO API Client — handles token refresh, pagination, and all entity queries.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Generator

import requests

TOKENS_FILE = os.path.join(os.path.dirname(__file__), "qbo_tokens.json")
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
BASE_URL = "https://quickbooks.api.intuit.com/v3/company/{realm_id}"
SANDBOX_URL = "https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}"


class QBOClient:
    def __init__(self, sandbox: bool = False):
        self.tokens = self._load_tokens()
        self.realm_id = self.tokens["realm_id"]
        base = SANDBOX_URL if sandbox else BASE_URL
        self.base_url = base.format(realm_id=self.realm_id)
        self._ensure_fresh_token()

    def _load_tokens(self) -> dict:
        if not os.path.exists(TOKENS_FILE):
            raise FileNotFoundError(
                f"Token file not found: {TOKENS_FILE}\n"
                "Run qbo_oauth.py first to authorize."
            )
        with open(TOKENS_FILE) as f:
            return json.load(f)

    def _save_tokens(self):
        with open(TOKENS_FILE, "w") as f:
            json.dump(self.tokens, f, indent=2)

    def _ensure_fresh_token(self):
        expires_at = datetime.fromisoformat(self.tokens["expires_at"])
        if datetime.utcnow() >= expires_at - timedelta(minutes=5):
            self._refresh_token()

    def _refresh_token(self):
        client_id = os.getenv("QBO_CLIENT_ID", "")
        client_secret = os.getenv("QBO_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise ValueError("QBO_CLIENT_ID and QBO_CLIENT_SECRET must be set in .env")

        resp = requests.post(
            TOKEN_URL,
            auth=(client_id, client_secret),
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.tokens["refresh_token"],
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

        self.tokens["access_token"] = data["access_token"]
        self.tokens["refresh_token"] = data["refresh_token"]
        self.tokens["expires_at"] = (
            datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))
        ).isoformat()
        self.tokens["refresh_expires_at"] = (
            datetime.utcnow() + timedelta(seconds=data.get("x_refresh_token_expires_in", 8726400))
        ).isoformat()
        self._save_tokens()
        print("  [token refreshed]")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.tokens['access_token']}",
            "Accept": "application/json",
        }

    def query(self, entity: str, where: str = "", max_results: int = 1000) -> list:
        """Fetch all records for an entity, handling pagination automatically."""
        results = []
        start = 1
        while True:
            sql = f"SELECT * FROM {entity}"
            if where:
                sql += f" WHERE {where}"
            sql += f" MAXRESULTS {max_results} STARTPOSITION {start}"

            self._ensure_fresh_token()
            resp = requests.get(
                f"{self.base_url}/query",
                params={"query": sql, "minorversion": 65},
                headers=self._headers(),
            )

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 60))
                print(f"  Rate limited — waiting {retry_after}s...")
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
            data = resp.json()

            query_response = data.get("QueryResponse", {})
            batch = query_response.get(entity, [])
            results.extend(batch)

            total_count = query_response.get("totalCount", len(batch))
            if len(batch) < max_results or len(results) >= total_count:
                break
            start += max_results

        return results

    def query_since(self, entity: str, since_iso: str) -> list:
        """Fetch records modified since a given ISO timestamp (for incremental sync)."""
        where = f"MetaData.LastUpdatedTime > '{since_iso}'"
        return self.query(entity, where=where)

    def get_company_info(self) -> dict:
        self._ensure_fresh_token()
        resp = requests.get(
            f"{self.base_url}/companyinfo/{self.realm_id}",
            params={"minorversion": 65},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json().get("CompanyInfo", {})
