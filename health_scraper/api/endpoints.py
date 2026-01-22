import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
import time
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from ..models.institution import (
    HealthInstitution, ScrapeResult, BulkScrapeRequest, 
    BulkScrapeResponse, InstitutionType
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