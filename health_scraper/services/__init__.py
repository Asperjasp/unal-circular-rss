"""
Services module for Health Institutions Scraper

This module provides high-level services for:
- Natural language query parsing and search
- Database operations with deduplication
- Scraping orchestration

Example Usage:
    from health_scraper.services import PromptSearchService, search_health_institutions
    
    # Quick search
    results = search_health_institutions("Odontología cerca de Soacha")
    
    # Or with full service
    service = PromptSearchService()
    results = service.search_and_scrape("Clínica dental con implantes en Bogotá")
"""

from .search_service import (
    QueryParser,
    ParsedQuery,
    SearchResult,
    PromptSearchService,
    search_health_institutions
)

from .vision_service import (
    VisionExtractorService,
    ExtractionResult,
    DocumentType
)

__all__ = [
    "QueryParser",
    "ParsedQuery", 
    "SearchResult",
    "PromptSearchService",
    "search_health_institutions",
    "VisionExtractorService",
    "ExtractionResult",
    "DocumentType"
]
