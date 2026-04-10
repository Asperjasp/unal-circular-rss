#!/usr/bin/env python3
"""
send_campaign.py — AiMedic Outreach Campaign CLI
=================================================

Send personalized cold email campaigns via Zoho Mail with full cadence
management (M1 -> M2 -> M3 sequences).

QUICK START
-----------
  # Preview what would be sent (no emails sent):
  python send_campaign.py --csv prospects.csv --template M1_CONNECT --dry-run

  # Send first 5 as a test:
  python send_campaign.py --csv prospects.csv --template M1_CONNECT --limit 5 --send

  # Send full campaign:
  python send_campaign.py --csv prospects.csv --template M1_CONNECT --send

  # Process due M2/M3 follow-ups (run daily):
  python send_campaign.py --process

  # Check cadence stats:
  python send_campaign.py --stats

  # Mark a reply (pauses their sequence):
  python send_campaign.py --mark-replied someone@clinica.com.co

CSV FORMAT
----------
Required columns vary by template. Minimum for M1_CONNECT:
  nombre, empresa, email, tipo_entidad, contexto_personalizado

Minimum for M1_OPERATOR:
  nombre, empresa, email, especialidad, dolor

Create from the included template:
  cp prospects_template.csv prospects.csv
"""

import argparse
import csv
import os
import sys
import logging
from pathlib import Path
from typing import Optional

# ── Path setup ───────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from health_scraper.integrations.zoho_email_service import ZohoEmailService
from health_scraper.integrations.zoho_cadence_service import CadenceEngine, init_db
from health_scraper.integrations.outreach_templates import (
    render_template, list_templates, TEMPLATES
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("send_campaign")

# ── Color helpers (no external deps) ────────────────────────────────────
BOLD   = "\033[1m"
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
RESET  = "\033[0m"

def _h(t):    return BOLD + t + RESET
def _ok(t):   return GREEN + "✓" + RESET + " " + t
def _err(t):  return RED + "✗" + RESET + " " + t
def _warn(t): return YELLOW + "⚠" + RESET + "  " + t
def _info(t): return CYAN + "→" + RESET + " " + t

def _strip_html(html):
    import re
    return re.sub(r"<[^>]+>", "", html).strip()


# ── CSV Loading ───────────────────────────────────────────────────────────

def load_csv(path):
    p = Path(path)
    if not p.exists():
        print(_err("File not found: " + path))
        sys.exit(1)
    with open(p, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    rows = [{k.strip(): v.strip() for k, v in row.items()} for row in rows]
    print(_ok("Loaded " + str(len(rows)) + " prospects from " + p.name))
    return rows


# ── Zoho Setup ────────────────────────────────────────────────────────────

def build_zoho():
    cid   = os.getenv("ZOHO_CLIENT_ID")
    csec  = os.getenv("ZOHO_CLIENT_SECRET")
    rtok  = os.getenv("ZOHO_REFRESH_TOKEN")
    accid = os.getenv("ZOHO_ACCOUNT_ID")
    frm   = os.getenv("ZOHO_FROM_EMAIL")
    if not all([cid, csec, rtok, accid, frm]):
        return None
    return ZohoEmailService(
        client_id=cid, client_secret=csec,
        refresh_token=rtok, account_id=accid, from_email=frm,
    )


# ── Preview ───────────────────────────────────────────────────────────────

def preview_campaign(prospects, template, limit):
    tmpl_meta = TEMPLATES[template]
    print("\n" + _h("CAMPAIGN PREVIEW"))
    print("Template: " + _h(template) + " — " + tmpl_meta["name"])
    print("Required vars: " + ", ".join(tmpl_meta["required_vars"]) + "\n")

    shown = errors = 0
    for i, p in enumerate(prospects):
        if shown >= limit:
            print("\n" + _warn(str(len(prospects) - i) + " more prospects not shown (--limit)"))
            break
        email = p.get("email", "").strip()
        if not email:
            print(_err("Row " + str(i + 1) + ": no email — skipped"))
            errors += 1
            continue
        try:
            rendered = render_template(template, p)
        except ValueError as e:
            print(_err("Row " + str(i + 1) + " (" + email + "): " + str(e)))
            errors += 1
            continue

        print("─" * 60)
        print(_h("TO:     ") + " " + email)
        print(_h("SUBJECT:") + " " + rendered["subject"])
        print(_h("BODY:"))
        body_text = _strip_html(rendered["body"])
        print(body_text[:600] + ("  [...]" if len(body_text) > 600 else ""))
        shown += 1

    print("\n" + "─" * 60)
    print(_ok(str(shown) + " previews shown") + "  " + _err(str(errors) + " skipped (missing vars)"))
    if errors:
        print(_warn("Fix missing variables in your CSV before sending."))


# ── Send ──────────────────────────────────────────────────────────────────

def run_send(prospects, template, limit, yes):
    zoho = build_zoho()
    if not zoho:
        print(_err("Zoho credentials missing in .env. Cannot send."))
        sys.exit(1)

    engine = CadenceEngine(zoho=zoho)
    subset = prospects[:limit]

    valid, invalid = [], []
    for p in subset:
        email = p.get("email", "").strip()
        if not email:
            invalid.append({"email": "?", "reason": "no email"})
            continue
        try:
            render_template(template, p)
            valid.append(p)
        except ValueError as e:
            invalid.append({"email": email, "reason": str(e)})

    print("\n" + _h("SEND SUMMARY"))
    print("  Template:  " + template)
    print("  Valid:     " + _ok(str(len(valid))))
    print("  Invalid:   " + _err(str(len(invalid))))
    for inv in invalid[:5]:
        print("    " + _warn(inv["email"]) + " — " + inv["reason"])
    if len(invalid) > 5:
        print("    ... and " + str(len(invalid) - 5) + " more")

    if not valid:
        print(_err("No valid prospects. Aborting."))
        sys.exit(1)

    if not yes:
        print("\n" + _warn("About to send M1 to " + str(len(valid)) + " prospects via Zoho."))
        answer = input("Type 'yes' to confirm: ").strip().lower()
        if answer != "yes":
            print("Aborted.")
            sys.exit(0)

    print("\n" + _info("Enqueuing..."))
    eq = engine.enqueue(valid, m1_template=template)
    print("  Added: " + str(eq["added"]) + "  Skipped: " + str(eq["skipped"]) + "  Failed: " + str(eq["failed"]))

    print("\n" + _info("Sending M1 emails..."))
    sr = engine.process_due()

    print("\n" + _h("RESULTS"))
    print("  " + _ok("Sent:   " + str(sr["sent"])))
    print("  " + _err("Failed: " + str(sr["failed"])))
    if sr.get("skipped_daily_limit"):
        print("  " + _warn("Skipped (daily limit): " + str(sr["skipped_daily_limit"])))

    for d in sr["details"][:20]:
        icon = _ok("") if d.get("success") else _err("")
        print("    " + icon + d["email"] + " — " + str(d.get("error") or d.get("message_id", "ok")))


# ── Process Due ───────────────────────────────────────────────────────────

def run_process(dry_run=False):
    zoho = None if dry_run else build_zoho()
    if not dry_run and not zoho:
        print(_err("Zoho credentials missing in .env. Use --dry-run to preview."))
        sys.exit(1)

    engine = CadenceEngine(zoho=zoho)
    r = engine.process_due(dry_run=dry_run)

    mode = " (DRY RUN)" if dry_run else ""
    print("\n" + _h("PROCESS DUE" + mode))
    print("  " + _ok("Sent:   " + str(r["sent"])))
    print("  " + _err("Failed: " + str(r["failed"])))
    if r.get("skipped_daily_limit"):
        print("  " + _warn("Skipped (daily limit): " + str(r["skipped_daily_limit"])))


# ── Stats ─────────────────────────────────────────────────────────────────

def run_stats():
    engine = CadenceEngine()
    s = engine.stats()
    print("\n" + _h("CADENCE STATS"))
    print("  Today's sends:         " + str(s["today_sends"]) + " / " + str(s["daily_limit"]))
    print("  Total sent (all time): " + str(s["total_sent_all_time"]))
    print("\n  Status breakdown:")
    for status, count in s["status_breakdown"].items():
        print("    " + status + ": " + str(count))
    print("\n  Active by step:")
    for step, count in s["active_by_step"].items():
        print("    " + step + ": " + str(count))


# ── Templates ─────────────────────────────────────────────────────────────

def run_list_templates():
    print("\n" + _h("AVAILABLE TEMPLATES"))
    for t in list_templates():
        print("\n  " + _h(t["id"]) + " — " + t["name"])
        print("    Product:       " + (t["product"] or "both"))
        print("    Required vars: " + ", ".join(t["required_vars"]))


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AiMedic Outreach Campaign CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--send",         action="store_true", help="Send M1 to prospects in --csv")
    mode.add_argument("--dry-run",      action="store_true", help="Preview emails without sending")
    mode.add_argument("--process",      action="store_true", help="Process due M2/M3 follow-ups")
    mode.add_argument("--stats",        action="store_true", help="Show cadence stats")
    mode.add_argument("--templates",    action="store_true", help="List available templates")
    mode.add_argument("--mark-replied", metavar="EMAIL",     help="Pause sequence for a prospect that replied")
    mode.add_argument("--mark-bounced", metavar="EMAIL",     help="Mark prospect email as bounced")

    parser.add_argument("--csv",      metavar="FILE",     help="Prospects CSV file")
    parser.add_argument("--template", metavar="TEMPLATE", help="Template name (e.g. M1_CONNECT)")
    parser.add_argument("--limit",    type=int, default=50, help="Max prospects to process (default: 50)")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()
    init_db()

    if args.templates:
        run_list_templates()

    elif args.stats:
        run_stats()

    elif args.mark_replied:
        engine = CadenceEngine()
        ok = engine.mark_replied(args.mark_replied)
        print(_ok("Paused sequence for " + args.mark_replied) if ok else _err("Email not found in cadences"))

    elif args.mark_bounced:
        engine = CadenceEngine()
        ok = engine.mark_bounced(args.mark_bounced)
        print(_ok("Marked " + args.mark_bounced + " as bounced") if ok else _err("Email not found in cadences"))

    elif args.process:
        run_process(dry_run=False)

    elif args.dry_run:
        if not args.csv or not args.template:
            parser.error("--dry-run requires --csv and --template")
        if args.template not in TEMPLATES:
            parser.error("Unknown template: " + args.template + ". Run --templates to see options.")
        preview_campaign(load_csv(args.csv), args.template, args.limit)

    elif args.send:
        if not args.csv or not args.template:
            parser.error("--send requires --csv and --template")
        if args.template not in TEMPLATES:
            parser.error("Unknown template: " + args.template + ". Run --templates to see options.")
        run_send(load_csv(args.csv), args.template, args.limit, args.yes)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
