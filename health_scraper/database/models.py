"""
Database Models for Health Institutions Scraper

This module defines SQLAlchemy ORM models for persistent storage of scraped
health institution data. The design ensures no duplicate entries are created
when the same institution is scraped multiple times.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, 
    ForeignKey, UniqueConstraint, Index, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
import hashlib

Base = declarative_base()


class InstitutionDB(Base):
    """
    Main table for health institution data.
    
    The `unique_hash` field is computed from key identifiable information
    (name, NIT, address) to prevent duplicate entries.
    
    Attributes:
        id: Primary key
        name: Institution name (e.g., "Clínica Dental Sonrisa")
        unique_hash: Hash for deduplication based on name + NIT + address
        institution_type: IPS, EPS, or specialty type
        specialty_type: Optional specialty (odontology, cardiology, etc.)
        registration_number: Official registration number
        nit: Colombian tax ID (NIT)
        address: Physical address
        city: City name
        department: Department/State
        phone: Main phone number
        email: Main email address
        website: Official website URL
        affiliation: Affiliation information
        legal_representative: Legal representative name
        medical_director: Medical director name
        services: JSON list of services offered
        specialties: JSON list of specialties
        certification_level: Certification/accreditation level
        accreditations: JSON list of accreditations
        bed_capacity: Number of beds (for hospitals)
        employee_count: Number of employees
        has_it_team: Whether institution has IT department
        technology_stack: JSON list of technologies used
        data_quality_score: Score indicating data completeness
        source_url: Original URL where data was scraped
        scraped_at: Timestamp of initial scraping
        updated_at: Timestamp of last update
    """
    __tablename__ = "institutions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    unique_hash = Column(String(64), unique=True, nullable=False, index=True)
    
    # Classification
    institution_type = Column(String(50), default="IPS")  # IPS, EPS
    specialty_type = Column(String(100), nullable=True, index=True)  # odontology, ophthalmology, etc.
    
    # Identification
    registration_number = Column(String(50), nullable=True)
    nit = Column(String(20), nullable=True, unique=True)
    
    # Location
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    department = Column(String(100), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Contact
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    
    # Organization
    affiliation = Column(String(255), nullable=True)
    legal_representative = Column(String(255), nullable=True)
    medical_director = Column(String(255), nullable=True)
    
    # Services (stored as JSON)
    services = Column(JSON, default=list)
    specialties = Column(JSON, default=list)
    treatments = Column(JSON, default=list)  # Specific treatments offered
    
    # Certifications
    certification_level = Column(String(100), nullable=True)
    accreditations = Column(JSON, default=list)
    
    # Capacity
    bed_capacity = Column(Integer, nullable=True)
    employee_count = Column(Integer, nullable=True)
    
    # IT Information
    has_it_team = Column(Boolean, default=False)
    it_department_name = Column(String(255), nullable=True)
    technology_stack = Column(JSON, default=list)
    
    # Metadata
    data_quality_score = Column(Float, nullable=True)
    source_url = Column(String(1000), nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contacts = relationship("ContactDB", back_populates="institution", cascade="all, delete-orphan")
    social_media = relationship("SocialMediaDB", back_populates="institution", cascade="all, delete-orphan")
    
    # Indexes for common search patterns
    __table_args__ = (
        Index('idx_city_specialty', 'city', 'specialty_type'),
        Index('idx_department_city', 'department', 'city'),
        Index('idx_specialty_services', 'specialty_type'),
    )
    
    @staticmethod
    def compute_hash(name: str, nit: Optional[str] = None, address: Optional[str] = None) -> str:
        """
        Compute a unique hash for deduplication.
        
        The hash is based on normalized name, NIT (if available), and address.
        This prevents the same institution from being added multiple times.
        
        Args:
            name: Institution name
            nit: Colombian tax ID (optional but preferred for uniqueness)
            address: Physical address (optional)
            
        Returns:
            SHA256 hash string for deduplication
        """
        # Normalize inputs
        normalized_name = name.lower().strip() if name else ""
        normalized_nit = (nit or "").strip().replace("-", "")
        normalized_address = (address or "").lower().strip()
        
        # Create hash input - prioritize NIT if available
        if normalized_nit:
            hash_input = f"{normalized_name}|{normalized_nit}"
        else:
            hash_input = f"{normalized_name}|{normalized_address}"
        
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    
    def __repr__(self):
        return f"<Institution(id={self.id}, name='{self.name}', city='{self.city}')>"


class ContactDB(Base):
    """
    Contact information for institutions.
    
    Stores individual contact persons or departments with their
    contact details and roles within the institution.
    """
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=True)
    position = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    mobile = Column(String(50), nullable=True)
    contact_type = Column(String(50), default="general")  # general, commercial, it, administrative
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    institution = relationship("InstitutionDB", back_populates="contacts")
    
    __table_args__ = (
        UniqueConstraint('institution_id', 'email', name='uq_institution_email'),
    )
    
    def __repr__(self):
        return f"<Contact(id={self.id}, name='{self.name}', email='{self.email}')>"


class SocialMediaDB(Base):
    """
    Social media profiles for institutions.
    
    Stores links to social media presence on various platforms.
    """
    __tablename__ = "social_media"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False)
    
    platform = Column(String(50), nullable=False)  # linkedin, facebook, twitter, instagram, youtube
    url = Column(String(500), nullable=False)
    username = Column(String(255), nullable=True)
    follower_count = Column(Integer, nullable=True)
    verified = Column(Boolean, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    institution = relationship("InstitutionDB", back_populates="social_media")
    
    __table_args__ = (
        UniqueConstraint('institution_id', 'platform', 'url', name='uq_institution_platform_url'),
    )
    
    def __repr__(self):
        return f"<SocialMedia(id={self.id}, platform='{self.platform}', url='{self.url}')>"


class SearchQueryDB(Base):
    """
    Log of search queries for analytics and caching.
    
    Stores search queries made by users, including the parsed
    parameters and results count. Useful for:
    - Understanding user needs
    - Optimizing search patterns
    - Caching frequent queries
    """
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Original query
    original_query = Column(Text, nullable=False)
    
    # Parsed components
    specialty = Column(String(100), nullable=True)  # odontology, cardiology, etc.
    treatment = Column(String(255), nullable=True)  # implants, orthodontics, etc.
    location_city = Column(String(100), nullable=True)
    location_department = Column(String(100), nullable=True)
    location_near = Column(String(255), nullable=True)  # "near Soacha"
    
    # Results
    results_count = Column(Integer, default=0)
    new_scraped_count = Column(Integer, default=0)  # How many new results were scraped
    
    # Metadata
    user_id = Column(String(100), nullable=True)  # Optional user identifier
    queried_at = Column(DateTime, default=datetime.utcnow, index=True)
    execution_time_seconds = Column(Float, nullable=True)
    
    def __repr__(self):
        return f"<SearchQuery(id={self.id}, query='{self.original_query[:50]}...')>"


class ScrapingJobDB(Base):
    """
    Track scraping jobs for batch processing and monitoring.
    """
    __tablename__ = "scraping_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    job_type = Column(String(50), nullable=False)  # single, bulk, search
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    
    # Job details
    target_institutions = Column(JSON, default=list)
    search_query = Column(Text, nullable=True)
    
    # Results
    total_targets = Column(Integer, default=0)
    successful_scrapes = Column(Integer, default=0)
    failed_scrapes = Column(Integer, default=0)
    duplicates_skipped = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ScrapingJob(id={self.id}, type='{self.job_type}', status='{self.status}')>"
