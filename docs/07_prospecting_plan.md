# Plan de Prospección — Sistema Completo SEMG

**Última actualización:** 2026-04-09  
**Email de prospección:** alejandro.sanchez@aimedic.com.co  
**Batch anterior:** [AIM-412 — Leads Abril 6-7 de 2026](https://linear.app/aimedic/issue/AIM-412/leads-abril-6-7de-2026)  
**Proyecto activo:** [Prospeccion Ciclo #10 - 06/04/2026](https://linear.app/aimedic/project/adcf7ad0-81fc-492b-ab4c-b52b2edb697a)

---

## 1. Estructura de un Ciclo de Prospección

### Jerarquía en Linear

```
Prospeccion Ciclo #10  (Project)
├── AIM-412  Leads - Abril 6-7  (Batch Issue — índice del día)
│   ├── AIM-413  [Empresa A - Cardiología Bogotá]  (SFT Issue)
│   ├── AIM-414  [Empresa B - Mental Antioquia]     (SFT Issue)
│   └── AIM-389  Clínica San Rafael               (SFT Issue)
└── AIM-XXX  Leads - Abril 9-10  (próximo batch)
    ├── ...
```

### Dos tipos de issue

| Tipo | Template | Ejemplo | Descripción |
|---|---|---|---|
| **Batch Issue** | Daily Prospecting | AIM-412 | Índice del día — lista las 50 empresas por segmento |
| **SFT Issue** | SFT PROSPECTING | AIM-389 | Una empresa: contactos, LinkedIn tracking, email cadencia, CRM sync |

---

## 2. Segmentación — 3 Niveles

```
País
├── Colombia (principal)
│   ├── Bogotá / Sabana
│   ├── Antioquia / Eje Cafetero
│   ├── Costa Caribe (Barranquilla, Cartagena, Santa Marta, Montería)
│   ├── Suroccidente (Cali, Pasto, Cauca)
│   └── Otros
├── Argentina
└── Chile

Patología (eje principal de contenido)
├── 🫀 Cardiology & Cardiovascular Care
├── 🧠 Mental Health & Psychiatry
├── 🦴 Pain Management, Rheumatology & Immunology
├── 🎗️ Specialized Care (Oncology & Respiratory)
├── 💊 Endocrinology, Metabolism & Nephrology
└── ♿ Rehabilitation & Physical Therapy

Tier ICP
├── Enterprise  (>200 empleados, alta complejidad)
├── Professional (50-200 empleados)
└── Essential   (<50 empleados)
```

**Regla de muestreo:** Cada batch de 50 debe tener representación de al menos 3 patologías y 2 regiones. La semana de contenido dicta qué patología domina (ej. semana cardiología → 60% cardio).

---

## 3. Meta Diaria — 50 Empresas Nuevas

### Definición de "Nueva"
Una empresa es **nueva** si:
1. NO aparece en ningún batch anterior (`batch_id` vacío en Google Sheet - Businesses tab)
2. NO tiene `prospected_at` en el Sheet
3. NO tiene un SFT issue en Linear con status `In Progress`, `In Review` o `Done`

### Anti-Duplicación — Columnas en Businesses Tab

Se agregan estas columnas al tab `Businesses` del Google Sheet:

| Columna | Tipo | Descripción |
|---|---|---|
| `batch_id` | string | ID del batch en que fue seleccionada (ej. `AIM-412`) |
| `prospected_at` | ISO timestamp | Cuándo fue incluida en un batch |
| `prospecting_cycle` | string | Ciclo (ej. `Ciclo10`) |
| `linear_sft_issue` | string | Issue AIM-XXX de su SFT |
| `pathology_tag` | string | Cardio / Mental / Pain / Special / EndoMeta / Rehab |
| `region_tag` | string | Bogota / Antioquia / CostaCaribe / Suroccidente / Otros / Argentina / Chile |
| `tier_icp` | string | Enterprise / Professional / Essential |
| `contacts_count` | int | Cuántos contactos identificados |
| `emails_sent` | int | Emails enviados (suma M1+M2+M3) |
| `li_connections_sent` | int | Conexiones LinkedIn enviadas |

### Flujo del Batch Sampler (código: `batch_sampler.py`)

```
1. Leer Businesses tab del Google Sheet
2. Filtrar: batch_id vacío AND prospected_at vacío
3. Aplicar filtros opcionales: pathology_tag, region_tag, tier_icp
4. Tomar 50 (aleatorio dentro del filtro o por score ICP)
5. Marcar las 50 con batch_id = "AIM-XXX" y prospected_at = now()
6. Devolver lista estructurada para crear issues en Linear
```

---

## 4. Ciclo de 9 Toques por Empresa

Cada empresa recibe hasta 9 puntos de contacto distribuidos en ~9 días:

| Día | Canal | Acción | Sistema |
|---|---|---|---|
| D0 | Email | M1 enviado a TODOS los contactos con email | Zoho CRM Cadencia (grupo) |
| D1 | LinkedIn | Conexión enviada a TODOS con LinkedIn | Manual / LinkedIn API |
| D2 | LinkedIn | Mensaje D2 a quienes aceptaron | Manual |
| D4 | Email | M2 follow-up (cadencia automática) | Zoho CRM Cadencia |
| D6 | LinkedIn | Mensaje con Calendly CEO | Manual |
| D8 | Email | M3 breakup (cadencia automática) | Zoho CRM Cadencia |
| D9 | WhatsApp/Llamada | Último intento | Manual |

### Email vs LinkedIn: filosofía

| Canal | Naturaleza | Tracking | Personalización |
|---|---|---|---|
| **Email** | Volumen, numérico | Zoho CRM (aperturas, clicks, bounces) | Template con variables (nombre, empresa) |
| **LinkedIn** | Calidad, relacional | Manual en Linear (SFT issue) | Totalmente personalizado por persona |

---

## 5. Zoho CRM — Cadencias Grupales

### Concepto de Grupo
En lugar de crear 5 cadencias individuales para 5 personas de CEMDE, se crea **una sola entrada de cadencia por empresa** que enrolla a todos los contactos con email de esa empresa.

```
CEMDE S.A.S. (empresa)
  → Cadencia "B2B IPS Ciclo 9 Toques"
    → Lead: dir.administrativa@cemde.com  (M1 → M2 → M3)
    → Lead: enfermerajefe@cemde.com       (M1 → M2 → M3)
    → Lead: dr.cuervo@cemde.com           (M1 → M2 → M3)
```

El tracking se hace a nivel empresa en el SFT issue de Linear, y a nivel individuo en Zoho CRM.

### API de Cadencias Zoho CRM (REST directo)

El MCP de Zoho CRM no funciona → usamos la REST API v3 directamente.

```
Base URL: https://www.zohoapis.com/crm/v3/

Endpoints clave:
  GET  /Cadences                          → listar cadencias disponibles
  POST /Cadences/{id}/actions/subscribe   → enrollar grupo de leads
  GET  /Leads?account_name=CEMDE          → buscar leads de una empresa
  POST /Leads                             → crear lead
  PUT  /Leads/{id}                        → actualizar lead
```

**Archivo:** `health_scraper/integrations/zoho_crm_service.py`

### Enrollment grupal en código

```python
# Enrollar 5 contactos de CEMDE en una cadencia
crm = ZohoCRMService(client_id=..., client_secret=..., refresh_token=...)

# 1. Crear los leads en Zoho si no existen
lead_ids = await crm.upsert_leads(contacts, account_name="CEMDE")

# 2. Enrollar TODO el grupo en la cadencia de una sola llamada
result = await crm.enroll_in_cadence(
    cadence_id="CADENCIA_B2B_IPS",
    lead_ids=lead_ids,
    account_name="CEMDE"      # para tracking grupal
)
# → {"enrolled": 5, "already_active": 0, "failed": 0}
```

---

## 6. Anti-Spam — Reglas Operacionales

### Límites de envío (conservadores)

| Regla | Valor | Razón |
|---|---|---|
| Máx emails/día | 40 | Límite configurado en CadenceEngine |
| Máx emails a mismo dominio/día | 3 | Evitar señales de spam a nivel dominio |
| Ventana de envío | Lun-Vie 8am-6pm COL (UTC-5) | Tasas de apertura + reputación |
| Intervalo entre emails | 2-5 min aleatorio | Evitar patrones de bot |
| Warmup (cuenta nueva) | +5/día durante 2 semanas | Construir reputación DMARC/SPF |

### Checks antes de enviar

```
1. ¿El contacto ya está en una cadencia activa? → skip
2. ¿Recibimos reply de este contacto? → pause, notificar
3. ¿El email rebotó antes? → blacklist, skip
4. ¿Ya mandamos a 3+ personas de este dominio hoy? → defer
5. ¿Es hora válida de envío? → queue para mañana
```

### SPF/DKIM/DMARC de alejandro.sanchez@aimedic.com.co
Verificar que Zoho Mail tenga configurados:
- SPF: `include:zoho.com` en DNS de aimedic.com.co
- DKIM: Firma DKIM activa en Zoho Mail
- DMARC: `v=DMARC1; p=none; rua=mailto:dmarc@aimedic.com.co`

---

## 7. Integración Google Sheet ↔ Zoho CRM

### Flujo de datos

```
REPS / Perplexity / Manual
    │
    ▼
Google Sheet (Businesses + Contacts tabs)  ← fuente de verdad
    │
    │  Batch Sampler selecciona 50 nuevas
    ▼
Zoho CRM (Leads + Accounts + Cadencias)   ← ejecución
    │
    │  Agent 2 sincroniza estados de vuelta
    ▼
Google Sheet (agent_status, emails_sent, etc.)
    │
    │  Agent 2 sincroniza a Linear
    ▼
Linear (SFT issues, Batch issues)          ← tracking humano
```

### Columnas de sync necesarias en Google Sheet

**Tab Businesses** (empresas):
```
batch_id, prospected_at, prospecting_cycle, linear_sft_issue,
pathology_tag, region_tag, tier_icp, contacts_count,
emails_sent, li_connections_sent, zoho_account_id
```

**Tab Contacts** (personas):
```
agent_status, email_m1_sent_at, email_m2_sent_at, email_m3_sent_at,
zoho_lead_id, zoho_cadence_status, li_connected, li_replied,
data_source, last_touched_at
```

---

## 8. Archivos a Construir / Estado

| Archivo | Estado | Descripción |
|---|---|---|
| `sheets_service.py` | **Listo** | R/W Google Sheet — agregar columnas de Businesses |
| `zoho_email_service.py` | **Listo** | Envío de emails via Zoho Mail API |
| `zoho_cadence_service.py` | **Listo** | Motor M1→M2→M3 con SQLite local |
| `outreach_templates.py` | **Listo** | Templates M1/M2/M3/CAMILO_V1 |
| `zoho_crm_service.py` | **PENDIENTE** | REST API Zoho CRM — leads, cuentas, cadencias grupales |
| `batch_sampler.py` | **PENDIENTE** | Seleccionar 50 nuevas, anti-duplicación, crear issues Linear |
| `prospecting_agent.py` | **PENDIENTE** | Orquestador del agente de prospección completo |
| Google Sheet service account | **PENDIENTE** | Setup con camilo.daza@aimedic.com.co |
| Zoho CRM MCP | **BLOQUEADO** | Pendiente soporte Claude |

---

## 9. Template de Batch Issue para Linear

Al crear un nuevo batch (AIM-XXX), el Batch Sampler crea este issue:

```markdown
# Leads - [Fecha] — Ciclo #[N]

## 🫀 Cardiology & Cardiovascular Care — Colombia
- [AIM-XXX] [Empresa 1] — Bogotá
- [AIM-XXX] [Empresa 2] — Medellín

## 🧠 Mental Health & Psychiatry — Colombia
- [AIM-XXX] [Empresa 3] — Bogotá

[... hasta 50 empresas]

## Métricas del Batch
- Total empresas: 50
- Emails enviados: 0 / ~150 esperados
- Conexiones LinkedIn enviadas: 0 / ~150 esperadas
- Replies recibidos: 0

## Patologías cubiertas
- Cardio: N
- Mental: N
- Pain: N
- Special: N
- EndoMeta: N
- Rehab: N
```

---

## 10. Próximos Pasos Inmediatos

1. **Construir `zoho_crm_service.py`** — grupo cadence enrollment via REST API  
2. **Construir `batch_sampler.py`** — muestreo de 50 nuevas con anti-duplicación  
3. **Setup Google Service Account** — para que los scripts lean/escriban el Sheet  
4. **Agregar columnas de batch** al tab Businesses del Sheet  
5. **Crear Ciclo #10 batch** para Abril 9-10 usando el sampler  
6. **Resolver Zoho CRM MCP** — contactar soporte Claude  
