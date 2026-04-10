"""
zoho_crm_service.py — Zoho CRM REST API Integration
=====================================================
Direct REST API calls to Zoho CRM v3 — bypasses the MCP connector
(which requires re-authentication and is unreliable).

Uses the same OAuth credentials already configured for Zoho Mail.
Required scopes (add to your existing Zoho OAuth app):
  ZohoCRM.modules.ALL
  ZohoCRM.settings.ALL

Key capabilities:
  - Create / upsert Leads and Accounts
  - List available Cadences
  - Enroll a GROUP of leads from the same company in one API call
  - Sync lead status back to Google Sheet

Zoho CRM API docs: https://www.zoho.com/crm/developer/docs/api/v3/

Usage:
    crm = ZohoCRMService.from_env()
    lead_ids = await crm.upsert_leads(contacts, account_name="CEMDE")
    await crm.enroll_in_cadence("CADENCE_ID", lead_ids, account_name="CEMDE")
"""

import logging
import httpx
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Zoho CRM API base — change to .eu / .in if on those data centers
ZOHO_CRM_API   = "https://www.zohoapis.com/crm/v3"
ZOHO_AUTH_URL  = "https://accounts.zoho.com/oauth/v2/token"


class ZohoCRMService:
    """
    Zoho CRM REST API client.

    All public methods are async. The access token is automatically
    refreshed when it expires.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        zoho_domain: str = "zoho.com",  # zoho.com | zoho.eu | zoho.in
    ):
        self.client_id     = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

        if "eu" in zoho_domain:
            self._auth_url = "https://accounts.zoho.eu/oauth/v2/token"
            self._api_base = "https://www.zohoapis.eu/crm/v3"
        elif "in" in zoho_domain:
            self._auth_url = "https://accounts.zoho.in/oauth/v2/token"
            self._api_base = "https://www.zohoapis.in/crm/v3"
        else:
            self._auth_url = ZOHO_AUTH_URL
            self._api_base = ZOHO_CRM_API

        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    # ── Constructors ──────────────────────────────────────────────────────

    @classmethod
    def from_env(cls) -> "ZohoCRMService":
        """Build from environment variables (same ones used by ZohoEmailService)."""
        import os
        return cls(
            client_id=os.environ["ZOHO_CLIENT_ID"],
            client_secret=os.environ["ZOHO_CLIENT_SECRET"],
            refresh_token=os.environ["ZOHO_REFRESH_TOKEN"],
            zoho_domain=os.environ.get("ZOHO_DOMAIN", "zoho.com"),
        )

    @property
    def available(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    # ── Auth ──────────────────────────────────────────────────────────────

    async def _get_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        if self._access_token and self._token_expiry and datetime.utcnow() < self._token_expiry:
            return self._access_token

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(self._auth_url, data={
                "grant_type":    "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
            })
            r.raise_for_status()
            data = r.json()

        if "access_token" not in data:
            raise RuntimeError(f"Zoho CRM token refresh failed: {data}")

        self._access_token = data["access_token"]
        self._token_expiry = datetime.utcnow() + timedelta(
            seconds=int(data.get("expires_in", 3600)) - 120
        )
        logger.info("Zoho CRM access token refreshed")
        return self._access_token

    async def _req(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Execute an authenticated CRM API request."""
        token = await self._get_token()
        url   = f"{self._api_base}/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type":  "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.request(method, url, json=json_data, params=params, headers=headers)
            if r.status_code == 204:
                return {}
            r.raise_for_status()
            return r.json()

    # ── Leads ─────────────────────────────────────────────────────────────

    async def search_leads(self, email: str) -> Optional[Dict]:
        """Find a Lead by email. Returns the first match or None."""
        data = await self._req("GET", "Leads/search", params={"email": email})
        records = data.get("data", [])
        return records[0] if records else None

    async def create_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a single Lead.

        Required keys: Last_Name, Email
        Recommended:   First_Name, Company, Phone, Lead_Source, Lead_Status,
                       linear_issue_id (custom field), azure_stage (custom field)
        """
        payload = {"data": [lead], "trigger": []}
        result  = await self._req("POST", "Leads", json_data=payload)
        records = result.get("data", [{}])
        record  = records[0]

        if record.get("code") == "SUCCESS":
            logger.info("Created lead %s → %s", lead.get("Email"), record["details"]["id"])
            return {"id": record["details"]["id"], "success": True}

        logger.warning("Lead creation issue for %s: %s", lead.get("Email"), record)
        return {"success": False, "detail": record}

    async def update_lead(self, lead_id: str, fields: Dict[str, Any]) -> bool:
        """Update specific fields on an existing Lead."""
        payload = {"data": [{**fields, "id": lead_id}]}
        result  = await self._req("PUT", "Leads", json_data=payload)
        record  = result.get("data", [{}])[0]
        ok = record.get("code") == "SUCCESS"
        if ok:
            logger.info("Updated lead %s: %s", lead_id, list(fields.keys()))
        else:
            logger.warning("Lead update failed %s: %s", lead_id, record)
        return ok

    async def upsert_leads(
        self,
        contacts: List[Dict[str, Any]],
        account_name: str = "",
        linear_issue_id: str = "",
        batch_id: str = "",
    ) -> List[str]:
        """
        Create-or-update Leads for a list of contacts (all from the same company).

        Each contact dict should have:
          email, nombre (first name), empresa (company), role (optional),
          phone (optional), linkedin_url (optional)

        Returns list of Zoho Lead IDs (for cadence enrollment).
        """
        lead_ids = []

        for c in contacts:
            email = (c.get("email") or c.get("Email") or "").strip().lower()
            if not email:
                logger.warning("Skipping contact with no email: %s", c)
                continue

            # Check if already exists
            existing = await self.search_leads(email)
            if existing:
                lead_id = existing["id"]
                # Update with latest info if available
                updates: Dict[str, Any] = {}
                if linear_issue_id:
                    updates["linear_issue_id"] = linear_issue_id
                if batch_id:
                    updates["batch_id"] = batch_id
                if updates:
                    await self.update_lead(lead_id, updates)
                lead_ids.append(lead_id)
                logger.info("Reusing existing lead %s → %s", email, lead_id)
                continue

            # Build lead payload
            nombre  = c.get("nombre") or c.get("First Name") or c.get("name") or ""
            empresa = c.get("empresa") or c.get("Business") or account_name or ""
            role    = c.get("role") or c.get("Role") or c.get("cargo") or ""
            phone   = c.get("phone") or c.get("Phone") or ""
            li_url  = c.get("LinkedIn URL") or c.get("linkedin_url") or ""

            lead_payload: Dict[str, Any] = {
                "Last_Name":    nombre.split()[-1] if nombre else email.split("@")[0],
                "First_Name":   nombre.split()[0] if nombre and " " in nombre else nombre,
                "Email":        email,
                "Company":      empresa,
                "Phone":        phone,
                "Title":        role,
                "Lead_Source":  c.get("data_source", "Email"),
                "Lead_Status":  "New",
            }

            # Custom fields (must be created in Zoho CRM field settings first)
            if li_url:
                lead_payload["LinkedIn_URL"] = li_url
            if linear_issue_id:
                lead_payload["linear_issue_id"] = linear_issue_id
            if batch_id:
                lead_payload["batch_id"] = batch_id
            if account_name:
                lead_payload["Account_Name"] = account_name

            result = await self.create_lead(lead_payload)
            if result.get("success"):
                lead_ids.append(result["id"])

        logger.info("upsert_leads: %d contacts → %d lead IDs", len(contacts), len(lead_ids))
        return lead_ids

    # ── Accounts (Companies) ──────────────────────────────────────────────

    async def search_account(self, name: str) -> Optional[Dict]:
        """Find an Account by company name."""
        data = await self._req("GET", "Accounts/search", params={"criteria": f"Account_Name:equals:{name}"})
        records = data.get("data", [])
        return records[0] if records else None

    async def upsert_account(self, company: Dict[str, Any]) -> str:
        """
        Create or return existing Account (company) in Zoho CRM.

        company dict keys: name (required), website, city, nit, pathology_tag,
                           region_tag, tier_icp, phone, linear_sft_issue
        Returns the Account ID.
        """
        name = company.get("name") or company.get("Business Name") or ""
        if not name:
            raise ValueError("company must have 'name'")

        existing = await self.search_account(name)
        if existing:
            return existing["id"]

        payload = {"data": [{
            "Account_Name": name,
            "Website":      company.get("website") or company.get("Website") or "",
            "Phone":        company.get("phone") or company.get("Phone") or "",
            "Billing_City": company.get("city") or company.get("City") or "",
            "Description":  company.get("description") or "",
            # Custom fields
            "NIT":              company.get("NIT") or company.get("nit") or "",
            "pathology_tag":    company.get("pathology_tag") or "",
            "region_tag":       company.get("region_tag") or "",
            "tier_icp":         company.get("tier_icp") or "",
            "linear_sft_issue": company.get("linear_sft_issue") or "",
        }], "trigger": []}

        result  = await self._req("POST", "Accounts", json_data=payload)
        records = result.get("data", [{}])
        record  = records[0]

        if record.get("code") == "SUCCESS":
            account_id = record["details"]["id"]
            logger.info("Created Account '%s' → %s", name, account_id)
            return account_id

        raise RuntimeError(f"Account creation failed for '{name}': {record}")

    # ── Cadences ──────────────────────────────────────────────────────────

    async def list_cadences(self) -> List[Dict[str, Any]]:
        """
        List all Cadences configured in Zoho CRM.

        Returns list of {id, name, status, module, created_time}
        Use the 'id' to enroll leads.
        """
        data    = await self._req("GET", "Cadences")
        records = data.get("data", [])
        cadences = []
        for r in records:
            cadences.append({
                "id":           r.get("id"),
                "name":         r.get("Name") or r.get("name"),
                "status":       r.get("Status") or r.get("status"),
                "module":       r.get("Module") or r.get("module"),
                "created_time": r.get("Created_Time"),
            })
        logger.info("Found %d cadences in Zoho CRM", len(cadences))
        return cadences

    async def enroll_in_cadence(
        self,
        cadence_id: str,
        lead_ids: List[str],
        account_name: str = "",
        skip_already_enrolled: bool = True,
    ) -> Dict[str, Any]:
        """
        Enroll a GROUP of leads into a Zoho CRM Cadence.

        This is the key "group enrollment" feature: instead of enrolling
        5 leads individually, you call this once with all 5 IDs and Zoho
        tracks them as a group under the same account/cadence.

        Args:
            cadence_id:            Zoho cadence ID (from list_cadences())
            lead_ids:              List of Zoho Lead IDs to enroll
            account_name:          Company name for logging / tracking
            skip_already_enrolled: If True, silently skip leads already active

        Returns:
            {"enrolled": N, "already_active": N, "failed": N, "details": [...]}
        """
        if not lead_ids:
            return {"enrolled": 0, "already_active": 0, "failed": 0, "details": []}

        # Zoho CRM v3 cadence subscribe endpoint
        # Enrolls all records in one API call
        payload = {
            "record_ids": lead_ids,
        }

        try:
            result = await self._req(
                "POST",
                f"Cadences/{cadence_id}/actions/subscribe",
                json_data=payload,
            )
        except httpx.HTTPStatusError as e:
            logger.error("Cadence enrollment failed: %s", e.response.text)
            return {
                "enrolled": 0, "already_active": 0,
                "failed": len(lead_ids),
                "error": str(e),
            }

        enrolled = already_active = failed = 0
        details  = []

        for record in result.get("data", []):
            code   = record.get("code", "")
            lead_id = record.get("details", {}).get("id", "")

            if code == "SUCCESS":
                enrolled += 1
                details.append({"id": lead_id, "status": "enrolled"})
            elif code == "ALREADY_ENROLLED" and skip_already_enrolled:
                already_active += 1
                details.append({"id": lead_id, "status": "already_active"})
            else:
                failed += 1
                details.append({"id": lead_id, "status": "failed", "code": code})

        logger.info(
            "Cadence %s — account '%s': enrolled=%d already_active=%d failed=%d",
            cadence_id, account_name, enrolled, already_active, failed,
        )
        return {
            "enrolled":      enrolled,
            "already_active": already_active,
            "failed":         failed,
            "details":        details,
        }

    async def unenroll_from_cadence(self, cadence_id: str, lead_ids: List[str]) -> bool:
        """Remove leads from an active cadence (e.g. when they reply)."""
        payload = {"record_ids": lead_ids}
        try:
            await self._req("POST", f"Cadences/{cadence_id}/actions/unsubscribe", json_data=payload)
            logger.info("Unenrolled %d leads from cadence %s", len(lead_ids), cadence_id)
            return True
        except Exception as e:
            logger.error("Unenroll failed: %s", e)
            return False

    # ── Lead Status Sync ──────────────────────────────────────────────────

    async def update_lead_status(self, lead_id: str, status: str, azure_stage: str = "") -> bool:
        """
        Update Lead_Status (and optionally azure_stage custom field).

        Status values: New | Contacted | Responded | Closed Won | Closed Lost
        Azure stage:   Frio | M1_Enviado | LI_Conectado | Respondio | Won | Lost
        """
        fields: Dict[str, Any] = {"Lead_Status": status}
        if azure_stage:
            fields["azure_stage"] = azure_stage
        return await self.update_lead(lead_id, fields)

    async def bulk_update_status(
        self,
        lead_ids: List[str],
        status: str,
        azure_stage: str = "",
    ) -> Dict[str, int]:
        """Update the same status on multiple leads (e.g. after M1 batch send)."""
        ok = fail = 0
        for lead_id in lead_ids:
            success = await self.update_lead_status(lead_id, status, azure_stage)
            if success:
                ok += 1
            else:
                fail += 1
        return {"updated": ok, "failed": fail}

    # ── Convenience: Full Company Onboard ────────────────────────────────

    async def onboard_company_to_cadence(
        self,
        company: Dict[str, Any],
        contacts: List[Dict[str, Any]],
        cadence_id: str,
        linear_sft_issue: str = "",
        batch_id: str = "",
    ) -> Dict[str, Any]:
        """
        Full onboarding of a company + its contacts into a Zoho CRM cadence.

        Steps:
        1. Create/find Account for the company
        2. Create/find Leads for each contact
        3. Enroll all leads into the cadence as a group

        Args:
            company:          Dict with company info (name, city, nit, pathology_tag, etc.)
            contacts:         List of contact dicts (email, nombre, role, linkedin_url, etc.)
            cadence_id:       Zoho CRM Cadence ID
            linear_sft_issue: AIM-XXX for traceability
            batch_id:         AIM-XXX of the batch issue

        Returns full summary for logging to Google Sheet.
        """
        account_name = company.get("name") or company.get("Business Name") or ""

        # Step 1: Account
        try:
            account_id = await self.upsert_account({
                **company,
                "linear_sft_issue": linear_sft_issue,
            })
        except Exception as e:
            logger.error("Account upsert failed for '%s': %s", account_name, e)
            return {"success": False, "error": str(e), "account_name": account_name}

        # Step 2: Leads (only contacts with email)
        email_contacts = [c for c in contacts if (c.get("email") or c.get("Email"))]
        lead_ids = await self.upsert_leads(
            email_contacts,
            account_name=account_name,
            linear_issue_id=linear_sft_issue,
            batch_id=batch_id,
        )

        if not lead_ids:
            return {
                "success":    True,
                "account_id": account_id,
                "lead_ids":   [],
                "cadence":    {"enrolled": 0, "message": "No contacts with email"},
            }

        # Step 3: Group enrollment in cadence
        cadence_result = await self.enroll_in_cadence(
            cadence_id=cadence_id,
            lead_ids=lead_ids,
            account_name=account_name,
        )

        return {
            "success":      True,
            "account_name": account_name,
            "account_id":   account_id,
            "lead_ids":     lead_ids,
            "cadence":      cadence_result,
            "linear_issue": linear_sft_issue,
            "batch_id":     batch_id,
        }

    # ── Utils ─────────────────────────────────────────────────────────────

    async def get_custom_fields(self, module: str = "Leads") -> List[Dict]:
        """List custom fields for a module — useful for setup verification."""
        data = await self._req("GET", f"settings/fields", params={"module": module})
        fields = []
        for f in data.get("fields", []):
            if f.get("custom_field"):
                fields.append({
                    "api_name":   f.get("api_name"),
                    "field_label": f.get("field_label"),
                    "data_type":  f.get("data_type"),
                })
        return fields

    async def verify_connection(self) -> Dict[str, Any]:
        """Quick health check — returns org info if credentials are valid."""
        try:
            data = await self._req("GET", "org")
            org  = data.get("org", [{}])[0] if data.get("org") else {}
            return {
                "connected":  True,
                "org_name":   org.get("company_name"),
                "org_id":     org.get("id"),
                "country":    org.get("country"),
                "time_zone":  org.get("time_zone"),
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}
