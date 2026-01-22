#!/usr/bin/env python3
"""
Example usage script for the Health Institutions Scraper

This script demonstrates:
1. Natural language search with the prompt-based service
2. Database operations with automatic deduplication
3. Scraping and storing new institutions
4. Querying stored data

Run this script after starting the API server or use it standalone.
"""

import asyncio
import json
from datetime import datetime

# Import the scraper components
from health_scraper.scrapers.base_scraper import BaseHealthScraper
from health_scraper.scrapers.social_media_scraper import SocialMediaScraper
from health_scraper.config import config
from health_scraper.database.service import DatabaseService
from health_scraper.services.search_service import PromptSearchService, QueryParser
from health_scraper.models.institution import HealthInstitution, InstitutionType, SpecialtyType


def example_1_natural_language_search():
    """
    Example 1: Natural Language Search
    
    Search for health institutions using plain Spanish/English queries.
    The system automatically parses and extracts:
    - Specialty (odontología, cardiología, etc.)
    - Treatment (implantes, ortodoncia, etc.)
    - Location (city, "near X")
    """
    print("\n" + "="*60)
    print("📖 Example 1: Natural Language Search")
    print("="*60)
    
    # Initialize search service
    service = PromptSearchService()
    
    # Example queries
    queries = [
        "Odontología especializada en implantes cerca de Soacha",
        "Clínica dental con ortodoncia en Kennedy",
        "Cardiología en Bogotá",
        "Hospital con pediatría en Medellín"
    ]
    
    for query in queries:
        print(f"\n🔍 Query: \"{query}\"")
        
        # Parse the query to see how it's interpreted
        parser = QueryParser()
        parsed = parser.parse(query)
        
        print(f"   📊 Parsed:")
        print(f"      - Specialty: {parsed.specialty}")
        print(f"      - Treatment: {parsed.treatment}")
        print(f"      - City: {parsed.city}")
        print(f"      - Near: {parsed.near_location}")
        print(f"      - Department: {parsed.department}")
        
        # Execute the search
        result = service.search(query, limit=5)
        print(f"   📋 Results: {result.total_count} institutions found")
        print(f"   ⏱️  Time: {result.execution_time:.3f}s")
        
        # Show first few results
        for inst in result.institutions[:3]:
            print(f"      • {inst.name} ({inst.city})")


def example_2_database_operations():
    """
    Example 2: Database Operations with Deduplication
    
    Demonstrates how to:
    - Save institutions with automatic deduplication
    - Check if an institution already exists
    - Search the database
    - Get statistics
    """
    print("\n" + "="*60)
    print("💾 Example 2: Database Operations & Deduplication")
    print("="*60)
    
    # Initialize database service
    db = DatabaseService()
    
    # Create sample institutions
    institutions = [
        HealthInstitution(
            name="Clínica Dental Sonrisa",
            institution_type=InstitutionType.CLINICA_DENTAL,
            city="Soacha",
            department="Cundinamarca",
            phone="3001234567",
            email="info@sonrisa.com",
            specialties=["odontología general", "ortodoncia"],
            services=["limpieza dental", "blanqueamiento", "implantes"]
        ),
        HealthInstitution(
            name="Centro Médico Kennedy",
            institution_type=InstitutionType.CENTRO_MEDICO,
            city="Kennedy",
            department="Bogotá D.C.",
            phone="3109876543",
            email="contacto@cmkennedy.com",
            specialties=["medicina general", "pediatría"],
            services=["consulta general", "vacunación"]
        ),
        HealthInstitution(
            name="Clínica Dental Sonrisa",  # Duplicate!
            institution_type=InstitutionType.CLINICA_DENTAL,
            city="Soacha",
            department="Cundinamarca",
            phone="3001234567",
            email="info@sonrisa.com"
        )
    ]
    
    print("\n📥 Saving institutions to database...")
    
    for inst in institutions:
        saved, is_new = db.save_institution(inst)
        status = "✅ NEW" if is_new else "⚠️  EXISTS (skipped duplicate)"
        print(f"   {status}: {inst.name}")
    
    # Check for duplicates
    print("\n🔍 Checking for duplicates...")
    exists = db.institution_exists("Clínica Dental Sonrisa")
    print(f"   'Clínica Dental Sonrisa' exists: {exists}")
    
    # Search the database
    print("\n🔎 Searching database for 'odontología' in 'Soacha'...")
    results = db.search_institutions(
        specialty="odontologia",
        city="Soacha",
        limit=10
    )
    print(f"   Found {len(results)} results:")
    for inst in results:
        print(f"      • {inst.name} - {inst.city}")
    
    # Get statistics
    print("\n📊 Database Statistics:")
    stats = db.get_statistics()
    print(f"   • Total institutions: {stats['total_institutions']}")
    print(f"   • Total contacts: {stats['total_contacts']}")
    print(f"   • Total social media profiles: {stats['total_social_media_profiles']}")
    print(f"   • Institutions by type: {stats['institutions_by_type']}")
    if stats['top_cities']:
        print(f"   • Top cities: {list(stats['top_cities'].items())[:3]}")


def example_3_scraping_with_storage():
    """
    Example 3: Scraping and Storing
    
    Demonstrates how to:
    - Scrape institutions from the web
    - Automatically store results in the database
    - Handle duplicates during scraping
    """
    print("\n" + "="*60)
    print("🕷️ Example 3: Scraping and Storing")
    print("="*60)
    
    # Initialize components
    scraper = BaseHealthScraper(
        headless=config.headless_mode,
        timeout=config.selenium_timeout,
        rate_limit=config.rate_limit_delay
    )
    db = DatabaseService()
    
    # Institutions to scrape
    institutions_to_scrape = [
        "Hospital San Ignacio Bogotá",
        "Clínica Shaio",
        "Nueva EPS"
    ]
    
    print(f"\n🔍 Scraping {len(institutions_to_scrape)} institutions...")
    print("   (This may take a few minutes)\n")
    
    try:
        for institution_name in institutions_to_scrape:
            print(f"📋 Scraping: {institution_name}")
            
            # Scrape the institution
            result = scraper.scrape_institution(institution_name)
            
            if result.success:
                inst = result.institution
                
                # Save to database (with deduplication)
                saved, is_new = db.save_institution(inst)
                
                status = "NEW" if is_new else "UPDATED"
                print(f"   [{status}] ✅ {inst.name}")
                print(f"   • Type: {inst.institution_type}")
                print(f"   • Contacts found: {len(inst.contacts)}")
                print(f"   • Social media: {len(inst.social_media)}")
                print(f"   • Processing time: {result.processing_time:.2f}s")
            else:
                print(f"   ❌ Failed: {result.error_message}")
            
            print()
            
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
    finally:
        # Clean up scraper resources
        scraper.cleanup()
        print("🧹 Scraper resources cleaned up")


def example_4_search_and_scrape():
    """
    Example 4: Smart Search and Scrape
    
    Demonstrates the search_and_scrape functionality that:
    - First searches the database
    - If insufficient results, automatically scrapes for more
    - Stores new results in the database
    """
    print("\n" + "="*60)
    print("🔍+🕷️ Example 4: Smart Search and Scrape")
    print("="*60)
    
    service = PromptSearchService()
    
    query = "Clínica dental especializada en implantes cerca de Kennedy"
    
    print(f"\n🔍 Query: \"{query}\"")
    print("   This will search the database first, then scrape if needed...\n")
    
    try:
        result = service.search_and_scrape(
            query=query,
            limit=10,
            min_results=3,
            scrape_if_insufficient=True
        )
        
        print(f"📊 Results:")
        print(f"   • Total found: {result.total_count}")
        print(f"   • From database: {result.from_database}")
        print(f"   • Newly scraped: {result.newly_scraped}")
        print(f"   • Execution time: {result.execution_time:.2f}s")
        
        print(f"\n📋 Institutions:")
        for inst in result.institutions:
            print(f"   • {inst.name} ({inst.city})")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        service.cleanup()


async def main():
    """Main example function"""
    print("\n" + "="*60)
    print("🏥 Health Institutions Scraper - Usage Examples")
    print("="*60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run examples
    try:
        # Example 1: Natural Language Search
        example_1_natural_language_search()
        
        # Example 2: Database Operations
        example_2_database_operations()
        
        # Uncomment to run scraping examples (requires internet):
        # example_3_scraping_with_storage()
        # example_4_search_and_scrape()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ Examples completed!")
    print("="*60)
    print("\n💡 Tips:")
    print("   • Start the API: python main.py")
    print("   • View docs: http://localhost:8000/docs")
    print("   • Use natural language: 'Odontología cerca de Soacha'")
    print("   • Data is stored in: health_institutions.db")


def save_results_to_json(results, filename="scraped_data.json"):
    """Save scraping results to JSON file"""
    json_data = []
    
    for result in results:
        if result.success and result.institution:
            # Convert to dictionary for JSON serialization
            institution_dict = result.institution.dict()
            json_data.append(institution_dict)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"💾 Results saved to {filename}")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())