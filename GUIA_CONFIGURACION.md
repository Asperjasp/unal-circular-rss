# 🚀 Guía de Configuración Completa - Scrapper Salud AiMedic

Esta guía te llevará paso a paso para configurar todas las integraciones y tener tu sistema funcionando al 100%.

---

## 📋 Índice Rápido

1. [Configuración Inicial](#1-configuración-inicial)
2. [APIs Obligatorias (Core)](#2-apis-obligatorias-core)
3. [HubSpot CRM](#3-hubspot-crm)
4. [Linear (Project Management)](#4-linear-project-management)
5. [Zoho Email](#5-zoho-email)
6. [Google Calendar](#6-google-calendar)
7. [Verificación Final](#7-verificación-final)

---

## 1. Configuración Inicial

### ⚡ Paso 1: Crea tu archivo .env

```bash
cp .env.template .env
```

### ✏️ Paso 2: Completa tu información personal

Abre `.env` y completa:

```env
YOUR_NAME=Tu Nombre
YOUR_ROLE=CEO / Founder
BUSINESS_NAME=AiMedic
BUSINESS_DESCRIPTION=Tu descripción del negocio...
```

✅ **Por qué es importante**: Gemini usará esta info para personalizar mensajes de outreach.

---

## 2. APIs Obligatorias (Core)

### 🤖 Google Gemini AI

**Para qué sirve**: Redacción de mensajes personalizados, análisis de imágenes web

#### Pasos:

1. Ve a: [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Click en **"Create API Key"**
3. Copia la key que empieza con `AIzaSy...`
4. En tu `.env`:
   ```env
   GOOGLE_AI_STUDIO=AIzaSy...tu-key-real
   ```

💰 **Costo**: GRATIS (15 requests/min con Gemini 1.5 Flash)

✅ **Verifica**: La key debe tener 39 caracteres aprox.

---

### 🔍 Perplexity AI

**Para qué sirve**: Investigación profunda de personas y empresas desde LinkedIn, Twitter, PDFs

#### Pasos:

1. Crea cuenta en: [https://www.perplexity.ai/](https://www.perplexity.ai/)
2. Ve a: [https://www.perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)
3. Click en **"Generate API Key"**
4. Copia la key que empieza con `pplx-...`
5. En tu `.env`:
   ```env
   PERPLEXITY_API_KEY=pplx-...tu-key-real
   ```

💰 **Costo**: ~$5-20/mes (modelo sonar-pro tiene mejor contexto)

✅ **Tip**: Empieza con el plan básico de $20/mes (incluye 1000 requests)

---

## 3. HubSpot CRM

**Para qué sirve**: Guardar automáticamente contactos y empresas en tu CRM

### 📝 Configuración Detallada:

#### Paso 1: Crea una Private App

1. **Inicia sesión en HubSpot**: [https://app.hubspot.com/](https://app.hubspot.com/)
2. Ve a: **Settings** (⚙️ arriba derecha) → **Integrations** → **Private Apps**
3. Click en **"Create a private app"**

#### Paso 2: Configura la App

- **Name**: `AiMedic Health Scraper`
- **Description**: `Integration for automated health institution data collection`

#### Paso 3: Permisos (Scopes)

En la pestaña **"Scopes"**, busca y activa:

**CRM → Companies**:
- ✅ `crm.objects.companies.read`
- ✅ `crm.objects.companies.write`

**CRM → Contacts**:
- ✅ `crm.objects.contacts.read`
- ✅ `crm.objects.contacts.write`

**CRM → Deals** (opcional, para tracking de ventas):
- ✅ `crm.objects.deals.read`
- ✅ `crm.objects.deals.write`

#### Paso 4: Genera el token

1. Click en **"Create app"**
2. Aparecerá un **Access Token** (empieza con `pat-na1-...`)
3. **¡IMPORTANTE!**: Cópialo inmediatamente (solo se muestra una vez)
4. En tu `.env`:
   ```env
   HUBSPOT_ACCESS_TOKEN=pat-na1-...tu-token-real
   ```

💰 **Costo**: GRATIS (plan gratuito de HubSpot disponible)

✅ **Verifica el token**:
```bash
curl -H "Authorization: Bearer pat-na1-tu-token" \
     https://api.hubapi.com/crm/v3/objects/companies?limit=1
```

Deberías ver un JSON con empresas (o vacío si aún no tienes).

---

## 4. Linear (Project Management)

**Para qué sirve**: Crear tareas automáticamente para seguimiento comercial y técnico

### 📝 Configuración:

#### Paso 1: Obtén tu API Key

1. Inicia sesión en Linear: [https://linear.app/](https://linear.app/)
2. Ve a: **Settings** → **API** → **Personal API Keys**
3. Click en **"Create new API key"**
4. Dale un nombre: `AiMedic Scraper`
5. Copia la key (empieza con `lin_api_...`)
6. En tu `.env`:
   ```env
   LINEAR_API_KEY=lin_api_...tu-key-real
   ```

#### Paso 2: Obtén tu Team ID (Opcional)

1. En Linear, ve a **Settings** → **Teams**
2. Click en tu team principal
3. En la URL verás algo como: `linear.app/team/ABC-123/settings`
4. El `ABC-123` es tu Team ID
5. En tu `.env`:
   ```env
   LINEAR_DEFAULT_TEAM_ID=ABC-123
   ```

💡 **Nota**: Si no configuras el Team ID, el sistema lo detectará automáticamente.

💰 **Costo**: GRATIS para equipos pequeños (<10 usuarios)

✅ **Verifica**:
```bash
curl -H "Authorization: lin_api_tu-key" \
     -H "Content-Type: application/json" \
     -d '{"query":"{ viewer { id name email } }"}' \
     https://api.linear.app/graphql
```

---

## 5. Zoho Email

**Para qué sirve**: Enviar emails automatizados de outreach desde tu dominio

### 📝 Configuración (Paso a Paso):

#### Paso 1: Crea una aplicación en Zoho

1. Ve a: [https://api-console.zoho.com/](https://api-console.zoho.com/)
2. Click en **"Add Client"**
3. Selecciona **"Self Client"** (más fácil)
4. Dale un nombre: `AiMedic Email Integration`
5. Click **"Create"**
6. Te mostrarán:
   - **Client ID**: `1000.XXXXXXXXXXXXXXX`
   - **Client Secret**: `xxxxxxxxxxxxxxxxx`
7. Cópialos a tu `.env`:
   ```env
   ZOHO_CLIENT_ID=1000.tu-client-id
   ZOHO_CLIENT_SECRET=tu-client-secret
   ```

#### Paso 2: Genera el Refresh Token

Este paso es el más técnico pero lo haremos simple:

1. En la misma página del API Console, ve a la pestaña **"Generate Code"**
2. **Scope**: Ingresa: `ZohoMail.messages.ALL,ZohoMail.accounts.READ`
3. **Time Duration**: Selecciona `10 minutes`
4. Click **"Generate"**
5. Te dará un **Code** → Cópialo

Ahora, en tu terminal (reemplaza los valores):

```bash
curl -X POST https://accounts.zoho.com/oauth/v2/token \
  -d "code=TU_CODE_AQUI" \
  -d "client_id=TU_CLIENT_ID" \
  -d "client_secret=TU_CLIENT_SECRET" \
  -d "grant_type=authorization_code"
```

Respuesta (JSON):
```json
{
  "access_token": "...",
  "refresh_token": "1000.xxxxx...",
  "expires_in": 3600
}
```

Copia el `refresh_token` a tu `.env`:
```env
ZOHO_REFRESH_TOKEN=1000.tu-refresh-token
```

#### Paso 3: Configura tu email

1. En tu `.env`:
   ```env
   ZOHO_FROM_EMAIL=tunombre@tudominio.com
   ZOHO_ACCOUNT_ID=tu-account-id
   ZOHO_DOMAIN=zoho.com
   ```

2. Para obtener `ZOHO_ACCOUNT_ID`:
   - Ve a Zoho Mail → Settings → Mail Accounts
   - El ID aparece en la URL o en la configuración

💰 **Costo**: Desde $1/usuario/mes (o usa un plan gratuito si tienes)

✅ **Verifica**: El sistema auto-refrescará el token cuando expire.

---

## 6. Google Calendar

**Para qué sirve**: Agendar reuniones y follow-ups automáticamente

### 📝 Opción A: Service Account (Recomendado)

#### Paso 1: Crea el proyecto en Google Cloud

1. Ve a: [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Crea un nuevo proyecto: `AiMedic Integration`
3. Habilita la API de Calendar:
   - **APIs & Services** → **Enable APIs and Services**
   - Busca: `Google Calendar API` → **Enable**

#### Paso 2: Crea Service Account

1. Ve a: **IAM & Admin** → **Service Accounts**
2. Click **"Create Service Account"**
3. Nombre: `aimedic-calendar-service`
4. Click **"Create and Continue"** → **"Done"**

#### Paso 3: Genera la clave

1. Click en la service account recién creada
2. Pestaña **"Keys"** → **"Add Key"** → **"Create new key"**
3. Formato: **JSON**
4. Se descargará un archivo `proyecto-123456-abc123.json`
5. Renómbralo a `google_service_account.json`
6. Guárdalo en la carpeta raíz del proyecto
7. En tu `.env`:
   ```env
   GOOGLE_SERVICE_ACCOUNT_FILE=google_service_account.json
   ```

#### Paso 4: Comparte tu calendario

1. Abre Google Calendar
2. Click en **Settings** (⚙️)
3. Selecciona tu calendario → **Share with specific people**
4. Agrega el email de tu service account (ej: `aimedic-calendar-service@proyecto.iam.gserviceaccount.com`)
5. Dale permisos: **"Make changes to events"**

💰 **Costo**: GRATIS (parte de Google Workspace)

✅ **Verifica**: El archivo JSON debe tener estas keys:
```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key": "...",
  "client_email": "..."
}
```

---

## 7. Verificación Final

### ✅ Checklist de Configuración

Ejecuta este comando para verificar qué está configurado:

```bash
python3 -c "
from health_scraper.config import config
for service, enabled in config.integrations_configured.items():
    status = '✅' if enabled else '❌'
    print(f'{status} {service}')
"
```

Deberías ver:

```
✅ gemini
✅ perplexity
✅ hubspot
✅ linear
✅ zoho_email
✅ google_calendar
✅ person_research
✅ outreach_drafting
✅ pipeline
✅ connect_api
```

### 🚀 Inicia el servidor

```bash
# Activa el entorno virtual
source .venv/bin/activate

# Inicia el servidor
python main.py
```

### 🧪 Prueba las integraciones

Abre: [http://localhost:8000/docs](http://localhost:8000/docs)

Prueba estos endpoints:

1. **HubSpot**: `POST /hubspot/companies`
2. **Linear**: `POST /linear/issues`
3. **Person Research**: `POST /research/person`
4. **Outreach Drafting**: `POST /outreach/draft`

---

## 🆘 Troubleshooting

### Problema: "Invalid API Key"

**Solución**:
- Verifica que copiaste la key completa (sin espacios al inicio/final)
- Revisa que no tenga comillas en el .env
- Reinicia el servidor después de cambiar el .env

### Problema: "HubSpot 403 Forbidden"

**Solución**:
- Verifica que diste todos los scopes necesarios en la Private App
- Regenera el token si es necesario

### Problema: "Linear team not found"

**Solución**:
- Deja `LINEAR_DEFAULT_TEAM_ID` vacío, se auto-detectará
- O verifica que el team ID sea correcto

---

## 📚 Recursos Adicionales

- **HubSpot API Docs**: https://developers.hubspot.com/docs/api/overview
- **Linear GraphQL Docs**: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
- **Perplexity API**: https://docs.perplexity.ai/
- **Gemini AI Studio**: https://ai.google.dev/docs

---

## 💡 Consejos Pro

1. **Empieza Gradual**: Configura primero Gemini y Perplexity (core), luego las integraciones
2. **Usa Variables de Entorno**: Nunca hardcodees API keys en el código
3. **Monitorea Costos**: Revisa regularmente el uso de APIs con costo
4. **Backups**: Guarda de forma segura tus API keys (ej: 1Password, Bitwarden)
5. **Testing**: Usa accounts de prueba antes de producción

---

¿Necesitas ayuda adicional? Revisa los logs en `health_scraper.log` o abre un issue.

¡Feliz scraping! 🚀
