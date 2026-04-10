#!/usr/bin/env python3
"""
zoho_setup.py — One-time Zoho OAuth setup for AiMedic Scrapper_Salud
=====================================================================

Run this ONCE after you get your Self Client authorization code from:
https://api-console.zoho.com/ → Self Client → Generate Code

Usage:
    python zoho_setup.py

It will:
1. Ask for your Client ID, Client Secret, and authorization code
2. Exchange the code for access_token + refresh_token
3. Fetch your Zoho Mail account ID automatically
4. Write all values to .env (appending/updating the ZOHO_* fields)
"""

import os
import sys
import httpx
import re
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"
ZOHO_TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"
ZOHO_MAIL_API = "https://mail.zoho.com/api"


def update_env_value(env_path: Path, key: str, value: str):
    """Update or append a key=value in the .env file."""
    content = env_path.read_text() if env_path.exists() else ""
    pattern = rf"^{re.escape(key)}=.*$"
    new_line = f"{key}={value}"

    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        content = content.rstrip("\n") + f"\n{new_line}\n"

    env_path.write_text(content)


def exchange_code_for_tokens(client_id: str, client_secret: str, code: str) -> dict:
    """Exchange a Self Client authorization code for access + refresh tokens."""
    print("\n[1/3] Exchanging authorization code for tokens...")
    resp = httpx.post(
        ZOHO_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        print(f"\nERROR: Zoho returned an error: {data}")
        print("\nCommon causes:")
        print("  - Code expired (Self Client codes expire in the time you set, usually 10 min)")
        print("  - Wrong Client ID or Client Secret")
        print("  - Code already used (each code is single-use)")
        sys.exit(1)

    return data


def get_mail_account_id(access_token: str) -> str:
    """Fetch the Zoho Mail account ID from the API."""
    print("[2/3] Fetching Zoho Mail account ID...")
    resp = httpx.get(
        f"{ZOHO_MAIL_API}/accounts",
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
        timeout=30,
    )
    resp.raise_for_status()
    accounts = resp.json().get("data", [])

    if not accounts:
        print("WARNING: No Zoho Mail accounts found. You may need to add ZohoMail scopes.")
        return ""

    # Use the first account (primary)
    account = accounts[0]
    account_id = account.get("accountId", "")
    email = account.get("emailAddress", "")
    print(f"  Found account: {email} (ID: {account_id})")
    return account_id


def main():
    print("=" * 60)
    print("  AiMedic — Zoho OAuth Setup")
    print("=" * 60)
    print()
    print("Before running this, you need to:")
    print("1. Go to https://api-console.zoho.com/")
    print("2. Open your Self Client app")
    print("3. Click 'Generate Code' with these scopes:")
    print("   ZohoCRM.modules.ALL,ZohoMail.accounts.READ,ZohoMail.messages.CREATE,ZohoMail.send.CREATE")
    print("4. Set duration to 10 minutes, generate, and copy the code")
    print()
    print("Note: Work fast — codes expire quickly!")
    print()

    client_id = input("Zoho Client ID: ").strip()
    client_secret = input("Zoho Client Secret: ").strip()
    code = input("Authorization Code (from Self Client): ").strip()
    from_email = input("From email address (e.g. camilo.daza@aimedic.com.co): ").strip()

    if not all([client_id, client_secret, code, from_email]):
        print("ERROR: All fields are required.")
        sys.exit(1)

    # Exchange code for tokens
    tokens = exchange_code_for_tokens(client_id, client_secret, code)
    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")

    if not refresh_token:
        print(f"ERROR: No refresh_token in response: {tokens}")
        print("Make sure the Self Client has 'offline_access' scope or equivalent.")
        sys.exit(1)

    print(f"  access_token: {access_token[:20]}... (expires in {tokens.get('expires_in', '?')}s)")
    print(f"  refresh_token: {refresh_token[:20]}...")

    # Get Mail account ID
    account_id = ""
    if access_token:
        try:
            account_id = get_mail_account_id(access_token)
        except Exception as e:
            print(f"  WARNING: Could not fetch account ID automatically: {e}")
            account_id = input("  Enter your Zoho Mail Account ID manually (or press Enter to skip): ").strip()

    # Write to .env
    print(f"[3/3] Writing to {ENV_FILE}...")
    update_env_value(ENV_FILE, "ZOHO_CLIENT_ID", client_id)
    update_env_value(ENV_FILE, "ZOHO_CLIENT_SECRET", client_secret)
    update_env_value(ENV_FILE, "ZOHO_REFRESH_TOKEN", refresh_token)
    update_env_value(ENV_FILE, "ZOHO_ACCOUNT_ID", account_id)
    update_env_value(ENV_FILE, "ZOHO_FROM_EMAIL", from_email)
    update_env_value(ENV_FILE, "ZOHO_DOMAIN", "zoho.com")

    print()
    print("=" * 60)
    print("  Setup complete!")
    print("=" * 60)
    print()
    print("Next step — validate the connection:")
    print("  python zoho_test.py")
    print()


if __name__ == "__main__":
    main()
