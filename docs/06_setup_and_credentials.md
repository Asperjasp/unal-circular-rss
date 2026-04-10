# Setup y Credenciales

## Variables de Entorno

Copia `.env.template` a `.env` y completa:

```bash
# ── AI APIs ──────────────────────────────────────────────
PERPLEXITY_API_KEY=pplx-...          # research de prospectos
GOOGLE_AI_STUDIO=AIza...             # redacción de mensajes (Gemini)

# ── Identity (aparece en mensajes redactados) ────────────
YOUR_NAME=Alejandro
YOUR_ROLE=Co-Founder & CEO
BUSINESS_NAME=AI Medic
BUSINESS_DESCRIPTION=Plataforma de IA para reportes clínicos en IPS/EPS colombianas

# ── Zoho Mail API (para envío de emails) ─────────────────
ZOHO_CLIENT_ID=...
ZOHO_CLIENT_SECRET=...
ZOHO_REFRESH_TOKEN=...
ZOHO_ACCOUNT_ID=...                  # ID de cuenta en Zoho Mail
ZOHO_FROM_EMAIL=alejandro@aimedic.com.co

# ── Google Sheets (fuente de verdad CRM) ─────────────────
GOOGLE_SERVICE_ACCOUNT_FILE=google_service_account.json
GOOGLE_SHEET_ID=1jBcTaANZTubNk3FWMnLdHFHyZhD31WTYIXe38g7eo9g

# ── Linear ───────────────────────────────────────────────
LINEAR_API_KEY=lin_api_...
LINEAR_TEAM_ID=0de683ca-5594-4ee3-a3de-6e54687908fe   # equipo AIMEDIC

# ── HubSpot (opcional, legado) ───────────────────────────
HUBSPOT_ACCESS_TOKEN=pat-...

# ── API Protection ───────────────────────────────────────
API_KEY=                             # dejar vacío para desarrollo local
```

---

## Zoho CRM — Autenticación MCP

Para que Claude Code tenga acceso a Zoho CRM via MCP:

```
1. En Claude Code, escribe en el prompt: /mcp
2. Selecciona "claude.ai Zoho CRM" de la lista
3. Se abrirá un flujo OAuth en el navegador
4. Autoriza el acceso con la cuenta de Zoho AI Medic
5. Al completar, las herramientas Zoho quedan disponibles en la sesión
```

**Herramientas disponibles post-autenticación:**
- `get_crm_objects` — leer leads/contacts/deals
- `search_crm_objects` — buscar por criterio
- `get_properties` — ver campos disponibles
- `search_owners` — ver usuarios Zoho

---

## Google Sheets — Service Account

### Crear Service Account

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto o selecciona el existente de AI Medic
3. Habilita las APIs:
   - Google Sheets API
   - Google Drive API
4. Ve a IAM & Admin → Service Accounts → Create
5. Nombre: `aimedic-sheets-agent`
6. Rol: Editor (o Viewer si solo lectura)
7. Descargar JSON de credenciales
8. Guardar como `google_service_account.json` en la raíz del proyecto

### Compartir el Sheet

```
1. Abre el Sheet: https://docs.google.com/spreadsheets/d/1jBcTaANZTubNk3FWMnLdHFHyZhD31WTYIXe38g7eo9g
   (con la cuenta camilo.daza@aimedic.com.co)
2. Click "Compartir"
3. Agregar el email de la service account: aimedic-sheets-agent@[project].iam.gserviceaccount.com
4. Rol: Editor
5. Desmarcar "Notificar a personas"
```

### Verificar acceso

```python
from health_scraper.integrations.sheets_service import SheetsService

svc = SheetsService.from_service_account("google_service_account.json")
contacts = svc.get_contacts(limit=3)
print(f"Acceso OK — {len(contacts)} contactos leídos")
```

---

## Zoho Mail API — Obtener Tokens

### Paso 1: Crear aplicación en Zoho API Console

1. Ve a [api-console.zoho.com](https://api-console.zoho.com/)
2. Add Client → Server-based Applications
3. Redirect URI: `http://localhost:8000/oauth/callback`
4. Copiar `Client ID` y `Client Secret`

### Paso 2: Obtener Refresh Token

```bash
# 1. Construir URL de autorización:
https://accounts.zoho.com/oauth/v2/auth?
  scope=ZohoMail.messages.CREATE,ZohoMail.accounts.READ&
  client_id=YOUR_CLIENT_ID&
  response_type=code&
  redirect_uri=http://localhost:8000/oauth/callback&
  access_type=offline

# 2. Abrir en navegador, autorizar
# 3. Copiar el `code` de la URL de redirección
# 4. Cambiar por tokens:
curl -X POST "https://accounts.zoho.com/oauth/v2/token" \
  -d "code=YOUR_CODE&grant_type=authorization_code&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET&redirect_uri=http://localhost:8000/oauth/callback"

# Response incluye refresh_token — guardar en .env
```

### Paso 3: Obtener Account ID

```python
import httpx, asyncio

async def get_account_id(access_token):
    r = await httpx.AsyncClient().get(
        "https://mail.zoho.com/api/accounts",
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"}
    )
    accounts = r.json()["data"]
    for acc in accounts:
        print(acc["accountId"], acc["emailAddress"])

# El accountId que corresponde al from_email es el ZOHO_ACCOUNT_ID
```

---

## Linear — Obtener API Key y Team ID

### API Key
1. Linear → Settings → My Account → API
2. Create new key → copiar en `LINEAR_API_KEY`

### Team ID
```python
import httpx, asyncio

async def get_team_id(api_key):
    query = '{ teams { nodes { id name } } }'
    r = await httpx.AsyncClient().post(
        "https://api.linear.app/graphql",
        json={"query": query},
        headers={"Authorization": api_key}
    )
    for team in r.json()["data"]["teams"]["nodes"]:
        print(team["id"], team["name"])

# El team ID de AIMEDIC es: 0de683ca-5594-4ee3-a3de-6e54687908fe
```

---

## Verificación Rápida del Sistema

```bash
# Verificar configuración general
python check_config.py

# Verificar acceso a Google Sheets
python -c "
from health_scraper.integrations.sheets_service import SheetsService
svc = SheetsService.from_service_account('google_service_account.json')
print('Contacts:', len(svc.get_contacts()))
print('Businesses:', len(svc.get_businesses()))
"

# Verificar estado de cadencias
python -c "
from health_scraper.integrations.zoho_cadence_service import CadenceEngine
engine = CadenceEngine()
import json; print(json.dumps(engine.stats(), indent=2))
"

# Dry run de envíos pendientes (sin enviar nada)
python -c "
from health_scraper.integrations.zoho_cadence_service import CadenceEngine
engine = CadenceEngine()  # sin zoho= → solo dry_run
result = engine.process_due(dry_run=True)
print(result)
"
```

---

## Azure Deployment

El proyecto se despliega en Azure App Service. Ver:
- `azure-deploy.sh` — script de deploy
- `.github/workflows/azure-deploy.yml` — CI/CD pipeline
- `Dockerfile` — imagen de producción

```bash
# Deploy manual
./azure-deploy.sh

# O via GitHub Actions (push a main)
git push origin main
```
