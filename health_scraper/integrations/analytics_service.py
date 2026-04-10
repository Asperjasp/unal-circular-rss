"""
Analytics Service for Connect Desktop App
============================================
Provides analytics data in formats optimized for:
- Connect desktop app (AI Medic's analytics product)
- CEO reporting dashboards
- Chart.js / visualization libraries

Data formats:
- Funnel charts (stages with counts/values)
- Time series (daily/weekly/monthly trends)
- KPI cards (summary metrics)
- Breakdown charts (by source, city, industry)
- Activity heatmaps
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from collections import defaultdict

from ..database.pipeline_service import PipelineService
from ..database.pipeline_models import (
    FunnelStage, ProspectSource, ActivityType, FUNNEL_STAGE_META,
    ProspectDB, ProspectActivityDB, PipelineSnapshotDB
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Provides analytics & chart data for:
    - Connect desktop app (AI Medic's product)
    - Dashboard visualizations
    - CEO reports
    
    All methods return data ready for Chart.js or similar libs.
    """
    
    def __init__(self, pipeline_service: PipelineService):
        self.pipeline = pipeline_service
    
    # =========================================================================
    # FUNNEL CHART DATA
    # =========================================================================
    
    def get_funnel_chart(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Get funnel chart data for visualization.
        
        Returns data optimized for a funnel/bar chart:
        - labels: Stage names
        - data: Counts per stage
        - colors: Stage colors
        - values: Monetary values per stage
        """
        analytics = self.pipeline.get_funnel_analytics(
            date_from=date_from, date_to=date_to
        )
        
        stages = analytics["funnel"]["stages"]
        # Exclude closed stages for funnel view
        active_stages = [s for s in stages if s["id"] not in ("closed_won", "closed_lost")]
        
        return {
            "chart_type": "funnel",
            "title": "Embudo de Ventas",
            "labels": [s["label"] for s in active_stages],
            "datasets": [
                {
                    "label": "Prospectos",
                    "data": [s["count"] for s in active_stages],
                    "backgroundColor": [s["color"] for s in active_stages],
                },
            ],
            "value_overlay": {
                "label": "Valor Estimado (COP)",
                "data": [s["value"] for s in active_stages],
            },
            "conversion_rates": analytics["funnel"]["conversion_rates"],
            "closed": {
                "won": next((s for s in stages if s["id"] == "closed_won"), {"count": 0, "value": 0}),
                "lost": next((s for s in stages if s["id"] == "closed_lost"), {"count": 0, "value": 0}),
            },
        }
    
    # =========================================================================
    # TIME SERIES CHARTS
    # =========================================================================
    
    def get_prospects_over_time(
        self,
        days: int = 30,
        granularity: str = "daily",  # daily, weekly, monthly
    ) -> Dict[str, Any]:
        """
        Time series: new prospects created over time.
        
        Returns data optimized for a line/bar chart.
        """
        session = self.pipeline.get_session()
        try:
            from sqlalchemy import func
            
            start_date = date.today() - timedelta(days=days)
            
            if granularity == "daily":
                group_by = func.date(ProspectDB.created_at)
            elif granularity == "weekly":
                group_by = func.strftime('%Y-W%W', ProspectDB.created_at)
            else:
                group_by = func.strftime('%Y-%m', ProspectDB.created_at)
            
            results = (
                session.query(
                    group_by.label("period"),
                    func.count().label("count"),
                    func.sum(ProspectDB.estimated_value).label("total_value"),
                )
                .filter(ProspectDB.created_at >= datetime.combine(start_date, datetime.min.time()))
                .group_by(group_by)
                .order_by(group_by)
                .all()
            )
            
            labels = []
            counts = []
            values = []
            for row in results:
                period_str = row.period.isoformat() if hasattr(row.period, 'isoformat') else str(row.period)
                labels.append(period_str)
                counts.append(row.count)
                values.append(float(row.total_value or 0))
            
            return {
                "chart_type": "line",
                "title": f"Nuevos Prospectos ({granularity})",
                "period": f"last_{days}_days",
                "labels": labels,
                "datasets": [
                    {
                        "label": "Nuevos Prospectos",
                        "data": counts,
                        "borderColor": "#6366f1",
                        "backgroundColor": "rgba(99, 102, 241, 0.1)",
                        "fill": True,
                    },
                ],
                "secondary_axis": {
                    "label": "Valor Total (COP)",
                    "data": values,
                    "borderColor": "#10b981",
                },
            }
        finally:
            session.close()
    
    def get_stage_evolution(self, days: int = 30) -> Dict[str, Any]:
        """
        Stacked area chart: how prospect counts per stage evolve over time.
        Uses pipeline snapshots if available.
        """
        session = self.pipeline.get_session()
        try:
            start_date = date.today() - timedelta(days=days)
            
            snapshots = (
                session.query(PipelineSnapshotDB)
                .filter(PipelineSnapshotDB.snapshot_date >= start_date)
                .order_by(PipelineSnapshotDB.snapshot_date)
                .all()
            )
            
            if not snapshots:
                return {
                    "chart_type": "stacked_area",
                    "title": "Evolución del Pipeline",
                    "message": "No hay snapshots disponibles. Los datos se acumularán diariamente.",
                    "labels": [],
                    "datasets": [],
                }
            
            labels = [s.snapshot_date.isoformat() for s in snapshots]
            
            stage_configs = [
                ("identified", "Identificado", "#94a3b8"),
                ("contacted", "Contactado", "#60a5fa"),
                ("interested", "Interesado", "#a78bfa"),
                ("meeting_scheduled", "Reunión", "#fbbf24"),
                ("proposal_sent", "Propuesta", "#f97316"),
                ("negotiation", "Negociación", "#fb923c"),
            ]
            
            datasets = []
            for stage_key, label, color in stage_configs:
                data = [getattr(s, f"{stage_key}_count", 0) for s in snapshots]
                datasets.append({
                    "label": label,
                    "data": data,
                    "backgroundColor": color + "40",
                    "borderColor": color,
                    "fill": True,
                })
            
            return {
                "chart_type": "stacked_area",
                "title": "Evolución del Pipeline",
                "period": f"last_{days}_days",
                "labels": labels,
                "datasets": datasets,
            }
        finally:
            session.close()
    
    # =========================================================================
    # KPI CARDS
    # =========================================================================
    
    def get_kpi_cards(self) -> Dict[str, Any]:
        """
        Get KPI summary cards for the dashboard header.
        
        Returns cards with current value, trend, and comparison.
        """
        analytics = self.pipeline.get_funnel_analytics()
        summary = analytics["summary"]
        
        session = self.pipeline.get_session()
        try:
            from sqlalchemy import func
            
            # This week vs last week
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            last_week_start = week_start - timedelta(days=7)
            
            this_week_new = (
                session.query(func.count(ProspectDB.id))
                .filter(ProspectDB.created_at >= datetime.combine(week_start, datetime.min.time()))
                .scalar() or 0
            )
            
            last_week_new = (
                session.query(func.count(ProspectDB.id))
                .filter(
                    ProspectDB.created_at >= datetime.combine(last_week_start, datetime.min.time()),
                    ProspectDB.created_at < datetime.combine(week_start, datetime.min.time()),
                )
                .scalar() or 0
            )
            
            # Email stats this week
            this_week_emails = (
                session.query(func.count(ProspectActivityDB.id))
                .filter(
                    ProspectActivityDB.created_at >= datetime.combine(week_start, datetime.min.time()),
                    ProspectActivityDB.activity_type == ActivityType.EMAIL_SENT,
                )
                .scalar() or 0
            )
            
            # Calculate trends
            new_trend = ((this_week_new - last_week_new) / last_week_new * 100) if last_week_new > 0 else 0
            
            return {
                "cards": [
                    {
                        "id": "total_pipeline",
                        "title": "Pipeline Total",
                        "value": summary["active_prospects"],
                        "subtitle": f"{summary['total_prospects']} totales",
                        "icon": "bi-funnel",
                        "color": "#6366f1",
                    },
                    {
                        "id": "pipeline_value",
                        "title": "Valor del Pipeline",
                        "value": summary["pipeline_value"],
                        "format": "currency",
                        "currency": "COP",
                        "icon": "bi-cash-stack",
                        "color": "#10b981",
                    },
                    {
                        "id": "win_rate",
                        "title": "Tasa de Cierre",
                        "value": summary["win_rate"],
                        "format": "percent",
                        "subtitle": f"{summary['won_deals']} ganados, {summary['lost_deals']} perdidos",
                        "icon": "bi-trophy",
                        "color": "#f59e0b",
                    },
                    {
                        "id": "new_this_week",
                        "title": "Nuevos esta Semana",
                        "value": this_week_new,
                        "trend": round(new_trend, 1),
                        "trend_label": f"vs semana anterior ({last_week_new})",
                        "icon": "bi-plus-circle",
                        "color": "#3b82f6",
                    },
                    {
                        "id": "emails_sent",
                        "title": "Emails esta Semana",
                        "value": this_week_emails,
                        "icon": "bi-envelope",
                        "color": "#8b5cf6",
                    },
                    {
                        "id": "avg_close_days",
                        "title": "Días Promedio Cierre",
                        "value": summary["avg_days_to_close"],
                        "format": "days",
                        "icon": "bi-clock",
                        "color": "#ec4899",
                    },
                ],
            }
        finally:
            session.close()
    
    # =========================================================================
    # BREAKDOWN CHARTS (PIE / DONUT)
    # =========================================================================
    
    def get_source_breakdown(self) -> Dict[str, Any]:
        """Pie chart: prospects by source"""
        analytics = self.pipeline.get_funnel_analytics()
        sources = analytics["breakdown"]["by_source"]
        
        source_labels = {
            "scraper": "Scraper",
            "excel_import": "Excel Import",
            "manual": "Manual",
            "hubspot": "HubSpot",
            "linkedin": "LinkedIn",
            "referral": "Referido",
            "conference": "Conferencia",
            "twitter": "Twitter",
            "other": "Otro",
        }
        
        source_colors = {
            "scraper": "#6366f1",
            "excel_import": "#10b981",
            "manual": "#f59e0b",
            "hubspot": "#ff7a59",
            "linkedin": "#0077b5",
            "referral": "#8b5cf6",
            "conference": "#ec4899",
            "twitter": "#1da1f2",
            "other": "#94a3b8",
        }
        
        labels = [source_labels.get(k, k) for k in sources.keys()]
        data = list(sources.values())
        colors = [source_colors.get(k, "#94a3b8") for k in sources.keys()]
        
        return {
            "chart_type": "doughnut",
            "title": "Prospectos por Fuente",
            "labels": labels,
            "datasets": [{
                "data": data,
                "backgroundColor": colors,
            }],
        }
    
    def get_city_breakdown(self) -> Dict[str, Any]:
        """Bar chart: prospects by city"""
        analytics = self.pipeline.get_funnel_analytics()
        cities = analytics["breakdown"]["by_city"]
        
        return {
            "chart_type": "horizontal_bar",
            "title": "Prospectos por Ciudad",
            "labels": list(cities.keys()),
            "datasets": [{
                "label": "Prospectos",
                "data": list(cities.values()),
                "backgroundColor": "#6366f1",
            }],
        }
    
    def get_industry_breakdown(self) -> Dict[str, Any]:
        """Bar chart: prospects by industry"""
        analytics = self.pipeline.get_funnel_analytics()
        industries = analytics["breakdown"]["by_industry"]
        
        return {
            "chart_type": "horizontal_bar",
            "title": "Prospectos por Sector",
            "labels": list(industries.keys()),
            "datasets": [{
                "label": "Prospectos",
                "data": list(industries.values()),
                "backgroundColor": "#10b981",
            }],
        }
    
    # =========================================================================
    # ACTIVITY ANALYTICS
    # =========================================================================
    
    def get_activity_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Activity breakdown for the period.
        Returns data for a bar chart + activity feed.
        """
        session = self.pipeline.get_session()
        try:
            from sqlalchemy import func
            
            start = datetime.utcnow() - timedelta(days=days)
            
            # Count by type
            by_type = (
                session.query(
                    ProspectActivityDB.activity_type,
                    func.count().label("count"),
                )
                .filter(ProspectActivityDB.created_at >= start)
                .group_by(ProspectActivityDB.activity_type)
                .all()
            )
            
            activity_labels = {
                "stage_change": "Cambio de Etapa",
                "email_sent": "Email Enviado",
                "email_opened": "Email Abierto",
                "email_replied": "Email Respondido",
                "call_made": "Llamada",
                "meeting_held": "Reunión",
                "note_added": "Nota",
                "linkedin_message": "LinkedIn",
                "whatsapp_message": "WhatsApp",
                "proposal_sent": "Propuesta",
            }
            
            labels = []
            data = []
            for row in by_type:
                labels.append(activity_labels.get(row.activity_type.value, row.activity_type.value))
                data.append(row.count)
            
            # By day of week
            by_weekday = (
                session.query(
                    func.strftime('%w', ProspectActivityDB.created_at).label("weekday"),
                    func.count().label("count"),
                )
                .filter(ProspectActivityDB.created_at >= start)
                .group_by(func.strftime('%w', ProspectActivityDB.created_at))
                .all()
            )
            
            weekday_names = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
            weekday_data = [0] * 7
            for row in by_weekday:
                try:
                    idx = int(row.weekday)
                    weekday_data[idx] = row.count
                except (ValueError, IndexError):
                    pass
            
            # Recent activities
            recent = (
                session.query(ProspectActivityDB)
                .order_by(ProspectActivityDB.created_at.desc())
                .limit(20)
                .all()
            )
            
            return {
                "by_type": {
                    "chart_type": "bar",
                    "title": f"Actividades (últimos {days} días)",
                    "labels": labels,
                    "datasets": [{
                        "label": "Actividades",
                        "data": data,
                        "backgroundColor": "#6366f1",
                    }],
                },
                "by_weekday": {
                    "chart_type": "bar",
                    "title": "Actividad por Día de la Semana",
                    "labels": weekday_names,
                    "datasets": [{
                        "label": "Actividades",
                        "data": weekday_data,
                        "backgroundColor": "#10b981",
                    }],
                },
                "recent": [
                    self.pipeline.activity_to_dict(a) for a in recent
                ],
                "total_activities": sum(data),
            }
        finally:
            session.close()
    
    # =========================================================================
    # CONNECT APP API FORMAT
    # =========================================================================
    
    def get_connect_dashboard_data(self) -> Dict[str, Any]:
        """
        Full dashboard data package for the Connect desktop app.
        
        Returns all data needed to render the analytics dashboard
        in a single API call, optimized for the Connect app.
        """
        return {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat(),
            "app": "aimedic_sales_pipeline",
            "kpi_cards": self.get_kpi_cards(),
            "funnel_chart": self.get_funnel_chart(),
            "prospects_timeline": self.get_prospects_over_time(days=30),
            "stage_evolution": self.get_stage_evolution(days=30),
            "source_breakdown": self.get_source_breakdown(),
            "city_breakdown": self.get_city_breakdown(),
            "industry_breakdown": self.get_industry_breakdown(),
            "activity_summary": self.get_activity_summary(days=30),
        }
    
    def get_connect_export(
        self,
        format: str = "json",
        days: int = 90,
    ) -> Dict[str, Any]:
        """
        Export data for Connect app import/sync.
        
        Formats:
        - json: Full JSON export
        - csv_ready: Data structured for CSV generation
        """
        session = self.pipeline.get_session()
        try:
            from sqlalchemy import func
            
            start = datetime.utcnow() - timedelta(days=days)
            
            prospects = (
                session.query(ProspectDB)
                .filter(ProspectDB.created_at >= start)
                .order_by(ProspectDB.created_at.desc())
                .all()
            )
            
            if format == "csv_ready":
                rows = []
                for p in prospects:
                    rows.append({
                        "ID": p.id,
                        "Empresa": p.company_name,
                        "Dominio": p.company_domain,
                        "NIT": p.company_nit,
                        "Sector": p.industry,
                        "Ciudad": p.city,
                        "Contacto": p.contact_name,
                        "Email": p.contact_email,
                        "Teléfono": p.contact_phone,
                        "Cargo": p.contact_position,
                        "Etapa": FUNNEL_STAGE_META[p.current_stage]["label"],
                        "Valor Estimado": p.estimated_value,
                        "Fuente": p.source.value if p.source else "",
                        "Asignado a": p.assigned_to,
                        "Emails Enviados": p.emails_sent,
                        "Emails Abiertos": p.emails_opened,
                        "Reuniones": p.meetings_held,
                        "Lead Score": p.lead_score,
                        "Activo": "Sí" if p.is_active else "No",
                        "Creado": p.created_at.isoformat() if p.created_at else "",
                        "Última Actividad": p.last_activity_at.isoformat() if p.last_activity_at else "",
                    })
                return {
                    "format": "csv_ready",
                    "columns": list(rows[0].keys()) if rows else [],
                    "rows": rows,
                    "total": len(rows),
                }
            
            # Default: full JSON
            return {
                "format": "json",
                "exported_at": datetime.utcnow().isoformat(),
                "period_days": days,
                "prospects": [self.pipeline.prospect_to_dict(p) for p in prospects],
                "analytics": self.get_connect_dashboard_data(),
                "total": len(prospects),
            }
        finally:
            session.close()
