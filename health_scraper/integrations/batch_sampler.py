"""
batch_sampler.py — Daily Prospecting Batch Sampler
====================================================
Selects 50 NEW businesses from the Google Sheet for each prospecting batch.

Key guarantee: NEVER selects a company that was already in a previous batch.
Tracks batches via the 'batch_id' column in the Businesses tab.

Segmentation filters:
  - pathology_tag: Cardio | Mental | Pain | Special | EndoMeta | Rehab
  - region_tag:    Bogota | Antioquia | CostaCaribe | Suroccidente | Otros |
                   Argentina | Chile
  - tier_icp:      Enterprise | Professional | Essential
  - country:       Colombia | Argentina | Chile

Usage:
    sampler = BatchSampler(sheets_svc, linear_svc)

    # See what's available before committing
    preview = sampler.preview(pathology_filter="Cardio", limit=50)

    # Select and lock 50 new businesses for today's batch
    batch = sampler.create_batch(
        batch_label="Leads - Abril 9-10 de 2026",
        pathology_filter="Cardio",   # optional, None = all pathologies
        region_filter=None,          # optional
        limit=50,
    )
    # batch.linear_issue_body → markdown to paste into Linear batch issue
    # batch.businesses        → list of selected businesses
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from health_scraper.integrations.sheets_service import SheetsService, _now

logger = logging.getLogger(__name__)

# ── Segment constants ──────────────────────────────────────────────────────

PATHOLOGY_TAGS = {
    "Cardio":   "🫀 Cardiology & Cardiovascular Care",
    "Mental":   "🧠 Mental Health & Psychiatry",
    "Pain":     "🦴 Pain Management, Rheumatology & Immunology",
    "Special":  "🎗️ Specialized Care (Oncology & Respiratory)",
    "EndoMeta": "💊 Endocrinology, Metabolism & Nephrology",
    "Rehab":    "♿ Rehabilitation & Physical Therapy",
    "General":  "🏥 General / Multi-specialty",
    "Lab":      "🔬 Laboratory / Diagnostics",
    "EPS":      "🏢 EPS / Aseguradora",
}

REGION_TAGS = {
    "Bogota":       "Bogotá / Sabana",
    "Antioquia":    "Antioquia / Eje Cafetero",
    "CostaCaribe":  "Costa Caribe (Barranquilla, Cartagena, Santa Marta, Montería)",
    "Suroccidente": "Suroccidente (Cali, Pasto, Cauca)",
    "Otros":        "Otros / Localidades específicas",
    "Argentina":    "Argentina",
    "Chile":        "Chile",
}

# Agent columns to add to Businesses tab (parallel to AGENT_COLUMNS in sheets_service)
BUSINESS_AGENT_COLUMNS = [
    "batch_id",             # AIM-XXX — which batch selected this company
    "prospected_at",        # ISO timestamp
    "prospecting_cycle",    # e.g. "Ciclo10"
    "linear_sft_issue",     # AIM-XXX of the SFT issue
    "pathology_tag",        # Cardio | Mental | Pain | ...
    "region_tag",           # Bogota | Antioquia | ...
    "tier_icp",             # Enterprise | Professional | Essential
    "contacts_count",       # int — contacts identified
    "emails_sent",          # int — M1+M2+M3 sent
    "li_connections_sent",  # int — LinkedIn connections sent
    "zoho_account_id",      # Zoho CRM Account ID
]


# ── Data classes ───────────────────────────────────────────────────────────

@dataclass
class BatchResult:
    """Result of a batch sampling operation."""
    batch_label:    str
    batch_id:       str          # AIM-XXX (set after Linear issue is created)
    selected_count: int
    businesses:     List[Dict[str, Any]] = field(default_factory=list)
    pathology_dist: Dict[str, int] = field(default_factory=dict)
    region_dist:    Dict[str, int] = field(default_factory=dict)
    locked:         bool = False   # True after written back to Sheet

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Batch: {self.batch_label}",
            f"Selected: {self.selected_count} businesses",
            f"Pathologies: {self.pathology_dist}",
            f"Regions: {self.region_dist}",
            f"Locked in Sheet: {self.locked}",
        ]
        return "\n".join(lines)

    def linear_issue_body(self) -> str:
        """
        Generate the markdown body for the Linear Batch Issue (like AIM-412).
        Grouped by pathology and country/region.
        """
        from collections import defaultdict
        groups: Dict[str, List[Dict]] = defaultdict(list)

        for biz in self.businesses:
            tag    = biz.get("pathology_tag") or "General"
            region = biz.get("region_tag") or "Otros"
            key    = f"{tag}|{region}"
            groups[key].append(biz)

        lines = [f"# {self.batch_label}\n"]

        # Group by pathology first
        by_pathology: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
        for biz in self.businesses:
            p = biz.get("pathology_tag") or "General"
            r = biz.get("region_tag") or "Otros"
            by_pathology[p][r].append(biz)

        for pathology, regions in sorted(by_pathology.items()):
            emoji_name = PATHOLOGY_TAGS.get(pathology, pathology)
            lines.append(f"\n## {emoji_name}\n")

            for region, bizs in sorted(regions.items()):
                region_name = REGION_TAGS.get(region, region)
                lines.append(f"\n### {region_name}\n")
                for b in bizs:
                    name       = b.get("Business Name") or b.get("name") or "—"
                    sft_issue  = b.get("linear_sft_issue") or ""
                    city       = b.get("City") or b.get("city") or ""
                    if sft_issue:
                        lines.append(f"- [{sft_issue}] {name}" + (f" — {city}" if city else ""))
                    else:
                        lines.append(f"- {name}" + (f" — {city}" if city else ""))

        lines.append(f"\n---\n")
        lines.append(f"## Métricas del Batch\n")
        lines.append(f"- **Total empresas:** {self.selected_count}")
        lines.append(f"- Emails enviados: 0 / ~{self.selected_count * 3} esperados")
        lines.append(f"- Conexiones LinkedIn enviadas: 0 / ~{self.selected_count * 3} esperadas")
        lines.append(f"- Replies recibidos: 0\n")

        lines.append(f"## Distribución por Patología\n")
        for p, count in sorted(self.pathology_dist.items()):
            lines.append(f"- {p}: {count}")

        return "\n".join(lines)


# ── BatchSampler ───────────────────────────────────────────────────────────

class BatchSampler:
    """
    Selects NEW businesses from the Google Sheet for each prospecting batch.

    Anti-duplication: a business is considered "already prospected" if its
    'batch_id' column is non-empty in the Businesses tab.
    """

    def __init__(self, sheets: SheetsService):
        self.sheets = sheets

    # ── Setup ─────────────────────────────────────────────────────────────

    def ensure_business_columns(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Add BUSINESS_AGENT_COLUMNS to the Businesses tab if not already there.
        Safe to run multiple times.
        """
        ws      = self.sheets._ws("Businesses")
        headers = ws.row_values(1)  # Businesses tab has headers on row 1

        added    = []
        existing = []

        for col_name in BUSINESS_AGENT_COLUMNS:
            if col_name in headers:
                existing.append(col_name)
            else:
                if not dry_run:
                    next_col = len(headers) + 1
                    ws.update_cell(1, next_col, col_name)
                    headers.append(col_name)
                added.append(col_name)

        if added and not dry_run:
            logger.info("Added batch columns to Businesses: %s", added)

        return {"added": added, "existing": existing}

    # ── Querying ──────────────────────────────────────────────────────────

    def get_available_businesses(
        self,
        pathology_filter: Optional[str] = None,
        region_filter: Optional[str] = None,
        tier_filter: Optional[str] = None,
        country_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return businesses from the Sheet that have NOT been prospected yet.

        Filters (all optional):
          pathology_filter: "Cardio" | "Mental" | "Pain" | "Special" | "EndoMeta" | "Rehab"
          region_filter:    "Bogota" | "Antioquia" | "CostaCaribe" | "Suroccidente" | ...
          tier_filter:      "Enterprise" | "Professional" | "Essential"
          country_filter:   "Colombia" | "Argentina" | "Chile"
        """
        ws   = self.sheets._ws("Businesses")
        rows = ws.get_all_records(default_blank="")

        available = []
        for row in rows:
            # Skip if already in a batch
            if row.get("batch_id", "").strip():
                continue

            # Must have a business name
            name = row.get("Business Name") or row.get("name") or row.get("Nombre") or ""
            if not name.strip():
                continue

            # Apply filters
            if pathology_filter:
                if row.get("pathology_tag", "").strip() != pathology_filter:
                    continue
            if region_filter:
                if row.get("region_tag", "").strip() != region_filter:
                    continue
            if tier_filter:
                if row.get("tier_icp", "").strip() != tier_filter:
                    continue
            if country_filter:
                # Derive country from region_tag or Country column
                country_col = row.get("Country") or row.get("Pais") or ""
                region_tag  = row.get("region_tag") or ""
                derived_country = _derive_country(region_tag, country_col)
                if derived_country.lower() != country_filter.lower():
                    continue

            available.append(row)

        logger.info(
            "get_available_businesses: %d available (pathology=%s region=%s)",
            len(available), pathology_filter, region_filter
        )
        return available

    def preview(
        self,
        pathology_filter: Optional[str] = None,
        region_filter: Optional[str] = None,
        tier_filter: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Preview what a batch would look like WITHOUT committing anything to the Sheet.

        Returns stats on available businesses by segment.
        """
        available = self.get_available_businesses(pathology_filter, region_filter, tier_filter)

        # Count by segment
        by_pathology: Dict[str, int] = {}
        by_region:    Dict[str, int] = {}
        for biz in available:
            p = biz.get("pathology_tag") or "Unknown"
            r = biz.get("region_tag")    or "Unknown"
            by_pathology[p] = by_pathology.get(p, 0) + 1
            by_region[r]    = by_region.get(r, 0) + 1

        sample = available[:limit] if len(available) >= limit else available

        return {
            "total_available": len(available),
            "would_select":    len(sample),
            "by_pathology":    by_pathology,
            "by_region":       by_region,
            "sample_names":    [b.get("Business Name") or b.get("name") for b in sample[:10]],
            "ready":           len(available) >= limit,
        }

    # ── Batch Creation ────────────────────────────────────────────────────

    def create_batch(
        self,
        batch_label: str,
        batch_id: str = "",
        pathology_filter: Optional[str] = None,
        region_filter: Optional[str] = None,
        tier_filter: Optional[str] = None,
        country_filter: Optional[str] = None,
        limit: int = 50,
        randomize: bool = True,
        cycle_name: str = "",
    ) -> BatchResult:
        """
        Select up to `limit` NEW businesses and lock them in the Sheet.

        Steps:
        1. Fetch all available (not yet prospected) businesses
        2. Apply filters
        3. Randomize or take top-N by ICP score
        4. Write batch_id + prospected_at to each selected row in the Sheet
        5. Return BatchResult with full data for Linear issue creation

        Args:
            batch_label:  Human-readable label (e.g. "Leads - Abril 9-10 de 2026")
            batch_id:     Linear batch issue ID (e.g. "AIM-443") — set after creating the issue
            pathology_filter: Optional pathology focus for this batch
            region_filter:    Optional region focus
            tier_filter:      Optional ICP tier
            country_filter:   Optional country filter
            limit:        Max businesses to select (default 50)
            randomize:    If True, shuffle before selecting (avoids always picking same segment)
            cycle_name:   e.g. "Ciclo10"

        Returns: BatchResult (with .linear_issue_body() for Linear)
        """
        available = self.get_available_businesses(
            pathology_filter, region_filter, tier_filter, country_filter
        )

        if not available:
            logger.warning("No businesses available for batch (filters: %s %s)", pathology_filter, region_filter)
            return BatchResult(
                batch_label=batch_label, batch_id=batch_id,
                selected_count=0, locked=False
            )

        if randomize:
            random.shuffle(available)

        selected = available[:limit]

        # Count distributions
        pathology_dist: Dict[str, int] = {}
        region_dist:    Dict[str, int] = {}
        for biz in selected:
            p = biz.get("pathology_tag") or "Unknown"
            r = biz.get("region_tag")    or "Unknown"
            pathology_dist[p] = pathology_dist.get(p, 0) + 1
            region_dist[r]    = region_dist.get(r, 0) + 1

        # Lock in Sheet — write batch columns to each selected row
        self._lock_batch_in_sheet(selected, batch_id, cycle_name)

        result = BatchResult(
            batch_label    = batch_label,
            batch_id       = batch_id,
            selected_count = len(selected),
            businesses     = selected,
            pathology_dist = pathology_dist,
            region_dist    = region_dist,
            locked         = True,
        )

        logger.info(
            "Batch created: %d businesses selected, locked in Sheet. Pathologies: %s",
            len(selected), pathology_dist
        )
        return result

    def _lock_batch_in_sheet(
        self,
        businesses: List[Dict[str, Any]],
        batch_id: str,
        cycle_name: str,
    ) -> None:
        """Write batch metadata to each selected business row in the Sheet."""
        ws      = self.sheets._ws("Businesses")
        records = ws.get_all_records(default_blank="")
        headers = ws.row_values(1)
        now     = _now()

        for biz in businesses:
            biz_name = biz.get("Business Name") or biz.get("name") or ""
            biz_id   = biz.get("Business ID") or biz.get("business_id") or ""

            # Find the row in the Sheet
            for i, row in enumerate(records):
                row_name = row.get("Business Name") or row.get("name") or ""
                row_id   = row.get("Business ID") or row.get("business_id") or ""

                match = (biz_id and row_id == biz_id) or (biz_name and row_name == biz_name)
                if not match:
                    continue

                row_num = i + 2  # +1 for 0-index, +1 for header row

                updates = {
                    "batch_id":          batch_id,
                    "prospected_at":     now,
                    "prospecting_cycle": cycle_name,
                }

                self.sheets._write_agent_cols(ws, headers, row_num, updates)
                break

    def update_sft_issue(self, business_name: str, sft_issue_id: str) -> bool:
        """
        After creating the SFT Linear issue for a business, write its ID
        back to the Businesses tab.
        """
        ws      = self.sheets._ws("Businesses")
        records = ws.get_all_records(default_blank="")
        headers = ws.row_values(1)

        for i, row in enumerate(records):
            name = row.get("Business Name") or row.get("name") or ""
            if name.strip().lower() == business_name.strip().lower():
                row_num = i + 2
                self.sheets._write_agent_cols(ws, headers, row_num, {
                    "linear_sft_issue": sft_issue_id,
                })
                logger.info("Updated SFT issue for '%s' → %s", business_name, sft_issue_id)
                return True

        logger.warning("Business '%s' not found in Sheet for SFT update", business_name)
        return False

    # ── Stats ─────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """
        Return overall prospecting stats from the Businesses tab.
        Useful for the weekly report.
        """
        ws   = self.sheets._ws("Businesses")
        rows = ws.get_all_records(default_blank="")

        total     = len([r for r in rows if (r.get("Business Name") or r.get("name"))])
        prospected = len([r for r in rows if r.get("batch_id", "").strip()])
        remaining = total - prospected

        by_pathology: Dict[str, Dict[str, int]] = {}
        for row in rows:
            if not (row.get("Business Name") or row.get("name")):
                continue
            p = row.get("pathology_tag") or "Unknown"
            if p not in by_pathology:
                by_pathology[p] = {"total": 0, "prospected": 0, "remaining": 0}
            by_pathology[p]["total"] += 1
            if row.get("batch_id", "").strip():
                by_pathology[p]["prospected"] += 1
            else:
                by_pathology[p]["remaining"] += 1

        # Batch history
        batches: Dict[str, int] = {}
        for row in rows:
            bid = row.get("batch_id", "").strip()
            if bid:
                batches[bid] = batches.get(bid, 0) + 1

        return {
            "total_businesses":  total,
            "prospected":        prospected,
            "remaining":         remaining,
            "coverage_pct":      round(prospected / total * 100, 1) if total else 0,
            "by_pathology":      by_pathology,
            "batches":           batches,
            "batch_count":       len(batches),
        }


# ── Helpers ────────────────────────────────────────────────────────────────

def _derive_country(region_tag: str, country_col: str) -> str:
    """Infer country from region_tag or explicit country column."""
    if country_col:
        return country_col.strip()
    if region_tag in ("Argentina",):
        return "Argentina"
    if region_tag in ("Chile",):
        return "Chile"
    return "Colombia"


def build_sft_issue_description(
    company: Dict[str, Any],
    contacts: List[Dict[str, Any]],
) -> str:
    """
    Generate the Linear SFT issue description (like AIM-389).
    Uses the canonical template with all sections.
    """
    name       = company.get("Business Name") or company.get("name") or "—"
    nit        = company.get("NIT") or company.get("nit") or "—"
    city       = company.get("City") or company.get("city") or "—"
    pathology  = PATHOLOGY_TAGS.get(company.get("pathology_tag") or "", "—")
    tier       = company.get("tier_icp") or "—"
    website    = company.get("Website") or company.get("website") or "—"
    phone      = company.get("Phone") or company.get("phone") or "—"
    summary    = company.get("description") or company.get("summary") or "—"

    # Build contacts table
    contact_rows = ""
    li_rows = ""
    email_rows = ""
    touch_rows = ""

    for c in contacts:
        fn    = c.get("First Name") or c.get("nombre") or ""
        ln    = c.get("Last Name") or ""
        email = c.get("email") or c.get("Email") or ""
        li    = c.get("LinkedIn URL") or ""
        role  = c.get("role") or c.get("Role") or ""
        phone_c = c.get("Phone") or c.get("phone") or ""
        notes = c.get("NOTAS") or ""

        contact_rows += f"| {fn} | {ln} | {email} | {li} | {name} | {role} | {phone_c} | {notes} |\n"

        if li:
            li_rows += f"| {fn} {ln} | {role} | ☐ | - [ ]  | - [ ]  | - [ ]  | |\n"
        if email:
            email_rows += f"| {fn} {ln} | {email} | - [ ]  | - [ ]  | ☐ | ☐ | ☐ | Frío |\n"

    touch_rows = """| D0 | Email | M1 enviado desde cadencia Zoho | - [ ]  | | |
| D1 | LinkedIn | Conexión enviada | - [ ]  | | |
| D2 | LinkedIn | Mensaje D2 (si aceptó) | - [ ]  | | |
| D4 | Email | M2 follow-up enviado | - [ ]  | | |
| D6 | LinkedIn | Mensaje con Calendly CEO | - [ ]  | | |
| D8 | Email | M3 breakup enviado | - [ ]  | | |
| D9 | WhatsApp/Llamada | Último intento | - [ ]  | | |"""

    return f"""### 🎯 Objetivo del Día

Ejecutar prospección omnicanal. Máximo 15 contactos por empresa.

{name} — {summary}

---

## 🏥 {name}

**NIT:** {nit}
**Ciudad:** {city}
**Especialidad:** {pathology}
**Tier ICP:** {tier}
**Website:** {website}
**Teléfono principal:** {phone}

---

## 👥 Contactos Objetivo

| First Name | Last Name | Business Email | LinkedIn | Business | Role | Phone | NOTES |
| -- | -- | -- | -- | -- | -- | -- | -- |
{contact_rows.strip()}

---

## 🔗 LinkedIn — Seguimiento de Conexiones

| Nombre | Cargo | Conexión enviada | Aceptó | Mensaje D2 enviado | Respondió | Fecha |
| -- | -- | -- | -- | -- | -- | -- |
{li_rows.strip() or "| — | — | ☐ | | | | |"}

**Métricas LinkedIn esta empresa:**
* Conexiones enviadas: `__`
* Aceptaron: `__`
* Respondieron mensaje: `__`

---

## 📧 Email — Cadencia Zoho

| Contacto | Email | M1 enviado | M1 abrió | M1 respondió | M2 enviado | M3 enviado | Estado |
| -- | -- | -- | -- | -- | -- | -- | -- |
{email_rows.strip() or "| — | — | - [ ]  | - [ ]  | ☐ | ☐ | ☐ | Frío |"}

---

## 🔄 Ciclo de 9 Toques — Estado

| Día | Canal | Acción | ✓ | Fecha | Notas |
| -- | -- | -- | -- | -- | -- |
{touch_rows}

---

## 🗄️ CRM — Sincronización

### Zoho CRM
- [ ] Cuenta creada en Zoho CRM
- [ ] Contactos añadidos y vinculados a la cuenta
- [ ] Contactos añadidos a cadencia "B2B IPS Ciclo 9 Toques"
- [ ] Stage actualizado: `Frío → Contactado → Respondió → Demo → Won/Lost`

### Google Sheet (aimedic_crm)
- [ ] Fila añadida en Contacts con todos los campos
- [ ] Empresa añadida en Businesses
- [ ] Interacciones logueadas en Interactions
- [ ] Sincronización Zoho verificada

---

## 📊 Resultado Final

**Stage actual:** `Frío`
**Próximo paso:** M1 email + LinkedIn connections D0-D1

**Notas GTM:**

---

## 🔗 Links

* Zoho CRM Account: —
* Google Sheet: https://docs.google.com/spreadsheets/d/1jBcTaANZTubNk3FWMnLdHFHyZhD31WTYIXe38g7eo9g
* Calendly CEO: https://calendar.app.google/iwNTpueCort26EuNA
"""
