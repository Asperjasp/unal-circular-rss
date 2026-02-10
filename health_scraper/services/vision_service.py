"""
Vision Extraction Service for Health Institutions

This service uses Google's Gemini Vision model to extract structured data
from images of health institution documents, signs, and certificates.

Workflow:
1. Receive image (upload or bytes)
2. Send to Gemini Pro Vision for analysis
3. Determine if document is health-related
4. Extract structured information (name, NIT, address, etc.)
5. Check for duplicates in database
6. Save new records or return existing

Key Features:
- Multimodal AI analysis (understands context, not just OCR)
- Automatic health sector classification
- Structured JSON output matching InstitutionDB schema
- Built-in duplicate detection
"""

import os
import io
import json
import base64
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from google import genai
from google.genai import types
from PIL import Image

from ..config import config
from ..database.service import DatabaseService
from ..models.institution import (
    HealthInstitution, InstitutionType, SpecialtyType,
    Contact, ContactType
)

logger = logging.getLogger(__name__)


class ExtractionResult(BaseModel):
    """Result from vision extraction"""
    success: bool
    is_health_related: bool
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_data: Optional[Dict[str, Any]] = None
    institution: Optional[HealthInstitution] = None
    is_duplicate: bool = False
    existing_id: Optional[int] = None
    message: str = ""
    raw_response: Optional[str] = None


class DocumentType(str, Enum):
    """Types of health documents that can be processed"""
    ISP_CERTIFICATE = "isp_certificate"
    CLINIC_SIGN = "clinic_sign"
    REGISTRATION_DOCUMENT = "registration_document"
    BUSINESS_CARD = "business_card"
    LETTERHEAD = "letterhead"
    PRESCRIPTION = "prescription"
    INVOICE = "invoice"
    UNKNOWN = "unknown"


class VisionExtractorService:
    """
    Service for extracting health institution data from images using Gemini Vision.
    
    Usage:
        extractor = VisionExtractorService()
        
        # Extract from file path
        result = await extractor.extract_from_image("/path/to/image.jpg")
        
        # Extract from bytes
        result = await extractor.extract_from_bytes(image_bytes)
        
        if result.success and result.is_health_related:
            print(f"Found: {result.extracted_data['name']}")
            if not result.is_duplicate:
                # New institution saved to database
                print(f"Saved with ID: {result.institution.id}")
    """
    
    # Prompt for health document analysis
    ANALYSIS_PROMPT = """Analyze this image carefully.

TASK 1 - HEALTH SECTOR CHECK:
Determine if this image shows a document, sign, certificate, or any material related to the HEALTH SECTOR.
Health sector includes: clinics, hospitals, dental offices, laboratories, pharmacies, medical centers, 
EPS (health insurance), IPS (healthcare providers), health certifications, medical prescriptions, 
ISP (Instituto de Salud Publica) documents, INVIMA certificates, or any health-related business.

TASK 2 - DATA EXTRACTION (only if health-related):
If this IS health-related, extract ALL visible information into structured JSON.

Respond ONLY with valid JSON in this exact format:
{
    "is_health_related": true/false,
    "confidence": 0.0-1.0,
    "document_type": "isp_certificate|clinic_sign|registration_document|business_card|letterhead|prescription|invoice|unknown",
    "reasoning": "Brief explanation of why this is/isn't health related",
    "extracted_data": {
        "name": "Full institution/clinic name",
        "institution_type": "IPS|EPS|HOSPITAL|CLINICA|CENTRO_MEDICO|LABORATORIO_CLINICO|FARMACIA|CENTRO_ODONTOLOGICO|etc",
        "nit": "Colombian tax ID if visible (format: XXX.XXX.XXX-X)",
        "registration_number": "Any official registration number",
        "address": "Full address",
        "city": "City name",
        "department": "Department/State",
        "phone": "Phone number(s)",
        "email": "Email address",
        "website": "Website URL",
        "legal_representative": "Legal representative name",
        "medical_director": "Medical director name",
        "services": ["List", "of", "services", "offered"],
        "specialties": ["List", "of", "medical", "specialties"],
        "certifications": ["Any", "certifications", "mentioned"],
        "additional_info": "Any other relevant information not captured above"
    }
}

IMPORTANT RULES:
1. If NOT health-related, set "is_health_related": false and "extracted_data": null
2. For missing fields, use null (not empty strings)
3. Clean up formatting (e.g., phone numbers should be digits only, NITs formatted properly)
4. If text is partially visible, include what you can read with "[partial]" note
5. Respond ONLY with JSON, no other text"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Vision Extractor Service.
        
        Args:
            api_key: Google AI Studio API key. If not provided, reads from 
                    GOOGLE_AI_STUDIO environment variable.
        """
        self.api_key = api_key or os.getenv("GOOGLE_AI_STUDIO")
        
        if not self.api_key:
            raise ValueError(
                "Google AI Studio API key is required. "
                "Set GOOGLE_AI_STUDIO in .env or pass api_key parameter."
            )
        
        # Configure Gemini client (new google-genai API)
        self.client = genai.Client(api_key=self.api_key)
        
        # Model name for vision tasks
        self.model_name = "gemini-2.0-flash"
        
        # Database service for duplicate checking and saving
        self.db_service = DatabaseService()
        
        logger.info(f"VisionExtractorService initialized with {self.model_name}")
    
    async def extract_from_image(
        self, 
        image_path: Union[str, Path],
        save_to_database: bool = True
    ) -> ExtractionResult:
        """
        Extract health institution data from an image file.
        
        Args:
            image_path: Path to the image file
            save_to_database: Whether to save extracted data to database
            
        Returns:
            ExtractionResult with extracted data and status
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            return ExtractionResult(
                success=False,
                is_health_related=False,
                confidence=0.0,
                message=f"Image file not found: {image_path}"
            )
        
        try:
            # Read image
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            return await self.extract_from_bytes(
                image_bytes, 
                save_to_database=save_to_database,
                source_filename=image_path.name
            )
            
        except Exception as e:
            logger.error(f"Error reading image file: {e}")
            return ExtractionResult(
                success=False,
                is_health_related=False,
                confidence=0.0,
                message=f"Error reading image: {str(e)}"
            )
    
    async def extract_from_bytes(
        self,
        image_bytes: bytes,
        save_to_database: bool = True,
        source_filename: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract health institution data from image bytes.
        
        Args:
            image_bytes: Raw image bytes
            save_to_database: Whether to save extracted data to database
            source_filename: Original filename for logging
            
        Returns:
            ExtractionResult with extracted data and status
        """
        try:
            # Prepare image for Gemini
            image = Image.open(io.BytesIO(image_bytes))
            
            logger.info(f"Processing image: {source_filename or 'uploaded'} ({image.size})")
            
            # Convert image to bytes for the new API
            img_buffer = io.BytesIO()
            image.save(img_buffer, format=image.format or 'PNG')
            img_buffer.seek(0)
            
            # Create image part for the new google-genai API
            image_part = types.Part.from_bytes(
                data=img_buffer.read(),
                mime_type=f"image/{(image.format or 'png').lower()}"
            )
            
            # Send to Gemini for analysis using new API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[self.ANALYSIS_PROMPT, image_part]
            )
            
            # Parse response
            raw_text = response.text.strip()
            
            # Clean up response (remove markdown code blocks if present)
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()
            
            # Parse JSON response
            try:
                parsed_data = json.loads(raw_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response as JSON: {e}")
                logger.debug(f"Raw response: {raw_text}")
                return ExtractionResult(
                    success=False,
                    is_health_related=False,
                    confidence=0.0,
                    message=f"Failed to parse AI response: {str(e)}",
                    raw_response=raw_text
                )
            
            # Check if health-related
            is_health = parsed_data.get("is_health_related", False)
            confidence = parsed_data.get("confidence", 0.0)
            
            if not is_health:
                return ExtractionResult(
                    success=True,
                    is_health_related=False,
                    confidence=confidence,
                    message=parsed_data.get("reasoning", "Document is not health-related"),
                    raw_response=raw_text
                )
            
            # Extract and validate data
            extracted = parsed_data.get("extracted_data", {})
            
            if not extracted or not extracted.get("name"):
                return ExtractionResult(
                    success=True,
                    is_health_related=True,
                    confidence=confidence,
                    message="Health document detected but could not extract institution name",
                    extracted_data=extracted,
                    raw_response=raw_text
                )
            
            # Check for duplicates
            is_duplicate, existing_id = self._check_duplicate(extracted)
            
            result = ExtractionResult(
                success=True,
                is_health_related=True,
                confidence=confidence,
                extracted_data=extracted,
                is_duplicate=is_duplicate,
                existing_id=existing_id,
                raw_response=raw_text
            )
            
            if is_duplicate:
                result.message = f"Institution already exists in database (ID: {existing_id})"
                logger.info(f"Duplicate found: {extracted.get('name')} -> ID {existing_id}")
            else:
                result.message = "New health institution extracted successfully"
                
                if save_to_database:
                    # Convert to HealthInstitution and save
                    institution = self._create_institution(extracted)
                    saved_inst, is_new = self.db_service.save_institution(institution)
                    result.existing_id = saved_inst.id
                    result.message = f"New institution saved to database (ID: {saved_inst.id})"
                    logger.info(f"Saved new institution: {extracted.get('name')} -> ID {saved_inst.id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing image with Gemini: {e}")
            return ExtractionResult(
                success=False,
                is_health_related=False,
                confidence=0.0,
                message=f"Error processing image: {str(e)}"
            )
    
    def _check_duplicate(self, extracted_data: Dict[str, Any]) -> Tuple[bool, Optional[int]]:
        """
        Check if extracted institution already exists in database.
        
        Returns:
            Tuple of (is_duplicate: bool, existing_id: Optional[int])
        """
        name = extracted_data.get("name")
        nit = extracted_data.get("nit")
        address = extracted_data.get("address")
        
        if not name:
            return False, None
        
        try:
            # Check using database service's duplicate detection
            exists = self.db_service.institution_exists(
                name=name,
                nit=nit,
                address=address
            )
            
            if exists:
                # Get the existing institution ID
                from ..database.models import InstitutionDB
                session = self.db_service.get_session()
                try:
                    unique_hash = InstitutionDB.compute_hash(
                        name=name,
                        nit=nit,
                        address=address
                    )
                    existing = session.query(InstitutionDB).filter(
                        InstitutionDB.unique_hash == unique_hash
                    ).first()
                    
                    if existing:
                        return True, existing.id
                finally:
                    session.close()
            
            return False, None
            
        except Exception as e:
            logger.warning(f"Error checking for duplicates: {e}")
            return False, None
    
    def _create_institution(self, extracted_data: Dict[str, Any]) -> HealthInstitution:
        """
        Convert extracted data to a HealthInstitution model.
        
        Args:
            extracted_data: Dictionary of extracted fields from Gemini
            
        Returns:
            HealthInstitution model ready for database storage
        """
        # Map institution type
        inst_type_str = extracted_data.get("institution_type", "OTRO")
        try:
            inst_type = InstitutionType(inst_type_str)
        except ValueError:
            inst_type = InstitutionType.OTRO
        
        # Clean up extracted data - handle "null" strings and invalid values
        def clean_value(val):
            """Clean up extracted values, handling 'null' strings."""
            if val is None or val == "null" or val == "None" or val == "":
                return None
            return val
        
        # Validate website URL
        website = clean_value(extracted_data.get("website"))
        if website and not website.startswith(('http://', 'https://')):
            # Try to fix common issues
            if '.' in website:
                website = f"https://{website}"
            else:
                website = None
        
        # Create contacts
        contacts = []
        phone = clean_value(extracted_data.get("phone"))
        email = clean_value(extracted_data.get("email"))
        
        if phone:
            contacts.append(Contact(
                phone=phone,
                contact_type=ContactType.GENERAL
            ))
        if email:
            contacts.append(Contact(
                email=email,
                contact_type=ContactType.GENERAL
            ))
        
        # Create the institution model (no Location class - direct fields)
        institution = HealthInstitution(
            name=clean_value(extracted_data.get("name")),
            institution_type=inst_type,
            nit=clean_value(extracted_data.get("nit")),
            registration_number=clean_value(extracted_data.get("registration_number")),
            address=clean_value(extracted_data.get("address")),
            city=clean_value(extracted_data.get("city")),
            department=clean_value(extracted_data.get("department")),
            phone=phone,
            email=email,
            website=website,
            contacts=contacts,
            services=extracted_data.get("services") or [],
            specialties=extracted_data.get("specialties") or [],
            accreditations=extracted_data.get("certifications") or [],
            legal_representative=extracted_data.get("legal_representative"),
            medical_director=extracted_data.get("medical_director"),
            scraped_at=datetime.utcnow()
        )
        
        return institution
    
    async def process_multiple_images(
        self,
        image_paths: List[Union[str, Path]],
        save_to_database: bool = True
    ) -> List[ExtractionResult]:
        """
        Process multiple images and extract health institution data.
        
        Args:
            image_paths: List of paths to image files
            save_to_database: Whether to save extracted data
            
        Returns:
            List of ExtractionResult for each image
        """
        results = []
        
        for path in image_paths:
            result = await self.extract_from_image(path, save_to_database)
            results.append(result)
            logger.info(f"Processed {path}: health={result.is_health_related}, duplicate={result.is_duplicate}")
        
        # Summary logging
        total = len(results)
        health_related = sum(1 for r in results if r.is_health_related)
        new_institutions = sum(1 for r in results if r.is_health_related and not r.is_duplicate)
        duplicates = sum(1 for r in results if r.is_duplicate)
        
        logger.info(
            f"Batch processing complete: {total} images, "
            f"{health_related} health-related, {new_institutions} new, {duplicates} duplicates"
        )
        
        return results
