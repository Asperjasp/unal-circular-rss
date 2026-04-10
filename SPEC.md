# SPEC.md — Ai Médic Scrapper_Salud
> **Contract**: Before writing any code, the relevant section of this file must describe the expected behavior.  
> **Rule**: If behavior is not in SPEC.md, it does not exist yet. Add the spec first, then the code.  
> **Owner**: Camilo / Alejandro  
> **Last updated**: 2026-03-16

---

## 1. System Overview

Scrapper_Salud is the **data + CRM engine** for Ai Médic prospecting.  
It has two layers that must never be mixed:

```
Layer A — REPS / Discovery Layer
  Purpose: Find and store health institutions (IPS, EPS, labs)
  Source:  REPS government files, web scraping, Gemini Vision
  Tables:  institutions, contacts (scraped), social_media, search_queries
  Rule:    READ-ONLY after import. Never mutate REPS data via CRM actions.

Layer B — CRM / Pipeline Layer  
  Purpose: Track prospects, deals, interactions, and message sequences
  Source:  Manual entry, HubSpot sync, Zoho Mail BCC
  Tables:  crm_contact, crm_deal, crm_interaccion, crm_message_log
  Rule:    Always links to Layer A via institution_id (FK → institutions.id)
```

---

## 2. Database Schema Contract

### 2.1 Existing Tables (Layer A — DO NOT MODIFY)
These tables are owned by the scraper layer. CRM layer reads them but never writes.

```
institutions     ← HealthInstitution scraped records (unique_hash dedup)
contacts         ← Scraped contact info (phone/email from websites)
social_media     ← LinkedIn, Facebook, Instagram profiles
search_queries   ← Query analytics log
scraping_jobs    ← Batch job tracking
```

### 2.2 New Tables (Layer B — CRM)

```sql
-- A person (survives job changes via crm_contact_company bridge)
crm_contact (
  id              UUID PK,
  first_name      TEXT NOT NULL,
  last_name       TEXT,
  email           TEXT UNIQUE,
  telefono        TEXT,
  linkedin_url    TEXT,
  fuente          TEXT,          -- LinkedIn/Perplexity/Referido/HubSpot
  hubspot_id      TEXT,          -- HubSpot Contact ID
  hs_last_sync    DATETIME,
  created_at      DATETIME DEFAULT now(),
  updated_at      DATETIME DEFAULT now()
)

-- N:N bridge: one person can work at multiple institutions over time
crm_contact_company (
  id              UUID PK,
  contact_id      UUID FK → crm_contact.id,
  institution_id  INTEGER FK → institutions.id,
  cargo           TEXT,
  es_actual       BOOLEAN DEFAULT TRUE,
  fecha_inicio    DATE,
  fecha_fin       DATE           -- NULL = current role
)

-- A sales opportunity
crm_deal (
  id              UUID PK,
  institution_id  INTEGER FK → institutions.id,
  contact_id      UUID FK → crm_contact.id,
  producto        TEXT NOT NULL,  -- P1_OPERATOR | P2_CONNECT | AMBOS
  stage           TEXT NOT NULL DEFAULT 'Frío',
  mrr_usd         DECIMAL(10,2) DEFAULT 0,
  responsable     TEXT,           -- Camilo | Alejandro
  notas           TEXT,
  hubspot_deal_id TEXT,
  hs_last_sync    DATETIME,
  expected_close  DATE,
  fecha_cierre    DATE,
  win_loss        TEXT,           -- Won | Lost | NULL (open)
  created_at      DATETIME DEFAULT now(),
  updated_at      DATETIME DEFAULT now(),
  CONSTRAINT chk_stage CHECK (stage IN
    ('Frío','Contactado','Conectado','En Negociación','Cerrado')),
  CONSTRAINT chk_producto CHECK (producto IN
    ('P1_OPERATOR','P2_CONNECT','AMBOS'))
)

-- Every touchpoint (email, call, LinkedIn, WhatsApp)
crm_interaccion (
  id              UUID PK,
  contact_id      UUID FK → crm_contact.id,
  institution_id  INTEGER FK → institutions.id,
  deal_id         UUID FK → crm_deal.id,
  canal           TEXT,   -- Email_Zoho | LinkedIn | Llamada | WhatsApp
  direccion       TEXT,   -- Inbound | Outbound
  responsable     TEXT,
  resumen         TEXT,
  next_step       TEXT,
  mensaje_tipo    TEXT,   -- M1 | M2 | M3 | NULL (manual)
  hubspot_act_id  TEXT,
  fecha           DATETIME DEFAULT now()
)

-- Sent message log (tracks M1/M2/M3 sequences)
crm_message_log (
  id              UUID PK,
  deal_id         UUID FK → crm_deal.id,
  contact_id      UUID FK → crm_contact.id,
  template_name   TEXT NOT NULL,  -- M1_EMAIL | M1_LINKEDIN | M2_EMAIL | etc.
  canal           TEXT NOT NULL,
  subject         TEXT,
  body            TEXT,
  variables_used  JSON,           -- {"empresa": "Areté IPS", "dolor": "RIPS"}
  sent_at         DATETIME,
  zoho_message_id TEXT,
  status          TEXT DEFAULT 'sent'  -- sent | bounced | opened | replied
)
```

### 2.3 Pipeline State Machine

Valid stage transitions (enforce in code, reject invalid ones):

```
Frío → Contactado         (first touch sent)
Contactado → Conectado    (prospect responded or accepted)
Conectado → En Negociación (demo done, proposal sent)
En Negociación → Cerrado  (contract signed = Won, or dropped = Lost)
ANY → Frío                (re-engagement after 90+ days silence)
```

---

## 3. Integration Contracts

### 3.1 Zoho Mail Integration (`integrations/zoho_mail.py`)

**Inputs required in `.env`:**
```
ZOHO_CLIENT_ID
ZOHO_CLIENT_SECRET
ZOHO_ACCESS_TOKEN    ← auto-refreshed by zoho_auth.py
ZOHO_REFRESH_TOKEN
ZOHO_ACCOUNT_ID
ZOHO_FROM_EMAIL
```

**Expected behavior:**
- `send_template(to, template_name, variables, contact_id, deal_id)` → sends email, logs to `crm_message_log` and `crm_interaccion`
- `get_templates()` → returns list of Zoho templates by name
- Token refresh: if access token expired (1hr), auto-refresh using refresh_token before sending
- Never raise on send failure — log the error to `crm_message_log.status = 'failed'` instead

**Template variable contract:**
```python
# All templates must accept these base variables:
BASE_VARS = {
    "empresa":       str,   # Institution name
    "ciudad":        str,   # City
    "responsable":   str,   # Camilo | Alejandro
}
# M1 additional:
M1_VARS = {"dolor": str, "especialidad": str}
# M2 additional:
M2_VARS = {"caso_similar": str}
# M3: no additional vars
```

### 3.2 HubSpot Sync (`integrations/hubspot_sync.py`)

**Sync direction:** Azure SQL → HubSpot (SQL is source of truth)  
**Webhook direction:** HubSpot → Azure SQL (deal stage changes come back)

**Object mapping:**
```
crm_contact     → HubSpot Contact
institutions    → HubSpot Company
crm_deal        → HubSpot Deal
crm_interaccion → HubSpot Activity
```

**Custom HubSpot properties required (create in HubSpot portal first):**
```
Company: nit_colombia (text), icp_segment (dropdown), tipo_entidad (dropdown)
Contact: fuente_aimedic (dropdown)
```

**Sync rules:**
- Upsert by email for contacts, by NIT for companies
- Never delete from HubSpot via sync (only create/update)
- Write HubSpot ID back to SQL after upsert (hubspot_id field)
- If HubSpot API returns 429 (rate limit), wait 10s and retry once

### 3.3 Azure SQL Migration

Current: SQLite via `DATABASE_URL=sqlite:///health_institutions.db`  
Target: Azure SQL via `DATABASE_URL=mssql+pyodbc://...`

**No code changes required** — SQLAlchemy handles the abstraction.  
**Migration steps:**
1. Change `DATABASE_URL` in `.env`
2. Run `python -c "from health_scrapper.database.models import Base, engine; Base.metadata.create_all(engine)"`
3. Run REPS ETL: `python etl/load_reps.py --file IPS20en20colombia_xlsx_1.ods`

---

## 4. API Contract

### 4.1 New CRM Endpoints (add to `api/crm_endpoints.py`)

```
POST   /api/v1/crm/contacts              → create contact + link to institution
GET    /api/v1/crm/contacts              → list with filters (stage, responsable)
PATCH  /api/v1/crm/contacts/{id}         → update contact

POST   /api/v1/crm/deals                 → create deal
GET    /api/v1/crm/deals                 → pipeline view
PATCH  /api/v1/crm/deals/{id}/stage      → advance stage (validates state machine)

POST   /api/v1/crm/interactions          → log touchpoint
GET    /api/v1/crm/interactions/{deal_id} → interaction history

POST   /api/v1/integrations/send-message → send M1/M2/M3 via Zoho
POST   /api/v1/integrations/hubspot-sync → trigger manual sync
POST   /api/v1/integrations/hubspot-webhook → receive stage changes from HubSpot
```

### 4.2 Prospecting Quick-Add Endpoint

```
POST /api/v1/crm/prospect
Body: {
  "institution_name": "Areté IPS",
  "prestador_id": "4427901010",   # optional if known from REPS
  "contact": { "email": "sistemas@areteips.com", "cargo": "TI" },
  "producto": "P1_OPERATOR",
  "responsable": "Alejandro",
  "send_m1": true,
  "m1_variables": { "dolor": "RIPS manuales" }
}
Response: {
  "deal_id": "uuid",
  "contact_id": "uuid",
  "institution_id": 42,
  "message_sent": true,
  "zoho_message_id": "..."
}
```

---

## 5. Testing Contract

### 5.1 Test file locations
```
tests/
├── test_crm_models.py
├── test_zoho_integration.py
├── test_hubspot_sync.py
├── test_pipeline.py
└── test_api_crm.py
```

### 5.2 Tests that must always pass before any merge

```python
def test_invalid_stage_transition_rejected():
    # Frío → En Negociación must raise ValueError

def test_deal_stage_advance():
    # Frío → Contactado must succeed

def test_contact_survives_company_change():
    # Contact row stays, new crm_contact_company added
    # Old row gets es_actual=False, fecha_fin=today

def test_m1_template_variables_filled():
    # All placeholders replaced; missing vars raise ValueError

def test_zoho_token_refresh():
    # Expired token → auto-refresh → send succeeds
```

---

## 6. File Responsibility Map

```
main.py                              ← FastAPI app, routers, middleware
health_scrapper/
  config.py                          ← All env var reading
  api/
    endpoints.py                     ← Scraper endpoints (DO NOT MODIFY)
    crm_endpoints.py                 ← NEW: CRM + integration endpoints
  database/
    models.py                        ← Extend with CRM tables (never delete)
    service.py                       ← Scraper DB ops (DO NOT MODIFY)
    crm_service.py                   ← NEW: CRM CRUD
  models/
    institution.py                   ← Existing Pydantic (DO NOT MODIFY)
    crm.py                           ← NEW: CRM Pydantic models
  scrapers/                          ← DO NOT MODIFY
  services/
    search_service.py                ← DO NOT MODIFY
    vision_service.py                ← DO NOT MODIFY
    pipeline_service.py              ← NEW: stage machine + workflow
  integrations/                      ← NEW
    zoho_mail.py
    zoho_auth.py
    hubspot_sync.py
    azure_blob.py
  utils/
    text_processor.py                ← DO NOT MODIFY
etl/
  load_reps.py                       ← REPS ODS → Azure SQL
  load_crm_excel.py                  ← Prospecting workbook → Azure SQL
  zoho_auth.py                       ← One-time OAuth setup
tests/
SPEC.md                              ← THIS FILE
CHANGELOG.md
.env                                 ← Never committed
.env.example                         ← Committed template
```

---

## 7. Environment Variables (Full List)

```bash
# Scraper
DATABASE_URL=sqlite:///health_institutions.db
SCRAPER_MODE=development
LOG_LEVEL=INFO
RATE_LIMIT_DELAY=2
HEADLESS_MODE=True
SELENIUM_TIMEOUT=30
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=
GOOGLE_AI_STUDIO=

# Azure SQL (production swap)
AZURE_SQL_CONNECTION_STRING=

# Azure Blob
AZURE_STORAGE_CONNECTION_STRING=
BLOB_CONTAINER=reps-raw

# Zoho Mail
ZOHO_CLIENT_ID=
ZOHO_CLIENT_SECRET=
ZOHO_ACCESS_TOKEN=
ZOHO_REFRESH_TOKEN=
ZOHO_ACCOUNT_ID=
ZOHO_FROM_EMAIL=

# HubSpot
HUBSPOT_TOKEN=
HUBSPOT_WEBHOOK_SECRET=
SYNC_INTERVAL_MINUTES=60
```

---

## 8. Development Workflow (Spec-Driven)

```
1. Write spec section in SPEC.md describing expected behavior
2. Write failing test in tests/
3. Write minimum code to pass the test
4. Run full suite — zero failures required
5. Update CHANGELOG.md
6. Commit: [SPEC|FEAT|FIX|TEST|DOCS] description
```

---

## 9. Protected Files (Do Not Modify Without Failing Test)

```
health_scrapper/scrapers/
health_scrapper/services/search_service.py
health_scrapper/services/vision_service.py
health_scrapper/database/models.py     (extend only)
health_scrapper/database/service.py    (extend only)
static/index.html
templates/index.html
Dockerfile
.github/workflows/azure-deploy.yml
```