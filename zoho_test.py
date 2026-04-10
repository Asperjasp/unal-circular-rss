#!/usr/bin/env python3
"""
zoho_test.py — Validate Zoho connection and send a test email
=============================================================

Usage:
    python zoho_test.py              # Just validate credentials
    python zoho_test.py --send-test  # Also send a test email to yourself
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def check_env():
    required = [
        "ZOHO_CLIENT_ID",
        "ZOHO_CLIENT_SECRET",
        "ZOHO_REFRESH_TOKEN",
        "ZOHO_ACCOUNT_ID",
        "ZOHO_FROM_EMAIL",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}")
        print("Run: python zoho_setup.py")
        sys.exit(1)
    print("  .env check: all Zoho vars present")


async def run_tests(send_test: bool = False):
    from health_scraper.integrations.zoho_email_service import ZohoEmailService

    svc = ZohoEmailService(
        client_id=os.getenv("ZOHO_CLIENT_ID"),
        client_secret=os.getenv("ZOHO_CLIENT_SECRET"),
        refresh_token=os.getenv("ZOHO_REFRESH_TOKEN"),
        account_id=os.getenv("ZOHO_ACCOUNT_ID"),
        from_email=os.getenv("ZOHO_FROM_EMAIL"),
        zoho_domain=os.getenv("ZOHO_DOMAIN", "zoho.com"),
    )

    print("\n[1] Testing token refresh...")
    try:
        token = await svc._get_access_token()
        print(f"  OK — token: {token[:20]}...")
    except Exception as e:
        print(f"  FAILED: {e}")
        return

    print("\n[2] Fetching account info...")
    try:
        info = await svc.get_account_info()
        print(f"  OK — account: {info}")
    except Exception as e:
        print(f"  FAILED: {e}")

    print("\n[3] Fetching email folders...")
    try:
        folders = await svc.get_folders()
        print(f"  OK — {len(folders)} folders found: {[f.get('folderName') for f in folders[:5]]}")
    except Exception as e:
        print(f"  FAILED: {e}")

    if send_test:
        to_email = os.getenv("ZOHO_FROM_EMAIL")
        print(f"\n[4] Sending test email to {to_email}...")
        try:
            result = await svc.send_templated_email(
                to_email=to_email,
                subject_template="[TEST] AiMedic Zoho Integration — {{fecha}}",
                body_template="""
<div style="font-family: Arial, sans-serif; max-width: 600px; padding: 20px;">
    <h2>AiMedic — Zoho Mail Test</h2>
    <p>Si ves este correo, la integración está funcionando correctamente.</p>
    <ul>
        <li><strong>Fecha:</strong> {{fecha}}</li>
        <li><strong>Entorno:</strong> {{entorno}}</li>
    </ul>
    <p>Listo para enviar outreach M1/M2/M3.</p>
</div>
                """,
                variables={
                    "fecha": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "entorno": "Scrapper_Salud development",
                },
            )
            if result.get("success"):
                print(f"  OK — message_id: {result.get('message_id')}")
            else:
                print(f"  FAILED: {result.get('error')}")
        except Exception as e:
            print(f"  FAILED: {e}")

    print("\n=== Zoho connection OK — ready to send outreach ===")


if __name__ == "__main__":
    print("=" * 50)
    print("  AiMedic — Zoho Connection Test")
    print("=" * 50)
    check_env()
    send_test = "--send-test" in sys.argv
    asyncio.run(run_tests(send_test))
