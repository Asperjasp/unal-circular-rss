# 📦 Resumen de Configuración Completa - AiMedic Scrapper Salud

¡He creado un sistema completo de configuración para tu proyecto! Aquí está todo lo que necesitas saber.

---

## 🎯 ¿Qué tengo que hacer ahora?

### Opción 1: Setup Rápido (5 minutos) 🚀

```bash
# 1. Crear tu archivo de configuración (interactivo)
python setup_env.py

# 2. Verificar que todo esté bien
python check_config.py

# 3. ¡Iniciar!
python main.py
```

### Opción 2: Solo lo Mínimo (2 minutos) ⚡

```bash
# 1. Copiar template
cp .env.template .env

# 2. Editar .env y completar SOLO estos campos:
#    - YOUR_NAME
#    - YOUR_ROLE
#    - GOOGLE_AI_STUDIO (https://aistudio.google.com/apikey)
#    - PERPLEXITY_API_KEY (https://www.perplexity.ai/settings/api)

# 3. Verificar
python check_config.py

# 4. ¡Iniciar!
python main.py
```

---

## 📚 Nuevos Archivos Creados

He creado **7 archivos nuevos** para ayudarte con la configuración:

### 📖 Guías y Documentación

1. **`GUIA_CONFIGURACION.md`** 
   - 📖 Guía COMPLETA paso a paso de TODAS las integraciones
   - Para cada servicio: cómo obtener las API keys, configurar permisos, etc.
   - Lee esto si necesitas ayuda detallada

2. **`SETUP_RAPIDO.md`** 
   - 🚀 Versión resumida para empezar RÁPIDO (5 min)
   - Links directos a cada servicio
   - Setup en 2 minutos por integración

3. **`ENV_REFERENCE.md`** 
   - 📋 Tabla completa de todas las variables de entorno
   - Qué hace cada una, si es obligatoria, costos, etc.
   - Perfecto como referencia rápida

4. **`CHECKLIST.md`** 
   - ✅ Checklist paso a paso con checkboxes
   - Marca cada paso a medida que lo completas
   - Para asegurarte de no olvidar nada

### 🛠️ Archivos de Configuración

5. **`.env.template`** 
   - 🔧 Template del archivo .env con TODO bien documentado
   - Incluye comentarios en español
   - Indica qué es obligatorio, costos, y links

6. **`.env.example`** (actualizado)
   - 📝 Versión actualizada y mejorada
   - Con referencias a las guías

### 🔧 Scripts de Ayuda

7. **`setup_env.py`** 
   - 🤖 Asistente INTERACTIVO para crear tu .env
   - Te guía paso a paso preguntándote cada campo
   - Ejecutar: `python setup_env.py`

8. **`check_config.py`** 
   - ✅ Verifica tu configuración actual
   - Te dice qué falta y qué está bien configurado
   - Ejecutar: `python check_config.py`

9. **`test_integrations.sh`** 
   - 🧪 Prueba TODAS las integraciones automáticamente
   - Ejecutar: `./test_integrations.sh`
   - O prueba específicas: `./test_integrations.sh hubspot`

### 📝 README Actualizado

10. **`README.md`** (actualizado)
    - Ahora incluye sección de configuración al inicio
    - Con links a todas las guías

---

## 🔑 APIs que Necesitas Configurar

### ✅ OBLIGATORIAS (para que funcione)

| API | Costo | Dónde obtenerla | Para qué sirve |
|-----|-------|----------------|----------------|
| **Google Gemini** | GRATIS | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Redacción de mensajes |
| **Perplexity** | $20/mes | [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api) | Investigación de personas |

### ⭐ RECOMENDADAS (mejoran mucho la experiencia)

| API | Costo | Dónde obtenerla | Para qué sirve |
|-----|-------|----------------|----------------|
| **HubSpot** | GRATIS | Settings → Integrations → Private Apps | CRM automático |
| **Linear** | GRATIS | Settings → API → Personal Keys | Gestión de tareas |

### 🎁 OPCIONALES (bonuses)

| API | Costo | Dónde obtenerla | Para qué sirve |
|-----|-------|----------------|----------------|
| **Zoho Email** | $1-5/mes | [api-console.zoho.com](https://api-console.zoho.com/) | Envío automático de emails |
| **Google Calendar** | GRATIS | [console.cloud.google.com](https://console.cloud.google.com/) | Agendar reuniones |

---

## 💰 Costo Total

| Configuración | Costo Mensual | ¿Qué incluye? |
|---------------|---------------|---------------|
| **Mínima** | **$20** | Solo Core (Gemini + Perplexity) |
| **Recomendada** | **$20** | Core + HubSpot + Linear (todos GRATIS excepto Perplexity) |
| **Completa** | **$25** | Todo incluido |

💡 **Mi recomendación:** Empieza con la Mínima ($20), y cuando necesites más funcionalidad, agrega HubSpot y Linear (que son gratis).

---

## 🚀 Flujo de Configuración Recomendado

```
1. Ejecutar setup_env.py
   ↓
2. Completar las APIs OBLIGATORIAS (Gemini + Perplexity)
   ↓
3. Ejecutar check_config.py
   ↓
4. Iniciar servidor: python main.py
   ↓
5. Probar: ./test_integrations.sh core
   ↓
6. (Opcional) Configurar HubSpot
   ↓
7. (Opcional) Configurar Linear
   ↓
8. ¡A trabajar! 🎉
```

---

## 📖 ¿Qué Guía Debo Leer?

Depende de tu situación:

### "Quiero empezar YA, sin leer mucho"
👉 **Lee:** [SETUP_RAPIDO.md](SETUP_RAPIDO.md)  
⏱️ Tiempo: 5 minutos

### "Quiero entender todo en detalle"
👉 **Lee:** [GUIA_CONFIGURACION.md](GUIA_CONFIGURACION.md)  
⏱️ Tiempo: 15 minutos

### "Solo necesito ver qué variables hay"
👉 **Lee:** [ENV_REFERENCE.md](ENV_REFERENCE.md)  
⏱️ Tiempo: 2 minutos (es una tabla)

### "Quiero una checklist para no olvidar nada"
👉 **Lee:** [CHECKLIST.md](CHECKLIST.md)  
⏱️ Tiempo: Úsalo mientras configuras

### "Solo dime qué ejecutar"
👉 **Ejecuta:**
```bash
python setup_env.py
python check_config.py
python main.py
```

---

## 🎯 Variables de Entorno - Resumen Ultra-Rápido

### Lo MÍNIMO que necesitas en tu `.env`:

```env
# Tu información
YOUR_NAME=Tu Nombre
YOUR_ROLE=CEO

# APIs obligatorias
GOOGLE_AI_STUDIO=AIzaSy...          # GRATIS en aistudio.google.com/apikey
PERPLEXITY_API_KEY=pplx-...         # $20/mes en perplexity.ai/settings/api
```

### Con HubSpot (recomendado):

```env
# + Lo anterior
HUBSPOT_ACCESS_TOKEN=pat-na1-...    # GRATIS en HubSpot Settings
```

### Con Linear (recomendado):

```env
# + Lo anterior
LINEAR_API_KEY=lin_api_...          # GRATIS en Linear Settings
```

### Completo (todas las integraciones):

```env
# + Todo lo anterior

# Zoho Email
ZOHO_CLIENT_ID=...
ZOHO_CLIENT_SECRET=...
ZOHO_REFRESH_TOKEN=...
ZOHO_ACCOUNT_ID=...
ZOHO_FROM_EMAIL=...

# Google Calendar
GOOGLE_SERVICE_ACCOUNT_FILE=google_service_account.json
```

---

## 🔧 Comandos Útiles

```bash
# Crear .env interactivamente
python setup_env.py

# Verificar configuración
python check_config.py

# Iniciar servidor
python main.py

# Probar todas las integraciones
./test_integrations.sh all

# Probar solo las core
./test_integrations.sh core

# Probar solo HubSpot
./test_integrations.sh hubspot

# Ver logs en tiempo real
tail -f health_scraper.log

# Ver documentación API
# (después de iniciar el servidor)
# Abrir: http://localhost:8000/docs
```

---

## 🎓 Ejemplo de Uso Completo

Una vez configurado, así usarás el sistema:

```bash
# 1. Ves a alguien interesante en Twitter
# 2. Llamas al endpoint principal:

curl -X POST "http://localhost:8000/api/v1/integrations/pipeline/research-and-draft" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Dr. María López",
       "context": "Vista en Twitter hablando de IA en salud",
       "twitter_handle": "marialopezmD",
       "company": "Hospital San José",
       "tone": "professional",
       "language": "es",
       "goal": "Colaboración en IA diagnóstica"
     }'

# 3. Recibes:
#    ✅ Investigación completa de la persona
#    ✅ Mensaje personalizado listo para enviar
#    ✅ Canales de contacto sugeridos
#    ✅ (Opcional) Se guarda en HubSpot
#    ✅ (Opcional) Se crea tarea en Linear

# 4. Copias el mensaje y lo envías via LinkedIn/Email
```

---

## 🆘 Troubleshooting Rápido

### Error: ".env not found"
```bash
python setup_env.py
# O copiarlo manualmente:
cp .env.template .env
```

### Error: "Invalid API Key"
```bash
# 1. Verifica que la key esté correcta (sin espacios)
# 2. Verifica que no tenga comillas en el .env
# 3. Reinicia el servidor
python check_config.py
```

### Error: "Module not found"
```bash
pip install -r requirements.txt
```

### El servidor no inicia
```bash
# Ver qué falta:
python check_config.py

# Ver logs:
tail health_scraper.log
```

---

## 📞 Recursos

- **Guía Completa:** [GUIA_CONFIGURACION.md](GUIA_CONFIGURACION.md) - Todo en detalle
- **Setup Rápido:** [SETUP_RAPIDO.md](SETUP_RAPIDO.md) - 5 minutos
- **Referencia Variables:** [ENV_REFERENCE.md](ENV_REFERENCE.md) - Tabla completa
- **Checklist:** [CHECKLIST.md](CHECKLIST.md) - Paso a paso
- **API Docs:** http://localhost:8000/docs - Después de iniciar
- **Logs:** `health_scraper.log` - Para debugging

---

## ✨ Resumen Final

### Lo que tienes ahora:

✅ **7 archivos nuevos** de documentación completa  
✅ **3 scripts de ayuda** para setup automático  
✅ **Guías paso a paso** para cada integración  
✅ **Sistema de verificación** de configuración  
✅ **Tests automáticos** de todas las APIs  
✅ **Referencias rápidas** y checklists  

### Próximos pasos:

1. **Ejecuta:** `python setup_env.py` (o `cp .env.template .env`)
2. **Completa** las APIs obligatorias (Gemini + Perplexity)
3. **Verifica:** `python check_config.py`
4. **Inicia:** `python main.py`
5. **Prueba:** `./test_integrations.sh core`
6. **¡A trabajar!** 🚀

---

## 🎉 ¡Ya está todo listo!

Tienes todo lo necesario para configurar y usar el sistema al 100%. 

**¿Por dónde empiezo?**

Si tienes 2 minutos: Ejecuta `python setup_env.py`  
Si tienes 5 minutos: Lee [SETUP_RAPIDO.md](SETUP_RAPIDO.md)  
Si tienes 15 minutos: Lee [GUIA_CONFIGURACION.md](GUIA_CONFIGURACION.md)  

**¿Dudas?** Todo está explicado en las guías. ¡Adelante! 🚀

---

**Creado el:** 2026-03-08  
**Versión:** 1.0
