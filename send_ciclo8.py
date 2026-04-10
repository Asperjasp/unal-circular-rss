#!/usr/bin/env python3
"""
send_ciclo8.py — Envío Ciclo 8, template CAMILO_V1
====================================================
40 emails repartidos en 2 horas (3 min entre cada uno).

Fuentes de leads (en orden de prioridad):
  1. Google Sheet (si existe google_service_account.json)
  2. CSV local (--csv path/to/file.csv)

Uso:
    # Preview desde Google Sheet:
    python3 send_ciclo8.py --dry-run

    # Preview desde CSV:
    python3 send_ciclo8.py --csv leads_ciclo8.csv --dry-run

    # Enviar 40 emails desde Sheet (escalonado 3 min c/u):
    python3 send_ciclo8.py --send

    # Agregar columnas de agente al Sheet (una sola vez):
    python3 send_ciclo8.py --setup-sheet

Mapeo automático de columnas CSV:
    nombre:  'nombre', 'name', 'first name', 'contact name'
    empresa: 'empresa', 'company', 'ips', 'business', 'account name'
    email:   'email', 'correo', 'e-mail'
"""

import argparse
import asyncio
import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from health_scraper.integrations.zoho_email_service import ZohoEmailService
from health_scraper.integrations.outreach_templates import render_template

# ── Config ────────────────────────────────────────────────────────────────
MAX_EMAILS        = 40
WINDOW_HOURS      = 2
DELAY_SECS        = (WINDOW_HOURS * 3600) / MAX_EMAILS   # 180s = 3 min
TEMPLATE          = "CAMILO_V1"
SA_JSON           = ROOT / "google_service_account.json"
SHEET_ID          = "1jBcTaANZTubNk3FWMnLdHFHyZhD31WTYIXe38g7eo9g"
SESSION_REF       = "ciclo8-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")

BOLD = "\033[1m"; GREEN = "\033[32m"; RED = "\033[31m"
YELLOW = "\033[33m"; CYAN = "\033[36m"; RESET = "\033[0m"
def _ok(t):   return GREEN + "✓ " + RESET + t
def _err(t):  return RED + "✗ " + RESET + t
def _warn(t): return YELLOW + "⚠  " + RESET + t
def _info(t): return CYAN + "→ " + RESET + t
def _h(t):    return BOLD + t + RESET

# ── Column detection for CSV ──────────────────────────────────────────────
NOMBRE_KEYS  = ["nombre", "name", "first name", "nombre contacto", "contact name", "firstname"]
EMPRESA_KEYS = ["empresa", "company", "ips", "institucion", "business", "account", "account name",
                "business / ips", "razon social"]
EMAIL_KEYS   = ["email", "correo", "e-mail", "mail", "email address"]

def _find_col(headers, candidates):
    h = {h.lower().strip(): h for h in headers}
    for c in candidates:
        if c in h:
            return h[c]
    return None


# ── Lead loading ──────────────────────────────────────────────────────────

def load_from_sheet(limit: int) -> list:
    """Load prospects from Google Sheet Contacts tab."""
    from health_scraper.integrations.sheets_service import SheetsService
    svc = SheetsService.from_service_account(str(SA_JSON), sheet_id=SHEET_ID)
    prospects = svc.get_contacts_for_sending(template=TEMPLATE, limit=limit)
    print(_ok("Sheet conectado — " + str(len(prospects)) + " prospects listos para envío"))
    return prospects, svc

def load_from_csv(path: str, limit: int) -> list:
    """Load prospects from CSV file."""
    p = Path(path)
    if not p.exists():
        print(_err("Archivo no encontrado: " + path))
        sys.exit(1)

    with open(p, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    rows = [{k.strip(): v.strip() for k, v in row.items()} for row in rows]
    headers = list(rows[0].keys()) if rows else []

    col_n = _find_col(headers, NOMBRE_KEYS)
    col_e = _find_col(headers, EMPRESA_KEYS)
    col_m = _find_col(headers, EMAIL_KEYS)

    print(_h("\nDetección de columnas:"))
    print("  nombre:  " + (_ok(col_n) if col_n else _err("NO ENCONTRADO")))
    print("  empresa: " + (_ok(col_e) if col_e else _err("NO ENCONTRADO")))
    print("  email:   " + (_ok(col_m) if col_m else _err("NO ENCONTRADO")))

    if not col_m:
        print(_err("Sin columna de email. Columnas: " + ", ".join(headers)))
        sys.exit(1)

    seen = set()
    prospects = []
    for row in rows:
        email   = row.get(col_m, "").strip().lower()
        nombre  = row.get(col_n, "").strip() if col_n else ""
        empresa = row.get(col_e, "").strip() if col_e else ""
        if not email or "@" not in email or email in seen:
            continue
        seen.add(email)
        if not nombre:
            nombre = email.split("@")[0].replace(".", " ").title()
        if not empresa:
            empresa = email.split("@")[1].split(".")[0].title()
        prospects.append({"email": email, "nombre": nombre, "empresa": empresa})
        if len(prospects) >= limit:
            break

    print(_ok(str(len(prospects)) + " prospects válidos cargados del CSV"))
    return prospects, None


# ── Preview ───────────────────────────────────────────────────────────────

def preview(prospects, n=5):
    import re
    print("\n" + _h("PREVIEW — primeros " + str(min(n, len(prospects))) + " emails") + "\n")
    for p in prospects[:n]:
        r = render_template(TEMPLATE, p)
        print("─" * 60)
        print(_h("Para:    ") + p["email"])
        print(_h("Empresa: ") + p["empresa"])
        print(_h("Subject: ") + r["subject"])
        body = re.sub(r"<[^>]+>", "", r["body"]).strip()
        print(body[:320] + "  [...]")
    print("\n" + "─" * 60)
    print(_info("Total: " + str(len(prospects)) + " prospects  |  " +
                str(int(DELAY_SECS//60)) + " min entre envíos  |  ~" +
                str(round(len(prospects[:MAX_EMAILS]) * DELAY_SECS / 3600, 1)) + "h total"))


# ── Send ──────────────────────────────────────────────────────────────────

async def send_all(prospects, svc, yes):
    cid   = os.getenv("ZOHO_CLIENT_ID")
    csec  = os.getenv("ZOHO_CLIENT_SECRET")
    rtok  = os.getenv("ZOHO_REFRESH_TOKEN")
    accid = os.getenv("ZOHO_ACCOUNT_ID")
    frm   = os.getenv("ZOHO_FROM_EMAIL")
    if not all([cid, csec, rtok, accid, frm]):
        print(_err("Faltan credenciales Zoho en .env"))
        sys.exit(1)

    zoho  = ZohoEmailService(client_id=cid, client_secret=csec,
                              refresh_token=rtok, account_id=accid, from_email=frm)
    batch = prospects[:MAX_EMAILS]
    total = len(batch)

    print("\n" + _h("RESUMEN DEL ENVÍO"))
    print("  Emails:       " + str(total))
    print("  Template:     " + TEMPLATE)
    print("  Desde:        " + frm)
    print("  Delay:        " + str(int(DELAY_SECS)) + "s (" + str(int(DELAY_SECS//60)) + " min)")
    print("  Duración:     ~" + str(round(total * DELAY_SECS / 3600, 1)) + " horas")
    print("  Sesión ref:   " + SESSION_REF)

    if not yes:
        print("\n" + _warn("Enviará " + str(total) + " emails reales desde " + frm))
        resp = input("Escribe 'enviar' para confirmar: ").strip().lower()
        if resp != "enviar":
            print("Cancelado.")
            sys.exit(0)

    sent = failed = 0
    results = []
    print("\n" + _info("Iniciando envío...\n"))

    for i, p in enumerate(batch):
        rendered = render_template(TEMPLATE, p)
        result   = await zoho.send_email(
            to_email=p["email"],
            subject=rendered["subject"],
            body=rendered["body"],
            is_html=True,
        )

        ok      = result.get("success", False)
        msg_id  = result.get("message_id", "")
        err_msg = result.get("error", "")

        tag = "[" + str(i+1) + "/" + str(total) + "]"
        if ok:
            sent += 1
            print(_ok(tag + " " + p["email"] + " — " + p["empresa"]))
            # Update sheet if connected
            if svc:
                try:
                    svc.mark_contacted(
                        email=p["email"], zoho_message_id=msg_id,
                        step=1, session_ref=SESSION_REF,
                        action="M1 CAMILO_V1 sent via Zoho",
                    )
                    svc.log_interaction(
                        contact=p["nombre"], business=p["empresa"],
                        channel="Email Zoho", direction="Outbound",
                        summary="M1 CAMILO_V1 enviado — Propuesta Cooperación",
                        next_step="Esperar respuesta 4 días, luego M2",
                    )
                except Exception as e:
                    print("  " + _warn("Sheet update failed: " + str(e)))
        else:
            failed += 1
            print(_err(tag + " " + p["email"] + " — " + str(err_msg)))

        results.append({
            "email": p["email"], "nombre": p["nombre"], "empresa": p["empresa"],
            "success": ok, "error": err_msg, "msg_id": msg_id,
        })
        _save_results(results)

        if i < total - 1:
            print("  " + _info("Esperando " + str(int(DELAY_SECS//60)) + "m " +
                                str(int(DELAY_SECS % 60)) + "s..."))
            time.sleep(DELAY_SECS)

    print("\n" + "=" * 60)
    print(_h("RESULTADO FINAL"))
    print("  " + _ok("Enviados: " + str(sent)))
    print("  " + _err("Fallidos: " + str(failed)))
    print("  Guardado en: campaign_ciclo8_results.csv")


def _save_results(results):
    out = ROOT / "campaign_ciclo8_results.csv"
    keys = ["email", "nombre", "empresa", "success", "error", "msg_id"]
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k, "") for k in keys})


# ── Setup Sheet ───────────────────────────────────────────────────────────

def setup_sheet():
    """Add agent-tracking columns to the Contacts tab (run once)."""
    if not SA_JSON.exists():
        print(_err("google_service_account.json no encontrado."))
        print(_info("Sigue las instrucciones de setup para crear el service account."))
        sys.exit(1)

    from health_scraper.integrations.sheets_service import SheetsService, AGENT_COLUMNS
    svc = SheetsService.from_service_account(str(SA_JSON), sheet_id=SHEET_ID)

    print(_h("\nVerificando columnas de agente en Contacts..."))
    result = svc.ensure_agent_columns(dry_run=True)
    print("  Ya existen: " + ", ".join(result["existing"] or ["ninguna"]))
    print("  A agregar:  " + ", ".join(result["added"] or ["ninguna"]))

    if not result["added"]:
        print(_ok("Sheet ya tiene todas las columnas de agente. Nada que hacer."))
        return

    resp = input("\n¿Agregar " + str(len(result["added"])) + " columnas al Sheet? (s/n): ").strip().lower()
    if resp != "s":
        print("Cancelado.")
        return

    svc.ensure_agent_columns(dry_run=False)
    print(_ok("Columnas agregadas: " + ", ".join(result["added"])))
    print(_info("Columnas añadidas en la fila 3 del tab Contacts."))


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Envío Ciclo 8 — CAMILO_V1")
    parser.add_argument("--csv",         metavar="FILE",    help="CSV de leads (si no hay Sheet)")
    parser.add_argument("--dry-run",     action="store_true", help="Preview sin enviar")
    parser.add_argument("--send",        action="store_true", help="Enviar emails reales")
    parser.add_argument("--setup-sheet", action="store_true", help="Agregar columnas agente al Sheet")
    parser.add_argument("--limit",       type=int, default=MAX_EMAILS)
    parser.add_argument("--preview-n",   type=int, default=5)
    parser.add_argument("--yes", "-y",   action="store_true", help="Saltar confirmación")
    args = parser.parse_args()

    if args.setup_sheet:
        setup_sheet()
        return

    # Determine lead source
    svc       = None
    prospects = []

    if SA_JSON.exists() and not args.csv:
        print(_info("Service account encontrado — cargando leads del Google Sheet..."))
        prospects, svc = load_from_sheet(args.limit)
    elif args.csv:
        prospects, svc = load_from_csv(args.csv, args.limit)
    else:
        print(_warn("No hay google_service_account.json ni --csv."))
        print(_info("Opciones:"))
        print("  1. Configura el service account (ver instrucciones)")
        print("  2. Exporta el Sheet como CSV y usa --csv leads.csv")
        sys.exit(1)

    if not prospects:
        print(_warn("Sin prospects. Verifica el Sheet o CSV."))
        sys.exit(0)

    if args.dry_run:
        preview(prospects, args.preview_n)

    elif args.send:
        preview(prospects, 3)
        asyncio.run(send_all(prospects, svc, args.yes))

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
