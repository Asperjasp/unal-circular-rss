import logging
import time
import re
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ..models.institution import SocialMediaProfile, SocialMediaPlatform
from ..utils.text_processor import TextProcessor

logger = logging.getLogger(__name__)

class SocialMediaScraper:
    """Specialized scraper for social media profiles"""
    
    def __init__(self, driver: webdriver.Chrome = None, text_processor: TextProcessor = None):
        self.driver = driver
        self.text_processor = text_processor or TextProcessor()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def enhance_social_media_profiles(self, profiles: List[SocialMediaProfile]) -> List[SocialMediaProfile]:
        """Enhance social media profiles with additional data"""
        enhanced_profiles = []
        
        for profile in profiles:
            try:
                enhanced_profile = self._enhance_single_profile(profile)
                enhanced_profiles.append(enhanced_profile)
                time.sleep(2)  # Rate limiting
            except Exception as e:
                logger.warning(f"Failed to enhance profile {profile.url}: {e}")
                enhanced_profiles.append(profile)  # Keep original if enhancement fails
        
        return enhanced_profiles
    
    def _enhance_single_profile(self, profile: SocialMediaProfile) -> SocialMediaProfile:
        """Enhance a single social media profile with additional data"""
        if profile.platform == SocialMediaPlatform.LINKEDIN:
            return self._enhance_linkedin_profile(profile)
        elif profile.platform == SocialMediaPlatform.FACEBOOK:
            return self._enhance_facebook_profile(profile)
        elif profile.platform == SocialMediaPlatform.TWITTER:
            return self._enhance_twitter_profile(profile)
        else:
            return profile
    
    def _enhance_linkedin_profile(self, profile: SocialMediaProfile) -> SocialMediaProfile:
        """Enhance LinkedIn profile with additional data"""
        try:
            if not self.driver:
                logger.warning("Selenium driver required for LinkedIn scraping")
                return profile
            
            self.driver.get(str(profile.url))
            time.sleep(3)
            
            # Extract company name from URL or page
            url_parts = str(profile.url).split('/')
            if 'company' in url_parts:
                company_idx = url_parts.index('company')
                if company_idx + 1 < len(url_parts):
                    profile.username = url_parts[company_idx + 1]
            
            # Try to get follower count (LinkedIn often blocks this)
            try:
                follower_element = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    "[data-test-id='about-us-followers'] span, .org-top-card-summary-info-list__info-item"
                )
                follower_text = follower_element.text
                
                # Extract number from text like "1,234 followers"
                follower_match = re.search(r'([\d,]+)', follower_text)
                if follower_match:
                    follower_count = int(follower_match.group(1).replace(',', ''))
                    profile.follower_count = follower_count
            except (NoSuchElementException, ValueError):
                pass
            
            # Check if verified (premium badge)
            try:
                self.driver.find_element(By.CSS_SELECTOR, ".premium-icon, [data-test-id='premium-badge']")
                profile.verified = True
            except NoSuchElementException:
                profile.verified = False
                
        except Exception as e:
            logger.warning(f"Failed to enhance LinkedIn profile: {e}")
        
        return profile
    
    def _enhance_facebook_profile(self, profile: SocialMediaProfile) -> SocialMediaProfile:
        """Enhance Facebook profile with additional data"""
        try:
            # Extract username from URL
            url_parts = str(profile.url).split('/')
            for part in url_parts:
                if part and not part.startswith('www.') and part != 'facebook.com':
                    profile.username = part.split('?')[0]  # Remove query parameters
                    break
            
            # Facebook pages often require login for detailed info
            # We'll do basic scraping without login
            response = self.session.get(str(profile.url))
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Try to extract page title as name
                title = soup.find('title')
                if title:
                    profile.username = title.text.split(' - Facebook')[0] if ' - Facebook' in title.text else title.text
                    
        except Exception as e:
            logger.warning(f"Failed to enhance Facebook profile: {e}")
        
        return profile
    
    def _enhance_twitter_profile(self, profile: SocialMediaProfile) -> SocialMediaProfile:
        """Enhance Twitter profile with additional data"""
        try:
            # Extract username from URL
            url_parts = str(profile.url).split('/')
            for part in url_parts:
                if part and not part.startswith('www.') and part != 'twitter.com':
                    profile.username = part.split('?')[0]  # Remove query parameters
                    break
            
            # Twitter requires authentication for most data
            # We'll extract basic info only
            if self.driver:
                self.driver.get(str(profile.url))
                time.sleep(3)
                
                try:
                    # Look for verified badge
                    self.driver.find_element(By.CSS_SELECTOR, "[data-testid='icon-verified']")
                    profile.verified = True
                except NoSuchElementException:
                    profile.verified = False
                    
        except Exception as e:
            logger.warning(f"Failed to enhance Twitter profile: {e}")
        
        return profile
    
    def search_social_media_profiles(self, institution_name: str, website_url: str = None) -> List[SocialMediaProfile]:
        """Search for social media profiles of an institution"""
        profiles = []
        
        # Search patterns for different platforms
        search_queries = [
            f"{institution_name} site:linkedin.com/company",
            f"{institution_name} site:facebook.com",
            f"{institution_name} site:twitter.com",
            f"{institution_name} site:instagram.com"
        ]
        
        for query in search_queries:
            try:
                platform_profiles = self._search_platform_profiles(query, institution_name)
                profiles.extend(platform_profiles)
                time.sleep(2)  # Rate limiting
            except Exception as e:
                logger.warning(f"Failed to search for profiles with query '{query}': {e}")
        
        # If we have a website, check for social media links on the website
        if website_url:
            try:
                website_profiles = self._extract_social_links_from_website(website_url)
                profiles.extend(website_profiles)
            except Exception as e:
                logger.warning(f"Failed to extract social links from website: {e}")
        
        # Remove duplicates
        unique_profiles = []
        seen_urls = set()
        
        for profile in profiles:
            if str(profile.url) not in seen_urls:
                unique_profiles.append(profile)
                seen_urls.add(str(profile.url))
        
        return unique_profiles
    
    def _search_platform_profiles(self, query: str, institution_name: str) -> List[SocialMediaProfile]:
        """Search for profiles on a specific platform using Google"""
        profiles = []
        
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            if self.driver:
                self.driver.get(search_url)
                time.sleep(2)
                
                # Find search result links
                search_results = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/url?q=']")
                
                for result in search_results[:3]:  # Limit to top 3 results
                    href = result.get_attribute('href')
                    if '/url?q=' in href:
                        actual_url = href.split('/url?q=')[1].split('&')[0]
                        
                        # Determine platform
                        platform = None
                        if 'linkedin.com' in actual_url:
                            platform = SocialMediaPlatform.LINKEDIN
                        elif 'facebook.com' in actual_url:
                            platform = SocialMediaPlatform.FACEBOOK
                        elif 'twitter.com' in actual_url:
                            platform = SocialMediaPlatform.TWITTER
                        elif 'instagram.com' in actual_url:
                            platform = SocialMediaPlatform.INSTAGRAM
                        
                        if platform:
                            profile = SocialMediaProfile(
                                platform=platform,
                                url=actual_url
                            )
                            profiles.append(profile)
                            
        except Exception as e:
            logger.warning(f"Failed to search for platform profiles: {e}")
        
        return profiles
    
    def _extract_social_links_from_website(self, website_url: str) -> List[SocialMediaProfile]:
        """Extract social media links directly from institution's website"""
        profiles = []
        
        try:
            response = self.session.get(website_url, timeout=10)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find all links
            links = soup.find_all('a', href=True)
            
            social_patterns = {
                SocialMediaPlatform.LINKEDIN: r'linkedin\.com/(company|in)/',
                SocialMediaPlatform.FACEBOOK: r'facebook\.com/',
                SocialMediaPlatform.TWITTER: r'twitter\.com/',
                SocialMediaPlatform.INSTAGRAM: r'instagram\.com/',
                SocialMediaPlatform.YOUTUBE: r'youtube\.com/(channel|c|user)/'
            }
            
            for link in links:
                href = link.get('href', '')
                full_url = urljoin(website_url, href)
                
                for platform, pattern in social_patterns.items():
                    if re.search(pattern, full_url, re.IGNORECASE):
                        profile = SocialMediaProfile(
                            platform=platform,
                            url=full_url
                        )
                        profiles.append(profile)
                        break
                        
        except Exception as e:
            logger.warning(f"Failed to extract social links from website: {e}")
        
        return profiles