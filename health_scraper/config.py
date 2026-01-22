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
    
    def get_user_agent(self) -> str:
        """Get user agent string for web requests"""
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Global configuration instance
config = Config()