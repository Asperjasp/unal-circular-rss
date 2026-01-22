import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from health_scraper.api.endpoints import router
from health_scraper.scrapers.base_scraper import BaseHealthScraper

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Health Institutions Scraper API")
    yield
    # Shutdown
    logger.info("Shutting down Health Institutions Scraper API")
    # Cleanup any global resources
    try:
        from health_scraper.api.endpoints import scraper
        if scraper:
            scraper.cleanup()
    except:
        pass

# Create FastAPI application
app = FastAPI(
    title="Health Institutions Scraper API",
    description="""
    A comprehensive API for scraping Colombian IPS and EPS health institutions data.
    
    ## Features
    
    * **Single Institution Scraping**: Scrape detailed information for individual health institutions
    * **Bulk Scraping**: Process multiple institutions simultaneously
    * **Social Media Integration**: Extract LinkedIn, Facebook, Twitter profiles
    * **IT Team Detection**: Identify IT departments and technology contacts
    * **Contact Information**: Extract phone numbers, emails, and key personnel
    * **Colombian Focus**: Optimized for Colombian health system (IPS/EPS)
    
    ## Rate Limiting
    
    The API implements rate limiting to respect target websites and avoid being blocked.
    Default rate limit: 2 seconds between requests.
    
    ## Data Quality
    
    Each scraped institution includes a data quality score based on the completeness
    of extracted information.
    """,
    version="1.0.0",
    contact={
        "name": "Health-Tech Team",
        "email": "tech@healthcompany.co"
    },
    license_info={
        "name": "MIT License"
    },
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = time.time()
    
    logger.info(f"{request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"Completed {request.method} {request.url} - {response.status_code} - {process_time:.2f}s")
    
    return response

if __name__ == "__main__":
    import uvicorn
    import time
    
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("SCRAPER_MODE") == "development",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )