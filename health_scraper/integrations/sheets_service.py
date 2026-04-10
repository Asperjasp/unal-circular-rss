"""
sheets_service.py — AiMedic CRM Google Sheets Integration
==========================================================
Read/write the aimedic_crm Google Sheet as a source of truth for all agents.

Sheet ID: 1jBcTaANZTubNk3FWMnLdHFHyZhD31WTYIXe38g7eo9g

Tabs:
  Contacts     — people (emails, roles, business links)
  Businesses   — accounts (IPS/EPS/LAB, NIT, city, ICP)
  Deals        — pipeline (stage, MRR, responsable)
  Interactions — every touchpoint log (outbound/inbound)

Agentic columns added by this service:
  agent_status         — pending | enriching | contacted | replied | converted | skip
  last_agent_action    — human-readable last action description
  agent_session_ref    — session or run ID for traceability
  email_m1_sent_at     — ISO timestamp
  email_m2_sent_at     — ISO timestamp
  email_m3_sent_at     — ISO timestamp
  zoho_message_id      — Zoho message ID of last sent email
  data_source          — manual | agent_enriched | zoho_sync | linkedin_scrape
  last_touched_at      — ISO timestamp of any agent write

Usage:
    svc = SheetsService.from_service_account("google_service_account.json")
    contacts = svc.get_contacts()
    svc.mark_contacted("C-000000042", zoho_message_id="abc123")
    svc.log_interaction(contact_id="C-000000042", business="Salud Total EPS",
                        channel="Email Zoho", direction="Outbound",
                        summary="M1 CAMILO_V1 sent", next_step="Wait 4 days for M2")
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SHEET_ID = "1jBcTaANZTubNk3FWMnLdHFHyZhD31WTYIXe38g7eo9g"
SCOPES   = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# ── Agentic column definitions ────────────────────────────────────────────
# These are added to the Contacts sheet to make it AI-agent trackable.
AGENT_COLUMNS = [
    "agent_status",       # pending | enriching | contacted | replied | converted | skip
    "last_agent_action",  # e.g. "M1 CAMILO_V1 sent via Zoho"
    "agent_session_ref",  # traceability: Claude session or cron run ID
    "email_m1_sent_at",
    "email_m2_sent_at",
    "email_m3_sent_at",
    "zoho_message_id",
    "data_source",        # manual | agent_enriched | zoho_sync | linkedin_scrape
    "last_touched_at",
]


class SheetsService:
    """
    Read/write the AiMedic CRM Google Sheet.

    All writes are append-safe — this service never overwrites cells
    the user or another agent has manually edited, except for the
    designated AGENT_COLUMNS.
    """

    def __init__(self, client: gspread.Client, sheet_id: str = SHEET_ID):
        self.client   = client
        self.sheet_id = sheet_id
        self._wb: Optional[gspread.Spreadsheet] = None

    # ── Constructor helpers ───────────────────────────────────────────────

    @classmethod
    def from_service_account(cls, json_path: str, sheet_id: str = SHEET_ID) -> "SheetsService":
        p = Path(json_path)
        if not p.exists():
            raise FileNotFoundError(
                "Service account JSON not found: " + str(p) + "\n"
                "See README for setup instructions."
            )
        creds  = Credentials.from_service_account_file(str(p), scopes=SCOPES)
        client = gspread.authorize(creds)
        return cls(client, sheet_id)

    @classmethod
    def from_service_account_dict(cls, info: Dict, sheet_id: str = SHEET_ID) -> "SheetsService":
        creds  = Credentials.from_service_account_info(info, scopes=SCOPES)
        client = gspread.authorize(creds)
        return cls(client, sheet_id)

    # ── Workbook access ───────────────────────────────────────────────────

    @property
    def wb(self) -> gspread.Spreadsheet:
        if self._wb is None:
            self._wb = self.client.open_by_key(self.sheet_id)
        return self._wb

    def _ws(self, tab: str) -> gspread.Worksheet:
        return self.wb.worksheet(tab)

    # ── Contacts ──────────────────────────────────────────────────────────

    def get_contacts(
        self,
        status_filter: Optional[str] = None,
        has_email: bool = True,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return all contacts from the Contacts tab.

        Args:
            status_filter: Only return rows with this agent_status.
                           Use None for all, 'pending' for unsent leads.
            has_email: Skip rows with no email address.
            limit: Max rows to return.
        """
        ws   = self._ws("Contacts")
        rows = ws.get_all_records(default_blank="")

        result = []
        for row in rows:
            email = _coalesce(row, ["Email", "email", "correo", "e-mail"])
            if has_email and not email:
                continue

            agent_status = row.get("agent_status", "").strip()
            if status_filter and agent_status != status_filter:
                continue

            result.append({**row, "_email_resolved": email})

            if limit and len(result) >= limit:
                break

        logger.info("get_contacts: returned %d rows (filter=%s)", len(result), status_filter)
        return result

    def get_contacts_for_sending(self, template: str = "CAMILO_V1", limit: int = 40) -> List[Dict]:
        """
        Return contacts ready for M1 outreach: have email, agent_status is
        'pending' or empty, and m1 has not been sent.
        """
        ws   = self._ws("Contacts")
        rows = ws.get_all_records(default_blank="")

        prospects = []
        for row in rows:
            email = _coalesce(row, ["Email", "email", "correo"])
            if not email or "@" not in email:
                continue

            status  = row.get("agent_status", "").strip().lower()
            m1_sent = row.get("email_m1_sent_at", "").strip()

            # Skip already contacted or explicitly excluded
            if status in ("contacted", "replied", "converted", "skip"):
                continue
            if m1_sent:
                continue

            # Build variables for template
            nombre  = _coalesce(row, ["First Name", "nombre", "Nombre", "name", "Contact Name"])
            empresa = _coalesce(row, ["Business", "empresa", "Empresa", "Account", "Business / IPS"])

            if not nombre:
                nombre = email.split("@")[0].replace(".", " ").title()
            if not empresa:
                empresa = email.split("@")[1].split(".")[0].title()

            prospects.append({
                "email":   email,
                "nombre":  nombre,
                "empresa": empresa,
                "_row_id": row.get("contact_id") or row.get("C-id") or "",
                "_raw":    row,
            })

            if len(prospects) >= limit:
                break

        logger.info("get_contacts_for_sending: %d prospects ready", len(prospects))
        return prospects

    def mark_contacted(
        self,
        email: str,
        zoho_message_id: str = "",
        step: int = 1,
        session_ref: str = "",
        action: str = "",
    ) -> bool:
        """
        Mark a contact as contacted and record the send metadata.
        Writes only to AGENT_COLUMNS — never touches user data.
        """
        ws      = self._ws("Contacts")
        records = ws.get_all_records(default_blank="")
        headers = ws.row_values(3)  # Row 3 is headers (rows 1-2 are title/spacer)

        now = _now()
        email_lower = email.lower().strip()

        for i, row in enumerate(records):
            row_email = _coalesce(row, ["Email", "email", "correo", "e-mail"])
            if not row_email or row_email.lower().strip() != email_lower:
                continue

            row_num = i + 4  # +1 for 0-index, +3 for header rows

            updates = {
                "agent_status":      "contacted",
                "last_agent_action": action or ("M" + str(step) + " sent via Zoho"),
                "agent_session_ref": session_ref,
                "zoho_message_id":   zoho_message_id,
                "data_source":       "zoho_sync",
                "last_touched_at":   now,
            }
            if step == 1:
                updates["email_m1_sent_at"] = now
            elif step == 2:
                updates["email_m2_sent_at"] = now
            elif step == 3:
                updates["email_m3_sent_at"] = now

            self._write_agent_cols(ws, headers, row_num, updates)
            logger.info("Marked %s as contacted (step %d)", email, step)
            return True

        logger.warning("mark_contacted: email not found in sheet: %s", email)
        return False

    def mark_replied(self, email: str, summary: str = "") -> bool:
        """Mark a contact as replied — cadence should be paused."""
        ws      = self._ws("Contacts")
        records = ws.get_all_records(default_blank="")
        headers = ws.row_values(3)
        email_lower = email.lower().strip()

        for i, row in enumerate(records):
            row_email = _coalesce(row, ["Email", "email", "correo"])
            if not row_email or row_email.lower().strip() != email_lower:
                continue

            row_num = i + 4
            self._write_agent_cols(ws, headers, row_num, {
                "agent_status":      "replied",
                "last_agent_action": "Reply received — " + (summary or "human to handle"),
                "last_touched_at":   _now(),
            })
            return True

        return False

    # ── Interactions log ──────────────────────────────────────────────────

    def log_interaction(
        self,
        contact: str,
        business: str,
        channel: str,
        direction: str,
        summary: str,
        next_step: str = "",
        responsable: str = "Alejandro",
        deal_id: str = "",
    ) -> str:
        """
        Append a new row to the Interactions tab.

        Returns the new log_id (e.g. 'I-042').
        """
        ws      = self._ws("Interactions")
        records = ws.get_all_records(default_blank="")

        # Generate next log_id
        existing_ids = [r.get("log_id", "") for r in records if r.get("log_id", "").startswith("I-")]
        if existing_ids:
            last_num = max(int(x.split("-")[1]) for x in existing_ids if x.split("-")[1].isdigit())
            log_id   = "I-" + str(last_num + 1).zfill(3)
        else:
            log_id = "I-001"

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        new_row  = [log_id, date_str, contact, business, channel, direction, responsable, deal_id, summary, next_step]

        ws.append_row(new_row, value_input_option="USER_ENTERED")
        logger.info("Logged interaction %s for %s via %s", log_id, contact, channel)
        return log_id

    # ── Businesses ────────────────────────────────────────────────────────

    def get_businesses(self, type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return businesses, optionally filtered by Type (IPS, EPS, LAB)."""
        ws   = self._ws("Businesses")
        rows = ws.get_all_records(default_blank="")

        if type_filter:
            rows = [r for r in rows if r.get("Type", "").upper() == type_filter.upper()]

        return rows

    # ── Agentic column setup ──────────────────────────────────────────────

    def ensure_agent_columns(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Add missing AGENT_COLUMNS to the Contacts sheet header row.
        Safe to run multiple times — skips columns that already exist.

        Returns: {added: [...], existing: [...]}
        """
        ws      = self._ws("Contacts")
        headers = ws.row_values(3)  # row 3 = header row

        added    = []
        existing = []

        for col_name in AGENT_COLUMNS:
            if col_name in headers:
                existing.append(col_name)
            else:
                if not dry_run:
                    # Append header in next empty column
                    next_col = len(headers) + 1
                    ws.update_cell(3, next_col, col_name)
                    headers.append(col_name)
                added.append(col_name)

        if added and not dry_run:
            logger.info("Added agent columns to Contacts: %s", added)

        return {"added": added, "existing": existing}

    # ── Internal helpers ──────────────────────────────────────────────────

    def _write_agent_cols(
        self,
        ws: gspread.Worksheet,
        headers: List[str],
        row_num: int,
        updates: Dict[str, str],
    ) -> None:
        """Write key→value pairs to specific cells in a row, by header name."""
        for col_name, value in updates.items():
            if not value:
                continue
            try:
                col_idx = headers.index(col_name) + 1
                ws.update_cell(row_num, col_idx, value)
            except ValueError:
                logger.warning("Column '%s' not found in sheet headers — skipping", col_name)


# ── Standalone helpers ────────────────────────────────────────────────────

def _coalesce(row: Dict, keys: List[str]) -> str:
    """Return the first non-empty value from the list of possible keys."""
    for k in keys:
        val = row.get(k, "").strip()
        if val and val.upper() not in ("N/A", "NA", "-", "NONE"):
            return val
    return ""

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
