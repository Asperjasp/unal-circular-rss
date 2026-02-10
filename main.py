import logging
import os
import time
import secrets
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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

# ================================================================================
# API KEY AUTHENTICATION
# ================================================================================
# Set API_KEY in your .env file. If not set, a random one will be generated.
# 
# Usage options:
#   1. Header: X-API-Key: your-api-key
#   2. Query param: ?api_key=your-api-key
#   3. Frontend uses session token stored in localStorage
# ================================================================================

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    # Generate a random API key if not set
    API_KEY = secrets.token_urlsafe(32)
    logger.warning(f"No API_KEY set in .env. Generated temporary key: {API_KEY}")
    logger.warning("Add this to your .env file: API_KEY=" + API_KEY)

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

async def verify_api_key(
    api_key_header_value: str = Depends(api_key_header),
    api_key_query_value: str = Depends(api_key_query)
) -> str:
    """Verify API key from header or query parameter"""
    api_key = api_key_header_value or api_key_query_value
    
    if api_key == API_KEY:
        return api_key
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "ApiKey"}
    )

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

# Setup templates directory for frontend
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir)) if templates_dir.exists() else None

# Mount static files directory (optional, for additional assets)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend(request: Request):
    """Serve the frontend HTML page"""
    # First try templates directory
    index_template = templates_dir / "index.html"
    if index_template.exists():
        return FileResponse(str(index_template))
    
    # Fallback to static directory
    index_static = static_dir / "index.html"
    if index_static.exists():
        return FileResponse(str(index_static))
    
    return HTMLResponse(
        content="""
        <html>
            <head>
                <title>Health Scraper API</title>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
                    h1 { color: #0d6efd; }
                    a { color: #0d6efd; }
                </style>
            </head>
            <body>
                <h1>🏥 Health Scraper API</h1>
                <p>Welcome to the Health Institutions Scraper API.</p>
                <p>📚 <a href="/docs">API Documentation (Swagger)</a></p>
                <p>📖 <a href="/redoc">API Documentation (ReDoc)</a></p>
            </body>
        </html>
        """,
        status_code=200
    )

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for Azure Container Apps / Load Balancer"""
    return {
        "status": "healthy",
        "service": "health-scraper-api",
        "version": "1.0.0"
    }


# ================================================================================
# AUTHENTICATION ENDPOINTS
# ================================================================================

@app.post("/api/v1/auth/login", tags=["Authentication"])
async def login(api_key: str):
    """
    Verify API key and return authentication status.
    
    Use this to check if your API key is valid before making protected requests.
    """
    if api_key == API_KEY:
        return {
            "success": True,
            "message": "Authentication successful",
            "authenticated": True
        }
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )


@app.get("/api/v1/auth/verify", tags=["Authentication"])
async def verify_auth(api_key: str = Depends(verify_api_key)):
    """Verify if current API key is valid"""
    return {"authenticated": True, "message": "API key is valid"}


# ================================================================================
# PROTECTED EXPORT ENDPOINTS (require API key)
# ================================================================================

@app.get("/api/v1/secure/export/csv", tags=["Secure Export"])
async def secure_export_csv(
    api_key: str = Depends(verify_api_key),
    institution_type: Optional[str] = None,
    city: Optional[str] = None
):
    """
    🔐 PROTECTED: Download all institutions as CSV file.
    
    Requires API key authentication via:
    - Header: X-API-Key: your-key
    - Query: ?api_key=your-key
    """
    import io
    import csv
    import asyncio
    from health_scraper.database.service import get_db_service
    
    db = get_db_service()
    
    loop = asyncio.get_event_loop()
    institutions = await loop.run_in_executor(
        None,
        lambda: db.search_institutions(
            institution_type=institution_type,
            city=city,
            limit=10000
        )
    )
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'ID', 'Nombre', 'Tipo', 'Especialidad', 'NIT', 'Dirección',
        'Ciudad', 'Departamento', 'Teléfono', 'Email', 'Sitio Web',
        'LinkedIn', 'Twitter', 'Fuente'
    ])
    
    for inst in institutions:
        writer.writerow([
            inst.id, inst.name, inst.institution_type, inst.specialty_type,
            inst.nit, inst.address, inst.city, inst.department,
            inst.phone, inst.email, inst.website, inst.linkedin_url,
            inst.twitter_url, inst.source
        ])
    
    output.seek(0)
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=instituciones_salud.csv"
        }
    )


@app.get("/api/v1/secure/export/excel", tags=["Secure Export"])
async def secure_export_excel(
    api_key: str = Depends(verify_api_key),
    institution_type: Optional[str] = None,
    city: Optional[str] = None
):
    """
    🔐 PROTECTED: Download all institutions as Excel file.
    
    Requires API key authentication via:
    - Header: X-API-Key: your-key
    - Query: ?api_key=your-key
    """
    import io
    import asyncio
    from health_scraper.database.service import get_db_service
    
    try:
        import pandas as pd
    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="pandas is required for Excel export"
        )
    
    db = get_db_service()
    
    loop = asyncio.get_event_loop()
    institutions = await loop.run_in_executor(
        None,
        lambda: db.search_institutions(
            institution_type=institution_type,
            city=city,
            limit=10000
        )
    )
    
    # Create DataFrame
    data = []
    for inst in institutions:
        data.append({
            'ID': inst.id,
            'Nombre': inst.name,
            'Tipo': inst.institution_type,
            'Especialidad': inst.specialty_type,
            'NIT': inst.nit,
            'Dirección': inst.address,
            'Ciudad': inst.city,
            'Departamento': inst.department,
            'Teléfono': inst.phone,
            'Email': inst.email,
            'Sitio Web': inst.website,
            'LinkedIn': inst.linkedin_url,
            'Twitter': inst.twitter_url,
            'Fuente': inst.source
        })
    
    df = pd.DataFrame(data)
    
    # Write to Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Instituciones', index=False)
    output.seek(0)
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=instituciones_salud.xlsx"
        }
    )

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
    
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("SCRAPER_MODE") == "development",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )