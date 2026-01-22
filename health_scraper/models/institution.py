"""
Health Institution Models

This module defines Pydantic models for representing health institutions,
their contacts, social media profiles, and related data structures.

These models are used throughout the scraper for:
- Validating scraped data
- API request/response serialization
- Database storage conversion
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from enum import Enum


class InstitutionType(str, Enum):
    """
    Classification of health institution types in Colombia.
    
    This enum covers the main types of healthcare providers and insurers
    in the Colombian health system (Sistema General de Seguridad Social en Salud).
    """
    # Main Colombian Health System Classifications
    IPS = "IPS"  # Institución Prestadora de Servicios de Salud (Healthcare Provider)
    EPS = "EPS"  # Entidad Promotora de Salud (Health Insurance Entity)
    ESE = "ESE"  # Empresa Social del Estado (State Social Enterprise - Public Hospitals)
    
    # Clinical Facilities
    HOSPITAL = "HOSPITAL"  # Hospital (General or Specialized)
    CLINICA = "CLINICA"  # Private Clinic
    CENTRO_MEDICO = "CENTRO_MEDICO"  # Medical Center
    CONSULTORIO = "CONSULTORIO"  # Medical Office/Practice
    POLICLINICO = "POLICLINICO"  # Polyclinic (Multiple Specialties)
    
    # Specialized Health Centers
    CENTRO_ODONTOLOGICO = "CENTRO_ODONTOLOGICO"  # Dental Center
    CLINICA_DENTAL = "CLINICA_DENTAL"  # Dental Clinic
    CENTRO_OFTALMOLOGICO = "CENTRO_OFTALMOLOGICO"  # Eye Care Center
    CENTRO_DERMATOLOGICO = "CENTRO_DERMATOLOGICO"  # Dermatology Center
    CENTRO_CARDIOLOGICO = "CENTRO_CARDIOLOGICO"  # Cardiology Center
    CENTRO_ONCOLOGICO = "CENTRO_ONCOLOGICO"  # Oncology Center
    CENTRO_PEDIATRICO = "CENTRO_PEDIATRICO"  # Pediatric Center
    CENTRO_GINECOLOGICO = "CENTRO_GINECOLOGICO"  # Gynecology Center
    CENTRO_TRAUMATOLOGICO = "CENTRO_TRAUMATOLOGICO"  # Trauma/Orthopedic Center
    CENTRO_NEUROLOGICO = "CENTRO_NEUROLOGICO"  # Neurology Center
    
    # Diagnostic & Support Services
    LABORATORIO_CLINICO = "LABORATORIO_CLINICO"  # Clinical Laboratory
    CENTRO_DIAGNOSTICO = "CENTRO_DIAGNOSTICO"  # Diagnostic Imaging Center
    CENTRO_RADIOLOGIA = "CENTRO_RADIOLOGIA"  # Radiology Center
    BANCO_SANGRE = "BANCO_SANGRE"  # Blood Bank
    
    # Mental Health
    CLINICA_PSIQUIATRICA = "CLINICA_PSIQUIATRICA"  # Psychiatric Clinic
    CENTRO_SALUD_MENTAL = "CENTRO_SALUD_MENTAL"  # Mental Health Center
    
    # Rehabilitation & Therapy
    CENTRO_REHABILITACION = "CENTRO_REHABILITACION"  # Rehabilitation Center
    CENTRO_FISIOTERAPIA = "CENTRO_FISIOTERAPIA"  # Physiotherapy Center
    
    # Emergency & Urgent Care
    CENTRO_URGENCIAS = "CENTRO_URGENCIAS"  # Emergency Care Center
    CLINICA_DIA = "CLINICA_DIA"  # Day Clinic (Outpatient Surgery)
    
    # Aesthetic & Elective
    CLINICA_ESTETICA = "CLINICA_ESTETICA"  # Aesthetic/Cosmetic Clinic
    SPA_MEDICO = "SPA_MEDICO"  # Medical Spa
    
    # Home & Community Care
    ATENCION_DOMICILIARIA = "ATENCION_DOMICILIARIA"  # Home Care Services
    CENTRO_SALUD = "CENTRO_SALUD"  # Community Health Center (Primary Care)
    
    # Pharmacy & Dispensary
    FARMACIA = "FARMACIA"  # Pharmacy
    DROGUERIA = "DROGUERIA"  # Drugstore
    
    # Other
    FUNDACION = "FUNDACION"  # Health Foundation
    ONG_SALUD = "ONG_SALUD"  # Health NGO
    OTRO = "OTRO"  # Other


class SpecialtyType(str, Enum):
    """
    Medical specialties offered by health institutions.
    
    Used for filtering and searching specific types of medical services.
    """
    # Dental Specialties
    ODONTOLOGIA_GENERAL = "odontologia_general"  # General Dentistry
    ORTODONCIA = "ortodoncia"  # Orthodontics
    ENDODONCIA = "endodoncia"  # Endodontics (Root Canal)
    PERIODONCIA = "periodoncia"  # Periodontics (Gums)
    IMPLANTOLOGIA = "implantologia"  # Dental Implants
    CIRUGIA_ORAL = "cirugia_oral"  # Oral Surgery
    ODONTOPEDIATRIA = "odontopediatria"  # Pediatric Dentistry
    ESTETICA_DENTAL = "estetica_dental"  # Cosmetic Dentistry
    PROTESIS_DENTAL = "protesis_dental"  # Dental Prosthetics
    
    # General Medical Specialties
    MEDICINA_GENERAL = "medicina_general"  # General Medicine
    MEDICINA_INTERNA = "medicina_interna"  # Internal Medicine
    MEDICINA_FAMILIAR = "medicina_familiar"  # Family Medicine
    PEDIATRIA = "pediatria"  # Pediatrics
    GERIATRIA = "geriatria"  # Geriatrics
    
    # Surgical Specialties
    CIRUGIA_GENERAL = "cirugia_general"  # General Surgery
    CIRUGIA_PLASTICA = "cirugia_plastica"  # Plastic Surgery
    CIRUGIA_CARDIOVASCULAR = "cirugia_cardiovascular"  # Cardiovascular Surgery
    NEUROCIRUGIA = "neurocirugia"  # Neurosurgery
    
    # Organ System Specialties
    CARDIOLOGIA = "cardiologia"  # Cardiology
    NEUROLOGIA = "neurologia"  # Neurology
    GASTROENTEROLOGIA = "gastroenterologia"  # Gastroenterology
    NEFROLOGIA = "nefrologia"  # Nephrology
    NEUMOLOGIA = "neumologia"  # Pulmonology
    DERMATOLOGIA = "dermatologia"  # Dermatology
    OFTALMOLOGIA = "oftalmologia"  # Ophthalmology
    OTORRINOLARINGOLOGIA = "otorrinolaringologia"  # ENT
    UROLOGIA = "urologia"  # Urology
    
    # Women's Health
    GINECOLOGIA = "ginecologia"  # Gynecology
    OBSTETRICIA = "obstetricia"  # Obstetrics
    
    # Musculoskeletal
    TRAUMATOLOGIA = "traumatologia"  # Traumatology
    ORTOPEDIA = "ortopedia"  # Orthopedics
    REUMATOLOGIA = "reumatologia"  # Rheumatology
    FISIOTERAPIA = "fisioterapia"  # Physiotherapy
    
    # Mental Health
    PSIQUIATRIA = "psiquiatria"  # Psychiatry
    PSICOLOGIA = "psicologia"  # Psychology
    
    # Cancer Care
    ONCOLOGIA = "oncologia"  # Oncology
    RADIOTERAPIA = "radioterapia"  # Radiotherapy
    
    # Other Specialties
    ANESTESIOLOGIA = "anestesiologia"  # Anesthesiology
    RADIOLOGIA = "radiologia"  # Radiology
    PATOLOGIA = "patologia"  # Pathology
    MEDICINA_LABORAL = "medicina_laboral"  # Occupational Medicine
    MEDICINA_DEPORTIVA = "medicina_deportiva"  # Sports Medicine
    NUTRICION = "nutricion"  # Nutrition
    ALERGOLOGIA = "alergologia"  # Allergology
    ENDOCRINOLOGIA = "endocrinologia"  # Endocrinology
    HEMATOLOGIA = "hematologia"  # Hematology
    INFECTOLOGIA = "infectologia"  # Infectious Diseases


class ContactType(str, Enum):
    GENERAL = "general"
    COMMERCIAL = "commercial"
    IT = "it"
    ADMINISTRATIVE = "administrative"
    MEDICAL_DIRECTOR = "medical_director"

class SocialMediaPlatform(str, Enum):
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"

class Contact(BaseModel):
    name: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    contact_type: ContactType = ContactType.GENERAL
    
class SocialMediaProfile(BaseModel):
    platform: SocialMediaPlatform
    url: HttpUrl
    username: Optional[str] = None
    follower_count: Optional[int] = None
    verified: Optional[bool] = None

class ITTeamInfo(BaseModel):
    has_it_team: bool = False
    it_contacts: List[Contact] = []
    it_department_name: Optional[str] = None
    technology_stack: List[str] = []
    current_projects: List[str] = []

class HealthInstitution(BaseModel):
    """
    Main model representing a health institution.
    
    This model captures comprehensive information about a healthcare provider
    including contact details, services, specialties, and metadata.
    
    Example:
        institution = HealthInstitution(
            name="Clínica Dental Sonrisa",
            institution_type=InstitutionType.CLINICA_DENTAL,
            specialty_type=SpecialtyType.ORTODONCIA,
            city="Soacha",
            department="Cundinamarca"
        )
    """
    # Basic Information
    name: str = Field(..., description="Official name of the institution")
    institution_type: InstitutionType = Field(
        default=InstitutionType.IPS,
        description="Type/classification of the health institution"
    )
    specialty_type: Optional[SpecialtyType] = Field(
        default=None,
        description="Primary medical specialty if specialized"
    )
    registration_number: Optional[str] = Field(
        default=None,
        description="Official registration number with health authorities"
    )
    nit: Optional[str] = Field(
        default=None,
        description="Colombian Tax ID (NIT)"
    )
    
    # Contact Information
    address: Optional[str] = None
    city: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[HttpUrl] = None
    # Affiliation & Legal
    affiliation: Optional[str] = None
    legal_representative: Optional[str] = None
    medical_director: Optional[str] = None
    
    # Contacts
    contacts: List[Contact] = []
    key_personnel: List[Contact] = []
    
    # IT Information
    it_info: ITTeamInfo = ITTeamInfo()
    
    # Social Media
    social_media: List[SocialMediaProfile] = []
    
    # Services & Specialties
    services: List[str] = []
    specialties: List[str] = []
    
    # Additional Information
    certification_level: Optional[str] = None
    accreditations: List[str] = []
    bed_capacity: Optional[int] = None
    employee_count: Optional[int] = None
    
    # Metadata
    scraped_at: datetime = datetime.now()
    source_url: Optional[HttpUrl] = None
    data_quality_score: Optional[float] = None
    
class ScrapeResult(BaseModel):
    success: bool
    institution: Optional[HealthInstitution] = None
    error_message: Optional[str] = None
    scraped_urls: List[str] = []
    processing_time: Optional[float] = None

class BulkScrapeRequest(BaseModel):
    institution_names: List[str]
    include_social_media: bool = True
    include_it_details: bool = True
    max_concurrent: int = 5

class BulkScrapeResponse(BaseModel):
    total_requested: int
    successful_scrapes: int
    failed_scrapes: int
    results: List[ScrapeResult]
    processing_time: float