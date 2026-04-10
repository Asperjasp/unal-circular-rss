"""
Pipeline & Analytics API Endpoints
=====================================
FastAPI router for:
- Sales funnel (embudo) management
- Prospect CRUD and stage management
- Analytics & CEO reporting
- Zoho Email integration
- Connect desktop app API
"""

import logging
import os
import io
import csv
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..database.pipeline_service import PipelineService
from ..database.pipeline_models import (
    FunnelStage, ProspectSource, ActivityType, FUNNEL_STAGE_META
)
from .analytics_service import AnalyticsService
from .zoho_email_service import ZohoEmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipeline", tags=["Sales Pipeline"])
connect_router = APIRouter(prefix="/api/v1/connect", tags=["Connect App API"])

# ── Service Instances ──────────────────────────────────────────────────

_pipeline: Optional[PipelineService] = None
_analytics: Optional[AnalyticsService] = None
_zoho: Optional[ZohoEmailService] = None


def get_pipeline() -> PipelineService:
    global _pipeline
    if _pipeline is None:
        _pipeline = PipelineService()
    return _pipeline


def get_analytics() -> AnalyticsService:
    global _analytics
    if _analytics is None:
        _analytics = AnalyticsService(pipeline_service=get_pipeline())
    return _analytics


def get_zoho() -> Optional[ZohoEmailService]:
    global _zoho
    if _zoho is None:
        client_id = os.getenv("ZOHO_CLIENT_ID")
        client_secret = os.getenv("ZOHO_CLIENT_SECRET")
        refresh_token = os.getenv("ZOHO_REFRESH_TOKEN")
        account_id = os.getenv("ZOHO_ACCOUNT_ID")
        from_email = os.getenv("ZOHO_FROM_EMAIL")
        if all([client_id, client_secret, refresh_token, account_id, from_email]):
            _zoho = ZohoEmailService(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                account_id=account_id,
                from_email=from_email,
                zoho_domain=os.getenv("ZOHO_DOMAIN", "zoho.com"),
            )
    return _zoho


# ══════════════════════════════════════════════════════════════════════
# FUNNEL OVERVIEW
# ══════════════════════════════════════════════════════════════════════

@router.get("/funnel")
async def get_funnel():
    """
    Get the current sales funnel (embudo de ventas).
    
    Returns stage counts, values, and conversion rates.
    Perfect for rendering funnel visualizations.
    """
    pipeline = get_pipeline()
    return pipeline.get_funnel_analytics()


@router.get("/funnel/chart")
async def get_funnel_chart():
    """Get funnel data formatted for Chart.js visualization"""
    analytics = get_analytics()
    return analytics.get_funnel_chart()


@router.get("/stages")
async def list_stages():
    """Get all pipeline stages with metadata (labels, colors, icons)"""
    return {
        "stages": [
            {
                "id": stage.value,
                **FUNNEL_STAGE_META[stage],
            }
            for stage in FunnelStage
        ]
    }


# ══════════════════════════════════════════════════════════════════════
# PROSPECT CRUD
# ══════════════════════════════════════════════════════════════════════

class CreateProspectRequest(BaseModel):
    company_name: str = Field(..., description="Nombre de la empresa")
    company_domain: Optional[str] = None
    company_nit: Optional[str] = None
    industry: Optional[str] = None
    city: Optional[str] = None
    department: Optional[str] = None
    employee_count: Optional[int] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_position: Optional[str] = None
    contact_linkedin: Optional[str] = None
    estimated_value: Optional[float] = None
    source: str = Field("manual", description="scraper, excel_import, manual, hubspot, linkedin, referral, conference, twitter, other")
    source_detail: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


@router.post("/prospects")
async def create_prospect(request: CreateProspectRequest):
    """Create a new prospect in the sales pipeline"""
    pipeline = get_pipeline()
    try:
        source = ProspectSource(request.source)
    except ValueError:
        source = ProspectSource.MANUAL
    
    prospect = pipeline.create_prospect(
        company_name=request.company_name,
        source=source,
        source_detail=request.source_detail,
        company_domain=request.company_domain,
        company_nit=request.company_nit,
        industry=request.industry,
        city=request.city,
        department=request.department,
        employee_count=request.employee_count,
        contact_name=request.contact_name,
        contact_email=request.contact_email,
        contact_phone=request.contact_phone,
        contact_position=request.contact_position,
        contact_linkedin=request.contact_linkedin,
        estimated_value=request.estimated_value,
        assigned_to=request.assigned_to,
        tags=request.tags,
        notes=request.notes,
    )
    
    return pipeline.prospect_to_dict(prospect)


@router.get("/prospects")
async def list_prospects(
    stage: Optional[str] = Query(None, description="Filter by funnel stage"),
    source: Optional[str] = Query(None, description="Filter by source"),
    city: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    is_active: bool = Query(True),
    search: Optional[str] = Query(None, description="Search by company name, contact name, or email"),
    sort_by: str = Query("updated_at"),
    sort_desc: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    List prospects with filters and pagination.
    
    Use this for the pipeline board view or prospect list.
    """
    pipeline = get_pipeline()
    
    stage_enum = FunnelStage(stage) if stage else None
    source_enum = ProspectSource(source) if source else None
    
    prospects, total = pipeline.list_prospects(
        stage=stage_enum,
        source=source_enum,
        city=city,
        assigned_to=assigned_to,
        is_active=is_active,
        search=search,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    
    return {
        "prospects": [pipeline.prospect_to_dict(p) for p in prospects],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/prospects/board")
async def get_pipeline_board():
    """
    Get prospects organized by stage for Kanban board view.
    
    Returns prospects grouped by their current funnel stage.
    """
    pipeline = get_pipeline()
    
    board = {}
    for stage in FunnelStage:
        if stage in (FunnelStage.CLOSED_WON, FunnelStage.CLOSED_LOST):
            continue
        prospects, count = pipeline.list_prospects(stage=stage, limit=100)
        board[stage.value] = {
            "stage": stage.value,
            "label": FUNNEL_STAGE_META[stage]["label"],
            "color": FUNNEL_STAGE_META[stage]["color"],
            "icon": FUNNEL_STAGE_META[stage]["icon"],
            "count": count,
            "prospects": [pipeline.prospect_to_dict(p) for p in prospects],
        }
    
    return {"board": board}


@router.get("/prospects/{prospect_id}")
async def get_prospect(prospect_id: int):
    """Get a single prospect with full details"""
    pipeline = get_pipeline()
    prospect = pipeline.get_prospect(prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    activities = pipeline.get_prospect_activities(prospect_id, limit=50)
    
    return {
        "prospect": pipeline.prospect_to_dict(prospect),
        "activities": [pipeline.activity_to_dict(a) for a in activities],
    }


class UpdateProspectRequest(BaseModel):
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_position: Optional[str] = None
    contact_linkedin: Optional[str] = None
    estimated_value: Optional[float] = None
    probability: Optional[float] = None
    expected_close_date: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    lost_reason: Optional[str] = None


@router.patch("/prospects/{prospect_id}")
async def update_prospect(prospect_id: int, request: UpdateProspectRequest):
    """Update prospect fields"""
    pipeline = get_pipeline()
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    
    if "expected_close_date" in updates:
        updates["expected_close_date"] = date.fromisoformat(updates["expected_close_date"])
    
    prospect = pipeline.update_prospect(prospect_id, **updates)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    return pipeline.prospect_to_dict(prospect)


# ══════════════════════════════════════════════════════════════════════
# STAGE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════

class StageChangeRequest(BaseModel):
    stage: str = Field(..., description="New stage: identified, contacted, interested, meeting_scheduled, proposal_sent, negotiation, closed_won, closed_lost")
    notes: Optional[str] = None
    performed_by: Optional[str] = None


@router.post("/prospects/{prospect_id}/stage")
async def change_prospect_stage(prospect_id: int, request: StageChangeRequest):
    """
    Move a prospect to a new funnel stage.
    
    This is the core action of the pipeline - advancing prospects through the embudo.
    """
    pipeline = get_pipeline()
    
    try:
        new_stage = FunnelStage(request.stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {request.stage}. Valid: {[s.value for s in FunnelStage]}")
    
    prospect = pipeline.advance_stage(
        prospect_id=prospect_id,
        new_stage=new_stage,
        performed_by=request.performed_by,
        notes=request.notes,
    )
    
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    return pipeline.prospect_to_dict(prospect)


# ══════════════════════════════════════════════════════════════════════
# ACTIVITY LOGGING
# ══════════════════════════════════════════════════════════════════════

class LogActivityRequest(BaseModel):
    activity_type: str = Field(..., description="email_sent, call_made, meeting_held, note_added, linkedin_message, whatsapp_message, etc.")
    title: str
    description: Optional[str] = None
    performed_by: Optional[str] = None
    channel: Optional[str] = None
    external_url: Optional[str] = None
    email_subject: Optional[str] = None
    email_to: Optional[str] = None


@router.post("/prospects/{prospect_id}/activities")
async def log_prospect_activity(prospect_id: int, request: LogActivityRequest):
    """Log an activity for a prospect (email sent, call, meeting, note, etc.)"""
    pipeline = get_pipeline()
    
    try:
        act_type = ActivityType(request.activity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid activity type: {request.activity_type}")
    
    activity = pipeline.log_activity(
        prospect_id=prospect_id,
        activity_type=act_type,
        title=request.title,
        description=request.description,
        performed_by=request.performed_by,
        channel=request.channel,
        external_url=request.external_url,
        email_subject=request.email_subject,
        email_to=request.email_to,
    )
    
    return pipeline.activity_to_dict(activity)


@router.get("/prospects/{prospect_id}/activities")
async def get_prospect_activities(prospect_id: int, limit: int = Query(50, ge=1, le=200)):
    """Get activity history for a prospect"""
    pipeline = get_pipeline()
    activities = pipeline.get_prospect_activities(prospect_id, limit=limit)
    return {"activities": [pipeline.activity_to_dict(a) for a in activities]}


# ══════════════════════════════════════════════════════════════════════
# BULK OPERATIONS
# ══════════════════════════════════════════════════════════════════════

class BulkCreateFromInstitutionsRequest(BaseModel):
    institution_ids: List[int]
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None


@router.post("/prospects/bulk/from-institutions")
async def bulk_create_from_institutions(request: BulkCreateFromInstitutionsRequest):
    """
    Create prospects from scraped institutions already in the database.
    
    Use this to move institutions from the scraper into the sales pipeline.
    """
    pipeline = get_pipeline()
    return pipeline.bulk_create_from_institutions(
        institution_ids=request.institution_ids,
        source=ProspectSource.SCRAPER,
        assigned_to=request.assigned_to,
        tags=request.tags,
    )


# ══════════════════════════════════════════════════════════════════════
# ANALYTICS & REPORTING
# ══════════════════════════════════════════════════════════════════════

@router.get("/analytics/kpis")
async def get_kpi_cards():
    """Get KPI summary cards for the dashboard"""
    analytics = get_analytics()
    return analytics.get_kpi_cards()


@router.get("/analytics/funnel-chart")
async def get_funnel_chart_data():
    """Get funnel chart data for Chart.js"""
    analytics = get_analytics()
    return analytics.get_funnel_chart()


@router.get("/analytics/timeline")
async def get_timeline(
    days: int = Query(30, ge=7, le=365),
    granularity: str = Query("daily", description="daily, weekly, monthly"),
):
    """Get time series data for line/area charts"""
    analytics = get_analytics()
    return analytics.get_prospects_over_time(days=days, granularity=granularity)


@router.get("/analytics/stage-evolution")
async def get_stage_evolution(days: int = Query(30, ge=7, le=365)):
    """Get stacked area chart data: stage counts over time"""
    analytics = get_analytics()
    return analytics.get_stage_evolution(days=days)


@router.get("/analytics/by-source")
async def get_source_breakdown():
    """Get prospects breakdown by source (pie chart)"""
    analytics = get_analytics()
    return analytics.get_source_breakdown()


@router.get("/analytics/by-city")
async def get_city_breakdown():
    """Get prospects breakdown by city (bar chart)"""
    analytics = get_analytics()
    return analytics.get_city_breakdown()


@router.get("/analytics/by-industry")
async def get_industry_breakdown():
    """Get prospects breakdown by industry (bar chart)"""
    analytics = get_analytics()
    return analytics.get_industry_breakdown()


@router.get("/analytics/activities")
async def get_activity_analytics(days: int = Query(30, ge=7, le=365)):
    """Get activity analytics (by type, by weekday, recent feed)"""
    analytics = get_analytics()
    return analytics.get_activity_summary(days=days)


# ══════════════════════════════════════════════════════════════════════
# CEO REPORT
# ══════════════════════════════════════════════════════════════════════

@router.get("/report/ceo")
async def get_ceo_report(period_days: int = Query(30, ge=7, le=365)):
    """
    Generate a comprehensive CEO report.
    
    Includes executive summary, funnel analytics, top prospects,
    activity trends, and performance metrics.
    """
    pipeline = get_pipeline()
    return pipeline.generate_ceo_report(period_days=period_days)


# ══════════════════════════════════════════════════════════════════════
# ZOHO EMAIL ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@router.get("/email/status")
async def zoho_email_status():
    """Check if Zoho Email is configured"""
    zoho = get_zoho()
    return {
        "configured": bool(zoho and zoho.available),
        "from_email": os.getenv("ZOHO_FROM_EMAIL", ""),
    }


@router.get("/email/templates")
async def get_email_templates():
    """Get available email templates for outreach"""
    return {"templates": ZohoEmailService.get_default_templates()}


class SendEmailRequest(BaseModel):
    prospect_id: Optional[int] = Field(None, description="Link email to a prospect")
    to_email: str
    subject: str
    body: str
    cc: Optional[List[str]] = None
    is_html: bool = True


@router.post("/email/send")
async def send_email(request: SendEmailRequest):
    """
    Send an email via Zoho Mail.
    
    Optionally links the email to a prospect for tracking in the pipeline.
    """
    zoho = get_zoho()
    if not zoho or not zoho.available:
        raise HTTPException(status_code=503, detail="Zoho Email not configured. Set ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN, ZOHO_ACCOUNT_ID, ZOHO_FROM_EMAIL in .env")
    
    result = await zoho.send_email(
        to_email=request.to_email,
        subject=request.subject,
        body=request.body,
        cc=request.cc,
        is_html=request.is_html,
    )
    
    # Log activity if linked to prospect
    if request.prospect_id and result.get("success"):
        pipeline = get_pipeline()
        pipeline.log_activity(
            prospect_id=request.prospect_id,
            activity_type=ActivityType.EMAIL_SENT,
            title=f"Email enviado: {request.subject}",
            description=f"To: {request.to_email}",
            channel="email",
            email_subject=request.subject,
            email_to=request.to_email,
            email_message_id=result.get("message_id"),
        )
    
    return result


class SendTemplatedEmailRequest(BaseModel):
    prospect_id: Optional[int] = None
    to_email: str
    template_id: str = Field(..., description="Template ID from /email/templates")
    variables: Dict[str, str] = Field(..., description="Template variables to replace")


@router.post("/email/send-templated")
async def send_templated_email(request: SendTemplatedEmailRequest):
    """Send a templated email to a prospect"""
    zoho = get_zoho()
    if not zoho or not zoho.available:
        raise HTTPException(status_code=503, detail="Zoho Email not configured")
    
    templates = ZohoEmailService.get_default_templates()
    template = next((t for t in templates if t["id"] == request.template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{request.template_id}' not found")
    
    result = await zoho.send_templated_email(
        to_email=request.to_email,
        subject_template=template["subject"],
        body_template=template["body"],
        variables=request.variables,
    )
    
    if request.prospect_id and result.get("success"):
        pipeline = get_pipeline()
        pipeline.log_activity(
            prospect_id=request.prospect_id,
            activity_type=ActivityType.EMAIL_SENT,
            title=f"Email (template: {template['name']})",
            description=f"To: {request.to_email}",
            channel="email",
            email_subject=template["subject"],
            email_to=request.to_email,
            email_message_id=result.get("message_id"),
        )
    
    return result


class BulkEmailRequest(BaseModel):
    template_id: str
    recipients: List[Dict[str, Any]] = Field(
        ...,
        description="List of {prospect_id, email, variables: {}} dicts",
    )
    delay_seconds: float = Field(2.0, description="Delay between emails")


@router.post("/email/send-bulk")
async def send_bulk_emails(request: BulkEmailRequest):
    """
    Send templated emails to multiple prospects.
    
    Each recipient needs: prospect_id (optional), email, variables.
    Logs activities for linked prospects.
    """
    zoho = get_zoho()
    if not zoho or not zoho.available:
        raise HTTPException(status_code=503, detail="Zoho Email not configured")
    
    templates = ZohoEmailService.get_default_templates()
    template = next((t for t in templates if t["id"] == request.template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{request.template_id}' not found")
    
    result = await zoho.send_bulk_emails(
        recipients=[{"email": r.get("email"), "variables": r.get("variables", {})} for r in request.recipients],
        subject_template=template["subject"],
        body_template=template["body"],
        delay_seconds=request.delay_seconds,
    )
    
    # Log activities for linked prospects
    pipeline = get_pipeline()
    for i, recipient in enumerate(request.recipients):
        pid = recipient.get("prospect_id")
        if pid and i < len(result.get("sent_details", [])):
            sent = result["sent_details"][i] if i < len(result["sent_details"]) else None
            if sent:
                pipeline.log_activity(
                    prospect_id=pid,
                    activity_type=ActivityType.EMAIL_SENT,
                    title=f"Bulk email (template: {template['name']})",
                    channel="email",
                    email_to=recipient.get("email"),
                    email_message_id=sent.get("message_id"),
                )
    
    return result


# ══════════════════════════════════════════════════════════════════════
# PIPELINE SNAPSHOT (call daily)
# ══════════════════════════════════════════════════════════════════════

@router.post("/snapshot")
async def take_pipeline_snapshot():
    """
    Take a daily snapshot of the pipeline state.
    
    Call this once per day to build historical analytics.
    Can be triggered manually or via cron.
    """
    pipeline = get_pipeline()
    snapshot = pipeline.take_snapshot()
    return {
        "date": snapshot.snapshot_date.isoformat(),
        "total_active": snapshot.total_active,
        "total_value": snapshot.total_value,
        "new_prospects": snapshot.new_prospects,
        "conversion_rate": snapshot.conversion_rate,
    }


# ══════════════════════════════════════════════════════════════════════
# EXPORT
# ══════════════════════════════════════════════════════════════════════

@router.get("/export/csv")
async def export_prospects_csv(days: int = Query(90, ge=1, le=365)):
    """Export prospects to CSV for download"""
    analytics = get_analytics()
    data = analytics.get_connect_export(format="csv_ready", days=days)
    
    if not data.get("rows"):
        raise HTTPException(status_code=404, detail="No prospects found")
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data["columns"])
    writer.writeheader()
    writer.writerows(data["rows"])
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=prospects_export_{date.today().isoformat()}.csv"},
    )


@router.get("/export/json")
async def export_prospects_json(days: int = Query(90, ge=1, le=365)):
    """Export prospects and analytics as JSON"""
    analytics = get_analytics()
    return analytics.get_connect_export(format="json", days=days)


# ══════════════════════════════════════════════════════════════════════
# CONNECT DESKTOP APP API
# ══════════════════════════════════════════════════════════════════════

@connect_router.get("/dashboard")
async def connect_dashboard():
    """
    **Connect App**: Get full dashboard data in a single call.
    
    Returns all KPIs, charts, and analytics data needed for the
    Connect desktop app to render its analytics dashboard.
    
    This endpoint is optimized for the Connect app to minimize
    the number of API calls needed.
    """
    analytics = get_analytics()
    return analytics.get_connect_dashboard_data()


@connect_router.get("/sync")
async def connect_sync(
    since: Optional[str] = Query(None, description="ISO date to sync from (e.g., 2026-03-01)"),
    days: int = Query(30, ge=1, le=365),
):
    """
    **Connect App**: Sync pipeline data.
    
    Returns all prospects and analytics data updated since a given date.
    Use this for incremental sync with the Connect desktop app.
    """
    pipeline = get_pipeline()
    analytics = get_analytics()
    
    if since:
        date_from = date.fromisoformat(since)
    else:
        date_from = date.today() - timedelta(days=days)
    
    session = pipeline.get_session()
    try:
        from ..database.pipeline_models import ProspectDB
        
        updated_prospects = (
            session.query(ProspectDB)
            .filter(ProspectDB.updated_at >= datetime.combine(date_from, datetime.min.time()))
            .order_by(ProspectDB.updated_at.desc())
            .all()
        )
        
        return {
            "sync_since": date_from.isoformat(),
            "synced_at": datetime.utcnow().isoformat(),
            "prospects_updated": len(updated_prospects),
            "prospects": [pipeline.prospect_to_dict(p) for p in updated_prospects],
            "analytics": analytics.get_connect_dashboard_data(),
        }
    finally:
        session.close()


@connect_router.get("/kpis")
async def connect_kpis():
    """**Connect App**: Get KPI cards only (lightweight call)"""
    analytics = get_analytics()
    return analytics.get_kpi_cards()


@connect_router.get("/funnel")
async def connect_funnel():
    """**Connect App**: Get funnel chart data only"""
    analytics = get_analytics()
    return analytics.get_funnel_chart()


@connect_router.get("/report")
async def connect_ceo_report(period_days: int = Query(30)):
    """**Connect App**: Get CEO report data"""
    pipeline = get_pipeline()
    return pipeline.generate_ceo_report(period_days=period_days)


@connect_router.get("/export")
async def connect_export(
    format: str = Query("json", description="json or csv_ready"),
    days: int = Query(90),
):
    """**Connect App**: Export data for local analysis"""
    analytics = get_analytics()
    return analytics.get_connect_export(format=format, days=days)
