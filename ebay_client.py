"""Minimal client for eBay's Browse API using the OAuth2 client credentials flow.

Requires an eBay developer account (developer.ebay.com) with a production
App ID (client ID) and Client Secret, passed via the EBAY_CLIENT_ID and
EBAY_CLIENT_SECRET environment variables.
"""

import base64
import os
import time

import requests

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
BROWSE_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
SCOPE = "https://api.ebay.com/oauth/api_scope"


class EbayClient:
    def __init__(self, client_id=None, client_secret=None, marketplace_id="EBAY_IT"):
        self.client_id = client_id or os.environ["EBAY_CLIENT_ID"]
        self.client_secret = client_secret or os.environ["EBAY_CLIENT_SECRET"]
        self.marketplace_id = marketplace_id
        self._token = None
        self._token_expiry = 0

    def _get_token(self):
        if self._token and time.time() < self._token_expiry:
            return self._token

        credentials = f"{self.client_id}:{self.client_secret}"
        basic_auth = base64.b64encode(credentials.encode()).decode()

        response = requests.post(
            TOKEN_URL,
            headers={
                "Authorization": f"Basic {basic_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": SCOPE},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()

        self._token = payload["access_token"]
        self._token_expiry = time.time() + payload["expires_in"] - 60
        return self._token

    def search(self, query, limit=10, **filters):
        params = {"q": query, "limit": limit, **filters}
        response = requests.get(
            BROWSE_SEARCH_URL,
            headers={
                "Authorization": f"Bearer {self._get_token()}",
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
            },
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("itemSummaries", [])
