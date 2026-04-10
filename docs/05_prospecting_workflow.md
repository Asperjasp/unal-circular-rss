# Flujo de Prospección — Patrón AIM-326

## Referencia

El issue [AIM-326 — CEMDE](https://linear.app/aimedic/issue/AIM-326/centro-de-medicina-del-ejercicio-y-rehabilitacion-cardiaca-sas-cemde) es el **patrón canónico** de cómo se estructura cada empresa objetivo en un ciclo de prospección.

Proyecto padre: [Prospeccion Ciclo #8 — 23/03/2026](https://linear.app/aimedic/project/onboarding-a-equipos-tecnicos-y-de-growth-b47d7f75c09b/overview)

---

## Flujo Completo por Empresa Objetivo

### Paso 1: Research (Perplexity)

**Quién:** Agent 1 / Manual (Alejandro con Perplexity)  
**Output:** Tabla de contactos con nombre, cargo, email, teléfono, LinkedIn

```
Empresa target: CEMDE
↓
Perplexity query: "CEMDE IPS Medellín directivos email contacto LinkedIn"
↓
Resultado: 8 contactos (ver tabla AIM-326):
  - dir.administrativa@cemde.com (Dirección Administrativa) ← PRIORIDAD IA
  - enfermerajefe@cemde.com (Tatiana Palacios)
  - dr.cuervo@cemde.com (Alfonso Cuervo Aguilera)
  - etc.
```

**En Linear:** Issue creado con status `Backlog` → mover a `In Progress` al iniciar

### Paso 2: Data Entry — Consolidar en Google Sheet

**Quién:** Agent 2 (o manual)  
**Output:** Filas en tab `Contacts` con `data_source = manual` o `agent_enriched`

```python
# Si Agent 1 hace el research, escribe directamente al Sheet
sheets.ensure_agent_columns()  # primera vez

new_contacts = [
    {
        "First Name": "N/A",
        "Last Name": "Administrativa", 
        "Email": "dir.administrativa@cemde.com",
        "Phone": "(604) 3222656",
        "Business": "CEMDE",
        "LinkedIn URL": "",
        "agent_status": "pending",
        "data_source": "agent_enriched",
    },
    # ... más contactos
]
```

**Regla de prioridad de contactos:**
1. Gerencia / Dirección Administrativa (toma decisiones de compra)
2. Director de TI / Innovación
3. Director Médico / Jefe de Área relevante
4. Operativo (enfermera jefe, fisioterapeuta) — solo si no hay acceso a decisores

### Paso 3: CRM Sync — Subir a Zoho CRM

**Quién:** Agent 2  
**Acción:** Crear/actualizar Leads en Zoho con `Lead Status = New`

```python
# Agent 2 detecta nuevos contactos en Sheet sin zoho_lead_id
# y los crea en Zoho
zoho_crm.create_lead({
    "First_Name": "Dirección",
    "Last_Name": "Administrativa CEMDE",
    "Email": "dir.administrativa@cemde.com",
    "Phone": "6043222656",
    "Company": "CEMDE",
    "Lead_Status": "New",
    "Lead_Source": "REPS",
    "linear_issue_id": "AIM-326",
})
```

### Paso 4: Prompting — Redactar Mensajes

**Quién:** Agent 1 (Gemini) o Manual  
**Referencias de plantillas:**
- M1: [AIM-74](https://linear.app/aimedic/issue/AIM-74) — Email frío intro
- M2 LinkedIn: [AIM-71](https://linear.app/aimedic/issue/AIM-71) — Follow-up LinkedIn
- M3: [AIM-76](https://linear.app/aimedic/issue/AIM-76) — Breakup email

**Tono AI Medic (de AIMEDIC.md):**
- No lambón
- Resaltar trayectoria del prospecto
- Despedida humana "A sacarla del estadio"
- Evitar clichés de ventas

```python
# Agent 1 usa outreach_drafting_service
draft = drafting_svc.draft_outreach(
    person_data={
        "name": "Dirección Administrativa",
        "company": "CEMDE",
        "role": "Dirección Administrativa",
        "context": "IPS especializada en rehabilitación cardíaca, Medellín"
    },
    channels=["email"],
    tone="warm",
    language="es",
    goal="Agendar demo de AI Medic para reportes clínicos"
)
```

### Paso 5: Ejecución Toque 1 — Enviar Email M1

**Quién:** Agent 1 (CadenceEngine)  
**Límite:** 40 emails/día

```python
engine = CadenceEngine(zoho=zoho_email_svc)

# Enqueue todos los contactos con email de CEMDE
cemde_prospects = sheets.get_contacts_for_sending(limit=40)
engine.enqueue(cemde_prospects, m1_template="M1_CONNECT")

# Enviar M1s pendientes
result = engine.process_due()
# {"sent": 5, "failed": 0}

# Registrar en Sheet e Interactions
for sent in result["details"]:
    sheets.mark_contacted(sent["email"], step=1)
    sheets.log_interaction(
        contact=sent["email"],
        business="CEMDE",
        channel="Email Zoho",
        direction="Outbound",
        summary="M1 CAMILO_V1 enviado",
        next_step="M2 en 4 días"
    )
```

**Linear:** Mover AIM-326 a `In Progress`  
**Zoho:** Agent 2 sync → Lead `Contacted`, azure_stage `M1_Enviado`

### Paso 6: LinkedIn Connections

**Quién:** Agent 1 (linkedin_outreach_service)  
**Paralelo al email:** Para contactos con LinkedIn URL en el Sheet

```python
li_svc = LinkedInOutreachService(...)
for contact in cemde_prospects:
    if contact.get("LinkedIn URL"):
        li_svc.send_connection(
            linkedin_url=contact["LinkedIn URL"],
            message="Hola {nombre}, vi que trabajas en CEMDE..."
        )
        sheets._write_agent_cols(ws, headers, row_num, {
            "agent_status": "contacted",
            "last_agent_action": "LI connection sent",
            "last_touched_at": _now()
        })
```

### Paso 7: WhatsApp / Llamada

**Quién:** Manual (Alejandro)  
**Trigger:** Contactos que solo tienen teléfono, sin email ni LinkedIn

```
Agent 2 identifica:
  contact_id = C-000000015 (Yadira Moreno, Seguros Bolivar)
  → sin email, sin LinkedIn
  → tiene phone: 300-xxx-xxxx
  → crea tarea manual en Linear o notifica a Alejandro
```

---

## Estructura del Issue Linear (Patrón AIM-326)

Cada empresa target debe tener un issue con esta estructura:

```markdown
### Objetivo del Día
[Descripción de la empresa + ICP score]

### Contactos [Empresa]
| First Name | Last Name | Email | LinkedIn | Role | Phone | Notas |
| --- | --- | --- | --- | --- | --- | --- |
| ... | ... | ... | ... | ... | ... | PRIORIDAD IA |

### ICP Score
[Por qué es un buen prospect]

### Workflow de Adquisición
- [ ] 1. Research (Perplexity)
- [ ] 2. Data Entry (Google Sheet)
- [ ] 3. CRM Sync (Zoho)
- [ ] 4. Prompting (Gemini / plantillas AIM-74, AIM-71, AIM-76)
- [ ] 5. Ejecución Toque 1: Emails
- [ ] 6. Conexiones LinkedIn
- [ ] 7. WhatsApp / Llamada

Nota de Escalado: Si responde positivamente → crear Proyecto B2B
```

---

## Criterios de Priorización de Empresas

El backlog de empresas viene de REPS (Registro Especial de Prestadores de Servicios de Salud).

**ICP perfecto para AI Medic:**
- 20-200 empleados (piloto manejable)
- Especialidades: cardiología, oncología, neumología, rehabilitación
- Roles de interés: Director Médico, Gerente TI, Director Administrativo
- Ciudad: Bogotá, Medellín, Cali, Barranquilla (primera fase)
- Tipo: IPS especializada > Hospital > Clínica > EPS

**Señales positivas:**
- Tienen website (indica cierto nivel de madurez digital)
- Perfil LinkedIn activo
- Mencionan "innovación" o "tecnología" en su descripción
- 20+ empleados en LinkedIn

---

## Emails Inbound — Procesamiento

Cuando llega un email de una entidad de salud (no como reply a una cadencia), Agent 2 procesa:

```
Email inbound detectado en Zoho inbox
    │
    ├── ¿Es reply a M1/M2/M3?
    │   └── Sí → mark_replied(email) + notificar Alejandro
    │
    └── ¿Es email espontáneo (nuevo contacto)?
        └── Agent 2:
            1. Extraer empresa + nombre del remitente
            2. Buscar en Sheet si ya existe
            3. Si no existe → crear fila en Contacts con data_source=inbound
            4. Research con Perplexity del remitente
            5. Crear issue Linear si empresa es nueva
            6. Notificar a Alejandro con contexto
```
