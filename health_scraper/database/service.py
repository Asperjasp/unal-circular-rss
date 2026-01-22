"""
Database Service for Health Institutions Scraper

This service provides CRUD operations for the health institutions database
with built-in deduplication to prevent storing the same institution twice.

Key Features:
- Automatic deduplication based on institution name, NIT, and address
- Upsert functionality (update if exists, insert if new)
- Search with filters (city, specialty, treatment)
- Statistics and reporting
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import create_engine, and_, or_, func, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .models import (
    Base, InstitutionDB, ContactDB, SocialMediaDB, 
    SearchQueryDB, ScrapingJobDB
)
from ..models.institution import (
    HealthInstitution, Contact, SocialMediaProfile, 
    ScrapeResult, InstitutionType, ContactType
)
from ..config import config

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Service class for database operations.
    
    This class handles all database interactions with built-in deduplication
    to ensure the same clinic/institution is not added twice.
    
    Usage:
        db = DatabaseService()
        
        # Save a scraped institution (will not duplicate)
        result = db.save_institution(health_institution)
        
        # Search for institutions
        results = db.search_institutions(specialty="odontology", city="Bogotá")
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database service.
        
        Args:
            database_url: SQLAlchemy database URL. Defaults to config value.
                         Examples:
                         - sqlite:///health_institutions.db
                         - postgresql://user:pass@localhost/health_db
        """
        self.database_url = database_url or config.database_url
        self.engine = create_engine(self.database_url, echo=config.is_development)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        logger.info(f"Database initialized: {self.database_url}")
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    # =========================================================================
    # INSTITUTION CRUD OPERATIONS
    # =========================================================================
    
    def save_institution(
        self, 
        institution: HealthInstitution,
        update_if_exists: bool = True
    ) -> Tuple[InstitutionDB, bool]:
        """
        Save an institution to the database with deduplication.
        
        This method will NOT create duplicates. If an institution with the same
        unique_hash (based on name + NIT + address) already exists:
        - If update_if_exists=True: Updates the existing record
        - If update_if_exists=False: Returns the existing record without changes
        
        Args:
            institution: HealthInstitution model from scraping
            update_if_exists: Whether to update existing records
            
        Returns:
            Tuple of (InstitutionDB object, is_new: bool)
            - is_new=True if a new record was created
            - is_new=False if an existing record was found
        """
        session = self.get_session()
        try:
            # Compute unique hash for deduplication
            unique_hash = InstitutionDB.compute_hash(
                name=institution.name,
                nit=institution.nit,
                address=institution.address
            )
            
            # Check if institution already exists
            existing = session.query(InstitutionDB).filter(
                InstitutionDB.unique_hash == unique_hash
            ).first()
            
            if existing:
                logger.info(f"Institution already exists: {institution.name} (ID: {existing.id})")
                
                if update_if_exists:
                    # Update existing record with new data
                    self._update_institution_fields(existing, institution)
                    existing.updated_at = datetime.utcnow()
                    session.commit()
                    session.refresh(existing)
                    logger.info(f"Updated existing institution: {institution.name}")
                
                return existing, False
            
            # Create new institution record
            db_institution = InstitutionDB(
                name=institution.name,
                unique_hash=unique_hash,
                institution_type=institution.institution_type.value,
                registration_number=institution.registration_number,
                nit=institution.nit,
                address=institution.address,
                city=institution.city,
                department=institution.department,
                phone=institution.phone,
                email=institution.email,
                website=str(institution.website) if institution.website else None,
                affiliation=institution.affiliation,
                legal_representative=institution.legal_representative,
                medical_director=institution.medical_director,
                services=institution.services,
                specialties=institution.specialties,
                certification_level=institution.certification_level,
                accreditations=institution.accreditations,
                bed_capacity=institution.bed_capacity,
                employee_count=institution.employee_count,
                has_it_team=institution.it_info.has_it_team if institution.it_info else False,
                it_department_name=institution.it_info.it_department_name if institution.it_info else None,
                technology_stack=institution.it_info.technology_stack if institution.it_info else [],
                data_quality_score=institution.data_quality_score,
                source_url=str(institution.source_url) if institution.source_url else None,
                scraped_at=institution.scraped_at
            )
            
            session.add(db_institution)
            session.flush()  # Get the ID
            
            # Add contacts
            for contact in institution.contacts:
                self._add_contact(session, db_institution.id, contact)
            
            # Add social media
            for social in institution.social_media:
                self._add_social_media(session, db_institution.id, social)
            
            session.commit()
            session.refresh(db_institution)
            
            logger.info(f"Created new institution: {institution.name} (ID: {db_institution.id})")
            return db_institution, True
            
        except IntegrityError as e:
            session.rollback()
            logger.warning(f"Integrity error (possible duplicate): {e}")
            # Try to return existing record
            existing = session.query(InstitutionDB).filter(
                InstitutionDB.unique_hash == unique_hash
            ).first()
            return existing, False
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error saving institution: {e}")
            raise
            
        finally:
            session.close()
    
    def _update_institution_fields(self, existing: InstitutionDB, new_data: HealthInstitution):
        """Update institution fields with new data (only non-null values)."""
        if new_data.phone and not existing.phone:
            existing.phone = new_data.phone
        if new_data.email and not existing.email:
            existing.email = new_data.email
        if new_data.website and not existing.website:
            existing.website = str(new_data.website)
        if new_data.address and not existing.address:
            existing.address = new_data.address
        if new_data.city and not existing.city:
            existing.city = new_data.city
        if new_data.services:
            # Merge services lists
            existing_services = set(existing.services or [])
            new_services = set(new_data.services)
            existing.services = list(existing_services | new_services)
        if new_data.specialties:
            existing_specialties = set(existing.specialties or [])
            new_specialties = set(new_data.specialties)
            existing.specialties = list(existing_specialties | new_specialties)
    
    def _add_contact(self, session: Session, institution_id: int, contact: Contact):
        """Add a contact to an institution."""
        try:
            db_contact = ContactDB(
                institution_id=institution_id,
                name=contact.name,
                position=contact.position,
                department=contact.department,
                email=contact.email,
                phone=contact.phone,
                mobile=contact.mobile,
                contact_type=contact.contact_type.value if contact.contact_type else "general"
            )
            session.add(db_contact)
        except IntegrityError:
            session.rollback()
            logger.debug(f"Contact already exists: {contact.email}")
    
    def _add_social_media(self, session: Session, institution_id: int, social: SocialMediaProfile):
        """Add a social media profile to an institution."""
        try:
            db_social = SocialMediaDB(
                institution_id=institution_id,
                platform=social.platform.value if hasattr(social.platform, 'value') else social.platform,
                url=str(social.url),
                username=social.username,
                follower_count=social.follower_count,
                verified=social.verified
            )
            session.add(db_social)
        except IntegrityError:
            session.rollback()
            logger.debug(f"Social media already exists: {social.url}")
    
    def get_institution_by_id(self, institution_id: int) -> Optional[InstitutionDB]:
        """Get an institution by its ID."""
        session = self.get_session()
        try:
            return session.query(InstitutionDB).filter(
                InstitutionDB.id == institution_id
            ).first()
        finally:
            session.close()
    
    def get_institution_by_name(self, name: str) -> Optional[InstitutionDB]:
        """Get an institution by exact name match."""
        session = self.get_session()
        try:
            return session.query(InstitutionDB).filter(
                func.lower(InstitutionDB.name) == func.lower(name)
            ).first()
        finally:
            session.close()
    
    def institution_exists(self, name: str, nit: Optional[str] = None, address: Optional[str] = None) -> bool:
        """
        Check if an institution already exists in the database.
        
        Args:
            name: Institution name
            nit: NIT (optional but recommended)
            address: Address (optional)
            
        Returns:
            True if institution exists, False otherwise
        """
        session = self.get_session()
        try:
            unique_hash = InstitutionDB.compute_hash(name, nit, address)
            exists = session.query(InstitutionDB).filter(
                InstitutionDB.unique_hash == unique_hash
            ).first() is not None
            return exists
        finally:
            session.close()
    
    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================
    
    def search_institutions(
        self,
        specialty: Optional[str] = None,
        treatment: Optional[str] = None,
        city: Optional[str] = None,
        department: Optional[str] = None,
        institution_type: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[InstitutionDB]:
        """
        Search institutions with multiple filters.
        
        Args:
            specialty: Specialty type (e.g., "odontology", "cardiology")
            treatment: Specific treatment (e.g., "implants", "orthodontics")
            city: City name
            department: Department/state name
            institution_type: IPS or EPS
            keyword: General keyword search across name, services, specialties
            limit: Maximum results to return
            offset: Pagination offset
            
        Returns:
            List of matching institutions
        """
        session = self.get_session()
        try:
            query = session.query(InstitutionDB)
            
            # Apply filters
            filters = []
            
            if specialty:
                filters.append(or_(
                    func.lower(InstitutionDB.specialty_type).contains(specialty.lower()),
                    func.lower(InstitutionDB.name).contains(specialty.lower()),
                    # Search in JSON specialties array
                    InstitutionDB.specialties.contains([specialty])
                ))
            
            if treatment:
                filters.append(or_(
                    InstitutionDB.treatments.contains([treatment]),
                    InstitutionDB.services.contains([treatment]),
                    func.lower(InstitutionDB.name).contains(treatment.lower())
                ))
            
            if city:
                filters.append(func.lower(InstitutionDB.city).contains(city.lower()))
            
            if department:
                filters.append(func.lower(InstitutionDB.department).contains(department.lower()))
            
            if institution_type:
                filters.append(InstitutionDB.institution_type == institution_type.upper())
            
            if keyword:
                keyword_lower = keyword.lower()
                filters.append(or_(
                    func.lower(InstitutionDB.name).contains(keyword_lower),
                    func.lower(InstitutionDB.address).contains(keyword_lower),
                    InstitutionDB.services.contains([keyword]),
                    InstitutionDB.specialties.contains([keyword])
                ))
            
            if filters:
                query = query.filter(and_(*filters))
            
            # Order by data quality and recency
            query = query.order_by(
                InstitutionDB.data_quality_score.desc().nullsfirst(),
                InstitutionDB.updated_at.desc()
            )
            
            return query.offset(offset).limit(limit).all()
            
        finally:
            session.close()
    
    def search_nearby(
        self,
        city: str,
        specialty: Optional[str] = None,
        radius_km: float = 10.0,
        limit: int = 20
    ) -> List[InstitutionDB]:
        """
        Search for institutions near a specific city.
        
        Note: For accurate distance-based search, institutions need latitude/longitude.
        This method falls back to city/department matching if coordinates are not available.
        
        Args:
            city: Target city name (e.g., "Soacha")
            specialty: Optional specialty filter
            radius_km: Search radius in kilometers (requires coordinates)
            limit: Maximum results
            
        Returns:
            List of nearby institutions
        """
        session = self.get_session()
        try:
            # For now, search by city and nearby cities
            # TODO: Implement proper geo-distance search with PostGIS or similar
            nearby_cities = self._get_nearby_cities(city)
            
            query = session.query(InstitutionDB).filter(
                or_(
                    func.lower(InstitutionDB.city).in_([c.lower() for c in nearby_cities]),
                    func.lower(InstitutionDB.address).contains(city.lower())
                )
            )
            
            if specialty:
                query = query.filter(or_(
                    func.lower(InstitutionDB.specialty_type).contains(specialty.lower()),
                    InstitutionDB.specialties.contains([specialty])
                ))
            
            return query.limit(limit).all()
            
        finally:
            session.close()
    
    def _get_nearby_cities(self, city: str) -> List[str]:
        """
        Get list of cities that are geographically close.
        This is a simplified mapping for Colombian cities.
        """
        nearby_map = {
            "soacha": ["soacha", "bogotá", "bosa", "kennedy", "fontibón", "sibaté", "mosquera"],
            "bogotá": ["bogotá", "soacha", "chía", "cota", "funza", "mosquera", "madrid", "la calera"],
            "medellín": ["medellín", "envigado", "itagüí", "bello", "sabaneta", "la estrella"],
            "cali": ["cali", "palmira", "yumbo", "jamundí", "candelaria"],
            # Add more city mappings as needed
        }
        
        city_lower = city.lower()
        return nearby_map.get(city_lower, [city_lower])
    
    # =========================================================================
    # QUERY LOGGING
    # =========================================================================
    
    def log_search_query(
        self,
        original_query: str,
        specialty: Optional[str] = None,
        treatment: Optional[str] = None,
        city: Optional[str] = None,
        department: Optional[str] = None,
        location_near: Optional[str] = None,
        results_count: int = 0,
        new_scraped_count: int = 0,
        execution_time: Optional[float] = None,
        user_id: Optional[str] = None
    ) -> SearchQueryDB:
        """
        Log a search query for analytics.
        
        Args:
            original_query: The original natural language query
            specialty: Parsed specialty
            treatment: Parsed treatment
            city: Parsed city
            department: Parsed department
            location_near: "Near X" location phrase
            results_count: Number of results returned
            new_scraped_count: Number of new institutions scraped
            execution_time: Query execution time in seconds
            user_id: Optional user identifier
            
        Returns:
            The created SearchQueryDB record
        """
        session = self.get_session()
        try:
            query_log = SearchQueryDB(
                original_query=original_query,
                specialty=specialty,
                treatment=treatment,
                location_city=city,
                location_department=department,
                location_near=location_near,
                results_count=results_count,
                new_scraped_count=new_scraped_count,
                execution_time_seconds=execution_time,
                user_id=user_id
            )
            session.add(query_log)
            session.commit()
            session.refresh(query_log)
            return query_log
        finally:
            session.close()
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with various statistics about stored data
        """
        session = self.get_session()
        try:
            total_institutions = session.query(func.count(InstitutionDB.id)).scalar()
            total_contacts = session.query(func.count(ContactDB.id)).scalar()
            total_social_media = session.query(func.count(SocialMediaDB.id)).scalar()
            total_queries = session.query(func.count(SearchQueryDB.id)).scalar()
            
            # Count by type
            ips_count = session.query(func.count(InstitutionDB.id)).filter(
                InstitutionDB.institution_type == "IPS"
            ).scalar()
            eps_count = session.query(func.count(InstitutionDB.id)).filter(
                InstitutionDB.institution_type == "EPS"
            ).scalar()
            
            # Count by city (top 10)
            city_counts = session.query(
                InstitutionDB.city,
                func.count(InstitutionDB.id)
            ).group_by(InstitutionDB.city).order_by(
                func.count(InstitutionDB.id).desc()
            ).limit(10).all()
            
            # Count by specialty (top 10)
            specialty_counts = session.query(
                InstitutionDB.specialty_type,
                func.count(InstitutionDB.id)
            ).filter(
                InstitutionDB.specialty_type.isnot(None)
            ).group_by(InstitutionDB.specialty_type).order_by(
                func.count(InstitutionDB.id).desc()
            ).limit(10).all()
            
            return {
                "total_institutions": total_institutions,
                "total_contacts": total_contacts,
                "total_social_media_profiles": total_social_media,
                "total_search_queries": total_queries,
                "institutions_by_type": {
                    "IPS": ips_count,
                    "EPS": eps_count
                },
                "top_cities": {city: count for city, count in city_counts if city},
                "top_specialties": {spec: count for spec, count in specialty_counts if spec}
            }
            
        finally:
            session.close()
    
    def get_all_institutions(self, limit: int = 100, offset: int = 0) -> List[InstitutionDB]:
        """Get all institutions with pagination."""
        session = self.get_session()
        try:
            return session.query(InstitutionDB).order_by(
                InstitutionDB.updated_at.desc()
            ).offset(offset).limit(limit).all()
        finally:
            session.close()
    
    def delete_institution(self, institution_id: int) -> bool:
        """Delete an institution by ID."""
        session = self.get_session()
        try:
            institution = session.query(InstitutionDB).filter(
                InstitutionDB.id == institution_id
            ).first()
            if institution:
                session.delete(institution)
                session.commit()
                return True
            return False
        finally:
            session.close()
