# Arquitectura — Dos Agentes SEMG

## Visión General

El sistema opera con **dos agentes independientes** que se comunican a través del Google Sheet como fuente de verdad compartida.

```
┌──────────────────────────────────────────────────────────────────┐
│                      SEMG AGENT SYSTEM                           │
│                                                                  │
│  ┌─────────────────────────┐    ┌──────────────────────────────┐ │
│  │   AGENT 1               │    │   AGENT 2                    │ │
│  │   Prospecting &         │    │   Analytics & Safety         │ │
│  │   Outreach Agent        │◄──►│   (Data Watcher)             │ │
│  │                         │    │                              │ │
│  │  Herramientas:          │    │  Herramientas:               │ │
│  │  - Perplexity/Gemini    │    │  - Google Sheets (R/W)       │ │
│  │  - Zoho Mail API        │    │  - Zoho CRM sync             │ │
│  │  - LinkedIn outreach    │    │  - Analytics dashboard       │ │
│  │  - CadenceEngine        │    │  - Linear status sync        │ │
│  │  - Linear create issue  │    │  - Enrich missing data       │ │
│  │  - Template renderer    │    │  - Validate antes de envio   │ │
│  └─────────────────────────┘    └──────────────────────────────┘ │
│              │                               │                    │
│              └──────────────┬────────────────┘                   │
│                             ▼                                    │
│              ┌──────────────────────────┐                        │
│              │   FUENTE DE VERDAD       │                        │
│              │   Google Sheet CRM       │                        │
│              │   + Zoho CRM (espejo)    │                        │
│              └──────────────────────────┘                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Agent 1 — Prospecting & Outreach

**Responsabilidad:** Identificar prospectos, enriquecer datos, ejecutar secuencias de contacto.

### Capacidades

| Capacidad | Servicio | Archivo |
|---|---|---|
| Research de empresa/persona | Perplexity API | `enrichment_service.py`, `person_research_service.py` |
| Redacción de mensajes M1/M2/M3 | Gemini AI | `outreach_drafting_service.py`, `outreach_templates.py` |
| Envío de emails | Zoho Mail API | `zoho_email_service.py` |
| Gestión de secuencias (cadencias) | SQLite local | `zoho_cadence_service.py` |
| Outreach LinkedIn | LinkedIn API | `linkedin_outreach_service.py` |
| Crear issues Linear | Linear GraphQL | `linear_service.py` |
| Inscribir contactos a secuencias | CadenceEngine | `zoho_cadence_service.py` |

### Flujo principal (por ciclo de prospección)

```
1. Recibir empresa objetivo (ej. CEMDE desde AIM-326)
2. Research con Perplexity → obtener contactos, emails, roles
3. Enriquecer cada contacto (LinkedIn, cargo, teléfono)
4. Escribir en Google Sheet (columnas agent_status, data_source)
5. Separar por canal:
   a. Tiene email → enqueue en CadenceEngine → M1 inmediato
   b. Tiene LinkedIn → linkedin_outreach_service
   c. Solo teléfono → cola para WhatsApp/llamada manual
6. Crear issue Linear con estructura AIM-326 (si es empresa nueva)
7. Registrar en Interactions tab del Sheet
```

### Límites operacionales

- **40 emails/día** (MAX_SENDS_PER_DAY en `zoho_cadence_service.py:41`)
- **M1 → M2:** 4 días de espera
- **M2 → M3:** 9 días desde M1
- Si hay reply: pausa automática (`mark_replied`)

---

## Agent 2 — Analytics & Safety (Data Watcher)

**Responsabilidad:** Mantener la integridad de datos, sincronizar CRMs, analizar métricas de canal.

### Capacidades

| Capacidad | Servicio | Archivo |
|---|---|---|
| Leer/escribir Google Sheet | gspread | `sheets_service.py` |
| Sincronizar con Zoho CRM | Zoho CRM API | `zoho_cadence_service.py` + MCP |
| Analytics pipeline | PipelineService | `analytics_service.py` |
| KPIs y dashboards | Chart.js data | `analytics_service.py` |
| Enriquecer datos faltantes | Perplexity/Gemini | `enrichment_service.py` |
| Sincronizar estados Linear | Linear MCP | `linear_service.py` |
| Validar antes de envío | SheetsService | `sheets_service.py` |

### Responsabilidades específicas

1. **Data completeness:** Detectar filas con nombre pero sin email, o email sin LinkedIn, y lanzar enriquecimiento
2. **Zoho sync:** Cuando Agent 1 marca un contacto como `contacted` en el Sheet, Agent 2 actualiza el Lead en Zoho CRM al estado correspondiente
3. **Linear sync:** Cuando un Lead en Zoho cambia de estado, Agent 2 mueve el issue de Linear al status correcto (ver `docs/02_status_mapping.md`)
4. **Canal analytics:** Mide tasas de apertura por canal (email vs LinkedIn vs WhatsApp), retroalimenta a Agent 1 para priorizar canales
5. **Safety check:** Antes de que Agent 1 envíe un email, Agent 2 verifica que el contacto no esté ya en una secuencia activa en Zoho

---

## Comunicación entre Agentes

El canal de comunicación es el **Google Sheet** (no hay API directa entre agentes):

```
Agent 1 escribe:          Agent 2 lee:
  agent_status              agent_status → sync a Zoho
  last_agent_action         last_touched_at → detectar stale
  email_m1_sent_at          zoho_message_id → confirmar envío
  zoho_message_id           data_source → trigger enrich

Agent 2 escribe:          Agent 1 lee:
  agent_status='skip'       skip → no enviar
  data_source='enriched'    enriched data → usar en template
  last_agent_action         log para auditoría
```

Columnas agenticas en el Sheet → ver `docs/03_google_sheet_crm.md`

---

## Archivos Clave por Agente

### Agent 1
```
health_scraper/integrations/
├── zoho_cadence_service.py      # motor principal de secuencias
├── zoho_email_service.py        # envío via Zoho Mail API
├── outreach_templates.py        # plantillas M1/M2/M3
├── outreach_drafting_service.py # redacción con Gemini
├── person_research_service.py   # research con Perplexity
├── linkedin_outreach_service.py # outreach LinkedIn
└── linear_service.py            # crear/actualizar issues
```

### Agent 2
```
health_scraper/integrations/
├── sheets_service.py            # R/W Google Sheet (fuente de verdad)
├── analytics_service.py         # KPIs, funnel, dashboards
├── enrichment_service.py        # enriquecer datos faltantes
└── prospect_intel_service.py    # intel de prospectos
```

### Compartido
```
health_scraper/integrations/
├── workflow_orchestrator.py     # orquestador Excel→HubSpot→Linear
└── pipeline_endpoints.py        # API endpoints del pipeline
```
