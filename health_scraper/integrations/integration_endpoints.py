"""
Integration API Endpoints
==========================
FastAPI router with all integration endpoints for:
- HubSpot CRM
- Linear Project Management
- Google Calendar
- AI Enrichment
- Full Workflow Orchestration
"""

import logging
import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .hubspot_service import HubSpotService, HubSpotCompanyInput
from .linear_service import LinearService, LinearPriority
from .calendar_service import GoogleCalendarService
from .enrichment_service import AIEnrichmentService
from .workflow_orchestrator import WorkflowOrchestrator
from .person_research_service import PersonResearchService
from .outreach_drafting_service imp2026-03-07 11:27:17I was given now the access and I now was entered that they migrated everything in the email to zoho email, I am now in charge of streaming lighting the sells prospects, and I would like to have an "embudo" , and make it so that I can report charts statistics and stuff to my CEO of how the search and prospecting went, I want to integrate eveyrthing into the workflow with Linear, hubspot, to stream ligthe task, and well I do not know if for the analyticsort OutreachDraftingService, OutreachChannel, OutreachTone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])

# ── Service Instances (lazy init) ─────────────────────────────────────

_hubspot: Optional[HubSpotService] = None
_linear: Optional[LinearService] = None
_calendar: Optional[GoogleCalendarService] = None
_enrichment: Optional[AIEnrichmentService] = None
_person_research: Optional[PersonResearchService] = None
_outreach_drafting: Optional[OutreachDraftingService] = None


def get_hubspot() -> Optional[HubSpotService]:
    global _hubspot
    if _hubspot is None:
        token = os.getenv("HUBSPOT_ACCESS_TOKEN")
        if token:
            _hubspot = HubSpotService(access_token=token)
    return _hubspot


def get_linear() -> Optional[LinearService]:
    global _linear
    if _linear is None:
        key = os.getenv("LINEAR_API_KEY")
        if key:
            _linear = LinearService(api_key=key)
    return _linear


def get_calendar() -> Optional[GoogleCalendarService]:
    global _calendar
    if _calendar is None:
        sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE")
        if sa_file or creds_file:
            _calendar = GoogleCalendarService(
                service_account_file=sa_file,
                credentials_file=creds_file,
            )
    return _calendar


def get_enrichment() -> Optional[AIEnrichmentService]:
    global _enrichment
    if _enrichment is None:
        _enrichment = AIEnrichmentService(
            perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"),
            gemini_api_key=os.getenv("GOOGLE_AI_STUDIO"),
        )
    return _enrichment


def get_person_research() -> Optional[PersonResearchService]:
    global _person_research
    if _person_research is None:
        _person_research = PersonResearchService(
            perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"),
            gemini_api_key=os.getenv("GOOGLE_AI_STUDIO"),
        )
    return _person_research


def get_outreach_drafting() -> Optional[OutreachDraftingService]:
    global _outreach_drafting
    if _outreach_drafting is None:
        _outreach_drafting = OutreachDraftingService(
            gemini_api_key=os.getenv("GOOGLE_AI_STUDIO"),
            business_name=os.getenv("BUSINESS_NAME", ""),
            business_description=os.getenv("BUSINESS_DESCRIPTION", ""),
            your_name=os.getenv("YOUR_NAME", ""),
            your_role=os.getenv("YOUR_ROLE", ""),
        )
    return _outreach_drafting


def get_orchestrator() -> WorkflowOrchestrator:
    return WorkflowOrchestrator(
        hubspot=get_hubspot(),
        linear=get_linear(),
        calendar=get_calendar(),
        enrichment=get_enrichment(),
    )


# ── Status Endpoint ──────────────────────────────────────────────────

@router.get("/status")
async def integration_status():
    """Check which integrations are configured and available"""
    return {
        "hubspot": {
            "configured": bool(os.getenv("HUBSPOT_ACCESS_TOKEN")),
            "status": "ready" if get_hubspot() else "not_configured",
        },
        "linear": {
            "configured": bool(os.getenv("LINEAR_API_KEY")),
            "status": "ready" if get_linear() else "not_configured",
        },
        "google_calendar": {
            "configured": bool(
                os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or os.getenv("GOOGLE_CREDENTIALS_FILE")
            ),
            "status": "ready" if get_calendar() else "not_configured",
        },
        "ai_enrichment": {
            "perplexity": bool(os.getenv("PERPLEXITY_API_KEY")),
            "gemini": bool(os.getenv("GOOGLE_AI_STUDIO")),
            "status": "ready" if get_enrichment() and get_enrichment().available else "not_configured",
        },
        "person_research": {
            "configured": bool(os.getenv("PERPLEXITY_API_KEY") or os.getenv("GOOGLE_AI_STUDIO")),
            "status": "ready" if get_person_research() and get_person_research().available else "not_configured",
        },
        "outreach_drafting": {
            "configured": bool(os.getenv("GOOGLE_AI_STUDIO")),
            "status": "ready" if get_outreach_drafting() and get_outreach_drafting().available else "not_configured",
        },
    }


# ══════════════════════════════════════════════════════════════════════
# WORKFLOW ENDPOINTS (main feature)
# ══════════════════════════════════════════════════════════════════════

@router.post("/workflow/upload-excel")
async def workflow_upload_excel(
    file: UploadFile = File(..., description="Excel (.xlsx) or CSV file with company data"),
    enrich_with_ai: bool = Form(True, description="Enrich data with AI before creating"),
    create_in_hubspot: bool = Form(True, description="Create companies in HubSpot CRM"),
    create_linear_task: bool = Form(True, description="Create tracking tasks in Linear"),
    create_calendar_event: bool = Form(False, description="Create follow-up calendar events"),
    linear_team_id: Optional[str] = Form(None, description="Linear team ID for task creation"),
):
    """
    **Full Workflow**: Upload an Excel/CSV → Enrich with AI → Create in HubSpot + Linear + Calendar.

    This is the main endpoint that orchestrates the entire company onboarding workflow.

    The Excel file should have columns like:
    - Nombre de la empresa / Name
    - Nombre de dominio / Domain
    - Sector / Industry
    - Tipo / Type
    - Ciudad / City
    - Estado o región / State
    - Código postal / Zip
    - Número de empleados
    - Descripción
    - LinkedIn
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="File must be .xlsx, .xls, or .csv")

    content = await file.read()
    orchestrator = get_orchestrator()

    # Auto-detect Linear team if not provided
    if create_linear_task and not linear_team_id:
        linear = get_linear()
        if linear:
            try:
                teams = await linear.get_teams()
                if teams:
                    linear_team_id = teams[0]["id"]
            except Exception:
                pass

    result = await orchestrator.process_excel_file(
        file_content=content,
        filename=file.filename,
        enrich_with_ai=enrich_with_ai,
        create_in_hubspot=create_in_hubspot,
        create_linear_task=create_linear_task,
        create_calendar_event=create_calendar_event,
        linear_team_id=linear_team_id,
    )

    return result


class SingleCompanyRequest(BaseModel):
    """Request body for creating a single company through the workflow"""
    name: str = Field(..., description="Nombre de la empresa")
    domain: Optional[str] = Field(None, description="Dominio web")
    industry: Optional[str] = Field(None, description="Sector")
    type: Optional[str] = Field(None, description="Tipo (Cliente potencial, Cliente, etc.)")
    city: Optional[str] = Field(None, description="Ciudad")
    state: Optional[str] = Field(None, description="Estado o región")
    zip: Optional[str] = Field(None, description="Código postal")
    phone: Optional[str] = Field(None, description="Teléfono")
    description: Optional[str] = Field(None, description="Descripción")
    linkedin_company_page: Optional[str] = Field(None, description="LinkedIn")
    numberofemployees: Optional[int] = Field(None, description="Número de empleados")
    # Workflow options
    enrich_with_ai: bool = Field(True, description="Enriquecer con AI")
    create_in_hubspot: bool = Field(True, description="Crear en HubSpot")
    create_linear_task: bool = Field(True, description="Crear tarea en Linear")
    create_calendar_event: bool = Field(False, description="Crear evento en calendario")
    linear_team_id: Optional[str] = Field(None, description="ID del equipo en Linear")


@router.post("/workflow/single-company")
async def workflow_single_company(request: SingleCompanyRequest):
    """
    **Single company workflow**: Create a company through the full pipeline.

    Example (like SubRedSur):
    ```json
    {
        "name": "SubRedSur",
        "domain": "www.subredsur.gov.co",
        "industry": "Salud, bienestar y fitness",
        "type": "Cliente potencial",
        "city": "Bogota",
        "state": "Tunal",
        "zip": "110621"
    }
    ```
    """
    orchestrator = get_orchestrator()

    # Auto-detect Linear team if not provided
    linear_team_id = request.linear_team_id
    if request.create_linear_task and not linear_team_id:
        linear = get_linear()
        if linear:
            try:
                teams = await linear.get_teams()
                if teams:
                    linear_team_id = teams[0]["id"]
            except Exception:
                pass

    company_data = request.model_dump(exclude={
        "enrich_with_ai", "create_in_hubspot", "create_linear_task",
        "create_calendar_event", "linear_team_id",
    })

    result = await orchestrator.create_single_company_workflow(
        company_data=company_data,
        enrich_with_ai=request.enrich_with_ai,
        create_in_hubspot=request.create_in_hubspot,
        create_linear_task=request.create_linear_task,
        create_calendar_event=request.create_calendar_event,
        linear_team_id=linear_team_id,
    )

    return result


# ══════════════════════════════════════════════════════════════════════
# HUBSPOT ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@router.get("/hubspot/companies")
async def hubspot_search_companies(
    query: str = Query(..., description="Search term (name or domain)"),
    limit: int = Query(10, ge=1, le=100),
):
    """Search companies in HubSpot CRM"""
    hs = get_hubspot()
    if not hs:
        raise HTTPException(status_code=503, detail="HubSpot not configured. Set HUBSPOT_ACCESS_TOKEN in .env")
    return await hs.search_companies(query, limit)


@router.get("/hubspot/companies/{company_id}")
async def hubspot_get_company(company_id: str):
    """Get a specific company from HubSpot"""
    hs = get_hubspot()
    if not hs:
        raise HTTPException(status_code=503, detail="HubSpot not configured")
    return await hs.get_company(company_id)


@router.post("/hubspot/companies")
async def hubspot_create_company(company: HubSpotCompanyInput):
    """Create a single company in HubSpot (direct, no workflow)"""
    hs = get_hubspot()
    if not hs:
        raise HTTPException(status_code=503, detail="HubSpot not configured")
    return await hs.create_company(company)


@router.get("/hubspot/owners")
async def hubspot_get_owners():
    """Get HubSpot owners for assigning records"""
    hs = get_hubspot()
    if not hs:
        raise HTTPException(status_code=503, detail="HubSpot not configured")
    return await hs.get_owners()


# ══════════════════════════════════════════════════════════════════════
# LINEAR ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@router.get("/linear/teams")
async def linear_get_teams():
    """Get all Linear teams"""
    lin = get_linear()
    if not lin:
        raise HTTPException(status_code=503, detail="Linear not configured. Set LINEAR_API_KEY in .env")
    return await lin.get_teams()


@router.get("/linear/issues")
async def linear_get_issues(
    team_id: Optional[str] = None,
    label: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """Get Linear issues with optional filters"""
    lin = get_linear()
    if not lin:
        raise HTTPException(status_code=503, detail="Linear not configured")
    return await lin.get_issues(team_id=team_id, label_name=label, state_name=state, limit=limit)


@router.get("/linear/dashboard")
async def linear_dashboard(team_id: Optional[str] = None):
    """Get Linear dashboard summary (issues by state, priority, labels)"""
    lin = get_linear()
    if not lin:
        raise HTTPException(status_code=503, detail="Linear not configured")
    return await lin.get_dashboard_summary(team_id=team_id)


class LinearIssueRequest(BaseModel):
    team_id: str
    title: str
    description: Optional[str] = None
    priority: int = Field(3, ge=0, le=4, description="0=None, 1=Urgent, 2=High, 3=Medium, 4=Low")
    category: str = Field("development", description="'development' or 'commercial'")
    company_name: Optional[str] = None
    due_date: Optional[str] = None


@router.post("/linear/issues")
async def linear_create_issue(request: LinearIssueRequest):
    """Create a new issue in Linear (development or commercial)"""
    lin = get_linear()
    if not lin:
        raise HTTPException(status_code=503, detail="Linear not configured")

    priority = LinearPriority(request.priority)

    if request.category == "commercial":
        return await lin.create_commercial_task(
            team_id=request.team_id,
            title=request.title,
            description=request.description or "",
            company_name=request.company_name,
            priority=priority,
            due_date=request.due_date,
        )
    else:
        return await lin.create_development_task(
            team_id=request.team_id,
            title=request.title,
            description=request.description or "",
            priority=priority,
        )


@router.get("/linear/members")
async def linear_get_members():
    """Get all Linear workspace members"""
    lin = get_linear()
    if not lin:
        raise HTTPException(status_code=503, detail="Linear not configured")
    return await lin.get_members()


# ══════════════════════════════════════════════════════════════════════
# GOOGLE CALENDAR ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@router.get("/calendar/events")
async def calendar_get_events(
    max_results: int = Query(20, ge=1, le=100),
    calendar_id: str = Query("primary"),
):
    """Get upcoming calendar events"""
    cal = get_calendar()
    if not cal:
        raise HTTPException(status_code=503, detail="Google Calendar not configured")
    return await cal.get_upcoming_events(calendar_id=calendar_id, max_results=max_results)


@router.get("/calendar/calendars")
async def calendar_list():
    """List available calendars"""
    cal = get_calendar()
    if not cal:
        raise HTTPException(status_code=503, detail="Google Calendar not configured")
    return await cal.list_calendars()


class CalendarEventRequest(BaseModel):
    summary: str = Field(..., description="Título del evento")
    start_datetime: str = Field(..., description="Fecha/hora inicio (ISO format)")
    end_datetime: str = Field(..., description="Fecha/hora fin (ISO format)")
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    calendar_id: str = "primary"


@router.post("/calendar/events")
async def calendar_create_event(request: CalendarEventRequest):
    """Create a calendar event"""
    cal = get_calendar()
    if not cal:
        raise HTTPException(status_code=503, detail="Google Calendar not configured")
    return await cal.create_event(
        summary=request.summary,
        start_datetime=request.start_datetime,
        end_datetime=request.end_datetime,
        description=request.description,
        location=request.location,
        attendees=request.attendees,
        calendar_id=request.calendar_id,
    )


# ══════════════════════════════════════════════════════════════════════
# AI ENRICHMENT ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

class EnrichRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None
    city: Optional[str] = None
    country: str = "Colombia"


@router.post("/enrich/company")
async def enrich_company(request: EnrichRequest):
    """
    Enrich company data using AI (Perplexity or Gemini).
    Returns researched company information.
    """
    enrichment = get_enrichment()
    if not enrichment or not enrichment.available:
        raise HTTPException(
            status_code=503, detail="No AI enrichment configured. Set PERPLEXITY_API_KEY or GOOGLE_AI_STUDIO in .env"
        )
    return await enrichment.enrich_company(
        company_name=request.company_name,
        domain=request.domain,
        city=request.city,
        country=request.country,
    )


# ══════════════════════════════════════════════════════════════════════
# PERSON RESEARCH ENDPOINTS (Perplexity-powered)
# ══════════════════════════════════════════════════════════════════════

class PersonResearchRequest(BaseModel):
    """Research a person from minimal input"""
    name: str = Field(..., description="Person's name")
    context: Optional[str] = Field(None, description="Where you found them (e.g., 'Twitter thread about AI in healthcare')")
    twitter_handle: Optional[str] = Field(None, description="Twitter/X handle")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    company: Optional[str] = Field(None, description="Their company if known")
    business_context: str = Field(
        "health-tech company selling to hospitals and clinics in Colombia",
        description="YOUR business context for relevance scoring",
    )


@router.post("/research/person", tags=["Person Research"])
async def research_person(request: PersonResearchRequest):
    """
    **Step 1 of your workflow**: Research a person using Perplexity AI.

    Feed in a name you found on Twitter, a PDF, a conference, etc.
    Perplexity will research everything about them online.

    Returns: Full profile with bio, company, role, contact channels, and relevance to your business.
    """
    svc = get_person_research()
    if not svc or not svc.available:
        raise HTTPException(
            status_code=503,
            detail="Person research not configured. Set PERPLEXITY_API_KEY or GOOGLE_AI_STUDIO in .env",
        )
    result = await svc.research_person(
        name=request.name,
        context=request.context,
        twitter_handle=request.twitter_handle,
        linkedin_url=request.linkedin_url,
        company=request.company,
        your_business_context=request.business_context,
    )
    return result.to_dict()


class PersonBatchResearchRequest(BaseModel):
    """Research multiple people at once"""
    people: List[PersonResearchRequest]
    business_context: str = Field(
        "health-tech company selling to hospitals and clinics in Colombia",
        description="YOUR business context",
    )


@router.post("/research/person/batch", tags=["Person Research"])
async def research_person_batch(request: PersonBatchResearchRequest):
    """
    Research multiple people in one call.
    Useful when you have a list from a conference, Twitter thread, or PDF.
    """
    svc = get_person_research()
    if not svc or not svc.available:
        raise HTTPException(status_code=503, detail="Person research not configured")

    people_dicts = [
        {
            "name": p.name,
            "context": p.context,
            "twitter_handle": p.twitter_handle,
            "linkedin_url": p.linkedin_url,
            "company": p.company,
        }
        for p in request.people
    ]
    results = await svc.research_batch(people_dicts, request.business_context)
    return {"results": results, "total": len(results)}


# ══════════════════════════════════════════════════════════════════════
# OUTREACH DRAFTING ENDPOINTS (Gemini-powered)
# ══════════════════════════════════════════════════════════════════════

class OutreachRequest(BaseModel):
    """Draft outreach messages for a researched person"""
    person_data: Dict[str, Any] = Field(
        ..., description="Output from /research/person endpoint"
    )
    channels: Optional[List[str]] = Field(
        None, description="Channels to draft for: email, linkedin, twitter, whatsapp. Auto-detected if not set."
    )
    tone: str = Field("professional", description="Tone: professional, casual, warm, direct")
    language: str = Field("es", description="Language: 'es' for Spanish, 'en' for English")
    custom_context: Optional[str] = Field(None, description="Extra context for the message")
    goal: str = Field("Schedule an introductory meeting", description="What you want to achieve")


@router.post("/outreach/draft", tags=["Outreach Drafting"])
async def draft_outreach(request: OutreachRequest):
    """
    **Step 2 of your workflow**: Draft personalized outreach messages using Gemini.

    Takes the output of /research/person and generates channel-specific messages
    (email, LinkedIn, Twitter, WhatsApp) with your business context.

    Returns: Drafts for each channel + strategy notes + recommended contact sequence.
    """
    svc = get_outreach_drafting()
    if not svc or not svc.available:
        raise HTTPException(
            status_code=503,
            detail="Outreach drafting not configured. Set GOOGLE_AI_STUDIO in .env",
        )

    channels = None
    if request.channels:
        channels = [OutreachChannel(c) for c in request.channels]

    tone = OutreachTone(request.tone) if request.tone else OutreachTone.PROFESSIONAL

    result = await svc.draft_outreach(
        person_data=request.person_data,
        channels=channels,
        tone=tone,
        language=request.language,
        custom_context=request.custom_context,
        goal=request.goal,
    )
    return result.to_dict()


class FullPipelineRequest(BaseModel):
    """Complete pipeline: Research + Draft in one call"""
    name: str = Field(..., description="Person's name")
    context: Optional[str] = Field(None, description="Where you found them")
    twitter_handle: Optional[str] = Field(None, description="Twitter/X handle")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn URL")
    company: Optional[str] = Field(None, description="Their company")
    business_context: str = Field(
        "health-tech company selling to hospitals and clinics in Colombia",
    )
    channels: Optional[List[str]] = Field(None)
    tone: str = Field("professional")
    language: str = Field("es")
    goal: str = Field("Schedule an introductory meeting")


@router.post("/pipeline/research-and-draft", tags=["Full Pipeline"])
async def full_pipeline(request: FullPipelineRequest):
    """
    **Complete workflow in one call**: Research person (Perplexity) → Draft outreach (Gemini).

    This is the main endpoint for your daily workflow:
    1. You find someone interesting (Twitter, PDF, conference...)
    2. Call this endpoint with their name + any context
    3. Get back: full research profile + ready-to-send outreach messages

    Then just copy-paste the messages to LinkedIn/Email/Twitter!
    """
    # Step 1: Research
    research_svc = get_person_research()
    if not research_svc or not research_svc.available:
        raise HTTPException(status_code=503, detail="Person research not configured")

    person = await research_svc.research_person(
        name=request.name,
        context=request.context,
        twitter_handle=request.twitter_handle,
        linkedin_url=request.linkedin_url,
        company=request.company,
        your_business_context=request.business_context,
    )

    # Step 2: Draft outreach
    drafting_svc = get_outreach_drafting()
    if not drafting_svc or not drafting_svc.available:
        return {
            "research": person.to_dict(),
            "outreach": {"error": "Gemini not configured for outreach drafting"},
        }

    channels = [OutreachChannel(c) for c in request.channels] if request.channels else None
    tone = OutreachTone(request.tone)

    drafts = await drafting_svc.draft_outreach(
        person_data=person.to_dict(),
        channels=channels,
        tone=tone,
        language=request.language,
        goal=request.goal,
    )

    return {
        "research": person.to_dict(),
        "outreach": drafts.to_dict(),
    }
