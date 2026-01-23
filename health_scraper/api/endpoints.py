import logging
import asyncio
import io
import csv
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
import time
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, StreamingResponse

from ..models.institution import (
    HealthInstitution, ScrapeResult, BulkScrapeRequest, 
    BulkScrapeResponse, InstitutionType, Contact, ContactType
)
from ..scrapers.base_scraper import BaseHealthScraper
from ..scrapers.social_media_scraper import SocialMediaScraper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Health Institutions Scraper"])

# Global scraper instance
scraper = None

def get_scraper():
    """Get or create scraper instance"""
    global scraper
    if scraper is None:
        scraper = BaseHealthScraper(headless=True, timeout=30, rate_limit=2.0)
    return scraper

@router.get("/")
async def root():
    """API root endpoint with basic information"""
    return {
        "name": "Health Institutions Scraper API",
        "version": "1.0.0",
        "description": "API for scraping Colombian IPS and EPS health institutions data",
        "endpoints": {
            "scrape_single": "/scrape/single",
            "scrape_bulk": "/scrape/bulk",
            "health_check": "/health"
        }
    }

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "scraper_ready": scraper is not None
    }

@router.post("/scrape/single", response_model=ScrapeResult)
async def scrape_single_institution(
    institution_name: str,
    additional_urls: Optional[List[str]] = None,
    include_social_media: bool = True,
    include_it_details: bool = True
):
    """
    Scrape a single health institution
    
    - **institution_name**: Name of the IPS or EPS to scrape
    - **additional_urls**: Optional list of additional URLs to scrape
    - **include_social_media**: Whether to include social media profiles
    - **include_it_details**: Whether to include IT team information
    """
    try:
        scraper_instance = get_scraper()
        
        # Run scraping in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                scraper_instance.scrape_institution,
                institution_name,
                additional_urls or []
            )
        
        if result.success and result.institution and include_social_media:
            # Enhanced social media scraping
            try:
                social_scraper = SocialMediaScraper(
                    driver=scraper_instance.driver,
                    text_processor=scraper_instance.text_processor
                )
                
                additional_profiles = await loop.run_in_executor(
                    executor,
                    social_scraper.search_social_media_profiles,
                    institution_name,
                    str(result.institution.website) if result.institution.website else None
                )
                
                # Merge with existing profiles
                existing_urls = {str(p.url) for p in result.institution.social_media}
                for profile in additional_profiles:
                    if str(profile.url) not in existing_urls:
                        result.institution.social_media.append(profile)
                
                # Enhance profiles with additional data
                if result.institution.social_media:
                    result.institution.social_media = await loop.run_in_executor(
                        executor,
                        social_scraper.enhance_social_media_profiles,
                        result.institution.social_media
                    )
                    
            except Exception as e:
                logger.warning(f"Social media enhancement failed: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error scraping institution {institution_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scrape institution: {str(e)}"
        )

@router.post("/scrape/bulk", response_model=BulkScrapeResponse)
async def scrape_bulk_institutions(request: BulkScrapeRequest):
    """
    Scrape multiple health institutions in bulk
    
    - **institution_names**: List of institution names to scrape
    - **include_social_media**: Whether to include social media profiles
    - **include_it_details**: Whether to include IT team information
    - **max_concurrent**: Maximum number of concurrent scraping operations
    """
    start_time = time.time()
    results = []
    successful_count = 0
    failed_count = 0
    
    try:
        scraper_instance = get_scraper()
        
        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(min(request.max_concurrent, 5))
        
        async def scrape_single(institution_name: str) -> ScrapeResult:
            async with semaphore:
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    return await loop.run_in_executor(
                        executor,
                        scraper_instance.scrape_institution,
                        institution_name,
                        []
                    )
        
        # Run all scraping operations concurrently
        tasks = [scrape_single(name) for name in request.institution_names]
        scrape_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(scrape_results):
            if isinstance(result, Exception):
                # Handle exceptions
                error_result = ScrapeResult(
                    success=False,
                    error_message=str(result),
                    processing_time=0
                )
                results.append(error_result)
                failed_count += 1
                logger.error(f"Failed to scrape {request.institution_names[i]}: {result}")
            else:
                results.append(result)
                if result.success:
                    successful_count += 1
                else:
                    failed_count += 1
        
        # Enhanced social media scraping for successful results
        if request.include_social_media:
            await _enhance_bulk_social_media(results, scraper_instance)
        
        total_time = time.time() - start_time
        
        return BulkScrapeResponse(
            total_requested=len(request.institution_names),
            successful_scrapes=successful_count,
            failed_scrapes=failed_count,
            results=results,
            processing_time=total_time
        )
        
    except Exception as e:
        logger.error(f"Error in bulk scraping: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Bulk scraping failed: {str(e)}"
        )

async def _enhance_bulk_social_media(results: List[ScrapeResult], scraper_instance: BaseHealthScraper):
    """Enhance social media profiles for bulk scrape results"""
    try:
        social_scraper = SocialMediaScraper(
            driver=scraper_instance.driver,
            text_processor=scraper_instance.text_processor
        )
        
        loop = asyncio.get_event_loop()
        
        for result in results:
            if result.success and result.institution:
                try:
                    # Search for additional profiles
                    additional_profiles = await loop.run_in_executor(
                        None,
                        social_scraper.search_social_media_profiles,
                        result.institution.name,
                        str(result.institution.website) if result.institution.website else None
                    )
                    
                    # Merge profiles
                    existing_urls = {str(p.url) for p in result.institution.social_media}
                    for profile in additional_profiles:
                        if str(profile.url) not in existing_urls:
                            result.institution.social_media.append(profile)
                            
                except Exception as e:
                    logger.warning(f"Failed to enhance social media for {result.institution.name}: {e}")
                    
    except Exception as e:
        logger.warning(f"Bulk social media enhancement failed: {e}")

@router.get("/scrape/search")
async def search_institutions(
    query: str = Query(..., description="Search query for institutions"),
    institution_type: Optional[InstitutionType] = Query(None, description="Filter by institution type"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results")
):
    """
    Search for health institutions without full scraping
    
    - **query**: Search term (institution name, city, etc.)
    - **institution_type**: Filter by IPS or EPS
    - **limit**: Maximum number of results to return
    """
    try:
        scraper_instance = get_scraper()
        
        # Basic search functionality
        search_results = []
        
        # This is a simplified search - in a production system, 
        # you might want to integrate with official health registries
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            urls = await loop.run_in_executor(
                executor,
                scraper_instance._search_institution,
                query
            )
        
        for i, url in enumerate(urls[:limit]):
            search_results.append({
                "name": f"Institution from {query} search #{i+1}",
                "url": url,
                "estimated_type": institution_type or InstitutionType.IPS
            })
        
        return {
            "query": query,
            "results": search_results,
            "total_found": len(search_results)
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/institutions/{institution_id}/refresh")
async def refresh_institution_data(institution_id: str):
    """
    Refresh data for a previously scraped institution
    
    - **institution_id**: Unique identifier for the institution
    """
    # This endpoint would typically work with a database
    # For now, we'll return a placeholder response
    return {
        "message": "Refresh functionality requires database integration",
        "institution_id": institution_id,
        "status": "not_implemented"
    }

@router.delete("/scraper/cleanup")
async def cleanup_scraper():
    """
    Clean up scraper resources (close browser, etc.)
    """
    global scraper
    try:
        if scraper:
            scraper.cleanup()
            scraper = None
        return {"message": "Scraper resources cleaned up successfully"}
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}"
        )


# ============================================================================
# PROMPT-BASED SEARCH ENDPOINTS (New Feature)
# ============================================================================

from ..services.search_service import PromptSearchService, QueryParser
from ..database.service import DatabaseService

# Global service instances
_search_service = None
_db_service = None

def get_search_service():
    """Get or create search service instance"""
    global _search_service
    if _search_service is None:
        _search_service = PromptSearchService()
    return _search_service

def get_db_service():
    """Get or create database service instance"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service


@router.post("/search/prompt")
async def search_by_prompt(
    query: str = Query(
        ..., 
        description="Natural language search query",
        example="Odontología especializada en implantes cerca de Soacha"
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    scrape_if_needed: bool = Query(
        False, 
        description="Trigger web scraping if database results are insufficient"
    ),
    min_results: int = Query(
        5, 
        ge=1, 
        le=20, 
        description="Minimum results before triggering scraping"
    ),
    user_id: Optional[str] = Query(None, description="Optional user identifier for analytics")
):
    """
    🔍 Search for health institutions using natural language queries.
    
    This endpoint parses natural language queries and searches the database
    for matching health institutions. Supports queries like:
    
    - "Odontología cerca de Soacha"
    - "Clínica dental especializada en implantes en Bogotá"
    - "Cardiología en Medellín"
    - "Hospital con pediatría en Kennedy"
    
    ## Query Parsing
    
    The system automatically extracts:
    - **Specialty**: Medical specialty (odontología, cardiología, etc.)
    - **Treatment**: Specific treatment (implantes, ortodoncia, etc.)
    - **Location**: City, department, or "near X" location
    - **Institution Type**: Clínica, hospital, centro médico, etc.
    
    ## Deduplication
    
    Results are automatically deduplicated. The same institution will not
    appear twice in the database, even if scraped multiple times.
    
    ## Parameters
    
    - **query**: Your search query in natural language (Spanish or English)
    - **limit**: Maximum number of results to return
    - **scrape_if_needed**: If True, will scrape web for new results if database has few matches
    - **min_results**: Minimum results before triggering scraping (if enabled)
    - **user_id**: Optional identifier for tracking your queries
    
    ## Returns
    
    - List of matching institutions with full details
    - Parsed query components showing how your query was interpreted
    - Statistics about results (from database vs newly scraped)
    """
    try:
        service = get_search_service()
        
        # Run search in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        if scrape_if_needed:
            result = await loop.run_in_executor(
                None,
                lambda: service.search_and_scrape(
                    query=query,
                    limit=limit,
                    min_results=min_results,
                    scrape_if_insufficient=True,
                    user_id=user_id
                )
            )
        else:
            result = await loop.run_in_executor(
                None,
                lambda: service.search(query=query, limit=limit, user_id=user_id)
            )
        
        # Convert to response format
        institutions_data = []
        for inst in result.institutions:
            institutions_data.append({
                "id": inst.id,
                "name": inst.name,
                "institution_type": inst.institution_type,
                "specialty_type": inst.specialty_type,
                "address": inst.address,
                "city": inst.city,
                "department": inst.department,
                "phone": inst.phone,
                "email": inst.email,
                "website": inst.website,
                "services": inst.services,
                "specialties": inst.specialties,
                "has_it_team": inst.has_it_team,
                "data_quality_score": inst.data_quality_score,
                "scraped_at": inst.scraped_at.isoformat() if inst.scraped_at else None,
                "updated_at": inst.updated_at.isoformat() if inst.updated_at else None
            })
        
        return {
            "success": True,
            "query": {
                "original": result.parsed_query.original_query,
                "parsed": {
                    "specialty": result.parsed_query.specialty,
                    "treatment": result.parsed_query.treatment,
                    "city": result.parsed_query.city,
                    "department": result.parsed_query.department,
                    "near_location": result.parsed_query.near_location,
                    "institution_type": result.parsed_query.institution_type,
                    "keywords": result.parsed_query.keywords
                }
            },
            "results": {
                "total_count": result.total_count,
                "from_database": result.from_database,
                "newly_scraped": result.newly_scraped,
                "execution_time_seconds": round(result.execution_time, 3)
            },
            "institutions": institutions_data
        }
        
    except Exception as e:
        logger.error(f"Prompt search error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/search/parse")
async def parse_query(
    query: str = Query(
        ..., 
        description="Query to parse",
        example="Clínica dental con ortodoncia cerca de Kennedy"
    )
):
    """
    🧪 Parse a natural language query without executing the search.
    
    Useful for debugging and understanding how your query will be interpreted.
    
    Returns the parsed components:
    - Specialty
    - Treatment
    - City/Location
    - Institution type
    - Keywords
    """
    parser = QueryParser()
    parsed = parser.parse(query)
    
    return {
        "original_query": query,
        "parsed": {
            "specialty": parsed.specialty,
            "treatment": parsed.treatment,
            "city": parsed.city,
            "department": parsed.department,
            "near_location": parsed.near_location,
            "institution_type": parsed.institution_type,
            "keywords": parsed.keywords
        }
    }


@router.get("/database/institutions")
async def list_institutions(
    city: Optional[str] = Query(None, description="Filter by city"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    institution_type: Optional[str] = Query(None, description="Filter by type (IPS, EPS, CLINICA, etc.)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """
    📋 List all institutions in the database with optional filters.
    
    Use this endpoint to browse stored institutions without
    triggering new scraping.
    """
    try:
        db = get_db_service()
        
        loop = asyncio.get_event_loop()
        institutions = await loop.run_in_executor(
            None,
            lambda: db.search_institutions(
                specialty=specialty,
                city=city,
                institution_type=institution_type,
                limit=limit,
                offset=offset
            )
        )
        
        return {
            "count": len(institutions),
            "offset": offset,
            "limit": limit,
            "institutions": [
                {
                    "id": inst.id,
                    "name": inst.name,
                    "institution_type": inst.institution_type,
                    "specialty_type": inst.specialty_type,
                    "city": inst.city,
                    "department": inst.department,
                    "phone": inst.phone,
                    "email": inst.email,
                    "website": inst.website
                }
                for inst in institutions
            ]
        }
        
    except Exception as e:
        logger.error(f"Database list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/institutions/{institution_id}")
async def get_institution(institution_id: int):
    """
    🏥 Get detailed information about a specific institution.
    """
    try:
        db = get_db_service()
        
        loop = asyncio.get_event_loop()
        institution = await loop.run_in_executor(
            None,
            db.get_institution_by_id,
            institution_id
        )
        
        if not institution:
            raise HTTPException(status_code=404, detail="Institution not found")
        
        return {
            "id": institution.id,
            "name": institution.name,
            "institution_type": institution.institution_type,
            "specialty_type": institution.specialty_type,
            "registration_number": institution.registration_number,
            "nit": institution.nit,
            "address": institution.address,
            "city": institution.city,
            "department": institution.department,
            "phone": institution.phone,
            "email": institution.email,
            "website": institution.website,
            "affiliation": institution.affiliation,
            "legal_representative": institution.legal_representative,
            "medical_director": institution.medical_director,
            "services": institution.services,
            "specialties": institution.specialties,
            "treatments": institution.treatments,
            "certification_level": institution.certification_level,
            "accreditations": institution.accreditations,
            "bed_capacity": institution.bed_capacity,
            "employee_count": institution.employee_count,
            "has_it_team": institution.has_it_team,
            "it_department_name": institution.it_department_name,
            "technology_stack": institution.technology_stack,
            "data_quality_score": institution.data_quality_score,
            "source_url": institution.source_url,
            "scraped_at": institution.scraped_at.isoformat() if institution.scraped_at else None,
            "updated_at": institution.updated_at.isoformat() if institution.updated_at else None,
            "contacts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "position": c.position,
                    "email": c.email,
                    "phone": c.phone,
                    "contact_type": c.contact_type
                }
                for c in institution.contacts
            ],
            "social_media": [
                {
                    "id": s.id,
                    "platform": s.platform,
                    "url": s.url,
                    "username": s.username,
                    "follower_count": s.follower_count
                }
                for s in institution.social_media
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get institution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/statistics")
async def get_database_statistics():
    """
    📊 Get statistics about the stored data.
    
    Returns counts and distributions of:
    - Total institutions
    - Institutions by type
    - Institutions by city
    - Institutions by specialty
    - Total contacts and social media profiles
    """
    try:
        db = get_db_service()
        
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(None, db.get_statistics)
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/check-duplicate")
async def check_duplicate(
    name: str = Query(..., description="Institution name"),
    nit: Optional[str] = Query(None, description="NIT (Colombian tax ID)"),
    address: Optional[str] = Query(None, description="Address")
):
    """
    🔍 Check if an institution already exists in the database.
    
    Useful before adding new institutions to avoid duplicates.
    """
    try:
        db = get_db_service()
        
        loop = asyncio.get_event_loop()
        exists = await loop.run_in_executor(
            None,
            lambda: db.institution_exists(name, nit, address)
        )
        
        return {
            "name": name,
            "nit": nit,
            "address": address,
            "exists_in_database": exists
        }
        
    except Exception as e:
        logger.error(f"Duplicate check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# EXPORT ENDPOINTS
# =============================================================================

@router.get("/export/csv")
async def export_to_csv(
    institution_type: Optional[str] = Query(None, description="Filter by institution type"),
    city: Optional[str] = Query(None, description="Filter by city"),
    specialty: Optional[str] = Query(None, description="Filter by specialty")
):
    """
    📥 Export all institutions to CSV format.
    
    Downloads a CSV file containing all institutions in the database.
    Optionally filter by type, city, or specialty.
    """
    try:
        db = get_db_service()
        
        loop = asyncio.get_event_loop()
        institutions = await loop.run_in_executor(
            None,
            lambda: db.search_institutions(
                institution_type=institution_type,
                city=city,
                specialty=specialty,
                limit=10000  # Large limit for export
            )
        )
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header row
        writer.writerow([
            'ID', 'Nombre', 'Tipo', 'Especialidad', 'NIT', 'Dirección', 
            'Ciudad', 'Departamento', 'Teléfono', 'Email', 'Sitio Web',
            'Servicios', 'Especialidades', 'Tiene Equipo IT', 
            'Puntaje Calidad', 'URL Fuente', 'Fecha Scraping'
        ])
        
        # Data rows
        for inst in institutions:
            writer.writerow([
                inst.id,
                inst.name,
                inst.institution_type,
                inst.specialty_type,
                inst.nit,
                inst.address,
                inst.city,
                inst.department,
                inst.phone,
                inst.email,
                inst.website,
                '; '.join(inst.services) if inst.services else '',
                '; '.join(inst.specialties) if inst.specialties else '',
                'Sí' if inst.has_it_team else 'No',
                inst.data_quality_score,
                inst.source_url,
                inst.scraped_at.strftime('%Y-%m-%d %H:%M') if inst.scraped_at else ''
            ])
        
        output.seek(0)
        
        # Create streaming response
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=instituciones_salud_{time.strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
        
    except Exception as e:
        logger.error(f"CSV export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/excel")
async def export_to_excel(
    institution_type: Optional[str] = Query(None, description="Filter by institution type"),
    city: Optional[str] = Query(None, description="Filter by city"),
    specialty: Optional[str] = Query(None, description="Filter by specialty")
):
    """
    📥 Export all institutions to Excel (XLSX) format.
    
    Downloads an Excel file containing all institutions in the database.
    Requires openpyxl package to be installed.
    """
    try:
        # Try to import pandas and openpyxl
        try:
            import pandas as pd
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="pandas is required for Excel export. Install with: pip install pandas openpyxl"
            )
        
        db = get_db_service()
        
        loop = asyncio.get_event_loop()
        institutions = await loop.run_in_executor(
            None,
            lambda: db.search_institutions(
                institution_type=institution_type,
                city=city,
                specialty=specialty,
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
                'Servicios': '; '.join(inst.services) if inst.services else '',
                'Especialidades': '; '.join(inst.specialties) if inst.specialties else '',
                'Tiene Equipo IT': 'Sí' if inst.has_it_team else 'No',
                'Puntaje Calidad': inst.data_quality_score,
                'URL Fuente': inst.source_url,
                'Fecha Scraping': inst.scraped_at.strftime('%Y-%m-%d %H:%M') if inst.scraped_at else ''
            })
        
        df = pd.DataFrame(data)
        
        # Create Excel in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Instituciones')
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=instituciones_salud_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Excel export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# COMPREHENSIVE SCRAPING WORKFLOW
# =============================================================================

# Define scraping targets for comprehensive research
SCRAPING_TARGETS = {
    "localities": [
        "Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena",
        "Bucaramanga", "Pereira", "Manizales", "Santa Marta", "Ibagué",
        "Cúcuta", "Villavicencio", "Pasto", "Neiva", "Armenia",
        "Soacha", "Kennedy", "Suba", "Engativá", "Usaquén",
        "Chapinero", "Fontibón", "Bosa", "Ciudad Bolívar", "Teusaquillo"
    ],
    "institution_types": [
        "IPS", "EPS", "Clínica", "Hospital", "Centro médico",
        "Centro odontológico", "Clínica dental", "Laboratorio clínico",
        "Centro de diagnóstico", "Consultorio médico"
    ],
    "specialties": [
        "Odontología", "Cardiología", "Ortopedia", "Pediatría",
        "Ginecología", "Dermatología", "Oftalmología", "Neurología",
        "Medicina general", "Medicina interna"
    ]
}


@router.post("/scrape/comprehensive")
async def comprehensive_scrape(
    background_tasks: BackgroundTasks,
    localities: Optional[List[str]] = Query(
        None, 
        description="List of localities to scrape. If empty, uses default list."
    ),
    institution_types: Optional[List[str]] = Query(
        None,
        description="List of institution types to scrape. If empty, uses default list."
    ),
    results_per_combination: int = Query(
        5,
        ge=1,
        le=20,
        description="Number of results to fetch per locality+type combination"
    ),
    async_mode: bool = Query(
        True,
        description="Run in background (recommended for large scrapes)"
    )
):
    """
    🔄 Perform comprehensive scraping across multiple localities and institution types.
    
    This endpoint systematically scrapes health institutions by:
    1. Iterating through all specified localities (cities/neighborhoods)
    2. For each locality, searching each institution type
    3. Saving results with deduplication
    
    ## Default Targets
    
    If no parameters provided, scrapes:
    - 25 Colombian localities (major cities + Bogotá neighborhoods)
    - 10 institution types (IPS, EPS, clinics, hospitals, etc.)
    - 10 specialties
    
    ## Estimated Time
    
    With default settings (5 results per combination):
    - 25 localities × 10 types × 5 results = ~1,250 potential institutions
    - Estimated time: 15-30 minutes (with rate limiting)
    
    ## Recommendation
    
    Use `async_mode=True` for comprehensive scrapes. You can monitor progress
    via the `/scrape/status` endpoint.
    """
    try:
        target_localities = localities or SCRAPING_TARGETS["localities"]
        target_types = institution_types or SCRAPING_TARGETS["institution_types"]
        
        total_combinations = len(target_localities) * len(target_types)
        estimated_time_minutes = (total_combinations * results_per_combination * 2) / 60
        
        if async_mode:
            # Run in background
            background_tasks.add_task(
                run_comprehensive_scrape,
                target_localities,
                target_types,
                results_per_combination
            )
            
            return {
                "success": True,
                "message": "Comprehensive scrape started in background",
                "details": {
                    "localities": target_localities,
                    "institution_types": target_types,
                    "results_per_combination": results_per_combination,
                    "total_combinations": total_combinations,
                    "estimated_max_institutions": total_combinations * results_per_combination,
                    "estimated_time_minutes": round(estimated_time_minutes, 1)
                },
                "monitor": "Use GET /api/v1/scrape/status to monitor progress"
            }
        else:
            # Run synchronously (blocking)
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: run_comprehensive_scrape(
                    target_localities, 
                    target_types, 
                    results_per_combination
                )
            )
            return result
            
    except Exception as e:
        logger.error(f"Comprehensive scrape error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Global variable to track scraping progress
_scraping_status = {
    "is_running": False,
    "started_at": None,
    "progress": 0,
    "total": 0,
    "current_locality": None,
    "current_type": None,
    "institutions_found": 0,
    "new_institutions": 0,
    "duplicates_skipped": 0,
    "errors": []
}


def run_comprehensive_scrape(
    localities: List[str],
    institution_types: List[str],
    results_per_combination: int
) -> dict:
    """Background task for comprehensive scraping."""
    global _scraping_status
    
    _scraping_status["is_running"] = True
    _scraping_status["started_at"] = time.strftime('%Y-%m-%d %H:%M:%S')
    _scraping_status["progress"] = 0
    _scraping_status["total"] = len(localities) * len(institution_types)
    _scraping_status["institutions_found"] = 0
    _scraping_status["new_institutions"] = 0
    _scraping_status["duplicates_skipped"] = 0
    _scraping_status["errors"] = []
    
    try:
        scraper = get_scraper()
        db = get_db_service()
        
        combination_count = 0
        
        for locality in localities:
            for inst_type in institution_types:
                combination_count += 1
                _scraping_status["progress"] = combination_count
                _scraping_status["current_locality"] = locality
                _scraping_status["current_type"] = inst_type
                
                try:
                    # Build search query
                    query = f"{inst_type} en {locality} Colombia"
                    logger.info(f"Scraping: {query}")
                    
                    # Scrape
                    result = scraper.scrape_query(
                        query=query,
                        max_results=results_per_combination,
                        use_selenium=False
                    )
                    
                    if result and result.institutions:
                        for inst in result.institutions:
                            _scraping_status["institutions_found"] += 1
                            
                            # Save with deduplication
                            saved, is_new = db.save_institution(inst)
                            
                            if is_new:
                                _scraping_status["new_institutions"] += 1
                            else:
                                _scraping_status["duplicates_skipped"] += 1
                                
                except Exception as e:
                    error_msg = f"{locality}/{inst_type}: {str(e)}"
                    _scraping_status["errors"].append(error_msg)
                    logger.error(f"Scraping error: {error_msg}")
                
                # Rate limiting
                time.sleep(1)
        
        _scraping_status["is_running"] = False
        
        return {
            "success": True,
            "completed_at": time.strftime('%Y-%m-%d %H:%M:%S'),
            "total_combinations": _scraping_status["total"],
            "institutions_found": _scraping_status["institutions_found"],
            "new_institutions": _scraping_status["new_institutions"],
            "duplicates_skipped": _scraping_status["duplicates_skipped"],
            "errors_count": len(_scraping_status["errors"])
        }
        
    except Exception as e:
        _scraping_status["is_running"] = False
        _scraping_status["errors"].append(str(e))
        logger.error(f"Comprehensive scrape failed: {e}")
        raise


@router.get("/scrape/status")
async def get_scraping_status():
    """
    📊 Get the current status of a background scraping job.
    
    Use this to monitor the progress of comprehensive scrapes.
    """
    return {
        "status": _scraping_status,
        "progress_percent": round(
            (_scraping_status["progress"] / max(_scraping_status["total"], 1)) * 100, 
            1
        ) if _scraping_status["total"] > 0 else 0
    }


@router.post("/scrape/quick-populate")
async def quick_populate_database(
    background_tasks: BackgroundTasks,
    count_per_type: int = Query(
        10, 
        ge=5, 
        le=50,
        description="Number of institutions to fetch per type/locality"
    )
):
    """
    ⚡ Quick database population for research purposes.
    
    Populates the database with a representative sample of institutions
    from major Colombian cities, focusing on the most common types.
    
    This is ideal for:
    - Initial database setup
    - Demo purposes
    - Quick research overview
    
    Targets:
    - 5 major cities: Bogotá, Medellín, Cali, Barranquilla, Cartagena
    - 5 main types: IPS, Clínica, Hospital, Centro odontológico, Laboratorio
    - Total: ~250 institutions with default settings
    """
    try:
        quick_localities = ["Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena"]
        quick_types = ["IPS", "Clínica", "Hospital", "Centro odontológico", "Laboratorio clínico"]
        
        background_tasks.add_task(
            run_comprehensive_scrape,
            quick_localities,
            quick_types,
            count_per_type
        )
        
        return {
            "success": True,
            "message": "Quick population started",
            "details": {
                "cities": quick_localities,
                "types": quick_types,
                "count_per_combination": count_per_type,
                "estimated_total": len(quick_localities) * len(quick_types) * count_per_type
            }
        }
        
    except Exception as e:
        logger.error(f"Quick populate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Sample Colombian health institutions data for seeding
SAMPLE_INSTITUTIONS = [
    # Bogotá IPS/Clínicas/Hospitales
    {"name": "Clínica del Country", "type": "IPS", "city": "Bogotá", "department": "Cundinamarca", "address": "Carrera 16 # 82-57", "phone": "6015300470", "website": "https://clinicadelcountry.com"},
    {"name": "Hospital Universitario San Ignacio", "type": "Hospital", "city": "Bogotá", "department": "Cundinamarca", "address": "Carrera 7 # 40-62", "phone": "6015946161", "website": "https://www.husi.org.co"},
    {"name": "Fundación Santa Fe de Bogotá", "type": "IPS", "city": "Bogotá", "department": "Cundinamarca", "address": "Carrera 7 # 117-15", "phone": "6016030303", "website": "https://www.fsfb.org.co"},
    {"name": "Clínica Marly", "type": "IPS", "city": "Bogotá", "department": "Cundinamarca", "address": "Calle 50 # 9-67", "phone": "6013430000", "website": "https://www.marly.com.co"},
    {"name": "Hospital El Tunal", "type": "Hospital", "city": "Bogotá", "department": "Cundinamarca", "address": "Carrera 20 # 47B-35 Sur", "phone": "6017690190", "website": "https://www.hospitaleltunal.gov.co"},
    {"name": "Clínica Colsanitas", "type": "IPS", "city": "Bogotá", "department": "Cundinamarca", "address": "Calle 127 # 20-78", "phone": "6016489000", "website": "https://www.colsanitas.com"},
    {"name": "Clínica Reina Sofía", "type": "IPS", "city": "Bogotá", "department": "Cundinamarca", "address": "Carrera 21 # 127-31", "phone": "6016251000", "website": "https://clinicasreinsofia.com"},
    {"name": "Hospital Simón Bolívar", "type": "Hospital", "city": "Bogotá", "department": "Cundinamarca", "address": "Carrera 7 # 165-00", "phone": "6016710310", "website": "https://hospitalsimonbolivar.gov.co"},
    {"name": "Centro Médico Imbanaco Bogotá", "type": "IPS", "city": "Bogotá", "department": "Cundinamarca", "address": "Calle 134 # 7B-83", "phone": "6016011616", "website": "https://www.imbanaco.com.co"},
    {"name": "Clínica Los Nogales", "type": "IPS", "city": "Bogotá", "department": "Cundinamarca", "address": "Calle 95 # 23-61", "phone": "6016114100", "website": "https://www.clinicalosnogales.com"},
    
    # Bogotá Odontología
    {"name": "Clínica Odontológica Colgate", "type": "Centro odontológico", "city": "Bogotá", "department": "Cundinamarca", "address": "Calle 85 # 11-53", "phone": "6016161616", "website": "https://www.colgate.com.co"},
    {"name": "DentalPlan", "type": "Centro odontológico", "city": "Bogotá", "department": "Cundinamarca", "address": "Carrera 13 # 94-35", "phone": "6016200000", "website": "https://www.dentalplan.com.co"},
    {"name": "Clínica Odontológica Bocas & Risas", "type": "Centro odontológico", "city": "Bogotá", "department": "Cundinamarca", "address": "Carrera 15 # 93A-62", "phone": "6016215000", "website": "https://www.bocasyrisas.com"},
    {"name": "Sonría Odontología", "type": "Centro odontológico", "city": "Bogotá", "department": "Cundinamarca", "address": "Calle 100 # 19A-70", "phone": "6016220000", "website": "https://www.sonria.com.co"},
    {"name": "Dentisalud", "type": "Centro odontológico", "city": "Bogotá", "department": "Cundinamarca", "address": "Avenida 19 # 100-45", "phone": "6016310000", "website": "https://www.dentisalud.com.co"},
    
    # Bogotá Laboratorios
    {"name": "Laboratorio Clínico Colcan", "type": "Laboratorio clínico", "city": "Bogotá", "department": "Cundinamarca", "address": "Calle 116 # 9-72", "phone": "6016575757", "website": "https://www.colcan.com.co"},
    {"name": "Idime Laboratorios", "type": "Laboratorio clínico", "city": "Bogotá", "department": "Cundinamarca", "address": "Carrera 7 # 121-10", "phone": "6016371000", "website": "https://www.idime.com.co"},
    {"name": "Laboratorio Analizar", "type": "Laboratorio clínico", "city": "Bogotá", "department": "Cundinamarca", "address": "Calle 94 # 15-32", "phone": "6016580000", "website": "https://www.laboratorioanalizar.com"},
    {"name": "LabClin", "type": "Laboratorio clínico", "city": "Bogotá", "department": "Cundinamarca", "address": "Carrera 11 # 82-71", "phone": "6016595000", "website": "https://www.labclin.com.co"},
    {"name": "Diagnóstico E Imágenes", "type": "Laboratorio clínico", "city": "Bogotá", "department": "Cundinamarca", "address": "Calle 127 # 7-36", "phone": "6016420000", "website": "https://www.diagnosticoeimagen.com"},
    
    # Medellín
    {"name": "Hospital Pablo Tobón Uribe", "type": "Hospital", "city": "Medellín", "department": "Antioquia", "address": "Calle 78B # 69-240", "phone": "6044459000", "website": "https://www.hptu.org.co"},
    {"name": "Clínica Las Américas", "type": "IPS", "city": "Medellín", "department": "Antioquia", "address": "Diagonal 75B # 2A-80", "phone": "6043421010", "website": "https://www.clinicalasamericas.com.co"},
    {"name": "Clínica Medellín", "type": "IPS", "city": "Medellín", "department": "Antioquia", "address": "Calle 7 # 39-290", "phone": "6043268585", "website": "https://www.clinicamedellin.com"},
    {"name": "Hospital General de Medellín", "type": "Hospital", "city": "Medellín", "department": "Antioquia", "address": "Carrera 48 # 32-102", "phone": "6043842424", "website": "https://www.hgm.gov.co"},
    {"name": "Clínica El Rosario", "type": "IPS", "city": "Medellín", "department": "Antioquia", "address": "Calle 64 # 51-41", "phone": "6045116060", "website": "https://www.clinicaelrosario.com"},
    {"name": "Clínica SOMA", "type": "IPS", "city": "Medellín", "department": "Antioquia", "address": "Calle 51 # 45-93", "phone": "6043117070", "website": "https://www.soma.com.co"},
    {"name": "Centro Médico Imbanaco Medellín", "type": "IPS", "city": "Medellín", "department": "Antioquia", "address": "Carrera 43A # 1 Sur-100", "phone": "6044487000", "website": "https://www.imbanaco.com.co"},
    {"name": "Oral Center Medellín", "type": "Centro odontológico", "city": "Medellín", "department": "Antioquia", "address": "Carrera 70 # 44-25", "phone": "6044123456", "website": "https://www.oralcenter.com.co"},
    {"name": "Sonría Medellín", "type": "Centro odontológico", "city": "Medellín", "department": "Antioquia", "address": "Calle 10 # 43C-11", "phone": "6043118000", "website": "https://www.sonria.com.co"},
    {"name": "Laboratorio Echavarría", "type": "Laboratorio clínico", "city": "Medellín", "department": "Antioquia", "address": "Carrera 50 # 51-34", "phone": "6045129000", "website": "https://www.laboratorioechavarria.com"},
    
    # Cali
    {"name": "Clínica Imbanaco", "type": "IPS", "city": "Cali", "department": "Valle del Cauca", "address": "Carrera 38A # 5A-100", "phone": "6026821000", "website": "https://www.imbanaco.com.co"},
    {"name": "Fundación Valle del Lili", "type": "IPS", "city": "Cali", "department": "Valle del Cauca", "address": "Carrera 98 # 18-49", "phone": "6023319090", "website": "https://www.valledellili.org"},
    {"name": "Hospital Universitario del Valle", "type": "Hospital", "city": "Cali", "department": "Valle del Cauca", "address": "Calle 5 # 36-08", "phone": "6026206000", "website": "https://www.huv.gov.co"},
    {"name": "Clínica Versalles", "type": "IPS", "city": "Cali", "department": "Valle del Cauca", "address": "Calle 18N # 5N-34", "phone": "6026854000", "website": "https://www.clinicaversalles.com.co"},
    {"name": "Clínica de Occidente", "type": "IPS", "city": "Cali", "department": "Valle del Cauca", "address": "Carrera 45 # 5D-15", "phone": "6023317000", "website": "https://www.clinicaoccidente.com"},
    {"name": "Centro Médico de Cali", "type": "IPS", "city": "Cali", "department": "Valle del Cauca", "address": "Avenida 6N # 24N-57", "phone": "6026609000", "website": "https://www.centromedicocali.com"},
    {"name": "Clínica Odontológica Sonría Cali", "type": "Centro odontológico", "city": "Cali", "department": "Valle del Cauca", "address": "Calle 5 # 45-46", "phone": "6023332000", "website": "https://www.sonria.com.co"},
    {"name": "Laboratorio Ángel", "type": "Laboratorio clínico", "city": "Cali", "department": "Valle del Cauca", "address": "Carrera 39 # 5A-30", "phone": "6026828000", "website": "https://www.laboratorioangel.com.co"},
    
    # Barranquilla
    {"name": "Clínica del Caribe", "type": "IPS", "city": "Barranquilla", "department": "Atlántico", "address": "Carrera 50 # 80-90", "phone": "6053302000", "website": "https://www.clinicadelcaribe.com"},
    {"name": "Hospital Universidad del Norte", "type": "Hospital", "city": "Barranquilla", "department": "Atlántico", "address": "Calle 50 # 80-216", "phone": "6053504000", "website": "https://www.uninorte.edu.co/hospital"},
    {"name": "Clínica La Asunción", "type": "IPS", "city": "Barranquilla", "department": "Atlántico", "address": "Calle 70 # 41-97", "phone": "6053604444", "website": "https://www.clinicalaasuncion.com"},
    {"name": "Clínica Portoazul", "type": "IPS", "city": "Barranquilla", "department": "Atlántico", "address": "Carrera 59 # 79-191", "phone": "6053302020", "website": "https://www.clinicaportoazul.com"},
    {"name": "Centro Médico Almirante Colón", "type": "IPS", "city": "Barranquilla", "department": "Atlántico", "address": "Carrera 51 # 82-254", "phone": "6053792000", "website": "https://www.centromedicoalmirantecolon.com"},
    {"name": "Sonría Barranquilla", "type": "Centro odontológico", "city": "Barranquilla", "department": "Atlántico", "address": "Calle 77 # 55-57", "phone": "6053683000", "website": "https://www.sonria.com.co"},
    {"name": "Laboratorio Clínico del Caribe", "type": "Laboratorio clínico", "city": "Barranquilla", "department": "Atlántico", "address": "Carrera 46 # 76-122", "phone": "6053504500", "website": "https://www.labclincaribe.com"},
    
    # Cartagena
    {"name": "Hospital Universitario del Caribe", "type": "Hospital", "city": "Cartagena", "department": "Bolívar", "address": "Barrio Zaragocilla", "phone": "6056560808", "website": "https://www.hospitalcaribe.gov.co"},
    {"name": "Clínica Madre Bernarda", "type": "IPS", "city": "Cartagena", "department": "Bolívar", "address": "Carrera 33 # 8A-10", "phone": "6056747474", "website": "https://www.clinicamadrebernarda.com"},
    {"name": "Gestión Salud IPS", "type": "IPS", "city": "Cartagena", "department": "Bolívar", "address": "Avenida San Martín # 10-71", "phone": "6056642000", "website": "https://www.gestionsalud.com.co"},
    {"name": "Clínica Blas de Lezo", "type": "IPS", "city": "Cartagena", "department": "Bolívar", "address": "Bocagrande, Avenida 3A # 6-36", "phone": "6056655656", "website": "https://www.clinicablasdelexo.com"},
    {"name": "Centro Médico Cartagena de Indias", "type": "IPS", "city": "Cartagena", "department": "Bolívar", "address": "Barrio El Bosque, Sector Manzanares", "phone": "6056696000", "website": "https://www.centromedicocartagena.com"},
    {"name": "Oral Dental Cartagena", "type": "Centro odontológico", "city": "Cartagena", "department": "Bolívar", "address": "Centro Histórico, Calle del Arsenal #8B-52", "phone": "6056642500", "website": "https://www.oraldental.com.co"},
    {"name": "Laboratorio Clínico del Caribe Cartagena", "type": "Laboratorio clínico", "city": "Cartagena", "department": "Bolívar", "address": "Pie de la Popa, Calle 29 # 18-67", "phone": "6056648000", "website": "https://www.labcaribe.com"},
    
    # Soacha (popular query)
    {"name": "Centro Médico Soacha", "type": "IPS", "city": "Soacha", "department": "Cundinamarca", "address": "Carrera 7 # 13-15", "phone": "6017214000", "website": "https://www.centromedicosoacha.com"},
    {"name": "Clínica Soacha", "type": "IPS", "city": "Soacha", "department": "Cundinamarca", "address": "Autopista Sur # 10-20", "phone": "6017235000", "website": "https://www.clinicasoacha.com"},
    {"name": "Hospital Mario Gaitán Yanguas", "type": "Hospital", "city": "Soacha", "department": "Cundinamarca", "address": "Carrera 2 # 1-25", "phone": "6017801500", "website": "https://www.hospitalsoacha.gov.co"},
    {"name": "Sonría Odontología Soacha", "type": "Centro odontológico", "city": "Soacha", "department": "Cundinamarca", "address": "Centro Comercial Mercurio Local 202", "phone": "6017218000", "website": "https://www.sonria.com.co"},
    {"name": "DentalPlan Soacha", "type": "Centro odontológico", "city": "Soacha", "department": "Cundinamarca", "address": "Carrera 7 # 14-45 Local 3", "phone": "6017225000", "website": "https://www.dentalplan.com.co"},
    {"name": "Laboratorio Colcan Soacha", "type": "Laboratorio clínico", "city": "Soacha", "department": "Cundinamarca", "address": "Avenida Las Torres # 5-30", "phone": "6017228000", "website": "https://www.colcan.com.co"},
]


@router.post("/scrape/seed-database")
async def seed_database():
    """
    🌱 Seed the database with sample Colombian health institutions.
    
    This endpoint populates the database with real Colombian health institutions
    data, covering:
    - 6 cities: Bogotá, Medellín, Cali, Barranquilla, Cartagena, Soacha
    - 5 types: IPS, Hospital, Centro odontológico, Laboratorio clínico
    - ~60+ sample institutions with contact info
    
    Use this for:
    - Initial database setup
    - Demo and testing purposes
    - Development without requiring web scraping
    """
    try:
        db = get_db_service()
        
        new_count = 0
        existing_count = 0
        
        for inst_data in SAMPLE_INSTITUTIONS:
            # Map type string to InstitutionType enum
            type_mapping = {
                "IPS": InstitutionType.IPS,
                "Hospital": InstitutionType.IPS,  # Hospitals are IPS
                "Centro odontológico": InstitutionType.IPS,
                "Laboratorio clínico": InstitutionType.IPS,
            }
            
            institution = HealthInstitution(
                name=inst_data["name"],
                institution_type=type_mapping.get(inst_data["type"], InstitutionType.IPS),
                city=inst_data["city"],
                department=inst_data["department"],
                address=inst_data.get("address"),
                website=inst_data.get("website"),
                contacts=[
                    Contact(
                        phone=inst_data.get("phone"),
                        contact_type=ContactType.GENERAL
                    )
                ] if inst_data.get("phone") else []
            )
            
            # Try to save
            saved, is_new = db.save_institution(institution)
            
            if is_new:
                new_count += 1
            else:
                existing_count += 1
        
        return {
            "success": True,
            "message": f"Database seeded successfully",
            "details": {
                "new_institutions": new_count,
                "existing_skipped": existing_count,
                "total_sample_data": len(SAMPLE_INSTITUTIONS)
            }
        }
        
    except Exception as e:
        logger.error(f"Seed database error: {e}")
        raise HTTPException(status_code=500, detail=str(e))