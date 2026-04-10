"""
Workflow Orchestrator Service
==============================
Coordinates the full workflow:
  Excel Upload → AI Enrichment → HubSpot Company Creation → Linear Task → Calendar Event

This is the central piece that ties all integrations together.
"""

import logging
import pandas as pd
import io
from typing import Optional, Dict, Any, List
from datetime import datetime

from .hubspot_service import HubSpotService, HubSpotCompanyInput
from .linear_service import LinearService, LinearPriority
from .calendar_service import GoogleCalendarService
from .enrichment_service import AIEnrichmentService
from ..database.pipeline_service import PipelineService
from ..database.pipeline_models import ProspectSource, FunnelStage, ActivityType

logger = logging.getLogger(__name__)


class WorkflowResult:
    """Result of a workflow execution"""

    def __init__(self):
        self.companies_created: List[Dict] = []
        self.companies_failed: List[Dict] = []
        self.linear_issues_created: List[Dict] = []
        self.calendar_events_created: List[Dict] = []
        self.enrichment_results: List[Dict] = []
        self.prospects_created: List[Dict] = []
        self.errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "companies_created": len(self.companies_created),
                "companies_failed": len(self.companies_failed),
                "linear_issues": len(self.linear_issues_created),
                "calendar_events": len(self.calendar_events_created),
                "prospects_created": len(self.prospects_created),
                "errors": len(self.errors),
            },
            "companies_created": self.companies_created,
            "companies_failed": self.companies_failed,
            "linear_issues": self.linear_issues_created,
            "calendar_events": self.calendar_events_created,
            "prospects_created": self.prospects_created,
            "enrichment_results": self.enrichment_results,
            "errors": self.errors,
        }


class WorkflowOrchestrator:
    """
    Orchestrates the full company onboarding workflow.
    
    Initialize with the services you want to use. If a service is None,
    that step is skipped gracefully.
    """

    def __init__(
        self,
        hubspot: Optional[HubSpotService] = None,
        linear: Optional[LinearService] = None,
        calendar: Optional[GoogleCalendarService] = None,
        enrichment: Optional[AIEnrichmentService] = None,
        pipeline: Optional[PipelineService] = None,
    ):
        self.hubspot = hubspot
        self.linear = linear
        self.calendar = calendar
        self.enrichment = enrichment
        self.pipeline = pipeline or PipelineService()

    async def process_excel_file(
        self,
        file_content: bytes,
        filename: str,
        # Workflow options
        enrich_with_ai: bool = True,
        create_in_hubspot: bool = True,
        create_linear_task: bool = True,
        create_calendar_event: bool = False,
        # Linear options
        linear_team_id: Optional[str] = None,
        # Calendar options
        meeting_attendees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Full workflow: Process an uploaded Excel/CSV file.

        Steps:
        1. Parse Excel/CSV into company records
        2. Enrich each company with AI (if enabled)
        3. Create companies in HubSpot (if enabled)
        4. Create tracking tasks in Linear (if enabled)
        5. Create calendar events for follow-up (if enabled)
        """
        result = WorkflowResult()

        # ── Step 1: Parse the file ────────────────────────────────────
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_content))
            else:
                df = pd.read_excel(io.BytesIO(file_content))
            
            logger.info(f"Parsed {len(df)} rows from {filename}")
        except Exception as e:
            result.errors.append(f"Error parsing file: {e}")
            return result.to_dict()

        # ── Step 2: AI Enrichment ─────────────────────────────────────
        companies_data = HubSpotService.parse_excel_to_companies(df)
        
        if enrich_with_ai and self.enrichment and self.enrichment.available:
            logger.info(f"Enriching {len(companies_data)} companies with AI...")
            for i, company in enumerate(companies_data):
                try:
                    enriched = await self.enrichment.enrich_company(
                        company_name=company.name,
                        domain=company.domain,
                        city=company.city,
                    )
                    if enriched.get("enriched"):
                        # Update company with enriched data (only fill blanks)
                        if not company.description and enriched.get("description"):
                            company.description = enriched["description"]
                        if not company.industry and enriched.get("industry"):
                            company.industry = enriched["industry"]
                        if not company.linkedin_company_page and enriched.get("linkedin_company_page"):
                            company.linkedin_company_page = enriched["linkedin_company_page"]
                        if not company.phone and enriched.get("phone"):
                            company.phone = enriched["phone"]
                        if not company.state and enriched.get("state"):
                            company.state = enriched["state"]
                        if company.numberofemployees is None and enriched.get("numberofemployees"):
                            try:
                                company.numberofemployees = int(enriched["numberofemployees"])
                            except (ValueError, TypeError):
                                pass

                        result.enrichment_results.append({
                            "company": company.name,
                            "enriched_fields": [
                                k for k, v in enriched.items()
                                if v and k not in ("enriched", "source", "raw")
                            ],
                            "source": enriched.get("source", "unknown"),
                        })
                except Exception as e:
                    logger.warning(f"Enrichment failed for {company.name}: {e}")
                    result.errors.append(f"Enrichment failed for {company.name}: {e}")

        # ── Step 3: Create in HubSpot ─────────────────────────────────
        if create_in_hubspot and self.hubspot:
            logger.info(f"Creating {len(companies_data)} companies in HubSpot...")
            for company in companies_data:
                try:
                    hs_result = await self.hubspot.create_company(company)
                    if hs_result.get("conflict"):
                        result.companies_failed.append({
                            "name": company.name,
                            "reason": "Already exists in HubSpot",
                        })
                    else:
                        result.companies_created.append({
                            "name": company.name,
                            "hubspot_id": hs_result.get("id"),
                            "domain": company.domain,
                        })
                except Exception as e:
                    result.companies_failed.append({
                        "name": company.name,
                        "reason": str(e),
                    })

        # ── Step 4: Create Linear tasks ───────────────────────────────
        if create_linear_task and self.linear and linear_team_id:
            logger.info("Creating Linear tracking tasks...")
            for company in companies_data:
                try:
                    issue = await self.linear.create_commercial_task(
                        team_id=linear_team_id,
                        title=f"Seguimiento comercial: {company.name}",
                        description=(
                            f"## Empresa importada desde Excel\n\n"
                            f"- **Nombre:** {company.name}\n"
                            f"- **Dominio:** {company.domain or 'N/A'}\n"
                            f"- **Ciudad:** {company.city or 'N/A'}\n"
                            f"- **Sector:** {company.industry or 'N/A'}\n"
                            f"- **Tipo:** {company.type or 'N/A'}\n\n"
                            f"### Tareas\n"
                            f"- [ ] Contactar a la empresa\n"
                            f"- [ ] Agendar reunión inicial\n"
                            f"- [ ] Preparar propuesta\n"
                            f"- [ ] Enviar propuesta\n"
                            f"- [ ] Follow-up\n"
                        ),
                        company_name=company.name,
                        priority=LinearPriority.MEDIUM,
                    )
                    result.linear_issues_created.append({
                        "company": company.name,
                        "issue_id": issue.get("identifier"),
                        "url": issue.get("url"),
                    })
                except Exception as e:
                    result.errors.append(f"Linear task failed for {company.name}: {e}")

        # ── Step 5: Create Calendar events ────────────────────────────
        if create_calendar_event and self.calendar:
            logger.info("Creating follow-up calendar events...")
            for company in companies_data:
                try:
                    event = await self.calendar.create_meeting_event(
                        company_name=company.name,
                        meeting_type="Seguimiento comercial",
                        attendees=meeting_attendees,
                        notes=f"Empresa importada desde {filename}. Sector: {company.industry or 'N/A'}",
                    )
                    result.calendar_events_created.append({
                        "company": company.name,
                        "event_id": event.get("id"),
                        "link": event.get("htmlLink"),
                    })
                except Exception as e:
                    result.errors.append(f"Calendar event failed for {company.name}: {e}")

        logger.info(
            f"Workflow complete: {len(result.companies_created)} companies created, "
            f"{len(result.linear_issues_created)} Linear issues, "
            f"{len(result.calendar_events_created)} calendar events"
        )

        # ── Step 6: Create Pipeline Prospects ─────────────────────────
        logger.info("Creating pipeline prospects…")
        for company in companies_data:
            try:
                # Find HubSpot and Linear IDs for this company
                hs_id = None
                for c in result.companies_created:
                    if c.get("name") == company.name:
                        hs_id = c.get("hubspot_id")
                        break
                li_id = None
                for li in result.linear_issues_created:
                    if li.get("company") == company.name:
                        li_id = li.get("issue_id")
                        break

                prospect = self.pipeline.create_prospect(
                    company_name=company.name,
                    source=ProspectSource.EXCEL_IMPORT,
                    source_detail=filename,
                    company_domain=company.domain,
                    industry=company.industry,
                    city=company.city,
                    department=company.state,
                    employee_count=company.numberofemployees,
                    contact_name=getattr(company, "contact_name", None),
                    contact_email=getattr(company, "contact_email", None),
                    contact_phone=company.phone,
                    hubspot_company_id=hs_id,
                    linear_issue_id=li_id,
                )
                result.prospects_created.append({
                    "company": company.name,
                    "prospect_id": prospect.id,
                    "stage": prospect.current_stage.value,
                })
            except Exception as e:
                logger.warning(f"Pipeline prospect failed for {company.name}: {e}")
                result.errors.append(f"Pipeline prospect failed for {company.name}: {e}")

        return result.to_dict()

    async def create_single_company_workflow(
        self,
        company_data: Dict[str, Any],
        enrich_with_ai: bool = True,
        create_in_hubspot: bool = True,
        create_linear_task: bool = True,
        create_calendar_event: bool = False,
        linear_team_id: Optional[str] = None,
        meeting_attendees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Workflow for a single company (manual form submission).
        """
        result = WorkflowResult()
        company = HubSpotCompanyInput(**company_data)

        # Enrich
        if enrich_with_ai and self.enrichment and self.enrichment.available:
            try:
                enriched = await self.enrichment.enrich_company(
                    company_name=company.name,
                    domain=company.domain,
                    city=company.city,
                )
                if enriched.get("enriched"):
                    if not company.description and enriched.get("description"):
                        company.description = enriched["description"]
                    if not company.industry and enriched.get("industry"):
                        company.industry = enriched["industry"]
                    if not company.linkedin_company_page and enriched.get("linkedin_company_page"):
                        company.linkedin_company_page = enriched["linkedin_company_page"]
                    result.enrichment_results.append({
                        "company": company.name,
                        "source": enriched.get("source"),
                    })
            except Exception as e:
                result.errors.append(f"Enrichment: {e}")

        # HubSpot
        if create_in_hubspot and self.hubspot:
            try:
                hs = await self.hubspot.create_company(company)
                result.companies_created.append({
                    "name": company.name,
                    "hubspot_id": hs.get("id"),
                })
            except Exception as e:
                result.companies_failed.append({"name": company.name, "reason": str(e)})

        # Linear
        if create_linear_task and self.linear and linear_team_id:
            try:
                issue = await self.linear.create_commercial_task(
                    team_id=linear_team_id,
                    title=f"Seguimiento: {company.name}",
                    description=f"Nueva empresa registrada: {company.name}\nDominio: {company.domain or 'N/A'}",
                    company_name=company.name,
                )
                result.linear_issues_created.append({
                    "company": company.name,
                    "issue_id": issue.get("identifier"),
                    "url": issue.get("url"),
                })
            except Exception as e:
                result.errors.append(f"Linear: {e}")

        # Calendar
        if create_calendar_event and self.calendar:
            try:
                event = await self.calendar.create_meeting_event(
                    company_name=company.name,
                    attendees=meeting_attendees,
                )
                result.calendar_events_created.append({
                    "company": company.name,
                    "event_id": event.get("id"),
                    "link": event.get("htmlLink"),
                })
            except Exception as e:
                result.errors.append(f"Calendar: {e}")

        # Pipeline prospect
        try:
            hs_id = result.companies_created[0].get("hubspot_id") if result.companies_created else None
            li_id = result.linear_issues_created[0].get("issue_id") if result.linear_issues_created else None
            prospect = self.pipeline.create_prospect(
                company_name=company.name,
                source=ProspectSource.MANUAL,
                company_domain=company.domain,
                industry=company.industry,
                city=company.city,
                department=company.state,
                employee_count=company.numberofemployees,
                contact_phone=company.phone,
                hubspot_company_id=hs_id,
                linear_issue_id=li_id,
            )
            result.prospects_created.append({
                "company": company.name,
                "prospect_id": prospect.id,
                "stage": prospect.current_stage.value,
            })
        except Exception as e:
            result.errors.append(f"Pipeline: {e}")

        return result.to_dict()
