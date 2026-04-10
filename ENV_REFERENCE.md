# 📋 Referencia Rápida de Variables de Entorno

Tabla completa de todas las variables disponibles en `.env`

---

## 🏢 Información Personal

| Variable | Obligatorio | Descripción | Ejemplo |
|----------|-------------|-------------|---------|
| `BUSINESS_NAME` | No | Nombre de tu empresa | `AiMedic` |
| `BUSINESS_DESCRIPTION` | No | Descripción del negocio | `Empresa de salud digital...` |
| `YOUR_NAME` | **Sí** | Tu nombre completo | `Juan Pérez` |
| `YOUR_ROLE` | **Sí** | Tu cargo/rol | `CEO`, `Business Development` |

---

## 🔧 Configuración General

| Variable | Obligatorio | Default | Descripción |
|----------|-------------|---------|-------------|
| `SCRAPER_MODE` | No | `development` | Modo de ejecución: `development` o `production` |
| `LOG_LEVEL` | No | `INFO` | Nivel de logs: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `API_HOST` | No | `0.0.0.0` | Host del servidor API |
| `API_PORT` | No | `8000` | Puerto del servidor API |
| `API_KEY` | No | - | API key para proteger tu servidor (opcional) |

---

## 💾 Base de Datos

| Variable | Obligatorio | Default | Descripción |
|----------|-------------|---------|-------------|
| `DATABASE_URL` | No | `sqlite:///health_institutions.db` | URL de conexión a la base de datos |

**Ejemplos:**
- SQLite local: `sqlite:///health_institutions.db`
- PostgreSQL: `postgresql://user:password@localhost:5432/dbname`
- MySQL: `mysql://user:password@localhost:3306/dbname`

---

## 🌐 Scraping / Selenium

| Variable | Obligatorio | Default | Descripción |
|----------|-------------|---------|-------------|
| `HEADLESS_MODE` | No | `True` | Ejecutar navegador sin interfaz gráfica |
| `SELENIUM_TIMEOUT` | No | `30` | Timeout en segundos para operaciones de Selenium |
| `RATE_LIMIT_DELAY` | No | `2` | Delay en segundos entre requests para evitar bloqueos |
| `LINKEDIN_ENABLED` | No | `True` | Habilitar scraping de LinkedIn |
| `TWITTER_ENABLED` | No | `True` | Habilitar scraping de Twitter |

---

## 🤖 Inteligencia Artificial (CORE)

### Google Gemini AI

| Variable | Obligatorio | Dónde obtener | Costo |
|----------|-------------|---------------|-------|
| `GOOGLE_AI_STUDIO` | **Sí** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | **GRATIS** |
| `VISION_MODEL` | No (auto) | - | Default: `gemini-1.5-flash` |

**Uso:** Redacción de mensajes personalizados, análisis de imágenes web

---

### Perplexity AI

| Variable | Obligatorio | Dónde obtener | Costo |
|----------|-------------|---------------|-------|
| `PERPLEXITY_API_KEY` | **Sí** | [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api) | **$20/mes** |

**Uso:** Investigación profunda de personas y empresas

---

## 📊 CRM & Ventas

### HubSpot

| Variable | Obligatorio | Descripción |
|----------|-------------|-------------|
| `HUBSPOT_ACCESS_TOKEN` | No | Token de Private App de HubSpot |

**Setup:**
1. HubSpot → Settings → Integrations → Private Apps
2. Crear app con scopes: `crm.objects.{companies,contacts,deals}.read/write`
3. Copiar Access Token

**Costo:** GRATIS

---

## 📋 Gestión de Proyectos

### Linear

| Variable | Obligatorio | Descripción |
|----------|-------------|-------------|
| `LINEAR_API_KEY` | No | Personal API Key de Linear |
| `LINEAR_DEFAULT_TEAM_ID` | No | ID del equipo por defecto (se auto-detecta si no se especifica) |

**Setup:**
1. Linear → Settings → API → Personal API Keys
2. Crear nueva key
3. (Opcional) Copiar Team ID desde Settings → Teams

**Costo:** GRATIS para equipos pequeños (<10 usuarios)

---

## 📧 Email Automation

### Zoho Mail

| Variable | Obligatorio | Descripción |
|----------|-------------|-------------|
| `ZOHO_CLIENT_ID` | No | Client ID de aplicación Zoho |
| `ZOHO_CLIENT_SECRET` | No | Client Secret de aplicación Zoho |
| `ZOHO_REFRESH_TOKEN` | No | Refresh token OAuth2 |
| `ZOHO_ACCOUNT_ID` | No | ID de tu cuenta de Zoho Mail |
| `ZOHO_FROM_EMAIL` | No | Email desde el que enviarás |
| `ZOHO_DOMAIN` | No | Default: `zoho.com` (o `.eu`, `.in`, etc.) |

**Setup:**
1. [api-console.zoho.com](https://api-console.zoho.com/) → Create Self Client
2. Generate OAuth tokens con scopes: `ZohoMail.messages.ALL`, `ZohoMail.accounts.READ`
3. Seguir flujo OAuth2 para obtener refresh token

**Costo:** Desde $1/usuario/mes

---

## 📅 Calendario

### Google Calendar

| Variable | Obligatorio | Descripción |
|----------|-------------|-------------|
| `GOOGLE_SERVICE_ACCOUNT_FILE` | No | Ruta al archivo JSON de service account |
| `GOOGLE_CREDENTIALS_FILE` | No | Ruta al archivo JSON de OAuth2 credentials |

**Setup (Service Account - recomendado):**
1. Google Cloud Console → IAM → Service Accounts → Create
2. Download JSON key → guardar como `google_service_account.json`
3. Compartir calendario con email de service account

**Setup (OAuth2 - desarrollo):**
1. Google Cloud Console → APIs → Credentials → OAuth 2.0
2. Download como `credentials.json`

**Costo:** GRATIS

---

## ⚙️ Configuración Avanzada

| Variable | Obligatorio | Default | Descripción |
|----------|-------------|---------|-------------|
| `PIPELINE_AUTO_SNAPSHOT` | No | `True` | Auto-guardar snapshots del pipeline |
| `CONNECT_API_ENABLED` | No | `True` | Habilitar Connect API |

---

## 📊 Resumen de Prioridades

### ✅ Configuración Mínima (para empezar)

```env
YOUR_NAME=Tu Nombre
YOUR_ROLE=CEO
GOOGLE_AI_STUDIO=AIzaSy...
PERPLEXITY_API_KEY=pplx-...
```

### ⭐ Configuración Recomendada (completa)

Mínima + estas integraciones:

```env
HUBSPOT_ACCESS_TOKEN=pat-na1-...
LINEAR_API_KEY=lin_api_...
GOOGLE_SERVICE_ACCOUNT_FILE=google_service_account.json
```

### 🚀 Configuración Máxima (todas las funcionalidades)

Todas las anteriores + Zoho Email

---

## 💰 Resumen de Costos

| Servicio | Costo Mensual | Estado | Nota |
|----------|---------------|--------|------|
| Google Gemini | **GRATIS** | Obligatorio | Incluido |
| Perplexity | **$20** | Obligatorio | Necesario |
| HubSpot | **GRATIS** | Opcional | Plan free disponible |
| Linear | **GRATIS** | Opcional | <10 usuarios |
| Google Calendar | **GRATIS** | Opcional | Part of Google |
| Zoho Mail | **$1-5** | Opcional | Según plan |
| **TOTAL MÍNIMO** | **$20/mes** | | Solo APIs core |
| **TOTAL COMPLETO** | **~$25/mes** | | Con todas las integraciones |

---

## 🔒 Seguridad

### ⚠️ NUNCA hagas esto:

- ❌ Compartir tu archivo `.env`
- ❌ Subir `.env` a Git (ya está en `.gitignore`)
- ❌ Exponer API keys en el código
- ❌ Compartir logs que contengan keys

### ✅ Buenas prácticas:

- ✅ Usa un password manager para guardar API keys
- ✅ Regenera keys si sospechas que fueron comprometidas
- ✅ Usa diferentes keys para desarrollo y producción
- ✅ Revisa los logs de uso de las APIs regularmente

---

## 🔍 Verificación

Para verificar tu configuración actual:

```bash
python check_config.py
```

---

## 📚 Recursos

- **Guía Completa**: [GUIA_CONFIGURACION.md](GUIA_CONFIGURACION.md)
- **Setup Rápido**: [SETUP_RAPIDO.md](SETUP_RAPIDO.md)
- **Setup Interactivo**: `python setup_env.py`
- **Documentación API**: http://localhost:8000/docs (después de iniciar)

---

**Última actualización:** 2026-03-08
