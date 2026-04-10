# 🚀 Resumen Rápido de Configuración

¿Necesitas configurar todo rápido? Aquí está lo esencial.

---

## ⚡ Setup en 5 Minutos

### 1️⃣ Crea tu archivo de configuración
```bash
cp .env.template .env
```

### 2️⃣ Completa estos campos OBLIGATORIOS en `.env`:

```env
# Tu información
YOUR_NAME=Tu Nombre
YOUR_ROLE=CEO

# APIs Core (OBLIGATORIAS)
GOOGLE_AI_STUDIO=AIzaSy...    # https://aistudio.google.com/apikey (GRATIS)
PERPLEXITY_API_KEY=pplx-...   # https://www.perplexity.ai/settings/api (~$20/mes)
```

### 3️⃣ Verifica tu configuración
```bash
python check_config.py
```

### 4️⃣ ¡Inicia el servidor!
```bash
python main.py
```

---

## 🔑 Dónde Obtener Cada API Key (Links Directos)

| Servicio | Link Directo | Costo | Obligatorio |
|----------|-------------|-------|-------------|
| **Google Gemini** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | GRATIS | ✅ SÍ |
| **Perplexity** | [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api) | $20/mes | ✅ SÍ |
| **HubSpot** | HubSpot → Settings → Integrations → Private Apps | GRATIS | ❌ No |
| **Linear** | Linear → Settings → API | GRATIS | ❌ No |
| **Zoho Mail** | [api-console.zoho.com](https://api-console.zoho.com/) | $1+/mes | ❌ No |
| **Google Calendar** | [console.cloud.google.com](https://console.cloud.google.com/) | GRATIS | ❌ No |

---

## 📊 HubSpot - Setup en 2 Minutos

**1.** Ve a tu HubSpot → **Settings** (⚙️) → **Integrations** → **Private Apps**

**2.** Click **"Create a private app"**
   - Name: `AiMedic Scraper`

**3.** En la pestaña **Scopes**, activa:
   - ✅ `crm.objects.companies.read`
   - ✅ `crm.objects.companies.write`
   - ✅ `crm.objects.contacts.read`
   - ✅ `crm.objects.contacts.write`

**4.** Copia el **Access Token** (empieza con `pat-na1-...`)

**5.** En tu `.env`:
```env
HUBSPOT_ACCESS_TOKEN=pat-na1-tu-token-aqui
```

✅ **Listo!**

---

## 📋 Linear - Setup en 1 Minuto

**1.** Ve a Linear → **Settings** → **API** → **Personal API Keys**

**2.** Click **"Create new API key"**
   - Name: `AiMedic`

**3.** Copia la key (empieza con `lin_api_...`)

**4.** En tu `.env`:
```env
LINEAR_API_KEY=lin_api_tu-key-aqui
```

✅ **Listo!**

---

## 🤖 Google Gemini - Setup en 30 Segundos

**1.** Ve a: [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)

**2.** Click **"Create API Key"**

**3.** Copia la key (empieza con `AIzaSy...`)

**4.** En tu `.env`:
```env
GOOGLE_AI_STUDIO=AIzaSy-tu-key-aqui
```

✅ **Listo!** GRATIS con 15 requests/min

---

## 🔍 Perplexity - Setup en 1 Minuto

**1.** Crea cuenta en: [https://www.perplexity.ai/](https://www.perplexity.ai/)

**2.** Ve a: [https://www.perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)

**3.** Click **"Generate API Key"**

**4.** Copia la key (empieza con `pplx-...`)

**5.** En tu `.env`:
```env
PERPLEXITY_API_KEY=pplx-tu-key-aqui
```

💰 **Plan recomendado**: $20/mes (incluye 1000 requests)

---

## 📧 Zoho Email - Setup (5 min)

### Paso 1: Crea la aplicación
1. Ve a: [https://api-console.zoho.com/](https://api-console.zoho.com/)
2. Click **"Add Client"** → **"Self Client"**
3. Name: `AiMedic Email`
4. Copia **Client ID** y **Client Secret**

### Paso 2: Genera el Refresh Token
1. En el API Console, tab **"Generate Code"**
2. Scope: `ZohoMail.messages.ALL,ZohoMail.accounts.READ`
3. Click **"Generate"** → Copia el **Code**

4. En tu terminal (reemplaza los valores):
```bash
curl -X POST https://accounts.zoho.com/oauth/v2/token \
  -d "code=TU_CODE" \
  -d "client_id=TU_CLIENT_ID" \
  -d "client_secret=TU_CLIENT_SECRET" \
  -d "grant_type=authorization_code"
```

5. Copia el `refresh_token` de la respuesta JSON

### Paso 3: En tu `.env`:
```env
ZOHO_CLIENT_ID=1000.tu-client-id
ZOHO_CLIENT_SECRET=tu-client-secret
ZOHO_REFRESH_TOKEN=1000.tu-refresh-token
ZOHO_FROM_EMAIL=tu-email@tudominio.com
```

✅ **Listo!**

---

## 📅 Google Calendar - Setup (5 min)

### Opción Recomendada: Service Account

**1.** Ve a: [https://console.cloud.google.com/](https://console.cloud.google.com/)

**2.** Crea proyecto: `AiMedic Integration`

**3.** Habilita **Google Calendar API**:
   - **APIs & Services** → **Enable APIs** → Busca "Calendar"

**4.** Crea Service Account:
   - **IAM & Admin** → **Service Accounts** → **Create**
   - Name: `aimedic-calendar`

**5.** Genera clave JSON:
   - Click en la service account → **Keys** → **Add Key** → **JSON**
   - Descarga el archivo → Renómbralo a `google_service_account.json`
   - Guárdalo en la carpeta raíz del proyecto

**6.** Comparte tu calendario:
   - Google Calendar → Settings → Tu calendario
   - **Share** → Agrega el email de la service account
   - Permisos: **"Make changes to events"**

**7.** En tu `.env`:
```env
GOOGLE_SERVICE_ACCOUNT_FILE=google_service_account.json
```

✅ **Listo!**

---

## 🧪 Verificación Rápida

Ejecuta este comando para ver qué está configurado:

```bash
python check_config.py
```

Deberías ver algo como:

```
✓ GOOGLE_AI_STUDIO         AIzaSy...xyz
✓ PERPLEXITY_API_KEY       pplx-...abc
✓ HUBSPOT_ACCESS_TOKEN     pat-na1...def
✓ LINEAR_API_KEY           lin_api...ghi
```

---

## 🔥 Comandos Útiles

```bash
# Copiar template de configuración
cp .env.template .env

# Verificar configuración
python check_config.py

# Iniciar servidor
python main.py

# Ver logs
tail -f health_scraper.log

# Probar las APIs
curl http://localhost:8000/docs
```

---

## 🆘 Solución de Problemas Comunes

### ❌ "Invalid API Key"
- Verifica que copiaste la key completa (sin espacios)
- Revisa que no tenga comillas en el .env
- Reinicia el servidor

### ❌ "HubSpot 403 Forbidden"
- Verifica que diste todos los scopes en la Private App
- Regenera el token si es necesario

### ❌ ".env not found"
```bash
cp .env.template .env
# Luego edita .env con tus keys
```

### ❌ "Module not found"
```bash
pip install -r requirements.txt
```

---

## 💰 Costos Totales Estimados

| Item | Costo Mensual | Notas |
|------|--------------|-------|
| Google Gemini | **GRATIS** | 15 req/min |
| Perplexity | **$20** | Plan básico |
| HubSpot | **GRATIS** | Plan free |
| Linear | **GRATIS** | Equipos <10 |
| Zoho Email | **$1-5** | Según plan |
| Google Calendar | **GRATIS** | Incluido en Google |
| **TOTAL** | **~$25/mes** | |

💡 **Tip**: Empieza solo con las APIs obligatorias ($20/mes), luego agrega integraciones según las necesites.

---

## 📚 Más Info

- **Guía Completa**: [GUIA_CONFIGURACION.md](GUIA_CONFIGURACION.md)
- **API Docs**: http://localhost:8000/docs (después de iniciar)
- **Logs**: `health_scraper.log`

---

**¿Listo para empezar?** 🚀

```bash
python main.py
```

Abre: [http://localhost:8000/docs](http://localhost:8000/docs)
