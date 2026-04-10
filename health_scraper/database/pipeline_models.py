"""
Sales Pipeline (Embudo de Ventas) Database Models
===================================================
Models for tracking prospects through the sales funnel stages.

Stages (default):
  1. Identificado (Identified) - Found via scraping/research
  2. Contactado (Contacted) - First outreach sent
  3. Interesado (Interested) - Responded positively
  4. Reunión Agendada (Meeting Scheduled) - Meeting booked
  5. Propuesta Enviada (Proposal Sent) - Proposal delivered
  6. Negociación (Negotiation) - In negotiation
  7. Cerrado Ganado (Closed Won) - Deal won
  8. Cerrado Perdido (Closed Lost) - Deal lost
"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, Date,
    ForeignKey, UniqueConstraint, Index, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from .models import Base

import enum


class FunnelStage(str, enum.Enum):
    """Sales funnel stages"""
    IDENTIFIED = "identified"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    MEETING_SCHEDULED = "meeting_scheduled"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


# Stage metadata with order, Spanish labels, and colors
FUNNEL_STAGE_META = {
    FunnelStage.IDENTIFIED: {"order": 1, "label": "Identificado", "color": "#94a3b8", "icon": "bi-search"},
    FunnelStage.CONTACTED: {"order": 2, "label": "Contactado", "color": "#60a5fa", "icon": "bi-envelope"},
    FunnelStage.INTERESTED: {"order": 3, "label": "Interesado", "color": "#a78bfa", "icon": "bi-hand-thumbs-up"},
    FunnelStage.MEETING_SCHEDULED: {"order": 4, "label": "Reunión Agendada", "color": "#fbbf24", "icon": "bi-calendar-check"},
    FunnelStage.PROPOSAL_SENT: {"order": 5, "label": "Propuesta Enviada", "color": "#f97316", "icon": "bi-file-text"},
    FunnelStage.NEGOTIATION: {"order": 6, "label": "Negociación", "color": "#fb923c", "icon": "bi-chat-dots"},
    FunnelStage.CLOSED_WON: {"order": 7, "label": "Cerrado Ganado", "color": "#10b981", "icon": "bi-trophy"},
    FunnelStage.CLOSED_LOST: {"order": 8, "label": "Cerrado Perdido", "color": "#ef4444", "icon": "bi-x-circle"},
}


class ProspectSource(str, enum.Enum):
    """Where the prospect was found"""
    SCRAPER = "scraper"
    EXCEL_IMPORT = "excel_import"
    MANUAL = "manual"
    HUBSPOT = "hubspot"
    LINKEDIN = "linkedin"
    REFERRAL = "referral"
    CONFERENCE = "conference"
    TWITTER = "twitter"
    OTHER = "other"


class ActivityType(str, enum.Enum):
    """Types of prospect activities"""
    STAGE_CHANGE = "stage_change"
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_REPLIED = "email_replied"
    CALL_MADE = "call_made"
    MEETING_HELD = "meeting_held"
    NOTE_ADDED = "note_added"
    LINKEDIN_MESSAGE = "linkedin_message"
    WHATSAPP_MESSAGE = "whatsapp_message"
    PROPOSAL_SENT = "proposal_sent"
    DOCUMENT_SHARED = "document_shared"
    HUBSPOT_SYNCED = "hubspot_synced"
    LINEAR_TASK_CREATED = "linear_task_created"


class ProspectDB(Base):
    """
    Main prospect tracking table for the sales funnel.
    
    Each prospect represents a potential customer being tracked
    through the sales pipeline stages.
    """
    __tablename__ = "prospects"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Company info
    company_name = Column(String(255), nullable=False, index=True)
    company_domain = Column(String(255), nullable=True)
    company_nit = Column(String(20), nullable=True)
    industry = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    department = Column(String(100), nullable=True)
    employee_count = Column(Integer, nullable=True)
    
    # Primary contact
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    contact_position = Column(String(255), nullable=True)
    contact_linkedin = Column(String(500), nullable=True)
    
    # Pipeline state
    current_stage = Column(
        SQLEnum(FunnelStage), 
        default=FunnelStage.IDENTIFIED, 
        nullable=False, 
        index=True
    )
    previous_stage = Column(SQLEnum(FunnelStage), nullable=True)
    
    # Deal info
    estimated_value = Column(Float, nullable=True)  # Estimated deal value (COP/USD)
    currency = Column(String(3), default="COP")
    probability = Column(Float, nullable=True)  # Win probability (0-100)
    expected_close_date = Column(Date, nullable=True)
    
    # Source & attribution
    source = Column(SQLEnum(ProspectSource), default=ProspectSource.MANUAL, index=True)
    source_detail = Column(String(500), nullable=True)  # e.g., "Excel file: companies_march.xlsx"
    assigned_to = Column(String(255), nullable=True)  # Assignee name/email
    
    # External IDs (linking to other systems)
    hubspot_company_id = Column(String(50), nullable=True, index=True)
    hubspot_deal_id = Column(String(50), nullable=True)
    linear_issue_id = Column(String(50), nullable=True)
    institution_db_id = Column(Integer, ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True)
    
    # Engagement tracking
    emails_sent = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_replied = Column(Integer, default=0)
    calls_made = Column(Integer, default=0)
    meetings_held = Column(Integer, default=0)
    
    # Notes
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list)  # ["ips", "dental", "high-priority"]
    
    # Custom data
    custom_fields = Column(JSON, default=dict)
    
    # Scoring
    lead_score = Column(Float, default=0)  # 0-100 based on engagement & fit
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    first_contacted_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    lost_reason = Column(String(500), nullable=True)
    
    # Relationships
    activities = relationship("ProspectActivityDB", back_populates="prospect", cascade="all, delete-orphan", order_by="ProspectActivityDB.created_at.desc()")
    institution = relationship("InstitutionDB", foreign_keys=[institution_db_id])
    
    __table_args__ = (
        Index('idx_prospect_stage_active', 'current_stage', 'is_active'),
        Index('idx_prospect_source', 'source', 'created_at'),
        Index('idx_prospect_assigned', 'assigned_to', 'current_stage'),
    )
    
    def __repr__(self):
        return f"<Prospect(id={self.id}, company='{self.company_name}', stage='{self.current_stage}')>"


class ProspectActivityDB(Base):
    """
    Activity log for each prospect.
    
    Records every interaction and stage change for full audit trail.
    """
    __tablename__ = "prospect_activities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Activity details
    activity_type = Column(SQLEnum(ActivityType), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Stage transition (for stage_change type)
    from_stage = Column(SQLEnum(FunnelStage), nullable=True)
    to_stage = Column(SQLEnum(FunnelStage), nullable=True)
    
    # Email tracking
    email_subject = Column(String(500), nullable=True)
    email_to = Column(String(255), nullable=True)
    email_message_id = Column(String(255), nullable=True)  # For tracking opens/replies
    
    # Metadata
    performed_by = Column(String(255), nullable=True)
    channel = Column(String(50), nullable=True)  # email, phone, linkedin, whatsapp, in-person
    external_url = Column(String(1000), nullable=True)  # Link to HubSpot, Linear, etc.
    extra_data = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    prospect = relationship("ProspectDB", back_populates="activities")
    
    def __repr__(self):
        return f"<Activity(id={self.id}, type='{self.activity_type}', prospect_id={self.prospect_id})>"


class PipelineSnapshotDB(Base):
    """
    Daily snapshot of the pipeline state for historical analytics.
    
    Captures the count of prospects in each stage daily so we can
    generate time-series charts showing how the funnel evolves.
    """
    __tablename__ = "pipeline_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    
    # Counts per stage
    identified_count = Column(Integer, default=0)
    contacted_count = Column(Integer, default=0)
    interested_count = Column(Integer, default=0)
    meeting_scheduled_count = Column(Integer, default=0)
    proposal_sent_count = Column(Integer, default=0)
    negotiation_count = Column(Integer, default=0)
    closed_won_count = Column(Integer, default=0)
    closed_lost_count = Column(Integer, default=0)
    
    # Totals
    total_active = Column(Integer, default=0)
    total_value = Column(Float, default=0)  # Sum of estimated values
    
    # Conversion metrics
    conversion_rate = Column(Float, nullable=True)  # won / (won + lost) %
    avg_deal_value = Column(Float, nullable=True)
    avg_days_to_close = Column(Float, nullable=True)
    
    # New metrics for the day
    new_prospects = Column(Integer, default=0)
    prospects_advanced = Column(Integer, default=0)  # Moved to next stage
    prospects_lost = Column(Integer, default=0)
    prospects_won = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('snapshot_date', name='uq_snapshot_date'),
    )
    
    def __repr__(self):
        return f"<PipelineSnapshot(date='{self.snapshot_date}', active={self.total_active})>"


class EmailCampaignDB(Base):
    """
    Track email campaigns/sequences sent via Zoho Email.
    """
    __tablename__ = "email_campaigns"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    name = Column(String(255), nullable=False)
    subject_template = Column(String(500), nullable=False)
    body_template = Column(Text, nullable=False)
    
    # Stats
    total_sent = Column(Integer, default=0)
    total_opened = Column(Integer, default=0)
    total_replied = Column(Integer, default=0)
    total_bounced = Column(Integer, default=0)
    
    # Config
    from_email = Column(String(255), nullable=True)
    reply_to = Column(String(255), nullable=True)
    
    status = Column(String(50), default="draft")  # draft, active, paused, completed
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<EmailCampaign(id={self.id}, name='{self.name}', status='{self.status}')>"
