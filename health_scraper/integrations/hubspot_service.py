"""
HubSpot CRM Integration Service
=================================
Integrates with HubSpot API v3 for company and contact management.

HubSpot API docs: https://developers.hubspot.com/docs/api/crm

Setup:
1. Go to HubSpot → Settings → Integrations → Private Apps
2. Create a new Private App with scopes:
   - crm.objects.companies.read
   - crm.objects.companies.write
   - crm.objects.contacts.read
   - crm.objects.contacts.write
   - crm.objects.deals.read
   - crm.objects.deals.write
3. Copy the access token and add to .env as HUBSPOT_ACCESS_TOKEN
"""

import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

HUBSPOT_API_BASE = "https://api.hubapi.com"


# ── Pydantic Models for HubSpot Company fields ───────────────────────

class HubSpotCompanyInput(BaseModel):
    """
    Maps to HubSpot Company properties.
    Field names match HubSpot's internal property names.
    """
    # Required / Common
    name: str = Field(..., description="Nombre de la empresa")
    domain: Optional[str] = Field(None, description="Dominio web (ej: www.subredsur.gov.co)")

    # Owner
    hubspot_owner_id: Optional[str] = Field(None, description="ID del propietario en HubSpot")

    # Classification
    industry: Optional[str] = Field(None, description="Sector (ej: 'HEALTH_CARE')")
    type: Optional[str] = Field(None, description="Tipo: PROSPECT, CUSTOMER, PARTNER, etc.")

    # Location
    city: Optional[str] = Field(None, description="Ciudad")
    state: Optional[str] = Field(None, description="Estado o región")
    zip: Optional[str] = Field(None, description="Código postal")
    country: Optional[str] = Field(None, description="País")

    # Details
    numberofemployees: Optional[int] = Field(None, description="Número de empleados")
    annualrevenue: Optional[float] = Field(None, description="Ingresos anuales")
    timezone: Optional[str] = Field(None, description="Zona horaria")
    description: Optional[str] = Field(None, description="Descripción de la empresa")
    linkedin_company_page: Optional[str] = Field(None, description="LinkedIn de la empresa")
    phone: Optional[str] = Field(None, description="Teléfono")
    website: Optional[str] = Field(None, description="Sitio web")

    # Custom - NIT (Colombian tax ID)
    nit: Optional[str] = Field(None, description="NIT de la empresa")


# Mapping of Spanish industry names to HubSpot industry codes
INDUSTRY_MAP = {
    "salud": "HEALTH_CARE",
    "salud, bienestar y fitness": "HEALTH_CARE",
    "tecnología": "INFORMATION_TECHNOLOGY_AND_SERVICES",
    "educación": "EDUCATION_MANAGEMENT",
    "gobierno": "GOVERNMENT_ADMINISTRATION",
    "finanzas": "FINANCIAL_SERVICES",
    "legal": "LEGAL_SERVICES",
    "construcción": "CONSTRUCTION",
    "manufactura": "INDUSTRIAL_AUTOMATION",
    "retail": "RETAIL",
    "telecomunicaciones": "TELECOMMUNICATIONS",
}

# Mapping of Spanish type names to HubSpot type values
TYPE_MAP = {
    "cliente potencial": "PROSPECT",
    "prospect": "PROSPECT",
    "cliente": "CUSTOMER",
    "customer": "CUSTOMER",
    "partner": "PARTNER",
    "socio": "PARTNER",
    "vendor": "VENDOR",
    "proveedor": "VENDOR",
    "otro": "OTHER",
}


class HubSpotService:
    """Service for interacting with HubSpot CRM API v3"""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self, method: str, endpoint: str, json_data: Optional[Dict] = None, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute an HTTP request to HubSpot API"""
        url = f"{HUBSPOT_API_BASE}{endpoint}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method, url, json=json_data, params=params, headers=self.headers
            )
            if response.status_code == 409:
                # Conflict = company already exists
                return {"conflict": True, "detail": response.json()}
            response.raise_for_status()
            return response.json() if response.content else {}

    # ── Companies ─────────────────────────────────────────────────────

    async def create_company(self, company: HubSpotCompanyInput) -> Dict[str, Any]:
        """
        Create a company in HubSpot CRM.

        Maps Spanish field names to HubSpot property names.
        Returns the created company record.
        """
        properties: Dict[str, Any] = {}

        # Map fields to HubSpot properties
        if company.name:
            properties["name"] = company.name
        if company.domain:
            properties["domain"] = company.domain.replace("www.", "").replace("http://", "").replace("https://", "")
        if company.hubspot_owner_id:
            properties["hubspot_owner_id"] = company.hubspot_owner_id
        if company.industry:
            # Convert Spanish industry name to HubSpot code
            industry_code = INDUSTRY_MAP.get(company.industry.lower(), company.industry)
            properties["industry"] = industry_code
        if company.type:
            type_code = TYPE_MAP.get(company.type.lower(), company.type)
            properties["type"] = type_code
        if company.city:
            properties["city"] = company.city
        if company.state:
            properties["state"] = company.state
        if company.zip:
            properties["zip"] = company.zip
        if company.country:
            properties["country"] = company.country or "Colombia"
        if company.numberofemployees is not None:
            properties["numberofemployees"] = str(company.numberofemployees)
        if company.annualrevenue is not None:
            properties["annualrevenue"] = str(company.annualrevenue)
        if company.timezone:
            properties["hs_timezone"] = company.timezone
        if company.description:
            properties["description"] = company.description
        if company.linkedin_company_page:
            properties["linkedin_company_page"] = company.linkedin_company_page
        if company.phone:
            properties["phone"] = company.phone
        if company.website:
            properties["website"] = company.website

        payload = {"properties": properties}
        result = await self._request("POST", "/crm/v3/objects/companies", json_data=payload)
        logger.info(f"Created HubSpot company: {company.name} (ID: {result.get('id')})")
        return result

    async def search_companies(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search companies by name or domain.
        """
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {"propertyName": "name", "operator": "CONTAINS_TOKEN", "value": query}
                    ]
                },
                {
                    "filters": [
                        {"propertyName": "domain", "operator": "CONTAINS_TOKEN", "value": query}
                    ]
                },
            ],
            "properties": [
                "name", "domain", "industry", "type", "city", "state",
                "phone", "website", "linkedin_company_page",
                "numberofemployees", "description",
            ],
            "limit": limit,
        }
        result = await self._request("POST", "/crm/v3/objects/companies/search", json_data=payload)
        return result.get("results", [])

    async def get_company(self, company_id: str) -> Dict[str, Any]:
        """Get a company by ID"""
        return await self._request(
            "GET",
            f"/crm/v3/objects/companies/{company_id}",
            params={
                "properties": "name,domain,industry,type,city,state,zip,phone,website,"
                             "linkedin_company_page,numberofemployees,annualrevenue,description"
            },
        )

    async def update_company(self, company_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Update company properties"""
        return await self._request(
            "PATCH",
            f"/crm/v3/objects/companies/{company_id}",
            json_data={"properties": properties},
        )

    # ── Contacts ──────────────────────────────────────────────────────

    async def create_contact(
        self,
        email: str,
        firstname: str,
        lastname: str,
        company_id: Optional[str] = None,
        phone: Optional[str] = None,
        jobtitle: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a contact in HubSpot"""
        properties: Dict[str, Any] = {
            "email": email,
            "firstname": firstname,
            "lastname": lastname,
        }
        if phone:
            properties["phone"] = phone
        if jobtitle:
            properties["jobtitle"] = jobtitle

        result = await self._request(
            "POST", "/crm/v3/objects/contacts", json_data={"properties": properties}
        )

        # Associate with company if provided
        if company_id and result.get("id"):
            await self._associate_contact_to_company(result["id"], company_id)

        logger.info(f"Created HubSpot contact: {firstname} {lastname}")
        return result

    async def _associate_contact_to_company(self, contact_id: str, company_id: str):
        """Associate a contact with a company"""
        try:
            await self._request(
                "PUT",
                f"/crm/v3/objects/contacts/{contact_id}/associations/companies/{company_id}/contact_to_company",
            )
        except Exception as e:
            logger.warning(f"Failed to associate contact {contact_id} with company {company_id}: {e}")

    # ── Deals / Opportunities ─────────────────────────────────────────

    async def create_deal(
        self,
        dealname: str,
        pipeline: str = "default",
        dealstage: str = "appointmentscheduled",
        amount: Optional[float] = None,
        company_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a deal/opportunity in HubSpot"""
        properties: Dict[str, Any] = {
            "dealname": dealname,
            "pipeline": pipeline,
            "dealstage": dealstage,
        }
        if amount is not None:
            properties["amount"] = str(amount)

        result = await self._request(
            "POST", "/crm/v3/objects/deals", json_data={"properties": properties}
        )

        if company_id and result.get("id"):
            try:
                await self._request(
                    "PUT",
                    f"/crm/v3/objects/deals/{result['id']}/associations/companies/{company_id}/deal_to_company",
                )
            except Exception as e:
                logger.warning(f"Failed to associate deal with company: {e}")

        return result

    # ── Owners ────────────────────────────────────────────────────────

    async def get_owners(self) -> List[Dict[str, Any]]:
        """Get all HubSpot owners (for assigning records)"""
        result = await self._request("GET", "/crm/v3/owners")
        return result.get("results", [])

    # ── Bulk Operations ───────────────────────────────────────────────

    async def bulk_create_companies(
        self, companies: List[HubSpotCompanyInput]
    ) -> Dict[str, Any]:
        """
        Create multiple companies from a list.
        Returns summary of created and failed records.
        """
        created = []
        failed = []

        for company in companies:
            try:
                result = await self.create_company(company)
                if result.get("conflict"):
                    failed.append({"name": company.name, "reason": "Ya existe en HubSpot"})
                else:
                    created.append({
                        "name": company.name,
                        "hubspot_id": result.get("id"),
                    })
            except Exception as e:
                failed.append({"name": company.name, "reason": str(e)})

        return {
            "total": len(companies),
            "created": len(created),
            "failed": len(failed),
            "created_companies": created,
            "failed_companies": failed,
        }

    # ── Excel/CSV Parsing ─────────────────────────────────────────────

    @staticmethod
    def parse_excel_to_companies(df) -> List[HubSpotCompanyInput]:
        """
        Parse a pandas DataFrame (from Excel/CSV) into HubSpotCompanyInput objects.

        Expected columns (flexible matching, case-insensitive):
        - nombre / name / empresa / company → name
        - dominio / domain / web / website → domain
        - sector / industry → industry
        - tipo / type → type
        - ciudad / city → city
        - estado / state / región → state
        - código postal / zip → zip
        - empleados / employees → numberofemployees
        - descripción / description → description
        - linkedin → linkedin_company_page
        - teléfono / phone → phone
        - nit → nit
        """
        import pandas as pd

        # Normalize column names
        col_map = {}
        for col in df.columns:
            cl = col.strip().lower()
            if cl in ("nombre", "name", "empresa", "company", "nombre de la empresa"):
                col_map[col] = "name"
            elif cl in ("dominio", "domain", "web", "website", "nombre de dominio de la empresa", "sitio web"):
                col_map[col] = "domain"
            elif cl in ("sector", "industry", "industria"):
                col_map[col] = "industry"
            elif cl in ("tipo", "type"):
                col_map[col] = "type"
            elif cl in ("ciudad", "city"):
                col_map[col] = "city"
            elif cl in ("estado", "state", "región", "estado o región", "departamento"):
                col_map[col] = "state"
            elif cl in ("código postal", "zip", "postal"):
                col_map[col] = "zip"
            elif cl in ("empleados", "employees", "número de empleados"):
                col_map[col] = "numberofemployees"
            elif cl in ("ingresos", "revenue", "ingresos anuales"):
                col_map[col] = "annualrevenue"
            elif cl in ("descripción", "description"):
                col_map[col] = "description"
            elif cl in ("linkedin", "linkedin de la empresa", "página corporativa de linkedin"):
                col_map[col] = "linkedin_company_page"
            elif cl in ("teléfono", "phone", "tel"):
                col_map[col] = "phone"
            elif cl in ("nit",):
                col_map[col] = "nit"
            elif cl in ("zona horaria", "timezone"):
                col_map[col] = "timezone"

        df_mapped = df.rename(columns=col_map)

        companies = []
        for _, row in df_mapped.iterrows():
            name = row.get("name")
            if not name or pd.isna(name):
                continue

            company_data: Dict[str, Any] = {"name": str(name).strip()}

            for field in [
                "domain", "industry", "type", "city", "state", "zip",
                "description", "linkedin_company_page", "phone",
                "timezone", "nit", "website",
            ]:
                val = row.get(field)
                if val and not pd.isna(val):
                    company_data[field] = str(val).strip()

            for int_field in ["numberofemployees"]:
                val = row.get(int_field)
                if val and not pd.isna(val):
                    try:
                        company_data[int_field] = int(float(val))
                    except (ValueError, TypeError):
                        pass

            for float_field in ["annualrevenue"]:
                val = row.get(float_field)
                if val and not pd.isna(val):
                    try:
                        company_data[float_field] = float(val)
                    except (ValueError, TypeError):
                        pass

            companies.append(HubSpotCompanyInput(**company_data))

        return companies
