# Scrapper Salud — AI Medic Growth Engine (SEMG)

> **Proyecto:** SEMG — Sales Engine & Marketing Growth | **Equipo:** AI Medic

---

## Session Reference

| Campo | Valor |
|---|---|
| Fecha de última sesión | 2026-04-06 |
| Directorio | `SEMG-Growth_Sales_Engine_Marketing_Growth/Scrapper_Salud` |
| Proyecto Linear | [Onboarding Equipos Técnicos y de Growth](https://linear.app/aimedic/project/onboarding-a-equipos-tecnicos-y-de-growth-b47d7f75c09b/overview) |
| Issue referencia | [AIM-326 — CEMDE (Prospeccion Ciclo #8)](https://linear.app/aimedic/issue/AIM-326/centro-de-medicina-del-ejercicio-y-rehabilitacion-cardiaca-sas-cemde) |
| Google Sheet CRM | [aimedic_crm](https://docs.google.com/spreadsheets/d/1jBcTaANZTubNk3FWMnLdHFHyZhD31WTYIXe38g7eo9g/edit?gid=202554457#gid=202554457) — cuenta: camilo.daza@aimedic.com.co |

> Para retomar: abre Claude Code en este directorio y referencia este README. Busca en historial Claude.ai por fecha 2026-04-06 y proyecto `Scrapper_Salud`.

---

## SEMG Agent System — Documentación

| Archivo | Descripción |
|---|---|
| [docs/01_architecture.md](docs/01_architecture.md) | Arquitectura de dos agentes: Outreach vs Analytics |
| [docs/02_status_mapping.md](docs/02_status_mapping.md) | Mapeo canónico Linear ↔ Zoho ↔ Azure |
| [docs/03_google_sheet_crm.md](docs/03_google_sheet_crm.md) | Estructura del Google Sheet, columnas agenticas, tabs |
| [docs/04_zoho_crm_sync.md](docs/04_zoho_crm_sync.md) | Sincronización Zoho CRM: leads, cadencias, autenticación |
| [docs/05_prospecting_workflow.md](docs/05_prospecting_workflow.md) | Flujo prospección ciclo (patrón AIM-326) |
| [docs/06_setup_and_credentials.md](docs/06_setup_and_credentials.md) | Variables de entorno, credenciales, Zoho MCP setup |
| [docs/07_prospecting_plan.md](docs/07_prospecting_plan.md) | Plan completo: 50 empresas/día, segmentación, ciclo 9 toques, anti-spam |

---

# 🔍 People Research & Outreach Tool

A personal workflow tool that turns **casual discoveries** (Twitter, PDFs, conferences) into **researched profiles** and **ready-to-send outreach messages** — powered by Perplexity AI for research and Gemini for drafting.

---

## 📚 Documentación de Configuración

¿Primera vez aquí? **Empieza con una de estas guías:**

- **🚀 [Setup Rápido (5 minutos)](SETUP_RAPIDO.md)** - Lo mínimo para empezar YA
- **📖 [Guía Completa de Configuración](GUIA_CONFIGURACION.md)** - Paso a paso detallado de TODAS las integraciones
- **🔧 Verificar tu configuración**: Ejecuta `python check_config.py`

**Integraciones disponibles:**
- ✅ Google Gemini AI (redacción)
- ✅ Perplexity AI (investigación)
- ✅ HubSpot CRM
- ✅ Linear (project management)
- ✅ Zoho Email
- ✅ Google Calendar

---

## Your Workflow

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  1. DISCOVER     │────▶│  2. RESEARCH     │────▶│  3. DRAFT        │────▶│  4. CONTACT      │
│                  │     │                  │     │                  │     │                  │
│  Twitter, PDFs,  │     │  Perplexity API  │     │  Gemini drafts   │     │  Copy-paste to   │
│  conferences,    │     │  finds everything│     │  personalized    │     │  LinkedIn, Email, │
│  articles...     │     │  about them      │     │  messages using  │     │  Twitter, etc.   │
│                  │     │                  │     │  YOUR biz context│     │                  │
└─────────────────┘     └──────────────────┘     └──────────────────┘     └─────────────────┘
```

**One API call does it all:** `/api/v1/integrations/pipeline/research-and-draft`

---

## Quick Start

### 1. Install

```bash
git clone <repository-url>
cd Scrapper_Salud
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Keys

**Opción Rápida (5 minutos):**
```bash
# Copia el template
cp .env.template .env

# Edita .env con tus API keys (solo las obligatorias para empezar)
# - GOOGLE_AI_STUDIO (https://aistudio.google.com/apikey)
# - PERPLEXITY_API_KEY (https://www.perplexity.ai/settings/api)
# - YOUR_NAME y YOUR_ROLE

# Verifica que todo esté bien
python check_config.py
```

**¿Necesitas ayuda?** → Lee el [Setup Rápido](SETUP_RAPIDO.md) o la [Guía Completa](GUIA_CONFIGURACION.md)

### 3. Start

```bash
python main.py
```

Open: http://localhost:8000/docs — full interactive API documentation.

---

## API Endpoints — Your Daily Workflow

### Full Pipeline (recommended)

**POST** `/api/v1/integrations/pipeline/research-and-draft`

One call that researches + drafts. This is what you'll use most.

```bash
curl -X POST "http://localhost:8000/api/v1/integrations/pipeline/research-and-draft" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. Juan Pérez",
    "context": "Saw on Twitter discussing AI adoption in Colombian hospitals",
    "twitter_handle": "juanperezmd",
    "company": "Hospital San Ignacio",
    "tone": "warm",
    "language": "es",
    "goal": "Explore partnership for AI diagnostic tools"
  }'
```

**Response:**
```json
{
  "research": {
    "name": "Dr. Juan Pérez",
    "title": "Director de Innovación",
    "company": "Hospital San Ignacio",
    "bio": "Médico especialista en informática clínica...",
    "linkedin_url": "https://linkedin.com/in/juanperezmd",
    "interests": ["AI in healthcare", "digital health", "telemedicine"],
    "mutual_relevance": "Decision-maker at a major hospital actively exploring AI...",
    "contact_channels": ["LinkedIn", "Twitter", "Email"]
  },
  "outreach": {
    "drafts": [
      {
        "channel": "linkedin",
        "subject": "",
        "body": "Hola Dr. Pérez, vi su thread sobre adopción de IA en hospitales colombianos...",
        "notes": "Send connection request first, wait 2 days, then InMail"
      },
      {
        "channel": "email",
        "subject": "Re: IA diagnóstica en Hospital San Ignacio",
        "body": "Dr. Pérez, ...",
        "notes": "Best sent Tuesday-Thursday morning"
      }
    ],
    "strategy_notes": "Approach via LinkedIn first since he's active there...",
    "recommended_sequence": ["linkedin", "twitter", "email"]
  }
}
```

### Step 1 only: Research a Person

**POST** `/api/v1/integrations/research/person`

Just research without drafting. Useful when you want to evaluate relevance first.

```bash
curl -X POST "http://localhost:8000/api/v1/integrations/research/person" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "María García",
    "twitter_handle": "mariagarcia_tech",
    "context": "Speaker at Health-Tech Bogotá 2026"
  }'
```

### Step 2 only: Draft Outreach

**POST** `/api/v1/integrations/outreach/draft`

Draft messages from already-researched data. Useful for re-drafting with different tone/channels.

```bash
curl -X POST "http://localhost:8000/api/v1/integrations/outreach/draft" \
  -H "Content-Type: application/json" \
  -d '{
    "person_data": { "...output from /research/person..." },
    "channels": ["email", "linkedin"],
    "tone": "casual",
    "language": "es",
    "goal": "Invite to a coffee chat about health-tech"
  }'
```

### Batch Research

**POST** `/api/v1/integrations/research/person/batch`

Research multiple people at once (e.g., conference speaker list).

```bash
curl -X POST "http://localhost:8000/api/v1/integrations/research/person/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "people": [
      {"name": "Dr. Juan Pérez", "company": "Hospital San Ignacio"},
      {"name": "Ana López", "twitter_handle": "analopez_health"},
      {"name": "Carlos Ruiz", "linkedin_url": "https://linkedin.com/in/carlosruiz"}
    ],
    "business_context": "health-tech company selling AI diagnostic tools"
  }'
```

---

## All Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/integrations/pipeline/research-and-draft` | POST | **Full pipeline**: Research + Draft in one call |
| `/api/v1/integrations/research/person` | POST | Research a person (Perplexity) |
| `/api/v1/integrations/research/person/batch` | POST | Research multiple people |
| `/api/v1/integrations/outreach/draft` | POST | Draft outreach messages (Gemini) |
| `/api/v1/integrations/enrich/company` | POST | Enrich company data with AI |
| `/api/v1/integrations/status` | GET | Check which integrations are active |
| `/api/v1/integrations/workflow/upload-excel` | POST | Upload Excel → Enrich → HubSpot + Linear |
| `/api/v1/integrations/workflow/single-company` | POST | Single company through full pipeline |
| `/api/v1/integrations/hubspot/*` | GET/POST | HubSpot CRM operations |
| `/api/v1/integrations/linear/*` | GET/POST | Linear project management |
| `/api/v1/integrations/calendar/*` | GET/POST | Google Calendar operations |
| `/api/v1/search/prompt` | POST | Natural language search for institutions |
| `/api/v1/database/institutions` | GET | Browse stored institutions |
| `/api/v1/database/statistics` | GET | Database stats |
| `/docs` | GET | Interactive Swagger API docs |

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PERPLEXITY_API_KEY` | **Yes** (for research) | Perplexity API key — [get one here](https://www.perplexity.ai/settings/api) |
| `GOOGLE_AI_STUDIO` | **Yes** (for drafting) | Gemini API key — [get one here](https://aistudio.google.com/apikey) |
| `BUSINESS_NAME` | Recommended | Your company name (used in outreach) |
| `BUSINESS_DESCRIPTION` | Recommended | What your company does (for relevance + drafting) |
| `YOUR_NAME` | Recommended | Your name (appears in drafted messages) |
| `YOUR_ROLE` | Recommended | Your role/title |
| `API_KEY` | Optional | Protect your API with a key |
| `HUBSPOT_ACCESS_TOKEN` | Optional | HubSpot CRM integration |
| `LINEAR_API_KEY` | Optional | Linear project management |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Optional | Google Calendar integration |

### How the AI Services Work Together

| Step | Service | API | What it does |
|------|---------|-----|-------------|
| **Research** | Perplexity (sonar) | `PERPLEXITY_API_KEY` | Real-time web search for person info, LinkedIn, background |
| **Drafting** | Google Gemini | `GOOGLE_AI_STUDIO` | Writes personalized messages using YOUR business context |
| **Fallback** | Gemini also researches | `GOOGLE_AI_STUDIO` | If no Perplexity key, Gemini does both (less real-time data) |

---

## Outreach Options

### Channels
- `email` — Professional email (max ~150 words)
- `linkedin` — Connection request (300 chars) or InMail
- `twitter` — DM (280 chars)
- `whatsapp` — Brief direct message (100 words)

### Tones
- `professional` — Formal business tone
- `casual` — Friendly, conversational
- `warm` — Personal and approachable
- `direct` — Straight to the point

### Languages
- `es` — Spanish (default)
- `en` — English

---

## Architecture

```
health_scraper/
├── integrations/
│   ├── person_research_service.py    ← NEW: Perplexity person research
│   ├── outreach_drafting_service.py  ← NEW: Gemini outreach drafting
│   ├── integration_endpoints.py      ← API routes for all integrations
│   ├── enrichment_service.py         ← Company enrichment (Perplexity/Gemini)
│   ├── workflow_orchestrator.py      ← Excel → HubSpot → Linear → Calendar
│   ├── hubspot_service.py            ← HubSpot CRM integration
│   ├── linear_service.py             ← Linear project management
│   └── calendar_service.py           ← Google Calendar
├── api/
│   └── endpoints.py                  ← Core scraping/search API routes
├── database/
│   ├── models.py                     ← SQLAlchemy ORM models
│   └── service.py                    ← Database CRUD operations
├── models/
│   └── institution.py                ← Pydantic data models
├── scrapers/
│   ├── base_scraper.py               ← Web scraping engine
│   ├── social_media_scraper.py       ← Social media profile scraper
│   └── starter_scraper.py            ← Sample data collector
├── services/
│   ├── search_service.py             ← Natural language search
│   └── vision_service.py             ← Vision AI features
├── utils/
│   └── text_processor.py             ← Text cleaning utilities
└── config.py                         ← Configuration management
```

### Key Files Changed (for your reference)

| File | What Changed |
|------|-------------|
| `health_scraper/integrations/person_research_service.py` | **NEW** — Perplexity-powered person research from minimal input |
| `health_scraper/integrations/outreach_drafting_service.py` | **NEW** — Gemini-powered personalized outreach message drafting |
| `health_scraper/integrations/integration_endpoints.py` | Added `/research/person`, `/outreach/draft`, `/pipeline/research-and-draft` endpoints |
| `health_scraper/integrations/__init__.py` | Updated module docs |
| `health_scraper/config.py` | Added `BUSINESS_NAME`, `BUSINESS_DESCRIPTION`, `YOUR_NAME`, `YOUR_ROLE` |
| `.env.example` | Reorganized with workflow-focused sections, added new variables |
| `README.md` | Complete rewrite focused on your workflow |

---

## Original Features (still available)

The tool still includes all the original health institution scraping capabilities:

- **Web Scraping**: 40+ institution types, 50+ medical specialties
- **Natural Language Search**: Search in Spanish/English for institutions
- **Database**: SQLite/PostgreSQL with deduplication
- **Company Enrichment**: Enrich company data via AI
- **Excel Upload Workflow**: Upload → Enrich → HubSpot → Linear → Calendar
- **HubSpot CRM**: Create/search companies and contacts
- **Linear**: Create tracking tasks for commercial follow-up
- **Google Calendar**: Schedule follow-up meetings
- **Export**: CSV and Excel download of all data

See `/docs` for the complete API reference.

---

## License

MIT License
