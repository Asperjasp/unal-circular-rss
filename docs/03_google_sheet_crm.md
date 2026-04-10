# Google Sheet CRM — Estructura y Sincronización

## Identificación

| Campo | Valor |
|---|---|
| Sheet ID | `1jBcTaANZTubNk3FWMnLdHFHyZhD31WTYIXe38g7eo9g` |
| URL | https://docs.google.com/spreadsheets/d/1jBcTaANZTubNk3FWMnLdHFHyZhD31WTYIXe38g7eo9g |
| Cuenta propietaria | camilo.daza@aimedic.com.co |
| Nombre en Drive | `aimedic_crm` |
| Servicio en código | `health_scraper/integrations/sheets_service.py` |

---

## Tabs (Pestañas)

### 1. Contacts
La hoja más importante. Un contacto = una persona.

**Estructura de filas:**
- Fila 1-2: Títulos / branding (no tocar)
- Fila 3: Headers de columnas
- Fila 4+: Datos

**Columnas de identidad (manuales):**

| Columna | Descripción |
|---|---|
| `contact_id` | ID único: `C-000000001`, `C-000000002`, ... |
| `First Name` | Nombre |
| `Last Name` | Apellido |
| `Email` | Email de negocio (columna más importante para cadencias) |
| `Phone` | Teléfono |
| `LinkedIn URL` | URL del perfil LinkedIn |
| `LinkedIn Connection Date` | Fecha de conexión |
| `Business` | Nombre de la empresa (referencia a tab Businesses) |

**Columnas agenticas (escritas por los agentes):**

| Columna | Valores posibles | Descripción |
|---|---|---|
| `agent_status` | `pending` / `enriching` / `contacted` / `replied` / `converted` / `skip` | Estado actual en el flujo |
| `last_agent_action` | texto libre | Última acción ejecutada (ej. "M1 CAMILO_V1 sent via Zoho") |
| `agent_session_ref` | session ID / run ID | Trazabilidad de qué sesión hizo qué |
| `email_m1_sent_at` | ISO timestamp | Cuándo se envió M1 |
| `email_m2_sent_at` | ISO timestamp | Cuándo se envió M2 |
| `email_m3_sent_at` | ISO timestamp | Cuándo se envió M3 |
| `zoho_message_id` | string | ID del mensaje en Zoho Mail |
| `data_source` | `manual` / `agent_enriched` / `zoho_sync` / `linkedin_scrape` | Origen del dato |
| `last_touched_at` | ISO timestamp | Última vez que un agente escribió en esta fila |

**Regla de escritura:** Los agentes NUNCA sobreescriben columnas no-agenticas. Solo tocan las columnas de la lista de arriba.

### 2. Businesses
Una fila = una empresa/institución.

| Columna clave | Descripción |
|---|---|
| `Business ID` | `B-000000001`, ... |
| `Business Name` | Nombre legal |
| `NIT` | NIT colombiano |
| `Type` | IPS / EPS / LAB / PHARMA / ASEGURADORA |
| `City` | Ciudad |
| `Department` | Departamento |
| `Website` | URL |
| `LinkedIn Company` | Página LinkedIn |
| `ICP Score` | 1-5 — qué tan bueno es el perfil para AI Medic |

### 3. Deals
Pipeline de oportunidades comerciales.

| Columna clave | Descripción |
|---|---|
| `Deal ID` | `D-000000001`, ... |
| `Business` | Empresa relacionada |
| `Stage` | Etapa del pipeline (mapea a Azure stages) |
| `MRR` | MRR estimado en COP |
| `Responsable` | Dueño del deal |
| `Linear Issue` | AIM-XXX para trazabilidad |
| `Zoho Deal ID` | ID en Zoho CRM |

### 4. Interactions
Log de todos los touchpoints. Append-only (solo se agregan filas, nunca se editan).

| Columna | Descripción |
|---|---|
| `log_id` | `I-001`, `I-002`, ... |
| `Date` | Fecha (YYYY-MM-DD) |
| `Contact` | Nombre o email del contacto |
| `Business` | Empresa |
| `Channel` | Email Zoho / LinkedIn / WhatsApp / Llamada / Reunión |
| `Direction` | Outbound / Inbound |
| `Responsable` | Alejandro / Agent1 / Agent2 |
| `Deal ID` | D-XXX si aplica |
| `Summary` | Descripción del touchpoint |
| `Next Step` | Qué sigue |

### 5. Schema Map (referencia)
Tab de documentación interna del Sheet — mapeo de columnas y su significado.

### 6. LI_Raw
Datos crudos de LinkedIn scraping antes de ser procesados y normalizados.

### 7. Reporte Semanal
Dashboard manual de métricas semanales por ciclo de prospección.

---

## Cómo usa el Código el Sheet

### Leer contactos para envío (`get_contacts_for_sending`)
```python
svc = SheetsService.from_service_account("google_service_account.json")
# Devuelve contactos con email, agent_status != contacted/replied/skip, sin m1_sent_at
prospects = svc.get_contacts_for_sending(limit=40)
```

### Marcar contactado (`mark_contacted`)
```python
# Después de enviar M1 via Zoho:
svc.mark_contacted(
    email="dir.administrativa@cemde.com",
    zoho_message_id="abc123",
    step=1,
    session_ref="session-2026-04-06",
    action="M1 CAMILO_V1 sent"
)
```

### Registrar interacción (`log_interaction`)
```python
svc.log_interaction(
    contact="dir.administrativa@cemde.com",
    business="CEMDE",
    channel="Email Zoho",
    direction="Outbound",
    summary="M1 CAMILO_V1 enviado",
    next_step="Esperar 4 días para M2"
)
```

### Agregar columnas agenticas (primera vez)
```python
# Solo necesario una vez al configurar el Sheet
result = svc.ensure_agent_columns(dry_run=True)  # preview
result = svc.ensure_agent_columns()               # ejecutar
# Returns: {"added": [...], "existing": [...]}
```

---

## Sincronización Bidireccional con Zoho CRM

```
Google Sheet  ←──────────────────────────────────────────►  Zoho CRM
              
 Contacts tab                                              Leads module
   contact_id ─────────────────────────────────────────► zoho_lead_id
   agent_status ───── Agent 2 sync ──────────────────────► Lead Status
   email_m1_sent_at ──────────────────────────────────────► m1_sent_date
   zoho_message_id ◄─────────────────────────────────────── message_id
   
 Businesses tab                                           Accounts module
   Business ID ──────────────────────────────────────────► Account ID
   
 Deals tab                                                Deals module
   Deal ID ──────────────────────────────────────────────► Zoho Deal ID
   Stage ──────────── Agent 2 sync ──────────────────────► Stage
```

**Dirección de escritura:**
- Sheet → Zoho: Agent 2 sincroniza cambios de `agent_status` hacia Zoho
- Zoho → Sheet: Agent 2 lee replies/bounces desde Zoho y actualiza `agent_status = replied`

---

## Setup de Service Account

Para que los agentes accedan al Sheet se necesita una Google Service Account:

1. Crear project en Google Cloud Console
2. Habilitar Google Sheets API y Google Drive API
3. Crear Service Account → descargar JSON
4. Compartir el Sheet con el email de la service account (editor)
5. Guardar JSON como `google_service_account.json` en la raíz del proyecto

Ver setup completo: [docs/06_setup_and_credentials.md](06_setup_and_credentials.md)
