import logging
import time
import re
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from ..models.institution import (
    HealthInstitution, InstitutionType, Contact, ContactType, 
    ITTeamInfo, SocialMediaProfile, SocialMediaPlatform, ScrapeResult
)
from ..utils.text_processor import TextProcessor

logger = logging.getLogger(__name__)

class BaseHealthScraper:
    """Base scraper class for health institutions in Colombia"""
    
    def __init__(self, headless: bool = True, timeout: int = 30, rate_limit: float = 2.0):
        self.headless = headless
        self.timeout = timeout
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.text_processor = TextProcessor()
        self.driver = None
        
    def _setup_selenium(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver with optimal settings"""
        if self.driver:
            return self.driver
            
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            return self.driver
        except Exception as e:
            logger.error(f"Failed to setup Selenium WebDriver: {e}")
            raise
    
    def _get_page_content(self, url: str, use_selenium: bool = False) -> Optional[BeautifulSoup]:
        """Fetch and parse page content using requests or selenium"""
        try:
            if use_selenium:
                if not self.driver:
                    self._setup_selenium()
                self.driver.get(url)
                time.sleep(2)  # Wait for page load
                html = self.driver.page_source
            else:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                html = response.text
                
            soup = BeautifulSoup(html, 'lxml')
            return soup
        except Exception as e:
            logger.error(f"Failed to fetch content from {url}: {e}")
            return None
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> List[Contact]:
        """Extract contact information from webpage"""
        contacts = []
        
        # Phone patterns
        phone_patterns = [
            r'\+?57[\s-]?\d{1,4}[\s-]?\d{3}[\s-]?\d{4}',
            r'\(\d{1,4}\)[\s-]?\d{3}[\s-]?\d{4}',
            r'\d{7,10}'
        ]
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        text_content = soup.get_text()
        
        # Extract emails
        emails = re.findall(email_pattern, text_content)
        
        # Extract phones
        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text_content))
        
        # Create contact objects from found information
        for email in emails:
            contact = Contact(email=email, contact_type=ContactType.GENERAL)
            contacts.append(contact)
        
        for phone in phones:
            # Clean phone number
            clean_phone = re.sub(r'[^\d+]', '', phone)
            if len(clean_phone) >= 7:
                contact = Contact(phone=clean_phone, contact_type=ContactType.GENERAL)
                contacts.append(contact)
        
        return contacts
    
    def _extract_social_media_links(self, soup: BeautifulSoup, base_url: str) -> List[SocialMediaProfile]:
        """Extract social media profile links"""
        social_profiles = []
        
        social_patterns = {
            SocialMediaPlatform.LINKEDIN: [
                r'linkedin\.com/company/[^/\s]+',
                r'linkedin\.com/in/[^/\s]+'
            ],
            SocialMediaPlatform.FACEBOOK: [r'facebook\.com/[^/\s]+'],
            SocialMediaPlatform.TWITTER: [r'twitter\.com/[^/\s]+'],
            SocialMediaPlatform.INSTAGRAM: [r'instagram\.com/[^/\s]+'],
            SocialMediaPlatform.YOUTUBE: [r'youtube\.com/channel/[^/\s]+', r'youtube\.com/c/[^/\s]+']
        }
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            full_url = urljoin(base_url, href)
            
            for platform, patterns in social_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, full_url, re.IGNORECASE):
                        profile = SocialMediaProfile(
                            platform=platform,
                            url=full_url
                        )
                        social_profiles.append(profile)
                        break
        
        return social_profiles
    
    def _extract_it_information(self, soup: BeautifulSoup) -> ITTeamInfo:
        """Extract IT team and technology information"""
        it_info = ITTeamInfo()
        
        # Keywords that indicate IT presence
        it_keywords = [
            'tecnología', 'sistemas', 'informática', 'digital', 'software',
            'desarrollo', 'programación', 'bases de datos', 'redes',
            'ciberseguridad', 'cloud', 'nube', 'ERP', 'CRM', 'telemedicina'
        ]
        
        text_content = soup.get_text().lower()
        
        # Check if institution mentions IT/technology
        it_mentions = sum(1 for keyword in it_keywords if keyword in text_content)
        it_info.has_it_team = it_mentions > 2
        
        # Look for specific IT-related sections
        it_sections = soup.find_all(['div', 'section', 'p'], 
                                   text=re.compile(r'(tecnología|sistemas|informática)', re.IGNORECASE))
        
        if it_sections:
            it_info.has_it_team = True
            # Extract potential IT department names
            for section in it_sections:
                if section.string:
                    it_info.it_department_name = section.string.strip()
                    break
        
        return it_info
    
    def scrape_institution(self, institution_name: str, additional_urls: List[str] = None) -> ScrapeResult:
        """Main method to scrape a health institution"""
        start_time = time.time()
        
        try:
            # Search for institution online
            search_urls = self._search_institution(institution_name)
            
            if additional_urls:
                search_urls.extend(additional_urls)
            
            if not search_urls:
                return ScrapeResult(
                    success=False,
                    error_message=f"No URLs found for institution: {institution_name}",
                    processing_time=time.time() - start_time
                )
            
            # Scrape from the found URLs
            institution_data = self._scrape_from_urls(institution_name, search_urls)
            
            processing_time = time.time() - start_time
            
            return ScrapeResult(
                success=True,
                institution=institution_data,
                scraped_urls=search_urls,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error scraping institution {institution_name}: {e}")
            return ScrapeResult(
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    def _search_institution(self, institution_name: str) -> List[str]:
        """Search for institution URLs using Google search"""
        search_urls = []
        
        # Google search query
        query = f"{institution_name} site:gov.co OR site:com.co OR site:org.co"
        google_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        
        try:
            soup = self._get_page_content(google_url, use_selenium=True)
            if soup:
                # Extract search result URLs
                result_links = soup.find_all('a', href=True)
                for link in result_links:
                    href = link.get('href', '')
                    if '/url?q=' in href:
                        # Extract actual URL from Google redirect
                        actual_url = href.split('/url?q=')[1].split('&')[0]
                        if any(domain in actual_url for domain in ['.gov.co', '.com.co', '.org.co']):
                            search_urls.append(actual_url)
                            
            time.sleep(self.rate_limit)
            
        except Exception as e:
            logger.warning(f"Failed to search for {institution_name}: {e}")
        
        return search_urls[:5]  # Limit to top 5 results
    
    def _scrape_from_urls(self, institution_name: str, urls: List[str]) -> HealthInstitution:
        """Scrape institution data from provided URLs"""
        institution = HealthInstitution(
            name=institution_name,
            institution_type=self._determine_institution_type(institution_name)
        )
        
        all_contacts = []
        all_social_media = []
        
        for url in urls:
            try:
                soup = self._get_page_content(url, use_selenium=False)
                if soup:
                    # Extract basic information
                    if not institution.website:
                        institution.website = url
                    
                    # Extract contacts
                    contacts = self._extract_contact_info(soup)
                    all_contacts.extend(contacts)
                    
                    # Extract social media
                    social_media = self._extract_social_media_links(soup, url)
                    all_social_media.extend(social_media)
                    
                    # Extract IT information
                    if not institution.it_info.has_it_team:
                        institution.it_info = self._extract_it_information(soup)
                    
                    time.sleep(self.rate_limit)
                    
            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {e}")
                continue
        
        # Deduplicate and assign results
        institution.contacts = self._deduplicate_contacts(all_contacts)
        institution.social_media = self._deduplicate_social_media(all_social_media)
        
        return institution
    
    def _determine_institution_type(self, name: str) -> InstitutionType:
        """Determine if institution is IPS or EPS based on name"""
        name_lower = name.lower()
        
        # EPS keywords
        eps_keywords = ['eps', 'salud total', 'nueva eps', 'sura', 'sanitas', 'compensar', 'salud colpatria']
        if any(keyword in name_lower for keyword in eps_keywords):
            return InstitutionType.EPS
            
        # IPS keywords
        ips_keywords = ['hospital', 'clínica', 'centro médico', 'ips', 'fundación']
        if any(keyword in name_lower for keyword in ips_keywords):
            return InstitutionType.IPS
            
        # Default to IPS
        return InstitutionType.IPS
    
    def _deduplicate_contacts(self, contacts: List[Contact]) -> List[Contact]:
        """Remove duplicate contacts"""
        unique_contacts = []
        seen_emails = set()
        seen_phones = set()
        
        for contact in contacts:
            is_duplicate = False
            
            if contact.email and contact.email in seen_emails:
                is_duplicate = True
            elif contact.phone and contact.phone in seen_phones:
                is_duplicate = True
            
            if not is_duplicate:
                unique_contacts.append(contact)
                if contact.email:
                    seen_emails.add(contact.email)
                if contact.phone:
                    seen_phones.add(contact.phone)
        
        return unique_contacts
    
    def _deduplicate_social_media(self, profiles: List[SocialMediaProfile]) -> List[SocialMediaProfile]:
        """Remove duplicate social media profiles"""
        unique_profiles = []
        seen_urls = set()
        
        for profile in profiles:
            if profile.url not in seen_urls:
                unique_profiles.append(profile)
                seen_urls.add(profile.url)
        
        return unique_profiles
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            self.driver = None
        if self.session:
            self.session.close()