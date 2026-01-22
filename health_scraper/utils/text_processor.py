import re
from typing import List, Optional, Dict
from urllib.parse import urlparse

class TextProcessor:
    """Utility class for processing and cleaning scraped text data"""
    
    def __init__(self):
        self.phone_patterns = [
            r'\+?57[\s-]?\d{1,4}[\s-]?\d{3}[\s-]?\d{4}',
            r'\(\d{1,4}\)[\s-]?\d{3}[\s-]?\d{4}',
            r'\d{7,10}'
        ]
        
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        self.nit_pattern = r'\b\d{8,10}-?\d\b'
        
        # Colombian department/city patterns
        self.colombian_cities = [
            'bogotá', 'medellín', 'cali', 'barranquilla', 'cartagena',
            'cúcuta', 'bucaramanga', 'pereira', 'ibagué', 'santa marta',
            'manizales', 'neiva', 'villavicencio', 'pasto', 'montería',
            'valledupar', 'armenia', 'popayán', 'sincelejo', 'tunja'
        ]
        
        self.colombian_departments = [
            'antioquia', 'bogotá d.c.', 'valle del cauca', 'atlantico',
            'cundinamarca', 'santander', 'norte de santander', 'tolima',
            'huila', 'magdalena', 'caldas', 'risaralda', 'quindío',
            'nariño', 'córdoba', 'cesar', 'boyacá', 'cauca', 'sucre',
            'meta', 'casanare', 'la guajira', 'chocó', 'putumayo'
        ]
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\-.,@()]+', '', text)
        
        return text
    
    def extract_phones(self, text: str) -> List[str]:
        """Extract Colombian phone numbers from text"""
        phones = []
        
        for pattern in self.phone_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Clean the phone number
                clean_phone = re.sub(r'[^\d+]', '', match)
                if len(clean_phone) >= 7:
                    phones.append(clean_phone)
        
        return list(set(phones))  # Remove duplicates
    
    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        emails = re.findall(self.email_pattern, text, re.IGNORECASE)
        return list(set(emails))  # Remove duplicates
    
    def extract_nit(self, text: str) -> Optional[str]:
        """Extract NIT (Colombian tax ID) from text"""
        nit_match = re.search(self.nit_pattern, text)
        return nit_match.group(0) if nit_match else None
    
    def extract_addresses(self, text: str) -> List[str]:
        """Extract Colombian addresses from text"""
        addresses = []
        
        # Look for address patterns with Colombian cities/departments
        for city in self.colombian_cities:
            city_pattern = rf'[\w\s,.-]*{re.escape(city)}[\w\s,.-]*'
            matches = re.findall(city_pattern, text, re.IGNORECASE)
            for match in matches:
                clean_address = self.clean_text(match)
                if len(clean_address) > 10:  # Filter out too short matches
                    addresses.append(clean_address)
        
        return addresses
    
    def identify_person_names(self, text: str) -> List[str]:
        """Identify potential person names in text"""
        names = []
        
        # Look for common title patterns
        title_patterns = [
            r'Dr\.\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Dra\.\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Director:\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Gerente:\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Coordinador:\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+[-–]\s*(Director|Gerente|Coordinador)'
        ]
        
        for pattern in title_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    names.extend([m for m in match if len(m) > 3])
                else:
                    names.append(match)
        
        return list(set(names))
    
    def extract_specialties(self, text: str) -> List[str]:
        """Extract medical specialties from text"""
        specialties_keywords = [
            'cardiología', 'neurología', 'pediatría', 'ginecología', 'urología',
            'oftalmología', 'dermatología', 'psiquiatría', 'ortopedia',
            'anestesiología', 'radiología', 'patología', 'medicina interna',
            'cirugía general', 'medicina familiar', 'emergencias', 'cuidados intensivos',
            'oncología', 'endocrinología', 'neumología', 'gastroenterología',
            'reumatología', 'infectología', 'nefrología', 'hematología'
        ]
        
        found_specialties = []
        text_lower = text.lower()
        
        for specialty in specialties_keywords:
            if specialty in text_lower:
                found_specialties.append(specialty.title())
        
        return found_specialties
    
    def extract_services(self, text: str) -> List[str]:
        """Extract medical services from text"""
        services_keywords = [
            'consulta externa', 'hospitalización', 'cirugía', 'laboratorio clínico',
            'imagenología', 'radiología', 'ecografía', 'tomografía', 'resonancia magnética',
            'urgencias', 'cuidados intensivos', 'rehabilitación', 'fisioterapia',
            'farmacia', 'banco de sangre', 'hemodiálisis', 'quimioterapia',
            'endoscopia', 'colonoscopia', 'cateterismo', 'telemedicina',
            'ambulancia', 'medicina domiciliaria', 'vacunación'
        ]
        
        found_services = []
        text_lower = text.lower()
        
        for service in services_keywords:
            if service in text_lower:
                found_services.append(service.title())
        
        return found_services
    
    def is_colombian_domain(self, url: str) -> bool:
        """Check if URL is from a Colombian domain"""
        colombian_domains = ['.co', '.com.co', '.org.co', '.net.co', '.gov.co', '.edu.co']
        
        try:
            domain = urlparse(url).netloc.lower()
            return any(domain.endswith(cd) for cd in colombian_domains)
        except:
            return False
    
    def calculate_data_quality_score(self, institution_data: dict) -> float:
        """Calculate a quality score for scraped data based on completeness"""
        score = 0.0
        max_score = 10.0
        
        # Basic info (2 points)
        if institution_data.get('name'):
            score += 0.5
        if institution_data.get('website'):
            score += 0.5
        if institution_data.get('address'):
            score += 0.5
        if institution_data.get('phone'):
            score += 0.5
        
        # Contact info (2 points)
        contacts = institution_data.get('contacts', [])
        if contacts:
            score += 1.0
            if len(contacts) > 1:
                score += 1.0
        
        # IT info (2 points)
        it_info = institution_data.get('it_info', {})
        if it_info.get('has_it_team'):
            score += 1.0
        if it_info.get('it_contacts'):
            score += 1.0
        
        # Social media (2 points)
        social_media = institution_data.get('social_media', [])
        if social_media:
            score += 1.0
            if len(social_media) > 1:
                score += 1.0
        
        # Services/specialties (2 points)
        if institution_data.get('services'):
            score += 1.0
        if institution_data.get('specialties'):
            score += 1.0
        
        return round(score / max_score, 2)