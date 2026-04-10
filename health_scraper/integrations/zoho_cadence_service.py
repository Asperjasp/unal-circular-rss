"""
Zoho Email Cadence Engine
=========================
Manages multi-step cold email sequences (M1 → M2 → M3) via Zoho Mail API.

Sequence schedule:
  M1 — Day 0  (cold intro, sent immediately on enqueue)
  M2 — Day 4  (follow-up with case study)
  M3 — Day 9  (breakup email)

If a prospect replies at any step, the sequence is paused automatically.
Rate limit: 40 sends/day (configurable) to stay well inside spam thresholds.

State is persisted in a local SQLite file (cadence.db) so the engine
survives restarts and can be driven by a cron job or manual CLI runs.

Usage:
    engine = CadenceEngine()
    engine.enqueue(prospects, template="M1_CONNECT")
    engine.process_due()          # call daily (or manually)
    engine.mark_replied("email")  # call when a reply is detected
"""

import sqlite3
import json
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from health_scraper.integrations.zoho_email_service import ZohoEmailService
from health_scraper.integrations.outreach_templates import render_template, TEMPLATES

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "cadence.db"
MAX_SENDS_PER_DAY = 40

STEP_DELAYS = {1: 4, 2: 9}   # M2 at day 4, M3 at day 9
STEP_TEMPLATES = {
    0: None,   # determined at enqueue time (M1_CONNECT or M1_OPERATOR)
    1: "M2_EMAIL",
    2: "M3_EMAIL",
}


# ── DB Setup ──────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    with _get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS cadences (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            email           TEXT NOT NULL,
            name            TEXT,
            empresa         TEXT,
            m1_template     TEXT NOT NULL,
            variables       TEXT NOT NULL,
            current_step    INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'active',
            m1_sent_at      TEXT,
            m2_send_after   TEXT,
            m2_sent_at      TEXT,
            m3_send_after   TEXT,
            m3_sent_at      TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            UNIQUE(email)
        );

        CREATE TABLE IF NOT EXISTS send_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            cadence_id      INTEGER REFERENCES cadences(id),
            email           TEXT NOT NULL,
            step            INTEGER NOT NULL,
            template_name   TEXT NOT NULL,
            subject         TEXT,
            zoho_message_id TEXT,
            status          TEXT,
            error           TEXT,
            sent_at         TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_cadences_status ON cadences(status);
        CREATE INDEX IF NOT EXISTS idx_send_log_date ON send_log(sent_at);
        """)


# ── CadenceEngine ─────────────────────────────────────────────────────────

class CadenceEngine:
    """
    Manages outreach sequences for a list of prospects.

    Each prospect goes through up to 3 email steps. The engine tracks
    state in SQLite so it's safe to call process_due() repeatedly.
    """

    def __init__(self, zoho: Optional[ZohoEmailService] = None):
        init_db()
        self.zoho = zoho

    # ── Enqueue ───────────────────────────────────────────────────────────

    def enqueue(
        self,
        prospects: List[Dict[str, Any]],
        m1_template: str,
        skip_existing: bool = True,
    ) -> Dict[str, int]:
        """
        Add prospects to the cadence. Sends M1 immediately if zoho is set.

        Each prospect dict must have 'email' and the variables required
        by m1_template. Optional: 'name', 'empresa'.

        Returns counts of added / skipped / failed.
        """
        if m1_template not in TEMPLATES:
            raise ValueError(f"Unknown template: {m1_template}. Options: {list(TEMPLATES)}")

        added = skipped = failed = 0

        for p in prospects:
            email = (p.get("email") or "").strip().lower()
            if not email:
                logger.warning("Skipping prospect with no email: %s", p)
                failed += 1
                continue

            try:
                # Validate all required vars are present
                render_template(m1_template, p)
            except ValueError as e:
                logger.warning("Skipping %s — missing vars: %s", email, e)
                failed += 1
                continue

            try:
                with _get_conn() as conn:
                    existing = conn.execute(
                        "SELECT id, status FROM cadences WHERE email = ?", (email,)
                    ).fetchone()

                    if existing:
                        if skip_existing:
                            logger.debug("Skipping existing cadence for %s", email)
                            skipped += 1
                            continue
                        else:
                            # Re-enqueue: reset sequence
                            conn.execute(
                                """UPDATE cadences SET status='active', current_step=0,
                                   m1_sent_at=NULL, m2_send_after=NULL, m2_sent_at=NULL,
                                   m3_send_after=NULL, m3_sent_at=NULL, variables=?,
                                   m1_template=?, updated_at=datetime('now')
                                   WHERE email=?""",
                                (json.dumps(p), m1_template, email),
                            )
                    else:
                        conn.execute(
                            """INSERT INTO cadences (email, name, empresa, m1_template, variables)
                               VALUES (?, ?, ?, ?, ?)""",
                            (
                                email,
                                p.get("nombre") or p.get("name", ""),
                                p.get("empresa", ""),
                                m1_template,
                                json.dumps(p),
                            ),
                        )
                    added += 1
            except sqlite3.Error as e:
                logger.error("DB error enqueuing %s: %s", email, e)
                failed += 1

        logger.info("Enqueued %d prospects (skipped %d, failed %d)", added, skipped, failed)
        return {"added": added, "skipped": skipped, "failed": failed}

    # ── Process Due ───────────────────────────────────────────────────────

    def process_due(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Send all emails that are due right now.

        Call this daily (via cron or manually). Returns a summary dict.
        """
        if not self.zoho and not dry_run:
            raise RuntimeError("No ZohoEmailService configured. Pass zoho= to CadenceEngine or use dry_run=True.")

        sent = []
        failed = []
        skipped_limit = 0

        due = self._get_due_sends()
        logger.info("Found %d due sends", len(due))

        for row in due:
            if self._daily_send_count() >= MAX_SENDS_PER_DAY:
                logger.warning("Daily limit (%d) reached. Stopping.", MAX_SENDS_PER_DAY)
                skipped_limit = len(due) - len(sent) - len(failed)
                break

            result = self._send_step(row, dry_run=dry_run)
            if result.get("success"):
                sent.append(result)
            else:
                failed.append(result)

        return {
            "sent": len(sent),
            "failed": len(failed),
            "skipped_daily_limit": skipped_limit,
            "details": sent + failed,
        }

    def _get_due_sends(self) -> List[sqlite3.Row]:
        """Return all cadence rows that have a step due now."""
        now = datetime.utcnow().isoformat()
        with _get_conn() as conn:
            # M1: never sent yet
            m1_due = conn.execute(
                """SELECT *, 0 as due_step FROM cadences
                   WHERE status='active' AND m1_sent_at IS NULL""",
            ).fetchall()

            # M2: scheduled and not sent
            m2_due = conn.execute(
                """SELECT *, 1 as due_step FROM cadences
                   WHERE status='active'
                     AND m1_sent_at IS NOT NULL
                     AND m2_send_after <= ?
                     AND m2_sent_at IS NULL""",
                (now,),
            ).fetchall()

            # M3: scheduled and not sent
            m3_due = conn.execute(
                """SELECT *, 2 as due_step FROM cadences
                   WHERE status='active'
                     AND m2_sent_at IS NOT NULL
                     AND m3_send_after <= ?
                     AND m3_sent_at IS NULL""",
                (now,),
            ).fetchall()

        return m1_due + m2_due + m3_due

    def _send_step(self, row: sqlite3.Row, dry_run: bool = False) -> Dict[str, Any]:
        """Send a single step for one cadence row."""
        step = row["due_step"]
        email = row["email"]
        variables = json.loads(row["variables"])

        # Determine template for this step
        if step == 0:
            template_name = row["m1_template"]
        else:
            template_name = STEP_TEMPLATES[step]

        # M2/M3 use minimal required vars — fill from stored variables
        try:
            rendered = render_template(template_name, variables)
        except ValueError:
            # M2/M3 have extra required vars (caso_similar, fecha_propuesta, etc.)
            # Fill defaults if missing
            variables = _fill_m2_m3_defaults(variables, template_name)
            try:
                rendered = render_template(template_name, variables)
            except ValueError as e:
                logger.error("Cannot render %s for %s: %s", template_name, email, e)
                return {"success": False, "email": email, "step": step, "error": str(e)}

        subject = rendered["subject"]
        body = rendered["body"]

        if dry_run:
            print(f"\n{'─'*60}")
            print(f"TO:      {email}")
            print(f"STEP:    M{step+1} ({template_name})")
            print(f"SUBJECT: {subject}")
            print(f"BODY:\n{_strip_html(body)[:400]}...")
            return {"success": True, "email": email, "step": step, "dry_run": True}

        # Send via Zoho
        result = asyncio.run(
            self.zoho.send_email(
                to_email=email,
                subject=subject,
                body=body,
                is_html=True,
            )
        )

        success = result.get("success", False)
        message_id = result.get("message_id")
        error = result.get("error")

        self._record_send(row, step, template_name, subject, message_id, success, error)

        if success:
            logger.info("Sent M%d to %s — msg_id=%s", step + 1, email, message_id)
        else:
            logger.error("Failed M%d to %s — %s", step + 1, email, error)

        return {
            "success": success,
            "email": email,
            "step": step,
            "template": template_name,
            "message_id": message_id,
            "error": error,
        }

    def _record_send(
        self,
        row: sqlite3.Row,
        step: int,
        template_name: str,
        subject: str,
        message_id: Optional[str],
        success: bool,
        error: Optional[str],
    ) -> None:
        """Update cadence state and write send_log entry."""
        now = datetime.utcnow().isoformat()
        cadence_id = row["id"]
        status_val = "sent" if success else "failed"

        with _get_conn() as conn:
            # Write log
            conn.execute(
                """INSERT INTO send_log (cadence_id, email, step, template_name, subject, zoho_message_id, status, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (cadence_id, row["email"], step, template_name, subject, message_id, status_val, error),
            )

            if not success:
                return

            if step == 0:
                m2_after = (datetime.utcnow() + timedelta(days=STEP_DELAYS[1])).isoformat()
                m3_after = (datetime.utcnow() + timedelta(days=STEP_DELAYS[2])).isoformat()
                conn.execute(
                    """UPDATE cadences SET m1_sent_at=?, m2_send_after=?, m3_send_after=?,
                          current_step=1, updated_at=datetime('now')
                       WHERE id=?""",
                    (now, m2_after, m3_after, cadence_id),
                )
            elif step == 1:
                conn.execute(
                    """UPDATE cadences SET m2_sent_at=?, current_step=2, updated_at=datetime('now')
                       WHERE id=?""",
                    (now, cadence_id),
                )
            elif step == 2:
                conn.execute(
                    """UPDATE cadences SET m3_sent_at=?, status='completed', current_step=3,
                          updated_at=datetime('now')
                       WHERE id=?""",
                    (now, cadence_id),
                )

    # ── Reply / Bounce Handling ───────────────────────────────────────────

    def mark_replied(self, email: str) -> bool:
        """Pause the sequence for a prospect (they replied — human takes over)."""
        with _get_conn() as conn:
            cursor = conn.execute(
                "UPDATE cadences SET status='replied', updated_at=datetime('now') WHERE email=?",
                (email.lower(),),
            )
        if cursor.rowcount:
            logger.info("Paused cadence for %s (replied)", email)
            return True
        return False

    def mark_bounced(self, email: str) -> bool:
        """Mark a prospect as bounced — removes from active sequences."""
        with _get_conn() as conn:
            cursor = conn.execute(
                "UPDATE cadences SET status='bounced', updated_at=datetime('now') WHERE email=?",
                (email.lower(),),
            )
        return bool(cursor.rowcount)

    def pause(self, email: str) -> bool:
        """Manually pause a sequence."""
        with _get_conn() as conn:
            cursor = conn.execute(
                "UPDATE cadences SET status='paused', updated_at=datetime('now') WHERE email=?",
                (email.lower(),),
            )
        return bool(cursor.rowcount)

    # ── Stats ─────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Return summary stats for the current cadence state."""
        with _get_conn() as conn:
            status_counts = dict(conn.execute(
                "SELECT status, COUNT(*) FROM cadences GROUP BY status"
            ).fetchall())

            today_sends = self._daily_send_count(conn)

            step_counts = dict(conn.execute(
                "SELECT current_step, COUNT(*) FROM cadences WHERE status='active' GROUP BY current_step"
            ).fetchall())

            total_sent = conn.execute(
                "SELECT COUNT(*) FROM send_log WHERE status='sent'"
            ).fetchone()[0]

        return {
            "status_breakdown": status_counts,
            "today_sends": today_sends,
            "daily_limit": MAX_SENDS_PER_DAY,
            "active_by_step": {f"M{k+1}_pending": v for k, v in step_counts.items()},
            "total_sent_all_time": total_sent,
        }

    def list_cadences(self, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """List cadences, optionally filtered by status."""
        with _get_conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM cadences WHERE status=? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM cadences ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
        return [dict(r) for r in rows]

    def _daily_send_count(self, conn: Optional[sqlite3.Connection] = None) -> int:
        """Count sends that happened today (UTC)."""
        close_after = conn is None
        if conn is None:
            conn = _get_conn()
        count = conn.execute(
            "SELECT COUNT(*) FROM send_log WHERE status='sent' AND date(sent_at) = date('now')"
        ).fetchone()[0]
        if close_after:
            conn.close()
        return count


# ── Helpers ───────────────────────────────────────────────────────────────

def _fill_m2_m3_defaults(variables: Dict[str, str], template_name: str) -> Dict[str, str]:
    """Fill missing M2/M3 variables with reasonable defaults."""
    vars_copy = dict(variables)
    if template_name == "M2_EMAIL":
        vars_copy.setdefault("caso_similar", "una clínica en Colombia")
        vars_copy.setdefault("resultado_caso", "reducir 40% el tiempo en reportes operacionales")
        vars_copy.setdefault("fecha_propuesta", "esta semana")
    # M3_EMAIL only needs nombre + empresa, which should always be present
    return vars_copy


def _strip_html(html: str) -> str:
    """Very basic HTML tag stripper for preview display."""
    import re
    return re.sub(r"<[^>]+>", "", html).strip()
