# CHANGELOG.md — Scrapper_Salud / Ai Médic CRM
 
All notable changes to this project will be documented here.  
Format: `[TYPE] Description — Author — Date`
Types: `SPEC | FEAT | FIX | TEST | DOCS | REFACTOR`
 
---
 
## Unreleased
 
### SPEC
- Added SPEC.md with full architecture contract for CRM + Zoho + HubSpot integration
- Defined Layer A (REPS/scraper) vs Layer B (CRM/pipeline) boundary
- Specified pipeline state machine: Frío→Contactado→Conectado→Negociación→Cerrado
- Defined all environment variables, table schemas, and API contracts
 
---
 
## [0.1.0] — 2026-03-16
 
### Initial repo state
- FastAPI backend with scraper endpoints
- SQLAlchemy models: InstitutionDB, ContactDB, SocialMediaDB
- Gemini Vision AI extraction from images
- Natural language search with QueryParser
- Azure Container Apps deployment scripts
- GitHub Actions CI/CD pipeline
- CSV/Excel export
- API key authentication