# Mapeo de Estados — Linear ↔ Zoho ↔ Azure

## Tabla Canónica

Esta es la tabla de verdad para sincronización de estados entre los tres sistemas.

| Linear Status | Zoho Lead Status | Azure Stage | Qué ocurrió | Quién mueve |
|---|---|---|---|---|
| **Backlog** | New | Frio | Identificado en REPS/Perplexity | Agent 1 al crear issue |
| **Todo** | New | Frio | Priorizado para esta semana (sprint) | Manual / Agent 1 |
| **In Progress** | Contacted | M1_Enviado | Email M1 enviado via Zoho | Agent 1 → Agent 2 sync |
| **In Progress** | Contacted | LI_Conectado | LinkedIn enviado/aceptado | Agent 1 → Agent 2 sync |
| **In Review** | Responded | Respondio | Respondió o agendó reunión | Agent 2 (detección de reply) |
| **Done** | Closed Won | Won | Reunión realizada, avanza a piloto | Manual (Alejandro) |
| **Cancelled** | Closed Lost | Lost | No respondió M3 / descartado | Agent 2 (post-M3 sin reply) |

---

## Reglas de Transición

### Backlog → Todo
- **Trigger:** Alejandro prioriza la empresa para el ciclo actual
- **Acción:** Mover issue en Linear a `Todo`
- **Zoho:** Sin cambio (sigue `New`)

### Todo → In Progress (M1_Enviado)
- **Trigger:** Agent 1 envía email M1 exitosamente
- **Acción:** 
  1. `cadence.db` actualiza `m1_sent_at`
  2. `sheets_service.mark_contacted(email, step=1)`
  3. Agent 2 lee Sheet → actualiza Zoho Lead a `Contacted`
  4. Agent 2 mueve issue Linear a `In Progress`
- **Zoho stage tag:** `M1_Enviado`

### Todo → In Progress (LI_Conectado)
- **Trigger:** Agent 1 envía/acepta conexión LinkedIn
- **Acción:**
  1. Sheet `agent_status = contacted`, `last_agent_action = "LI connection sent"`
  2. Agent 2 → Zoho Lead `Contacted`
  3. Agent 2 → Linear `In Progress`
- **Zoho stage tag:** `LI_Conectado`

### In Progress → In Review (Respondio)
- **Trigger:** Reply recibido (email o LinkedIn)
- **Acción:**
  1. Agent 2 detecta reply en Zoho inbox o Sheet marcado como replied
  2. `cadence_engine.mark_replied(email)` → pausa secuencia
  3. `sheets_service.mark_replied(email)`
  4. Zoho Lead → `Responded`
  5. Linear → `In Review`
- **Nota:** Humano (Alejandro) toma el hilo desde aquí

### In Review → Done (Won)
- **Trigger:** Reunión realizada, prospect avanza
- **Acción manual:**
  1. Alejandro mueve Linear a `Done`
  2. Zoho Lead → `Closed Won`
  3. Crear Deal en Zoho si corresponde
- **Azure:** `Won`

### Cualquiera → Cancelled (Lost)
- **Trigger A:** M3 enviado hace 5+ días sin reply
- **Trigger B:** Alejandro cancela manualmente
- **Acción:**
  1. `cadence_engine` marca `status = completed` (todos los pasos enviados)
  2. Agent 2 detecta completado sin reply → Zoho `Closed Lost`
  3. Linear → `Cancelled`
- **Azure:** `Lost`

---

## Implementación en Código

### Sheet → Zoho sync (Agent 2)

```python
# Pseudo-código de la lógica de sync
def sync_sheet_to_zoho(sheets_svc, zoho_crm):
    contacts = sheets_svc.get_contacts()
    for contact in contacts:
        agent_status = contact.get("agent_status")
        zoho_id = contact.get("zoho_lead_id")
        
        mapping = {
            "pending":    "New",
            "enriching":  "New",
            "contacted":  "Contacted",
            "replied":    "Responded",
            "converted":  "Closed Won",
            "skip":       "Closed Lost",
        }
        
        zoho_status = mapping.get(agent_status)
        if zoho_status and zoho_id:
            zoho_crm.update_lead(zoho_id, status=zoho_status)
```

### Linear → Zoho campo de referencia

Cada issue de Linear tiene un `gitBranchName` que incluye el ID (ej. `asperjasp/aim-326-cemde`).  
En Zoho, el campo custom `linear_issue_id` almacena `AIM-326` para trazabilidad.

---

## Diagrama de Flujo Visual

```
Identificado
    │
    ▼
[Backlog / New / Frio]
    │
    │ Priorizar
    ▼
[Todo / New / Frio]
    │
    │ M1 enviado        │ LI enviado
    ▼                   ▼
[In Progress / Contacted / M1_Enviado]
[In Progress / Contacted / LI_Conectado]
    │
    │ Reply detectado
    ▼
[In Review / Responded / Respondio]
    │
    ├── Reunión hecha ──► [Done / Closed Won / Won]
    │
    └── Sin respuesta M3 ► [Cancelled / Closed Lost / Lost]
```

---

## Campos Zoho CRM Relevantes

| Campo Zoho | Tipo | Descripción |
|---|---|---|
| `Lead Status` | Picklist | New / Contacted / Responded / Closed Won / Closed Lost |
| `Lead Source` | Picklist | Email / LinkedIn / WhatsApp / Referral / REPS |
| `linear_issue_id` | Text | AIM-XXX para trazabilidad |
| `m1_sent_date` | Date | Fecha envío M1 |
| `m2_sent_date` | Date | Fecha envío M2 |
| `m3_sent_date` | Date | Fecha envío M3 |
| `azure_stage` | Text | Frio / M1_Enviado / LI_Conectado / Respondio / Won / Lost |
