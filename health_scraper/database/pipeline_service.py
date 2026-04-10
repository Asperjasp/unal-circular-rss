"""
Pipeline Service (Embudo de Ventas)
=====================================
Manages the sales funnel: creating prospects, advancing stages,
recording activities, and providing analytics data.

This is the core service that ties together:
- Prospect tracking through funnel stages
- Activity logging for audit trail
- Pipeline snapshots for historical analytics
- Integration hooks for HubSpot/Linear sync
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import func, and_, or_, case, extract
from sqlalchemy.orm import Session

from .models import Base, InstitutionDB
from .pipeline_models import (
    ProspectDB, ProspectActivityDB, PipelineSnapshotDB, EmailCampaignDB,
    FunnelStage, ProspectSource, ActivityType, FUNNEL_STAGE_META
)
from ..config import config

logger = logging.getLogger(__name__)


class PipelineService:
    """
    Service for managing the sales pipeline (embudo de ventas).
    
    Usage:
        pipeline = PipelineService()
        
        # Create a prospect
        prospect = pipeline.create_prospect(
            company_name="SubRedSur",
            source=ProspectSource.SCRAPER,
            city="Bogotá"
        )
        
        # Advance stage
        pipeline.advance_stage(prospect.id, FunnelStage.CONTACTED)
        
        # Get funnel analytics  
        analytics = pipeline.get_funnel_analytics()
    """
    
    def __init__(self, database_url: Optional[str] = None):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        self.database_url = database_url or config.database_url
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create pipeline tables
        Base.metadata.create_all(self.engine)
        logger.info("Pipeline service initialized")
    
    def get_session(self) -> Session:
        return self.SessionLocal()
    
    # =========================================================================
    # PROSPECT CRUD
    # =========================================================================
    
    def create_prospect(
        self,
        company_name: str,
        source: ProspectSource = ProspectSource.MANUAL,
        source_detail: Optional[str] = None,
        company_domain: Optional[str] = None,
        company_nit: Optional[str] = None,
        industry: Optional[str] = None,
        city: Optional[str] = None,
        department: Optional[str] = None,
        employee_count: Optional[int] = None,
        contact_name: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        contact_position: Optional[str] = None,
        contact_linkedin: Optional[str] = None,
        estimated_value: Optional[float] = None,
        assigned_to: Optional[str] = None,
        hubspot_company_id: Optional[str] = None,
        linear_issue_id: Optional[str] = None,
        institution_db_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> ProspectDB:
        """
        Create a new prospect in the pipeline.
        Returns the created ProspectDB object.
        """
        session = self.get_session()
        try:
            prospect = ProspectDB(
                company_name=company_name,
                company_domain=company_domain,
                company_nit=company_nit,
                industry=industry,
                city=city,
                department=department,
                employee_count=employee_count,
                contact_name=contact_name,
                contact_email=contact_email,
                contact_phone=contact_phone,
                contact_position=contact_position,
                contact_linkedin=contact_linkedin,
                current_stage=FunnelStage.IDENTIFIED,
                estimated_value=estimated_value,
                source=source,
                source_detail=source_detail,
                assigned_to=assigned_to,
                hubspot_company_id=hubspot_company_id,
                linear_issue_id=linear_issue_id,
                institution_db_id=institution_db_id,
                tags=tags or [],
                notes=notes,
            )
            session.add(prospect)
            session.flush()
            
            # Log creation activity
            activity = ProspectActivityDB(
                prospect_id=prospect.id,
                activity_type=ActivityType.STAGE_CHANGE,
                title=f"Prospecto creado: {company_name}",
                description=f"Fuente: {source.value}" + (f" ({source_detail})" if source_detail else ""),
                to_stage=FunnelStage.IDENTIFIED,
                performed_by=assigned_to,
            )
            session.add(activity)
            session.commit()
            session.refresh(prospect)
            
            logger.info(f"Created prospect: {company_name} (ID: {prospect.id})")
            return prospect
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating prospect: {e}")
            raise
        finally:
            session.close()
    
    def get_prospect(self, prospect_id: int) -> Optional[ProspectDB]:
        """Get a single prospect by ID"""
        session = self.get_session()
        try:
            return session.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
        finally:
            session.close()
    
    def list_prospects(
        self,
        stage: Optional[FunnelStage] = None,
        source: Optional[ProspectSource] = None,
        city: Optional[str] = None,
        assigned_to: Optional[str] = None,
        is_active: bool = True,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = "updated_at",
        sort_desc: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ProspectDB], int]:
        """
        List prospects with filters.
        Returns (prospects, total_count).
        """
        session = self.get_session()
        try:
            query = session.query(ProspectDB)
            
            if is_active is not None:
                query = query.filter(ProspectDB.is_active == is_active)
            if stage:
                query = query.filter(ProspectDB.current_stage == stage)
            if source:
                query = query.filter(ProspectDB.source == source)
            if city:
                query = query.filter(ProspectDB.city.ilike(f"%{city}%"))
            if assigned_to:
                query = query.filter(ProspectDB.assigned_to == assigned_to)
            if search:
                query = query.filter(
                    or_(
                        ProspectDB.company_name.ilike(f"%{search}%"),
                        ProspectDB.contact_name.ilike(f"%{search}%"),
                        ProspectDB.contact_email.ilike(f"%{search}%"),
                    )
                )
            
            total = query.count()
            
            # Sort
            sort_col = getattr(ProspectDB, sort_by, ProspectDB.updated_at)
            if sort_desc:
                query = query.order_by(sort_col.desc())
            else:
                query = query.order_by(sort_col.asc())
            
            prospects = query.offset(offset).limit(limit).all()
            return prospects, total
        finally:
            session.close()
    
    def update_prospect(self, prospect_id: int, **kwargs) -> Optional[ProspectDB]:
        """Update prospect fields"""
        session = self.get_session()
        try:
            prospect = session.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
            if not prospect:
                return None
            
            for key, value in kwargs.items():
                if hasattr(prospect, key) and value is not None:
                    setattr(prospect, key, value)
            
            prospect.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(prospect)
            return prospect
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    # =========================================================================
    # STAGE MANAGEMENT
    # =========================================================================
    
    def advance_stage(
        self,
        prospect_id: int,
        new_stage: FunnelStage,
        performed_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[ProspectDB]:
        """
        Move a prospect to a new funnel stage.
        Records the transition in the activity log.
        """
        session = self.get_session()
        try:
            prospect = session.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
            if not prospect:
                return None
            
            old_stage = prospect.current_stage
            if old_stage == new_stage:
                return prospect
            
            # Update prospect
            prospect.previous_stage = old_stage
            prospect.current_stage = new_stage
            prospect.updated_at = datetime.utcnow()
            prospect.last_activity_at = datetime.utcnow()
            
            # Set first_contacted_at if moving to contacted
            if new_stage == FunnelStage.CONTACTED and not prospect.first_contacted_at:
                prospect.first_contacted_at = datetime.utcnow()
            
            # Set closed_at if closing
            if new_stage in (FunnelStage.CLOSED_WON, FunnelStage.CLOSED_LOST):
                prospect.closed_at = datetime.utcnow()
                if new_stage == FunnelStage.CLOSED_LOST:
                    prospect.is_active = False
            
            # Log the stage change
            old_label = FUNNEL_STAGE_META[old_stage]["label"]
            new_label = FUNNEL_STAGE_META[new_stage]["label"]
            
            activity = ProspectActivityDB(
                prospect_id=prospect_id,
                activity_type=ActivityType.STAGE_CHANGE,
                title=f"Etapa: {old_label} → {new_label}",
                description=notes,
                from_stage=old_stage,
                to_stage=new_stage,
                performed_by=performed_by,
            )
            session.add(activity)
            session.commit()
            session.refresh(prospect)
            
            logger.info(f"Prospect {prospect.company_name}: {old_stage.value} → {new_stage.value}")
            return prospect
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    # =========================================================================
    # ACTIVITY LOGGING
    # =========================================================================
    
    def log_activity(
        self,
        prospect_id: int,
        activity_type: ActivityType,
        title: str,
        description: Optional[str] = None,
        performed_by: Optional[str] = None,
        channel: Optional[str] = None,
        external_url: Optional[str] = None,
        metadata: Optional[Dict] = None,
        email_subject: Optional[str] = None,
        email_to: Optional[str] = None,
        email_message_id: Optional[str] = None,
    ) -> ProspectActivityDB:
        """Log an activity for a prospect"""
        session = self.get_session()
        try:
            activity = ProspectActivityDB(
                prospect_id=prospect_id,
                activity_type=activity_type,
                title=title,
                description=description,
                performed_by=performed_by,
                channel=channel,
                external_url=external_url,
                metadata=metadata or {},
                email_subject=email_subject,
                email_to=email_to,
                email_message_id=email_message_id,
            )
            session.add(activity)
            
            # Update prospect counters
            prospect = session.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
            if prospect:
                prospect.last_activity_at = datetime.utcnow()
                if activity_type == ActivityType.EMAIL_SENT:
                    prospect.emails_sent = (prospect.emails_sent or 0) + 1
                elif activity_type == ActivityType.EMAIL_OPENED:
                    prospect.emails_opened = (prospect.emails_opened or 0) + 1
                elif activity_type == ActivityType.EMAIL_REPLIED:
                    prospect.emails_replied = (prospect.emails_replied or 0) + 1
                elif activity_type == ActivityType.CALL_MADE:
                    prospect.calls_made = (prospect.calls_made or 0) + 1
                elif activity_type == ActivityType.MEETING_HELD:
                    prospect.meetings_held = (prospect.meetings_held or 0) + 1
            
            session.commit()
            session.refresh(activity)
            return activity
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_prospect_activities(
        self,
        prospect_id: int,
        limit: int = 50,
    ) -> List[ProspectActivityDB]:
        """Get activity history for a prospect"""
        session = self.get_session()
        try:
            return (
                session.query(ProspectActivityDB)
                .filter(ProspectActivityDB.prospect_id == prospect_id)
                .order_by(ProspectActivityDB.created_at.desc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()
    
    # =========================================================================
    # FUNNEL ANALYTICS
    # =========================================================================
    
    def get_funnel_analytics(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        assigned_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get complete funnel analytics for CEO reporting.
        
        Returns:
            - stage_counts: Number of prospects in each stage
            - stage_values: Total estimated value per stage
            - conversion_rates: Stage-to-stage conversion rates
            - summary: Total prospects, value, etc.
            - velocity: Average days in each stage
            - sources: Breakdown by prospect source
        """
        session = self.get_session()
        try:
            query = session.query(ProspectDB)
            
            if date_from:
                query = query.filter(ProspectDB.created_at >= datetime.combine(date_from, datetime.min.time()))
            if date_to:
                query = query.filter(ProspectDB.created_at <= datetime.combine(date_to, datetime.max.time()))
            if assigned_to:
                query = query.filter(ProspectDB.assigned_to == assigned_to)
            
            all_prospects = query.all()
            active_prospects = [p for p in all_prospects if p.is_active]
            
            # Stage counts & values
            stage_counts = {}
            stage_values = {}
            for stage in FunnelStage:
                count = len([p for p in all_prospects if p.current_stage == stage])
                value = sum(p.estimated_value or 0 for p in all_prospects if p.current_stage == stage)
                stage_counts[stage.value] = count
                stage_values[stage.value] = value
            
            # Conversion rates (stage-to-stage)
            stages_ordered = sorted(FunnelStage, key=lambda s: FUNNEL_STAGE_META[s]["order"])
            conversion_rates = {}
            for i in range(len(stages_ordered) - 1):
                current = stages_ordered[i]
                next_stage = stages_ordered[i + 1]
                current_count = stage_counts.get(current.value, 0)
                # Count all prospects that reached at least the next stage
                reached_next = len([
                    p for p in all_prospects 
                    if FUNNEL_STAGE_META[p.current_stage]["order"] >= FUNNEL_STAGE_META[next_stage]["order"]
                ])
                total_at_or_past = len([
                    p for p in all_prospects
                    if FUNNEL_STAGE_META[p.current_stage]["order"] >= FUNNEL_STAGE_META[current]["order"]
                ])
                if total_at_or_past > 0:
                    rate = (reached_next / total_at_or_past) * 100
                else:
                    rate = 0
                conversion_rates[f"{current.value}_to_{next_stage.value}"] = round(rate, 1)
            
            # Source breakdown
            sources = {}
            for p in all_prospects:
                src = p.source.value if p.source else "unknown"
                sources[src] = sources.get(src, 0) + 1
            
            # Win/loss stats
            won = len([p for p in all_prospects if p.current_stage == FunnelStage.CLOSED_WON])
            lost = len([p for p in all_prospects if p.current_stage == FunnelStage.CLOSED_LOST])
            win_rate = (won / (won + lost) * 100) if (won + lost) > 0 else 0
            
            # Average deal value (won deals)
            won_values = [p.estimated_value for p in all_prospects if p.current_stage == FunnelStage.CLOSED_WON and p.estimated_value]
            avg_deal_value = sum(won_values) / len(won_values) if won_values else 0
            
            # Total pipeline value (active non-closed)
            pipeline_value = sum(p.estimated_value or 0 for p in active_prospects if p.current_stage not in (FunnelStage.CLOSED_WON, FunnelStage.CLOSED_LOST))
            
            # Velocity: avg days to close (for closed deals)
            days_to_close = []
            for p in all_prospects:
                if p.closed_at and p.created_at:
                    delta = (p.closed_at - p.created_at).days
                    days_to_close.append(delta)
            avg_days = sum(days_to_close) / len(days_to_close) if days_to_close else 0
            
            # City breakdown
            cities = {}
            for p in all_prospects:
                c = p.city or "Sin ciudad"
                cities[c] = cities.get(c, 0) + 1
            
            # Industry breakdown
            industries = {}
            for p in all_prospects:
                ind = p.industry or "Sin sector"
                industries[ind] = industries.get(ind, 0) + 1
            
            return {
                "funnel": {
                    "stages": [
                        {
                            "id": stage.value,
                            "label": FUNNEL_STAGE_META[stage]["label"],
                            "color": FUNNEL_STAGE_META[stage]["color"],
                            "icon": FUNNEL_STAGE_META[stage]["icon"],
                            "count": stage_counts.get(stage.value, 0),
                            "value": stage_values.get(stage.value, 0),
                        }
                        for stage in stages_ordered
                    ],
                    "conversion_rates": conversion_rates,
                },
                "summary": {
                    "total_prospects": len(all_prospects),
                    "active_prospects": len(active_prospects),
                    "pipeline_value": pipeline_value,
                    "won_deals": won,
                    "lost_deals": lost,
                    "win_rate": round(win_rate, 1),
                    "avg_deal_value": round(avg_deal_value, 2),
                    "avg_days_to_close": round(avg_days, 1),
                },
                "breakdown": {
                    "by_source": sources,
                    "by_city": dict(sorted(cities.items(), key=lambda x: x[1], reverse=True)[:10]),
                    "by_industry": dict(sorted(industries.items(), key=lambda x: x[1], reverse=True)[:10]),
                },
                "stage_meta": {
                    stage.value: FUNNEL_STAGE_META[stage] for stage in FunnelStage
                },
            }
        finally:
            session.close()
    
    def get_timeline_analytics(
        self,
        days: int = 30,
        assigned_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get time-series data for charts.
        
        Returns daily counts of:
        - New prospects created
        - Stage changes
        - Activities performed
        - Deals won/lost
        """
        session = self.get_session()
        try:
            start_date = date.today() - timedelta(days=days)
            
            # Check for snapshots first
            snapshots = (
                session.query(PipelineSnapshotDB)
                .filter(PipelineSnapshotDB.snapshot_date >= start_date)
                .order_by(PipelineSnapshotDB.snapshot_date)
                .all()
            )
            
            if snapshots:
                return {
                    "period": f"last_{days}_days",
                    "data": [
                        {
                            "date": s.snapshot_date.isoformat(),
                            "total_active": s.total_active,
                            "new_prospects": s.new_prospects,
                            "prospects_won": s.prospects_won,
                            "prospects_lost": s.prospects_lost,
                            "total_value": s.total_value,
                            "conversion_rate": s.conversion_rate,
                            "stages": {
                                "identified": s.identified_count,
                                "contacted": s.contacted_count,
                                "interested": s.interested_count,
                                "meeting_scheduled": s.meeting_scheduled_count,
                                "proposal_sent": s.proposal_sent_count,
                                "negotiation": s.negotiation_count,
                                "closed_won": s.closed_won_count,
                                "closed_lost": s.closed_lost_count,
                            },
                        }
                        for s in snapshots
                    ],
                }
            
            # Fallback: compute from activities
            activities = (
                session.query(
                    func.date(ProspectActivityDB.created_at).label("day"),
                    ProspectActivityDB.activity_type,
                    func.count().label("count"),
                )
                .filter(ProspectActivityDB.created_at >= datetime.combine(start_date, datetime.min.time()))
                .group_by(func.date(ProspectActivityDB.created_at), ProspectActivityDB.activity_type)
                .all()
            )
            
            # Build day-by-day data
            daily_data = {}
            current = start_date
            while current <= date.today():
                daily_data[current.isoformat()] = {
                    "date": current.isoformat(),
                    "new_prospects": 0,
                    "stage_changes": 0,
                    "emails_sent": 0,
                    "activities_total": 0,
                }
                current += timedelta(days=1)
            
            for row in activities:
                day_str = row.day.isoformat() if hasattr(row.day, 'isoformat') else str(row.day)
                if day_str in daily_data:
                    daily_data[day_str]["activities_total"] += row.count
                    if row.activity_type == ActivityType.STAGE_CHANGE:
                        daily_data[day_str]["stage_changes"] += row.count
                    elif row.activity_type == ActivityType.EMAIL_SENT:
                        daily_data[day_str]["emails_sent"] += row.count
            
            # Count new prospects per day
            new_per_day = (
                session.query(
                    func.date(ProspectDB.created_at).label("day"),
                    func.count().label("count"),
                )
                .filter(ProspectDB.created_at >= datetime.combine(start_date, datetime.min.time()))
                .group_by(func.date(ProspectDB.created_at))
                .all()
            )
            for row in new_per_day:
                day_str = row.day.isoformat() if hasattr(row.day, 'isoformat') else str(row.day)
                if day_str in daily_data:
                    daily_data[day_str]["new_prospects"] = row.count
            
            return {
                "period": f"last_{days}_days",
                "data": list(daily_data.values()),
            }
        finally:
            session.close()
    
    def take_snapshot(self) -> PipelineSnapshotDB:
        """
        Take a daily snapshot of the pipeline state.
        Call this once per day (e.g., via cron or startup check).
        """
        session = self.get_session()
        try:
            today = date.today()
            
            # Check if snapshot already exists
            existing = session.query(PipelineSnapshotDB).filter(
                PipelineSnapshotDB.snapshot_date == today
            ).first()
            if existing:
                return existing
            
            # Count prospects per stage
            stage_counts = {}
            for stage in FunnelStage:
                count = session.query(ProspectDB).filter(
                    ProspectDB.current_stage == stage
                ).count()
                stage_counts[stage] = count
            
            # Total value
            total_value = session.query(func.sum(ProspectDB.estimated_value)).filter(
                ProspectDB.is_active == True
            ).scalar() or 0
            
            # Today's new
            today_start = datetime.combine(today, datetime.min.time())
            new_today = session.query(ProspectDB).filter(
                ProspectDB.created_at >= today_start
            ).count()
            
            # Won/lost today
            won_today = session.query(ProspectActivityDB).filter(
                ProspectActivityDB.created_at >= today_start,
                ProspectActivityDB.to_stage == FunnelStage.CLOSED_WON,
            ).count()
            lost_today = session.query(ProspectActivityDB).filter(
                ProspectActivityDB.created_at >= today_start,
                ProspectActivityDB.to_stage == FunnelStage.CLOSED_LOST,
            ).count()
            
            # Conversion rate
            won_total = stage_counts.get(FunnelStage.CLOSED_WON, 0)
            lost_total = stage_counts.get(FunnelStage.CLOSED_LOST, 0)
            conversion = (won_total / (won_total + lost_total) * 100) if (won_total + lost_total) > 0 else None
            
            active_total = sum(
                v for k, v in stage_counts.items() 
                if k not in (FunnelStage.CLOSED_WON, FunnelStage.CLOSED_LOST)
            )
            
            snapshot = PipelineSnapshotDB(
                snapshot_date=today,
                identified_count=stage_counts.get(FunnelStage.IDENTIFIED, 0),
                contacted_count=stage_counts.get(FunnelStage.CONTACTED, 0),
                interested_count=stage_counts.get(FunnelStage.INTERESTED, 0),
                meeting_scheduled_count=stage_counts.get(FunnelStage.MEETING_SCHEDULED, 0),
                proposal_sent_count=stage_counts.get(FunnelStage.PROPOSAL_SENT, 0),
                negotiation_count=stage_counts.get(FunnelStage.NEGOTIATION, 0),
                closed_won_count=stage_counts.get(FunnelStage.CLOSED_WON, 0),
                closed_lost_count=stage_counts.get(FunnelStage.CLOSED_LOST, 0),
                total_active=active_total,
                total_value=total_value,
                conversion_rate=conversion,
                new_prospects=new_today,
                prospects_won=won_today,
                prospects_lost=lost_today,
            )
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)
            
            logger.info(f"Pipeline snapshot taken: {today} (active={active_total})")
            return snapshot
        except Exception as e:
            session.rollback()
            logger.error(f"Error taking snapshot: {e}")
            raise
        finally:
            session.close()
    
    # =========================================================================
    # CEO REPORT
    # =========================================================================
    
    def generate_ceo_report(
        self,
        period_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive report for the CEO.
        
        Includes:
        - Executive summary
        - Funnel analytics
        - Timeline trends
        - Top prospects
        - Performance metrics
        - Recommendations
        """
        funnel = self.get_funnel_analytics()
        timeline = self.get_timeline_analytics(days=period_days)
        
        session = self.get_session()
        try:
            # Top prospects by estimated value
            top_by_value = (
                session.query(ProspectDB)
                .filter(ProspectDB.is_active == True, ProspectDB.estimated_value.isnot(None))
                .order_by(ProspectDB.estimated_value.desc())
                .limit(10)
                .all()
            )
            
            # Most engaged prospects
            top_by_activity = (
                session.query(ProspectDB)
                .filter(ProspectDB.is_active == True)
                .order_by(ProspectDB.lead_score.desc())
                .limit(10)
                .all()
            )
            
            # Stale prospects (no activity in 7+ days)
            stale_threshold = datetime.utcnow() - timedelta(days=7)
            stale = (
                session.query(ProspectDB)
                .filter(
                    ProspectDB.is_active == True,
                    or_(
                        ProspectDB.last_activity_at < stale_threshold,
                        ProspectDB.last_activity_at.is_(None),
                    ),
                    ProspectDB.current_stage.notin_([FunnelStage.CLOSED_WON, FunnelStage.CLOSED_LOST])
                )
                .count()
            )
            
            # Activity summary for period
            period_start = datetime.utcnow() - timedelta(days=period_days)
            activity_counts = (
                session.query(
                    ProspectActivityDB.activity_type,
                    func.count().label("count"),
                )
                .filter(ProspectActivityDB.created_at >= period_start)
                .group_by(ProspectActivityDB.activity_type)
                .all()
            )
            
            activity_summary = {row.activity_type.value: row.count for row in activity_counts}
            
            return {
                "report_date": date.today().isoformat(),
                "period_days": period_days,
                "executive_summary": {
                    "total_prospects": funnel["summary"]["total_prospects"],
                    "active_in_pipeline": funnel["summary"]["active_prospects"],
                    "pipeline_value": funnel["summary"]["pipeline_value"],
                    "win_rate": funnel["summary"]["win_rate"],
                    "deals_won": funnel["summary"]["won_deals"],
                    "deals_lost": funnel["summary"]["lost_deals"],
                    "avg_deal_value": funnel["summary"]["avg_deal_value"],
                    "avg_days_to_close": funnel["summary"]["avg_days_to_close"],
                    "stale_prospects": stale,
                },
                "funnel": funnel["funnel"],
                "breakdown": funnel["breakdown"],
                "activity_summary": activity_summary,
                "timeline": timeline,
                "top_prospects": {
                    "by_value": [
                        {
                            "id": p.id,
                            "company": p.company_name,
                            "stage": p.current_stage.value,
                            "stage_label": FUNNEL_STAGE_META[p.current_stage]["label"],
                            "value": p.estimated_value,
                            "city": p.city,
                        }
                        for p in top_by_value
                    ],
                    "by_engagement": [
                        {
                            "id": p.id,
                            "company": p.company_name,
                            "stage": p.current_stage.value,
                            "lead_score": p.lead_score,
                            "emails_sent": p.emails_sent,
                            "meetings_held": p.meetings_held,
                        }
                        for p in top_by_activity
                    ],
                },
            }
        finally:
            session.close()
    
    # =========================================================================
    # BULK OPERATIONS (for importing from scraper/Excel)
    # =========================================================================
    
    def bulk_create_from_institutions(
        self,
        institution_ids: List[int],
        source: ProspectSource = ProspectSource.SCRAPER,
        assigned_to: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create prospects from existing scraped institutions.
        Skips institutions already in the pipeline.
        """
        session = self.get_session()
        try:
            created = []
            skipped = []
            
            for inst_id in institution_ids:
                # Check if already in pipeline
                existing = session.query(ProspectDB).filter(
                    ProspectDB.institution_db_id == inst_id
                ).first()
                if existing:
                    skipped.append({"institution_id": inst_id, "reason": "Already in pipeline"})
                    continue
                
                institution = session.query(InstitutionDB).filter(
                    InstitutionDB.id == inst_id
                ).first()
                if not institution:
                    skipped.append({"institution_id": inst_id, "reason": "Not found"})
                    continue
                
                # Get primary contact if available
                contact = institution.contacts[0] if institution.contacts else None
                
                prospect = ProspectDB(
                    company_name=institution.name,
                    company_domain=institution.website,
                    company_nit=institution.nit,
                    industry=institution.specialty_type or institution.institution_type,
                    city=institution.city,
                    department=institution.department,
                    employee_count=institution.employee_count,
                    contact_name=contact.name if contact else None,
                    contact_email=contact.email if contact else institution.email,
                    contact_phone=contact.phone if contact else institution.phone,
                    contact_position=contact.position if contact else None,
                    current_stage=FunnelStage.IDENTIFIED,
                    source=source,
                    source_detail=f"Institution DB ID: {inst_id}",
                    assigned_to=assigned_to,
                    institution_db_id=inst_id,
                    tags=tags or [],
                )
                session.add(prospect)
                session.flush()
                
                # Log creation
                activity = ProspectActivityDB(
                    prospect_id=prospect.id,
                    activity_type=ActivityType.STAGE_CHANGE,
                    title=f"Prospecto creado desde scraper: {institution.name}",
                    to_stage=FunnelStage.IDENTIFIED,
                    performed_by=assigned_to,
                )
                session.add(activity)
                created.append({"institution_id": inst_id, "prospect_id": prospect.id, "name": institution.name})
            
            session.commit()
            
            return {
                "created": len(created),
                "skipped": len(skipped),
                "created_prospects": created,
                "skipped_prospects": skipped,
            }
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def prospect_to_dict(self, prospect: ProspectDB) -> Dict[str, Any]:
        """Convert a ProspectDB to a serializable dict"""
        return {
            "id": prospect.id,
            "company_name": prospect.company_name,
            "company_domain": prospect.company_domain,
            "company_nit": prospect.company_nit,
            "industry": prospect.industry,
            "city": prospect.city,
            "department": prospect.department,
            "employee_count": prospect.employee_count,
            "contact_name": prospect.contact_name,
            "contact_email": prospect.contact_email,
            "contact_phone": prospect.contact_phone,
            "contact_position": prospect.contact_position,
            "contact_linkedin": prospect.contact_linkedin,
            "current_stage": prospect.current_stage.value,
            "current_stage_label": FUNNEL_STAGE_META[prospect.current_stage]["label"],
            "current_stage_color": FUNNEL_STAGE_META[prospect.current_stage]["color"],
            "previous_stage": prospect.previous_stage.value if prospect.previous_stage else None,
            "estimated_value": prospect.estimated_value,
            "currency": prospect.currency,
            "probability": prospect.probability,
            "expected_close_date": prospect.expected_close_date.isoformat() if prospect.expected_close_date else None,
            "source": prospect.source.value if prospect.source else None,
            "source_detail": prospect.source_detail,
            "assigned_to": prospect.assigned_to,
            "hubspot_company_id": prospect.hubspot_company_id,
            "hubspot_deal_id": prospect.hubspot_deal_id,
            "linear_issue_id": prospect.linear_issue_id,
            "institution_db_id": prospect.institution_db_id,
            "emails_sent": prospect.emails_sent,
            "emails_opened": prospect.emails_opened,
            "emails_replied": prospect.emails_replied,
            "calls_made": prospect.calls_made,
            "meetings_held": prospect.meetings_held,
            "notes": prospect.notes,
            "tags": prospect.tags,
            "lead_score": prospect.lead_score,
            "is_active": prospect.is_active,
            "lost_reason": prospect.lost_reason,
            "created_at": prospect.created_at.isoformat() if prospect.created_at else None,
            "updated_at": prospect.updated_at.isoformat() if prospect.updated_at else None,
            "first_contacted_at": prospect.first_contacted_at.isoformat() if prospect.first_contacted_at else None,
            "last_activity_at": prospect.last_activity_at.isoformat() if prospect.last_activity_at else None,
            "closed_at": prospect.closed_at.isoformat() if prospect.closed_at else None,
        }
    
    def activity_to_dict(self, activity: ProspectActivityDB) -> Dict[str, Any]:
        """Convert an activity to a serializable dict"""
        return {
            "id": activity.id,
            "prospect_id": activity.prospect_id,
            "activity_type": activity.activity_type.value,
            "title": activity.title,
            "description": activity.description,
            "from_stage": activity.from_stage.value if activity.from_stage else None,
            "to_stage": activity.to_stage.value if activity.to_stage else None,
            "email_subject": activity.email_subject,
            "email_to": activity.email_to,
            "performed_by": activity.performed_by,
            "channel": activity.channel,
            "external_url": activity.external_url,
            "metadata": activity.metadata,
            "created_at": activity.created_at.isoformat() if activity.created_at else None,
        }
