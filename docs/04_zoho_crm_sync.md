# Zoho CRM — Integración y Sincronización

## Autenticación

### Zoho CRM MCP (Claude Code)

El acceso a Zoho CRM desde Claude Code se hace via MCP connector. **Pendiente autenticar:**

```
1. En Claude Code, escribe: /mcp
2. Selecciona "claude.ai Zoho CRM"
3. Completa el flujo OAuth en el navegador
4. Las herramientas Zoho quedan disponibles automáticamente
```

El servidor MCP es: `https://claude-zohocrm.zohomcp.com/mcp/message`

### Zoho Mail API (para envíos de email)

Usado por `zoho_email_service.py` — requiere credenciales OAuth de Zoho Mail:

```bash
# Variables de entorno necesarias:
ZOHO_CLIENT_ID=...
ZOHO_CLIENT_SECRET=...
ZOHO_REFRESH_TOKEN=...
ZOHO_ACCOUNT_ID=...       # ID de la cuenta en Zoho Mail
ZOHO_FROM_EMAIL=...       # email desde el que se envía
```

Ver setup completo en [docs/06_setup_and_credentials.md](06_setup_and_credentials.md)

---

## Módulos Zoho Relevantes

### Leads
El módulo principal para prospectos que aún no son clientes.

| Campo Zoho | Mapea a Sheet | Mapea a Linear |
|---|---|---|
| `Lead Status` | `agent_status` | Issue status |
| `Lead Source` | `data_source` | Label |
| `First Name` + `Last Name` | `First Name` + `Last Name` | Issue title |
| `Email` | `Email` | — |
| `Phone` | `Phone` | — |
| `Company` | `Business` | — |
| `LinkedIn_URL` (custom) | `LinkedIn URL` | — |
| `linear_issue_id` (custom) | — | Issue identifier |
| `m1_sent_date` (custom) | `email_m1_sent_at` | — |
| `m2_sent_date` (custom) | `email_m2_sent_at` | — |
| `m3_sent_date` (custom) | `email_m3_sent_at` | — |
| `azure_stage` (custom) | — | — |

### Contacts
Para prospectos que ya tienen relación activa (post-reunión).

### Deals
Para oportunidades en negociación.

### Accounts
Para empresas/instituciones (equivalente a `Businesses` tab en el Sheet).

---

## Cadencias de Email (CadenceEngine)

El motor de secuencias está implementado en `zoho_cadence_service.py` con estado local en SQLite (`cadence.db`).

### Estructura de Secuencia

```
Enqueue prospects
     │
     ▼
  M1 (Día 0) — Envío inmediato
     │
     │ ── 4 días de espera
     ▼
  M2 (Día 4) — Follow-up con caso de estudio
     │
     │ ── 5 días más (9 desde M1)
     ▼
  M3 (Día 9) — Breakup email
     │
     ▼
  completed (sin reply) → Agent 2 → Zoho Closed Lost
  replied (en cualquier paso) → pause → humano toma
```

### Templates Disponibles

| Template | Uso | Archivo |
|---|---|---|
| `M1_CONNECT` | M1 para contacto directo (médico/director) | `outreach_templates.py` |
| `M1_OPERATOR` | M1 para área operativa/administrativa | `outreach_templates.py` |
| `M2_EMAIL` | Follow-up Day 4 | `outreach_templates.py` |
| `M3_EMAIL` | Breakup Day 9 | `outreach_templates.py` |

Variables requeridas por templates: `nombre`, `empresa` + variables específicas por template.

Referencias de plantillas en Linear:
- M1: [AIM-74](https://linear.app/aimedic/issue/AIM-74/plantilla-del-m1-mensaje-de-email-con-ejemplos)
- M2: [AIM-71](https://linear.app/aimedic/issue/AIM-71/plantilla-del-m2-mensaje-de-linkedin-con-ejemplos)  
- M3: [AIM-76](https://linear.app/aimedic/issue/AIM-76/plantilla-del-m3-mensaje-de-email-con-ejemplos)

### Uso Programático

```python
from health_scraper.integrations.zoho_cadence_service import CadenceEngine
from health_scraper.integrations.zoho_email_service import ZohoEmailService
from health_scraper.integrations.sheets_service import SheetsService

# Setup
zoho_email = ZohoEmailService(...)
sheets = SheetsService.from_service_account("google_service_account.json")

# Obtener prospectos del Sheet
prospects = sheets.get_contacts_for_sending(limit=40)

# Inicializar motor
engine = CadenceEngine(zoho=zoho_email)

# Inscribir a secuencia
result = engine.enqueue(prospects, m1_template="M1_CONNECT")
print(result)  # {"added": 12, "skipped": 3, "failed": 0}

# Ejecutar envíos pendientes (M1 inmediato, M2/M3 si es tiempo)
summary = engine.process_due()
print(summary)  # {"sent": 5, "failed": 0, "skipped_daily_limit": 0}

# Stats del estado actual
stats = engine.stats()
# {"status_breakdown": {"active": 35, "replied": 3, "completed": 12},
#  "today_sends": 5, "daily_limit": 40, ...}
```

---

## Sincronización Agent 2: Sheet ↔ Zoho CRM

El Agent 2 es responsable de mantener Zoho CRM sincronizado con el Google Sheet.

### Lógica de Sync

```python
AGENT_STATUS_TO_ZOHO = {
    "pending":    "New",
    "enriching":  "New",
    "contacted":  "Contacted",
    "replied":    "Responded",
    "converted":  "Closed Won",
    "skip":       "Closed Lost",
}

ZOHO_STAGE_TAG = {
    # agent_status + last_agent_action → azure_stage
    ("contacted", "M1"):  "M1_Enviado",
    ("contacted", "LI"):  "LI_Conectado",
    ("replied", ""):      "Respondio",
    ("converted", ""):    "Won",
    ("skip", ""),         "Lost",
}
```

### Triggers de Sync

1. **Inmediato:** Cada vez que Agent 1 escribe `agent_status = contacted`
2. **Polling:** Agent 2 ejecuta cada X horas para detectar:
   - Contactos `contacted` sin `zoho_lead_id` → crear Lead en Zoho
   - Contactos sin email pero con LinkedIn → enriquecer
   - Deals en Sheet sin `zoho_deal_id` → crear Deal en Zoho

---

## Lógica de Enriquecimiento de Datos Faltantes

Un caso frecuente es tener filas en el Sheet con datos incompletos:

| Caso | Fuente posible | Acción Agent 2 |
|---|---|---|
| Nombre sin email | Perplexity research | Buscar email corporativo |
| Email sin LinkedIn | LinkedIn search | Buscar perfil por nombre+empresa |
| Empresa sin NIT | REPS / Google | Enriquecer con NIT |
| LinkedIn sin email | LinkedIn profile | Extraer email si público |

```python
# Pseudo-código Agent 2 — data completeness check
contacts = sheets.get_contacts(has_email=False)  # filas sin email
for contact in contacts:
    if contact.get("First Name") and contact.get("Business"):
        result = enrichment_svc.find_email(
            name=contact["First Name"] + " " + contact["Last Name"],
            company=contact["Business"]
        )
        if result.get("email"):
            sheets._write_agent_cols(ws, headers, row_num, {
                "Email": result["email"],
                "data_source": "agent_enriched",
                "last_agent_action": "Email found via Perplexity",
                "last_touched_at": _now()
            })
```
