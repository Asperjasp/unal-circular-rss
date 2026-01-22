"""
Prompt-Based Search Service for Health Institutions

This module provides natural language query parsing and search functionality.
Users can search using prompts like:
- "Odontology specialized in implants near Soacha"
- "Cardiología en Bogotá"
- "Clínica dental con ortodoncia cerca de Kennedy"

The service parses the query, extracts relevant filters, searches the database,
and optionally triggers new scraping if results are insufficient.
"""

import re
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import time

from ..database.service import DatabaseService
from ..database.models import InstitutionDB
from ..scrapers.base_scraper import BaseHealthScraper
from ..models.institution import HealthInstitution, SpecialtyType, InstitutionType

logger = logging.getLogger(__name__)


@dataclass
class ParsedQuery:
    """
    Parsed components from a natural language search query.
    
    Attributes:
        specialty: The medical specialty (e.g., "odontologia", "cardiologia")
        treatment: Specific treatment mentioned (e.g., "implantes", "ortodoncia")
        city: City name
        department: Department/state name
        near_location: "Near X" location phrase
        institution_type: Type of institution requested
        keywords: Additional keywords for search
        original_query: The original query string
    """
    specialty: Optional[str] = None
    treatment: Optional[str] = None
    city: Optional[str] = None
    department: Optional[str] = None
    near_location: Optional[str] = None
    institution_type: Optional[str] = None
    keywords: Optional[List[str]] = None
    original_query: str = ""
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


@dataclass
class SearchResult:
    """
    Results from a prompt-based search.
    
    Attributes:
        institutions: List of matching institutions
        total_count: Total number of matches
        from_database: How many came from the database
        newly_scraped: How many were scraped in this query
        parsed_query: The parsed query components
        execution_time: Time taken to execute the search
    """
    institutions: List[InstitutionDB]
    total_count: int
    from_database: int
    newly_scraped: int
    parsed_query: ParsedQuery
    execution_time: float


class QueryParser:
    """
    Parses natural language queries into structured search parameters.
    
    Supports Spanish and English queries with common patterns like:
    - "[specialty] near [location]"
    - "[specialty] specialized in [treatment] in [city]"
    - "Clínica de [specialty] en [city]"
    """
    
    # Specialty mappings (Spanish -> normalized)
    SPECIALTY_MAPPINGS = {
        # Dental
        "odontologia": "odontologia",
        "odontología": "odontologia",
        "dental": "odontologia",
        "dentista": "odontologia",
        "dientes": "odontologia",
        "ortodoncia": "ortodoncia",
        "brackets": "ortodoncia",
        "implantes dentales": "implantologia",
        "implantes": "implantologia",
        "endodoncia": "endodoncia",
        "conducto": "endodoncia",
        "periodoncia": "periodoncia",
        "encias": "periodoncia",
        "encías": "periodoncia",
        
        # Cardiology
        "cardiologia": "cardiologia",
        "cardiología": "cardiologia",
        "corazon": "cardiologia",
        "corazón": "cardiologia",
        "cardiaco": "cardiologia",
        "cardíaco": "cardiologia",
        
        # Ophthalmology
        "oftalmologia": "oftalmologia",
        "oftalmología": "oftalmologia",
        "ojos": "oftalmologia",
        "vision": "oftalmologia",
        "visión": "oftalmologia",
        "optica": "oftalmologia",
        "óptica": "oftalmologia",
        
        # Dermatology
        "dermatologia": "dermatologia",
        "dermatología": "dermatologia",
        "piel": "dermatologia",
        
        # Orthopedics
        "ortopedia": "ortopedia",
        "traumatologia": "traumatologia",
        "traumatología": "traumatologia",
        "huesos": "ortopedia",
        "fracturas": "traumatologia",
        
        # Gynecology
        "ginecologia": "ginecologia",
        "ginecología": "ginecologia",
        "obstetricia": "obstetricia",
        "embarazo": "obstetricia",
        
        # Pediatrics
        "pediatria": "pediatria",
        "pediatría": "pediatria",
        "niños": "pediatria",
        "infantil": "pediatria",
        
        # Neurology
        "neurologia": "neurologia",
        "neurología": "neurologia",
        "cerebro": "neurologia",
        "nervios": "neurologia",
        
        # Psychiatry/Psychology
        "psiquiatria": "psiquiatria",
        "psiquiatría": "psiquiatria",
        "psicologia": "psicologia",
        "psicología": "psicologia",
        "salud mental": "psiquiatria",
        
        # General
        "medicina general": "medicina_general",
        "medico general": "medicina_general",
        "médico general": "medicina_general",
        "medicina interna": "medicina_interna",
    }
    
    # Treatment mappings
    TREATMENT_MAPPINGS = {
        # Dental treatments
        "implantes": "implantes_dentales",
        "ortodoncia": "ortodoncia",
        "brackets": "brackets",
        "blanqueamiento": "blanqueamiento_dental",
        "limpieza dental": "limpieza_dental",
        "extraccion": "extraccion_dental",
        "extracción": "extraccion_dental",
        "corona": "coronas_dentales",
        "protesis": "protesis_dental",
        "prótesis": "protesis_dental",
        "endodoncia": "endodoncia",
        "conducto": "conducto_radicular",
        
        # Cardiology treatments
        "electrocardiograma": "electrocardiograma",
        "ecocardiograma": "ecocardiograma",
        "cateterismo": "cateterismo",
        "marcapasos": "marcapasos",
        
        # Ophthalmology treatments
        "lasik": "cirugia_lasik",
        "cataratas": "cirugia_cataratas",
        "lentes": "lentes",
        "gafas": "lentes",
        
        # General
        "cirugia": "cirugia",
        "cirugía": "cirugia",
        "consulta": "consulta_general",
        "examen": "examen_medico",
    }
    
    # Colombian cities and locations
    COLOMBIAN_LOCATIONS = {
        # Bogotá and surroundings
        "bogota": ("Bogotá", "Bogotá D.C."),
        "bogotá": ("Bogotá", "Bogotá D.C."),
        "soacha": ("Soacha", "Cundinamarca"),
        "chia": ("Chía", "Cundinamarca"),
        "chía": ("Chía", "Cundinamarca"),
        "zipaquira": ("Zipaquirá", "Cundinamarca"),
        "zipaquirá": ("Zipaquirá", "Cundinamarca"),
        "funza": ("Funza", "Cundinamarca"),
        "mosquera": ("Mosquera", "Cundinamarca"),
        "madrid": ("Madrid", "Cundinamarca"),
        "facatativa": ("Facatativá", "Cundinamarca"),
        "facatativá": ("Facatativá", "Cundinamarca"),
        "cota": ("Cota", "Cundinamarca"),
        "la calera": ("La Calera", "Cundinamarca"),
        "sibate": ("Sibaté", "Cundinamarca"),
        "sibaté": ("Sibaté", "Cundinamarca"),
        
        # Bogotá localities (treated as areas)
        "kennedy": ("Kennedy", "Bogotá D.C."),
        "bosa": ("Bosa", "Bogotá D.C."),
        "usme": ("Usme", "Bogotá D.C."),
        "ciudad bolivar": ("Ciudad Bolívar", "Bogotá D.C."),
        "fontibon": ("Fontibón", "Bogotá D.C."),
        "fontibón": ("Fontibón", "Bogotá D.C."),
        "engativa": ("Engativá", "Bogotá D.C."),
        "engativá": ("Engativá", "Bogotá D.C."),
        "suba": ("Suba", "Bogotá D.C."),
        "usaquen": ("Usaquén", "Bogotá D.C."),
        "usaquén": ("Usaquén", "Bogotá D.C."),
        "chapinero": ("Chapinero", "Bogotá D.C."),
        "teusaquillo": ("Teusaquillo", "Bogotá D.C."),
        "santa fe": ("Santa Fe", "Bogotá D.C."),
        "candelaria": ("La Candelaria", "Bogotá D.C."),
        
        # Major Colombian cities
        "medellin": ("Medellín", "Antioquia"),
        "medellín": ("Medellín", "Antioquia"),
        "cali": ("Cali", "Valle del Cauca"),
        "barranquilla": ("Barranquilla", "Atlántico"),
        "cartagena": ("Cartagena", "Bolívar"),
        "cucuta": ("Cúcuta", "Norte de Santander"),
        "cúcuta": ("Cúcuta", "Norte de Santander"),
        "bucaramanga": ("Bucaramanga", "Santander"),
        "pereira": ("Pereira", "Risaralda"),
        "ibague": ("Ibagué", "Tolima"),
        "ibagué": ("Ibagué", "Tolima"),
        "santa marta": ("Santa Marta", "Magdalena"),
        "manizales": ("Manizales", "Caldas"),
        "neiva": ("Neiva", "Huila"),
        "villavicencio": ("Villavicencio", "Meta"),
        "pasto": ("Pasto", "Nariño"),
        "monteria": ("Montería", "Córdoba"),
        "montería": ("Montería", "Córdoba"),
        "armenia": ("Armenia", "Quindío"),
        "popayan": ("Popayán", "Cauca"),
        "popayán": ("Popayán", "Cauca"),
        "valledupar": ("Valledupar", "Cesar"),
        "sincelejo": ("Sincelejo", "Sucre"),
        "tunja": ("Tunja", "Boyacá"),
    }
    
    # Institution type patterns
    INSTITUTION_TYPE_PATTERNS = {
        "clinica": InstitutionType.CLINICA,
        "clínica": InstitutionType.CLINICA,
        "hospital": InstitutionType.HOSPITAL,
        "centro medico": InstitutionType.CENTRO_MEDICO,
        "centro médico": InstitutionType.CENTRO_MEDICO,
        "consultorio": InstitutionType.CONSULTORIO,
        "laboratorio": InstitutionType.LABORATORIO_CLINICO,
        "eps": InstitutionType.EPS,
        "ips": InstitutionType.IPS,
        "fundacion": InstitutionType.FUNDACION,
        "fundación": InstitutionType.FUNDACION,
    }
    
    def parse(self, query: str) -> ParsedQuery:
        """
        Parse a natural language query into structured components.
        
        Args:
            query: Natural language search query
            
        Returns:
            ParsedQuery with extracted components
            
        Examples:
            >>> parser = QueryParser()
            >>> result = parser.parse("Odontología especializada en implantes cerca de Soacha")
            >>> result.specialty
            'odontologia'
            >>> result.treatment
            'implantes_dentales'
            >>> result.near_location
            'Soacha'
        """
        parsed = ParsedQuery(original_query=query)
        query_lower = query.lower()
        
        # Extract specialty
        parsed.specialty = self._extract_specialty(query_lower)
        
        # Extract treatment
        parsed.treatment = self._extract_treatment(query_lower)
        
        # Extract location
        city, department, near = self._extract_location(query_lower)
        parsed.city = city
        parsed.department = department
        parsed.near_location = near
        
        # Extract institution type
        parsed.institution_type = self._extract_institution_type(query_lower)
        
        # Extract remaining keywords
        parsed.keywords = self._extract_keywords(query_lower, parsed)
        
        logger.info(f"Parsed query '{query}' -> specialty={parsed.specialty}, "
                   f"treatment={parsed.treatment}, city={parsed.city}, near={parsed.near_location}")
        
        return parsed
    
    def _extract_specialty(self, query: str) -> Optional[str]:
        """Extract medical specialty from query."""
        for keyword, specialty in self.SPECIALTY_MAPPINGS.items():
            if keyword in query:
                return specialty
        return None
    
    def _extract_treatment(self, query: str) -> Optional[str]:
        """Extract specific treatment from query."""
        for keyword, treatment in self.TREATMENT_MAPPINGS.items():
            if keyword in query:
                return treatment
        return None
    
    def _extract_location(self, query: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract location information from query.
        
        Returns:
            Tuple of (city, department, near_location)
        """
        city = None
        department = None
        near_location = None
        
        # Check for "near" or "cerca de" patterns
        near_patterns = [
            r'cerca de\s+(\w+)',
            r'near\s+(\w+)',
            r'cercano a\s+(\w+)',
            r'próximo a\s+(\w+)',
            r'proximo a\s+(\w+)',
        ]
        
        for pattern in near_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                location_name = match.group(1).lower()
                if location_name in self.COLOMBIAN_LOCATIONS:
                    near_location = self.COLOMBIAN_LOCATIONS[location_name][0]
                    department = self.COLOMBIAN_LOCATIONS[location_name][1]
                else:
                    near_location = match.group(1).title()
        
        # Check for "en" (in) patterns
        en_patterns = [
            r'\ben\s+(\w+(?:\s+\w+)?)',
            r'\bin\s+(\w+(?:\s+\w+)?)',
        ]
        
        for pattern in en_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                location_name = match.group(1).lower().strip()
                if location_name in self.COLOMBIAN_LOCATIONS:
                    city = self.COLOMBIAN_LOCATIONS[location_name][0]
                    department = self.COLOMBIAN_LOCATIONS[location_name][1]
                    break
        
        # Direct location mention
        if not city and not near_location:
            for location_key, (loc_city, loc_dept) in self.COLOMBIAN_LOCATIONS.items():
                if location_key in query:
                    city = loc_city
                    department = loc_dept
                    break
        
        return city, department, near_location
    
    def _extract_institution_type(self, query: str) -> Optional[str]:
        """Extract institution type from query."""
        for keyword, inst_type in self.INSTITUTION_TYPE_PATTERNS.items():
            if keyword in query:
                return inst_type.value
        return None
    
    def _extract_keywords(self, query: str, parsed: ParsedQuery) -> List[str]:
        """Extract remaining keywords not captured by other extractors."""
        # Remove already extracted terms
        remaining = query
        
        # Remove common stopwords
        stopwords = [
            "de", "en", "con", "para", "cerca", "near", "que", "el", "la", "los", "las",
            "un", "una", "especializado", "especializada", "specialized", "in", "y", "o",
            "mejor", "mejores", "bueno", "buenos", "recomendado", "recomendados"
        ]
        
        words = remaining.split()
        keywords = [w for w in words if w.lower() not in stopwords and len(w) > 2]
        
        return keywords[:5]  # Limit to 5 keywords


class PromptSearchService:
    """
    Service for searching health institutions using natural language prompts.
    
    This service combines:
    1. Query parsing to extract search parameters
    2. Database search for existing institutions
    3. Optional web scraping for new results
    4. Deduplication to prevent storing duplicates
    
    Usage:
        service = PromptSearchService()
        
        # Simple search (database only)
        results = service.search("Odontología en Soacha")
        
        # Search with scraping enabled
        results = service.search_and_scrape(
            "Clínica dental especializada en implantes cerca de Kennedy"
        )
    """
    
    def __init__(
        self,
        database_service: Optional[DatabaseService] = None,
        scraper: Optional[BaseHealthScraper] = None
    ):
        """
        Initialize the search service.
        
        Args:
            database_service: Database service instance (created if not provided)
            scraper: Web scraper instance (created on demand if not provided)
        """
        self.db = database_service or DatabaseService()
        self._scraper = scraper
        self.parser = QueryParser()
    
    @property
    def scraper(self) -> BaseHealthScraper:
        """Lazy initialization of scraper."""
        if self._scraper is None:
            self._scraper = BaseHealthScraper(headless=True, timeout=30, rate_limit=2.0)
        return self._scraper
    
    def search(
        self,
        query: str,
        limit: int = 20,
        user_id: Optional[str] = None
    ) -> SearchResult:
        """
        Search for institutions using a natural language query.
        
        This method only searches the existing database, it does not
        trigger new scraping. Use `search_and_scrape` for that.
        
        Args:
            query: Natural language search query
            limit: Maximum number of results
            user_id: Optional user identifier for logging
            
        Returns:
            SearchResult with matching institutions
            
        Example:
            >>> service = PromptSearchService()
            >>> result = service.search("Odontología cerca de Soacha")
            >>> for inst in result.institutions:
            ...     print(f"{inst.name} - {inst.city}")
        """
        start_time = time.time()
        
        # Parse the query
        parsed = self.parser.parse(query)
        
        # Search database
        institutions = self._search_database(parsed, limit)
        
        execution_time = time.time() - start_time
        
        # Log the query
        self.db.log_search_query(
            original_query=query,
            specialty=parsed.specialty,
            treatment=parsed.treatment,
            city=parsed.city,
            department=parsed.department,
            location_near=parsed.near_location,
            results_count=len(institutions),
            new_scraped_count=0,
            execution_time=execution_time,
            user_id=user_id
        )
        
        return SearchResult(
            institutions=institutions,
            total_count=len(institutions),
            from_database=len(institutions),
            newly_scraped=0,
            parsed_query=parsed,
            execution_time=execution_time
        )
    
    def search_and_scrape(
        self,
        query: str,
        limit: int = 20,
        min_results: int = 5,
        scrape_if_insufficient: bool = True,
        user_id: Optional[str] = None
    ) -> SearchResult:
        """
        Search for institutions and scrape new ones if results are insufficient.
        
        This method first searches the database. If fewer than `min_results`
        are found and `scrape_if_insufficient` is True, it will trigger
        web scraping to find and store new institutions.
        
        Args:
            query: Natural language search query
            limit: Maximum number of results
            min_results: Minimum results before triggering scraping
            scrape_if_insufficient: Whether to scrape if results are low
            user_id: Optional user identifier for logging
            
        Returns:
            SearchResult with matching institutions (from DB and newly scraped)
        """
        start_time = time.time()
        
        # Parse the query
        parsed = self.parser.parse(query)
        
        # Search database first
        db_institutions = self._search_database(parsed, limit)
        newly_scraped = 0
        
        # Scrape if insufficient results
        if scrape_if_insufficient and len(db_institutions) < min_results:
            logger.info(f"Only {len(db_institutions)} results found, triggering scraping...")
            newly_scraped = self._scrape_and_save(parsed, limit - len(db_institutions))
            
            # Re-search to include new results
            db_institutions = self._search_database(parsed, limit)
        
        execution_time = time.time() - start_time
        
        # Log the query
        self.db.log_search_query(
            original_query=query,
            specialty=parsed.specialty,
            treatment=parsed.treatment,
            city=parsed.city,
            department=parsed.department,
            location_near=parsed.near_location,
            results_count=len(db_institutions),
            new_scraped_count=newly_scraped,
            execution_time=execution_time,
            user_id=user_id
        )
        
        return SearchResult(
            institutions=db_institutions,
            total_count=len(db_institutions),
            from_database=len(db_institutions) - newly_scraped,
            newly_scraped=newly_scraped,
            parsed_query=parsed,
            execution_time=execution_time
        )
    
    def _search_database(self, parsed: ParsedQuery, limit: int) -> List[InstitutionDB]:
        """Search the database using parsed query parameters."""
        # Use near_location as city if city is not set
        search_city = parsed.city or parsed.near_location
        
        return self.db.search_institutions(
            specialty=parsed.specialty,
            treatment=parsed.treatment,
            city=search_city,
            department=parsed.department,
            institution_type=parsed.institution_type,
            keyword=parsed.keywords[0] if parsed.keywords else None,
            limit=limit
        )
    
    def _scrape_and_save(self, parsed: ParsedQuery, max_new: int) -> int:
        """
        Scrape new institutions based on parsed query and save to database.
        
        Returns:
            Number of new institutions saved
        """
        # Build search query for scraper
        search_terms = []
        
        if parsed.specialty:
            search_terms.append(parsed.specialty)
        if parsed.treatment:
            search_terms.append(parsed.treatment)
        
        location = parsed.city or parsed.near_location or parsed.department
        if location:
            search_terms.append(location)
        
        if not search_terms:
            search_terms = parsed.keywords[:2] if parsed.keywords else []
        
        if not search_terms:
            logger.warning("No search terms to scrape")
            return 0
        
        search_query = " ".join(search_terms) + " Colombia"
        
        try:
            # Scrape institution
            result = self.scraper.scrape_institution(search_query)
            
            if result.success and result.institution:
                # Enrich with parsed data
                if parsed.specialty and not result.institution.specialties:
                    result.institution.specialties = [parsed.specialty]
                if parsed.city:
                    result.institution.city = parsed.city
                if parsed.department:
                    result.institution.department = parsed.department
                
                # Save to database (with deduplication)
                db_inst, is_new = self.db.save_institution(result.institution)
                
                if is_new:
                    logger.info(f"Saved new institution: {result.institution.name}")
                    return 1
                else:
                    logger.info(f"Institution already exists: {result.institution.name}")
                    return 0
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
        
        return 0
    
    def cleanup(self):
        """Clean up resources."""
        if self._scraper:
            self._scraper.cleanup()


# Convenience function for quick searches
def search_health_institutions(query: str, limit: int = 20) -> SearchResult:
    """
    Quick function to search health institutions.
    
    Args:
        query: Natural language search query
        limit: Maximum results
        
    Returns:
        SearchResult with matching institutions
        
    Example:
        >>> results = search_health_institutions("Dentista en Soacha")
        >>> for inst in results.institutions:
        ...     print(inst.name)
    """
    service = PromptSearchService()
    return service.search(query, limit)
