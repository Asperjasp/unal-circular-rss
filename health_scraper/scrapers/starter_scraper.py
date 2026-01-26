"""
Starter Scraper for Colombian Health Institutions
This scraper collects basic information from major health institution databases
"""

import logging
import time
import random
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus, urljoin
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ..models.institution import HealthInstitution, InstitutionType, Location, Contact, ContactType, SocialMediaProfile

logger = logging.getLogger(__name__)

class StarterHealthScraper:
    """Focused scraper for getting starter data on Colombian health institutions"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Known sources for health institutions data
        self.data_sources = [
            {
                'name': 'REPS - Registro Especial de Prestadores de Servicios de Salud',
                'url': 'https://prestadores.minsalud.gov.co/habilitacion/',
                'type': 'government'
            },
            {
                'name': 'Supersalud - EPS Registry',
                'url': 'https://www.supersalud.gov.co/',
                'type': 'regulatory'
            }
        ]
    
    def setup_driver(self):
        """Setup Chrome driver with optimized settings"""
        if self.driver:
            return
            
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            raise
    
    def scrape_sample_institutions(self, limit: int = 50) -> List[HealthInstitution]:
        """Scrape a sample of health institutions for starter data"""
        institutions = []
        
        # Sample IPS/EPS data - this would normally be scraped from real sources
        sample_data = self._get_sample_health_institutions()
        
        for i, data in enumerate(sample_data[:limit]):
            try:
                institution = self._create_institution_from_sample(data)
                if institution:
                    institutions.append(institution)
                    logger.info(f"Collected institution {i+1}: {institution.name}")
                
                # Rate limiting
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logger.error(f"Error processing sample institution {i+1}: {e}")
                continue
        
        return institutions
    
    def search_by_specialty(self, specialty: str, location: str = '') -> List[HealthInstitution]:
        """Search for institutions by medical specialty"""
        institutions = []
        
        # This would integrate with real search APIs
        search_results = self._mock_specialty_search(specialty, location)
        
        for result in search_results:
            try:
                institution = self._create_institution_from_search(result)
                if institution:
                    institutions.append(institution)
            except Exception as e:
                logger.error(f"Error processing search result: {e}")
                continue
        
        return institutions
    
    def scrape_institution_details(self, institution_name: str, website_url: str = None) -> Optional[HealthInstitution]:
        """Scrape detailed information for a specific institution"""
        try:
            if website_url:
                return self._scrape_from_website(institution_name, website_url)
            else:
                return self._search_and_scrape(institution_name)
        except Exception as e:
            logger.error(f"Error scraping {institution_name}: {e}")
            return None
    
    def _get_sample_health_institutions(self) -> List[Dict[str, Any]]:
        """Return sample health institution data for testing"""
        return [
            {
                'name': 'Hospital San Vicente Fundación',
                'type': 'IPS',
                'nit': '890903787-2',
                'city': 'Medellín',
                'department': 'Antioquia',
                'address': 'Calle 64 No. 51D-154',
                'phone': '+57 4 444 5555',
                'email': 'info@sanvicentefundacion.com',
                'website': 'https://sanvicentefundacion.com',
                'services': ['Urgencias', 'Cirugía', 'UCI', 'Cardiología'],
                'it_contact': 'Carlos Sistemas',
                'it_phone': '+57 4 444 5558',
                'it_email': 'sistemas@sanvicentefundacion.com'
            },
            {
                'name': 'Clínica Las Américas',
                'type': 'IPS',
                'nit': '890903123-4',
                'city': 'Medellín',
                'department': 'Antioquia',
                'address': 'Diagonal 75B No. 2A-80/140',
                'phone': '+57 4 342 1010',
                'email': 'contacto@clinicalasamericas.com.co',
                'website': 'https://clinicalasamericas.com.co',
                'services': ['Oncología', 'Cardiología', 'Neurología'],
                'linkedin': 'https://linkedin.com/company/clinica-las-americas'
            },
            {
                'name': 'Hospital Pablo Tobón Uribe',
                'type': 'IPS',
                'nit': '890900833-1',
                'city': 'Medellín',
                'department': 'Antioquia',
                'address': 'Calle 78B No. 69-240',
                'phone': '+57 4 445 9000',
                'email': 'info@hptu.org.co',
                'website': 'https://hptu.org.co',
                'services': ['Urgencias', 'Trasplantes', 'Pediatría'],
                'it_contact': 'Ana López',
                'it_email': 'tic@hptu.org.co'
            },
            {
                'name': 'EPS SURA',
                'type': 'EPS',
                'nit': '800251440-6',
                'city': 'Medellín',
                'department': 'Antioquia',
                'address': 'Carrera 48 No. 26-85',
                'phone': '+57 4 444 7000',
                'email': 'eps@sura.com.co',
                'website': 'https://www.epssura.com',
                'services': ['Plan Básico', 'Plan Complementario'],
                'linkedin': 'https://linkedin.com/company/eps-sura'
            },
            {
                'name': 'Compensar EPS',
                'type': 'EPS',
                'nit': '860002503-4',
                'city': 'Bogotá',
                'department': 'Cundinamarca',
                'address': 'Av. 68 No. 49A-47',
                'phone': '+57 1 489 8000',
                'email': 'servicioalcliente@compensar.com',
                'website': 'https://www.compensar.com',
                'services': ['POS', 'No POS', 'Promoción y Prevención']
            },
            # Adding dental/orthodontic specific institutions
            {
                'name': 'Centro Dental Especializado Soacha',
                'type': 'IPS',
                'nit': '900123456-7',
                'city': 'Soacha',
                'department': 'Cundinamarca',
                'address': 'Carrera 7 No. 13-45, Centro',
                'phone': '+57 1 456 7890',
                'email': 'info@dentalsoacha.com',
                'website': 'https://dentalsoacha.com',
                'services': ['Ortodoncia', 'Implantes Dentales', 'Endodoncia', 'Odontología General'],
                'it_contact': 'Laura Sistemas',
                'it_email': 'sistemas@dentalsoacha.com',
                'linkedin': 'https://linkedin.com/company/dental-soacha'
            },
            {
                'name': 'Clínica Odontológica Ortodent Bogotá',
                'type': 'IPS',
                'nit': '890456789-0',
                'city': 'Bogotá',
                'department': 'Cundinamarca',
                'address': 'Calle 53 No. 13-27, Chapinero',
                'phone': '+57 1 345 6789',
                'email': 'contacto@ortodent.com.co',
                'website': 'https://ortodent.com.co',
                'services': ['Ortodoncia Especializada', 'Brackets Metálicos', 'Brackets Estéticos', 'Invisalign'],
                'it_contact': 'Miguel TI',
                'it_phone': '+57 1 345 6790',
                'linkedin': 'https://linkedin.com/company/ortodent-bogota'
            },
            {
                'name': 'Centro de Especialidades Odontológicas Madrid',
                'type': 'IPS',
                'nit': '890234567-8',
                'city': 'Madrid',
                'department': 'Cundinamarca', 
                'address': 'Calle 3 No. 8-12, Centro',
                'phone': '+57 1 823 4567',
                'email': 'info@centrodentalmadrid.com',
                'website': 'https://centrodentalmadrid.com',
                'services': ['Ortodoncia', 'Cirugía Oral', 'Implantología', 'Periodoncia']
            },
            {
                'name': 'Dental Futura - Especialistas en Ortodoncia',
                'type': 'IPS',
                'nit': '890345678-9',
                'city': 'Bogotá',
                'department': 'Cundinamarca',
                'address': 'Av. Caracas No. 45-67, Sur',
                'phone': '+57 1 567 8901',
                'email': 'info@dentalfutura.com',
                'website': 'https://dentalfutura.com',
                'services': ['Ortodoncia Invisible', 'Ortodoncia Tradicional', 'Retenedores', 'Brackets Autoligables'],
                'linkedin': 'https://linkedin.com/company/dental-futura'
            },
            {
                'name': 'Clínica Shaio',
                'type': 'IPS',
                'nit': '860002397-0',
                'city': 'Bogotá',
                'department': 'Cundinamarca',
                'address': 'Calle 116 No. 18A-31',
                'phone': '+57 1 646 8000',
                'email': 'info@shaio.org',
                'website': 'https://shaio.org',
                'services': ['Cardiología', 'Cirugía Cardiovascular'],
                'it_contact': 'Luis Tecnología',
                'it_phone': '+57 1 646 8020'
            },
            {
                'name': 'Fundación Valle del Lili',
                'type': 'IPS',
                'nit': '890399002-6',
                'city': 'Cali',
                'department': 'Valle del Cauca',
                'address': 'Carrera 98 No. 18-49',
                'phone': '+57 2 331 9090',
                'email': 'info@valledellili.org',
                'website': 'https://valledellili.org',
                'services': ['Trasplantes', 'Oncología', 'Pediatría'],
                'linkedin': 'https://linkedin.com/company/fundacion-valle-del-lili'
            },
            {
                'name': 'Nueva EPS',
                'type': 'EPS',
                'nit': '900156264-9',
                'city': 'Bogotá',
                'department': 'Cundinamarca',
                'address': 'Calle 93 No. 19-75',
                'phone': '+57 1 489 8900',
                'email': 'atencionusuario@nuevaeps.com.co',
                'website': 'https://nuevaeps.com.co',
                'services': ['Régimen Contributivo', 'Régimen Subsidiado']
            }
        ]
    
    def _mock_specialty_search(self, specialty: str, location: str) -> List[Dict[str, Any]]:
        """Mock search results based on specialty"""
        all_data = self._get_sample_health_institutions()
        
        # Filter by specialty (simplified)
        specialty_keywords = {
            'cardiología': ['Hospital San Vicente', 'Clínica Shaio', 'Clínica Las Américas'],
            'oncología': ['Clínica Las Américas', 'Fundación Valle del Lili'],
            'pediatría': ['Hospital Pablo Tobón', 'Fundación Valle del Lili'],
            'urgencias': ['Hospital San Vicente', 'Hospital Pablo Tobón']
        }
        
        matching_institutions = []
        keywords = specialty_keywords.get(specialty.lower(), [])
        
        for data in all_data:
            if any(keyword.lower() in data['name'].lower() for keyword in keywords):
                matching_institutions.append(data)
        
        return matching_institutions[:10]  # Limit results
    
    def _create_institution_from_sample(self, data: Dict[str, Any]) -> Optional[HealthInstitution]:
        """Create HealthInstitution object from sample data"""
        try:
            # Create location
            location = Location(
                address=data.get('address', ''),
                city=data.get('city', ''),
                department=data.get('department', ''),
                country='Colombia'
            )
            
            # Create contacts
            contacts = []
            if data.get('phone'):
                contacts.append(Contact(
                    type=ContactType.PHONE,
                    value=data['phone'],
                    name='Principal'
                ))
            
            if data.get('email'):
                contacts.append(Contact(
                    type=ContactType.EMAIL,
                    value=data['email'],
                    name='Contacto General'
                ))
            
            if data.get('it_contact'):
                contacts.append(Contact(
                    type=ContactType.PERSON,
                    name=data['it_contact'],
                    department='IT/Sistemas',
                    phone=data.get('it_phone'),
                    email=data.get('it_email')
                ))
            
            # Create social media profiles
            social_media = []
            if data.get('linkedin'):
                social_media.append(SocialMediaProfile(
                    platform='LinkedIn',
                    url=data['linkedin']
                ))
            
            # Create institution
            institution = HealthInstitution(
                name=data['name'],
                type=InstitutionType.IPS if data['type'] == 'IPS' else InstitutionType.EPS,
                nit=data.get('nit'),
                location=location,
                contacts=contacts,
                website=data.get('website'),
                services=data.get('services', []),
                social_media=social_media
            )
            
            return institution
            
        except Exception as e:
            logger.error(f"Error creating institution from sample: {e}")
            return None
    
    def _create_institution_from_search(self, result: Dict[str, Any]) -> Optional[HealthInstitution]:
        """Create institution from search result"""
        return self._create_institution_from_sample(result)
    
    def _scrape_from_website(self, name: str, url: str) -> Optional[HealthInstitution]:
        """Scrape institution details from its website"""
        # This would implement actual website scraping
        # For now, return mock data
        return None
    
    def _search_and_scrape(self, name: str) -> Optional[HealthInstitution]:
        """Search for institution online and scrape details"""
        # This would implement Google search + scraping
        # For now, return mock data
        return None
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        self.session.close()