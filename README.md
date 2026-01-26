# 🏥 Colombian Health Institutions Scraper

A comprehensive Python-based web scraper and database system designed specifically for extracting and storing detailed information from Colombian IPS (Institución Prestadora de Servicios de Salud), EPS (Entidad Promotora de Salud), and other health institutions. Built for Health-Tech companies that need to gather contact information, IT team details, and social media profiles for business development and partnership opportunities.

## 🎯 NEW: Starter Scraping & Export Features

This tool now includes ready-to-use functionality for marketing teams:

### 📊 Instant Data Collection
- **Sample Scraping**: Click "Recopilar Datos de Muestra" to instantly collect 50+ health institutions
- **Real Data**: Uses actual Colombian IPS/EPS sample data including major hospitals and EPS providers
- **IT Contacts**: Automatically identifies IT team contacts when available
- **Social Media**: Collects LinkedIn and other professional profiles

### 📁 Marketing-Ready Exports
- **CSV Download**: Ready for CRM import and spreadsheet analysis
- **Excel Export**: Formatted Excel files with proper columns and headers
- **Instant Downloads**: One-click download buttons in the web interface
- **Data Statistics**: View collection progress and data quality metrics

### 🎯 Perfect for Health-Tech Companies
- **Partnership Development**: Find institutions ready for technology partnerships
- **IT Contact Discovery**: Identify technology decision-makers and IT departments
- **Social Media Outreach**: LinkedIn profiles for professional networking
- **Market Intelligence**: Geographic distribution and service analysis

---

## 📋 How to Get Started (Marketing Teams)

### Option 1: Web Interface (Recommended for Non-Technical Users)

1. **Start the Application**
   ```bash
   python main.py
   ```

2. **Open Your Browser**
   - Go to: http://localhost:8000

3. **Collect Sample Data**
   - Click the green **"Recopilar Datos de Muestra"** button
   - Wait 2-3 minutes for data collection
   - See progress updates in real-time

4. **Download Your Data**
   - Click **"Descargar CSV"** for CRM import
   - Click **"Descargar Excel"** for analysis
   - Use **"Estadísticas"** to view data quality

5. **Use the Data**
   - Import CSV into your CRM (Salesforce, HubSpot, etc.)
   - Open Excel file for analysis and list building
   - Use LinkedIn profiles for social outreach

### Sample Data Included

The scraper includes real sample data from major Colombian institutions:

| Institution | Type | City | IT Contact | LinkedIn | Services |
|-------------|------|------|------------|----------|----------|
| Hospital San Vicente Fundación | IPS | Medellín | ✅ Carlos Sistemas | ✅ Available | Urgencias, Cirugía, UCI |
| Clínica Las Américas | IPS | Medellín | ❌ No | ✅ Available | Oncología, Cardiología |
| EPS SURA | EPS | Medellín | ✅ Ana López | ✅ Available | Plan Básico, Complementario |
| Compensar EPS | EPS | Bogotá | ❌ No | ❌ No | POS, No POS |
| + 50 more institutions... | | | | | |

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage Guide](#-usage-guide)
  - [API Endpoints](#api-endpoints)
  - [Natural Language Search](#natural-language-search)
  - [Programmatic Usage](#programmatic-usage)
- [Data Models](#-data-models)
- [Database & Deduplication](#-database--deduplication)
- [Configuration](#-configuration)
- [Examples](#-examples)
- [Architecture](#-architecture)
- [Contributing](#-contributing)

---

## 🚀 Features

### Core Scraping Capabilities
- **40+ Institution Types**: Hospitals, clinics, dental centers, laboratories, and more
- **50+ Medical Specialties**: From odontology to cardiology, all Colombian health specialties
- **Contact Extraction**: Emails, phone numbers, addresses, and key personnel
- **IT Team Detection**: Identify IT departments and technology contacts
- **Social Media Profiles**: LinkedIn, Facebook, Twitter, Instagram, YouTube

### 🔍 Natural Language Search (NEW!)
Search using plain Spanish or English queries:
```
"Odontología especializada en implantes cerca de Soacha"
"Clínica dental con ortodoncia en Kennedy"
"Cardiología en Bogotá"
```

### 💾 Persistent Database (NEW!)
- **SQLite/PostgreSQL Support**: Store all scraped data persistently
- **Automatic Deduplication**: Same institution won't be added twice
- **Query Logging**: Track all searches for analytics
- **Smart Updates**: Existing records are updated with new data

### Technical Features
- **Dual Scraping Methods**: BeautifulSoup for static + Selenium for dynamic content
- **Rate Limiting**: Respects website policies
- **Concurrent Processing**: Bulk scraping with configurable limits
- **Data Quality Scoring**: Evaluates completeness of scraped data
- **RESTful API**: FastAPI-based with auto-generated docs

---

## ⚡ Quick Start

### 1. Install Dependencies
```bash
cd Scrapper
pip install -r requirements.txt
```

### 2. Start the API Server
```bash
python main.py
```

### 3. Open API Documentation
Navigate to: http://localhost:8000/docs

### 4. Make Your First Search
```bash
curl -X POST "http://localhost:8000/api/v1/search/prompt?query=Odontología%20en%20Soacha"
```

---

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Google Chrome browser (for Selenium)
- Internet connection

### Step-by-Step Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd Scrapper

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file (optional)
cp .env.example .env
# Edit .env with your settings
```

### Environment Variables (.env)

```env
# Scraper Settings
SCRAPER_MODE=development
LOG_LEVEL=INFO
RATE_LIMIT_DELAY=2

# Database (SQLite by default)
DATABASE_URL=sqlite:///health_institutions.db
# For PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost/health_db

# API Settings
API_HOST=0.0.0.0
API_PORT=8000

# Selenium
HEADLESS_MODE=True
SELENIUM_TIMEOUT=30
```

---

## 📖 Usage Guide

### API Endpoints

#### 🔍 Natural Language Search
**POST** `/api/v1/search/prompt`

Search using natural language queries with automatic parsing.

```bash
curl -X POST "http://localhost:8000/api/v1/search/prompt" \
  -G \
  --data-urlencode "query=Odontología especializada en implantes cerca de Soacha" \
  --data-urlencode "limit=20" \
  --data-urlencode "scrape_if_needed=false"
```

**Response:**
```json
{
  "success": true,
  "query": {
    "original": "Odontología especializada en implantes cerca de Soacha",
    "parsed": {
      "specialty": "odontologia",
      "treatment": "implantes_dentales",
      "city": null,
      "near_location": "Soacha",
      "institution_type": null
    }
  },
  "results": {
    "total_count": 5,
    "from_database": 5,
    "newly_scraped": 0,
    "execution_time_seconds": 0.023
  },
  "institutions": [...]
}
```

#### 🧪 Parse Query (Debug)
**GET** `/api/v1/search/parse`

See how your query will be interpreted without executing the search.

```bash
curl "http://localhost:8000/api/v1/search/parse?query=Clínica%20dental%20con%20ortodoncia%20en%20Kennedy"
```

#### 📋 List Institutions
**GET** `/api/v1/database/institutions`

Browse stored institutions with filters.

```bash
curl "http://localhost:8000/api/v1/database/institutions?city=Bogotá&specialty=odontologia&limit=50"
```

#### 🏥 Get Institution Details
**GET** `/api/v1/database/institutions/{id}`

Get full details of a specific institution.

```bash
curl "http://localhost:8000/api/v1/database/institutions/123"
```

#### 📊 Database Statistics
**GET** `/api/v1/database/statistics`

Get counts and distributions of stored data.

```bash
curl "http://localhost:8000/api/v1/database/statistics"
```

#### 🔍 Check for Duplicates
**GET** `/api/v1/database/check-duplicate`

Check if an institution already exists before scraping.

```bash
curl "http://localhost:8000/api/v1/database/check-duplicate?name=Clínica%20Dental%20Sonrisa&nit=900123456"
```

#### 🕷️ Scrape Single Institution
**POST** `/api/v1/scrape/single`

Scrape detailed information for one institution.

```bash
curl -X POST "http://localhost:8000/api/v1/scrape/single" \
  -G \
  --data-urlencode "institution_name=Hospital San Ignacio" \
  --data-urlencode "include_social_media=true"
```

#### 📦 Bulk Scraping
**POST** `/api/v1/scrape/bulk`

Scrape multiple institutions at once.

```bash
curl -X POST "http://localhost:8000/api/v1/scrape/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "institution_names": [
      "Hospital San Ignacio",
      "Clínica Shaio",
      "EPS Sanitas"
    ],
    "include_social_media": true,
    "max_concurrent": 3
  }'
```

---

### Natural Language Search

The search system understands queries in Spanish and English:

#### Supported Query Patterns

| Pattern | Example | Parsed As |
|---------|---------|-----------|
| Specialty + Location | "Odontología en Bogotá" | specialty=odontologia, city=Bogotá |
| Treatment + Near | "Implantes cerca de Soacha" | treatment=implantes, near=Soacha |
| Institution + Specialty | "Clínica dental en Kennedy" | type=CLINICA_DENTAL, city=Kennedy |
| Full Query | "Cardiología especializada en ecocardiograma en Medellín" | specialty=cardiologia, treatment=ecocardiograma, city=Medellín |

#### Supported Specialties

| Spanish | Aliases |
|---------|---------|
| Odontología | dental, dentista, dientes |
| Ortodoncia | brackets |
| Implantología | implantes, implantes dentales |
| Cardiología | corazón, cardíaco |
| Oftalmología | ojos, visión, óptica |
| Dermatología | piel |
| Traumatología | huesos, fracturas |
| Ginecología | obstetricia, embarazo |
| Pediatría | niños, infantil |
| Neurología | cerebro, nervios |
| Psiquiatría | psicología, salud mental |

#### Supported Locations

| City | Department |
|------|------------|
| Bogotá | Bogotá D.C. |
| Soacha | Cundinamarca |
| Kennedy, Bosa, Suba... | Bogotá D.C. (localities) |
| Medellín | Antioquia |
| Cali | Valle del Cauca |
| Barranquilla | Atlántico |
| Cartagena | Bolívar |
| And 30+ more... | |

---

### Programmatic Usage

#### Basic Search

```python
from health_scraper.services import PromptSearchService

# Initialize service
service = PromptSearchService()

# Search database only
result = service.search("Odontología en Soacha")

print(f"Found {result.total_count} institutions")
for inst in result.institutions:
    print(f"  - {inst.name} ({inst.city})")

# Search + scrape if needed
result = service.search_and_scrape(
    query="Clínica dental especializada en implantes cerca de Kennedy",
    min_results=5,
    scrape_if_insufficient=True
)

print(f"From database: {result.from_database}")
print(f"Newly scraped: {result.newly_scraped}")
```

#### Direct Database Operations

```python
from health_scraper.database import DatabaseService
from health_scraper.models.institution import HealthInstitution, InstitutionType

# Initialize database
db = DatabaseService()

# Save an institution (with automatic deduplication)
institution = HealthInstitution(
    name="Clínica Dental Sonrisa",
    institution_type=InstitutionType.CLINICA_DENTAL,
    city="Soacha",
    department="Cundinamarca",
    phone="3001234567",
    email="info@sonrisa.com"
)

saved, is_new = db.save_institution(institution)
if is_new:
    print(f"New institution saved with ID: {saved.id}")
else:
    print(f"Institution already exists (ID: {saved.id})")

# Search institutions
results = db.search_institutions(
    specialty="odontologia",
    city="Soacha",
    limit=20
)

# Check if exists
exists = db.institution_exists(
    name="Clínica Dental Sonrisa",
    nit="900123456"
)

# Get statistics
stats = db.get_statistics()
print(f"Total institutions: {stats['total_institutions']}")
```

#### Scraping

```python
from health_scraper.scrapers.base_scraper import BaseHealthScraper

# Initialize scraper
scraper = BaseHealthScraper(
    headless=True,
    timeout=30,
    rate_limit=2.0
)

try:
    # Scrape a single institution
    result = scraper.scrape_institution("Hospital San Ignacio")
    
    if result.success:
        inst = result.institution
        print(f"Name: {inst.name}")
        print(f"Type: {inst.institution_type}")
        print(f"Contacts: {len(inst.contacts)}")
        print(f"Social Media: {len(inst.social_media)}")
finally:
    scraper.cleanup()
```

---

## 📊 Data Models

### Institution Types

The system supports 40+ institution types:

```python
class InstitutionType(str, Enum):
    # Main Colombian Classifications
    IPS = "IPS"                    # Healthcare Provider
    EPS = "EPS"                    # Health Insurance
    ESE = "ESE"                    # State Social Enterprise
    
    # Clinical Facilities
    HOSPITAL = "HOSPITAL"
    CLINICA = "CLINICA"
    CENTRO_MEDICO = "CENTRO_MEDICO"
    CONSULTORIO = "CONSULTORIO"
    
    # Specialized Centers
    CENTRO_ODONTOLOGICO = "CENTRO_ODONTOLOGICO"
    CLINICA_DENTAL = "CLINICA_DENTAL"
    CENTRO_OFTALMOLOGICO = "CENTRO_OFTALMOLOGICO"
    CENTRO_CARDIOLOGICO = "CENTRO_CARDIOLOGICO"
    CENTRO_ONCOLOGICO = "CENTRO_ONCOLOGICO"
    # ... and many more
```

### Health Institution Data

```python
class HealthInstitution:
    # Basic Information
    name: str                       # "Clínica Dental Sonrisa"
    institution_type: InstitutionType
    specialty_type: SpecialtyType   # Primary specialty
    registration_number: str        # Official registration
    nit: str                        # Colombian tax ID
    
    # Location
    address: str
    city: str                       # "Soacha"
    department: str                 # "Cundinamarca"
    
    # Contact
    phone: str
    email: str
    website: str
    
    # Organization
    affiliation: str
    legal_representative: str
    medical_director: str
    
    # Services
    services: List[str]             # ["Ortodoncia", "Implantes"]
    specialties: List[str]          # ["Odontología general"]
    treatments: List[str]           # ["Blanqueamiento dental"]
    
    # IT Information
    has_it_team: bool
    technology_stack: List[str]
    
    # Social Media
    social_media: List[SocialMediaProfile]
    
    # Metadata
    data_quality_score: float       # 0.0 - 1.0
    scraped_at: datetime
```

---

## 💾 Database & Deduplication

### How Deduplication Works

The system uses a **unique hash** computed from:
1. Institution name (normalized)
2. NIT (Colombian tax ID) if available
3. Address if NIT is not available

```python
# This hash ensures the same institution isn't added twice
unique_hash = SHA256(normalize(name) + "|" + normalize(nit or address))
```

### Saving Institutions

```python
db = DatabaseService()

# First save: Creates new record
inst1, is_new = db.save_institution(institution)
print(is_new)  # True

# Second save: Returns existing record
inst2, is_new = db.save_institution(institution)
print(is_new)  # False
print(inst1.id == inst2.id)  # True
```

### Database Schema

```
institutions
├── id (Primary Key)
├── name
├── unique_hash (Unique Index)
├── institution_type
├── specialty_type
├── nit
├── address, city, department
├── phone, email, website
├── services, specialties (JSON)
├── has_it_team
├── scraped_at, updated_at
└── ...

contacts
├── id
├── institution_id (Foreign Key)
├── name, position, email, phone
└── contact_type

social_media
├── id
├── institution_id (Foreign Key)
├── platform, url, username
└── follower_count, verified

search_queries (Analytics)
├── id
├── original_query
├── specialty, treatment, city
├── results_count
└── queried_at
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCRAPER_MODE` | development | Mode (development/production) |
| `LOG_LEVEL` | INFO | Logging level |
| `DATABASE_URL` | sqlite:///health_institutions.db | Database connection |
| `RATE_LIMIT_DELAY` | 2 | Seconds between requests |
| `HEADLESS_MODE` | True | Run browser headless |
| `SELENIUM_TIMEOUT` | 30 | Browser timeout in seconds |
| `API_HOST` | 0.0.0.0 | API host |
| `API_PORT` | 8000 | API port |

### PostgreSQL Configuration

For production, use PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/health_institutions
```

Install PostgreSQL driver:
```bash
pip install psycopg2-binary
```

---

## 📝 Examples

### Example 1: Find Dental Clinics Near Soacha

```python
from health_scraper.services import PromptSearchService

service = PromptSearchService()
result = service.search("Clínica dental cerca de Soacha")

for inst in result.institutions:
    print(f"{inst.name}")
    print(f"  📍 {inst.address}, {inst.city}")
    print(f"  📞 {inst.phone}")
    print(f"  📧 {inst.email}")
    print()
```

### Example 2: Bulk Scrape with Database Storage

```python
from health_scraper.scrapers.base_scraper import BaseHealthScraper
from health_scraper.database import DatabaseService

scraper = BaseHealthScraper(headless=True)
db = DatabaseService()

institutions_to_scrape = [
    "Hospital San Ignacio",
    "Clínica Shaio",
    "Fundación Santa Fe"
]

for name in institutions_to_scrape:
    result = scraper.scrape_institution(name)
    
    if result.success:
        saved, is_new = db.save_institution(result.institution)
        status = "NEW" if is_new else "EXISTS"
        print(f"[{status}] {name}")
    else:
        print(f"[FAILED] {name}: {result.error_message}")

scraper.cleanup()

# Check statistics
stats = db.get_statistics()
print(f"\nTotal in database: {stats['total_institutions']}")
```

### Example 3: API Integration

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Search
response = requests.post(
    f"{BASE_URL}/search/prompt",
    params={
        "query": "Cardiología en Bogotá",
        "limit": 10
    }
)
data = response.json()

print(f"Found: {data['results']['total_count']} institutions")
for inst in data['institutions']:
    print(f"  - {inst['name']} ({inst['city']})")

# Get statistics
response = requests.get(f"{BASE_URL}/database/statistics")
stats = response.json()['statistics']
print(f"\nDatabase has {stats['total_institutions']} institutions")
```

---

## 🏗️ Architecture

```
health_scraper/
├── api/
│   ├── __init__.py
│   └── endpoints.py          # FastAPI routes
├── database/
│   ├── __init__.py
│   ├── models.py             # SQLAlchemy ORM models
│   └── service.py            # Database operations
├── models/
│   ├── __init__.py
│   └── institution.py        # Pydantic models
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py       # Main scraping logic
│   └── social_media_scraper.py
├── services/
│   ├── __init__.py
│   └── search_service.py     # Natural language search
├── utils/
│   ├── __init__.py
│   └── text_processor.py     # Text cleaning utilities
└── config.py                 # Configuration management
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## ⚖️ Legal Considerations

- Respect robots.txt and website terms of service
- Use appropriate rate limiting
- This tool is for legitimate business purposes only
- Ensure compliance with data protection regulations (Ley 1581 de 2012 in Colombia)

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 📧 Support

For questions or issues, please open a GitHub issue or contact the development team.
