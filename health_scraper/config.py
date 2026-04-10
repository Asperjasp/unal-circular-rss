import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration management for the health institutions scraper"""
    
    def __init__(self):
        self.scraper_mode = os.getenv("SCRAPER_MODE", "development")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.rate_limit_delay = float(os.getenv("RATE_LIMIT_DELAY", "2"))
        
        # Database configuration
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///health_institutions.db")
        
        # API configuration
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        
        # Selenium configuration
        self.headless_mode = os.getenv("HEADLESS_MODE", "True").lower() == "true"
        self.selenium_timeout = int(os.getenv("SELENIUM_TIMEOUT", "30"))
        
        # Social media scraping
        self.linkedin_enabled = os.getenv("LINKEDIN_ENABLED", "True").lower() == "true"
        self.twitter_enabled = os.getenv("TWITTER_ENABLED", "True").lower() == "true"
        
        # AI / Vision configuration
        self.google_ai_studio_key = os.getenv("GOOGLE_AI_STUDIO")
        self.vision_model = os.getenv("VISION_MODEL", "gemini-1.5-flash")
        
        # ── Integration API Keys ──────────────────────────────────────
        # HubSpot CRM
        self.hubspot_access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
        
        # Linear Project Management
        self.linear_api_key = os.getenv("LINEAR_API_KEY")
        self.linear_default_team_id = os.getenv("LINEAR_DEFAULT_TEAM_ID")
        
        # Google Calendar
        self.google_service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        self.google_credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE")
        
        # AI Enrichment (Perplexity)
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

        # Anthropic Claude (LinkedIn M1/M2/M3 outreach generation)
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        # Prospect Intel — Ventana de contexto global para búsquedas Perplexity
        self.perplexity_context_window = os.getenv(
            "PERPLEXITY_CONTEXT_WINDOW",
            (
                "Foco exclusivo en instituciones de salud colombianas. "
                "Busca SOLO contactos que tengan poder de decisión sobre compra de software/tecnología: "
                "CIO, CTO, Gerente de Sistemas, Director TI, Gerente de Tecnología, o equivalente. "
                "Incluir también el número de PBX / centralita si lo encuentras."
            ),
        )
        
        # ── Zoho Email ──────────────────────────────────────────────
        self.zoho_client_id = os.getenv("ZOHO_CLIENT_ID")
        self.zoho_client_secret = os.getenv("ZOHO_CLIENT_SECRET")
        self.zoho_refresh_token = os.getenv("ZOHO_REFRESH_TOKEN")
        self.zoho_account_id = os.getenv("ZOHO_ACCOUNT_ID")
        self.zoho_from_email = os.getenv("ZOHO_FROM_EMAIL")
        self.zoho_domain = os.getenv("ZOHO_DOMAIN", "zoho.com")
        
        # ── Pipeline / Connect ─────────────────────────────────────────
        self.pipeline_auto_snapshot = os.getenv("PIPELINE_AUTO_SNAPSHOT", "True").lower() == "true"
        self.connect_api_enabled = os.getenv("CONNECT_API_ENABLED", "True").lower() == "true"
        
        # ── Outreach / Personal Workflow ───────────────────────────
        self.business_name = os.getenv("BUSINESS_NAME", "")
        self.business_description = os.getenv("BUSINESS_DESCRIPTION", "")
        self.your_name = os.getenv("YOUR_NAME", "")
        self.your_role = os.getenv("YOUR_ROLE", "")
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging based on environment settings"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('health_scraper.log')
            ]
        )
        
        # Reduce noise from external libraries
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("selenium").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.scraper_mode == "development"
    
    @property
    def scraper_settings(self) -> Dict[str, Any]:
        """Get scraper configuration as dictionary"""
        return {
            "headless": self.headless_mode,
            "timeout": self.selenium_timeout,
            "rate_limit": self.rate_limit_delay
        }
    
    @property
    def integrations_configured(self) -> Dict[str, bool]:
        """Check which integrations are configured"""
        return {
            "hubspot": bool(self.hubspot_access_token),
            "linear": bool(self.linear_api_key),
            "google_calendar": bool(self.google_service_account_file or self.google_credentials_file),
            "perplexity": bool(self.perplexity_api_key),
            "gemini": bool(self.google_ai_studio_key),
            "anthropic": bool(self.anthropic_api_key),
            "person_research": bool(self.perplexity_api_key or self.google_ai_studio_key),
            "outreach_drafting": bool(self.google_ai_studio_key),
            "linkedin_outreach": bool(self.anthropic_api_key),
            "zoho_email": bool(self.zoho_client_id and self.zoho_refresh_token),
            "pipeline": True,
            "connect_api": self.connect_api_enabled,
        }
    
    def get_user_agent(self) -> str:
        """Get user agent string for web requests"""
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Global configuration instance
config = Config()