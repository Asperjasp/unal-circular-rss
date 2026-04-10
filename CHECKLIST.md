# ✅ Checklist de Configuración - AiMedic Scrapper Salud

Usa este checklist para asegurarte de que tienes todo configurado correctamente.

---

## 📦 Fase 1: Instalación Básica

- [ ] **Clonar/descargar el repositorio**
- [ ] **Crear y activar entorno virtual**
  ```bash
  python -m venv .venv
  source .venv/bin/activate  # En Linux/Mac
  # O: .venv\Scripts\activate  # En Windows
  ```
- [ ] **Instalar dependencias**
  ```bash
  pip install -r requirements.txt
  ```

---

## 🔑 Fase 2: APIs Obligatorias (Core)

### Google Gemini AI (GRATIS)

- [ ] **Ir a:** [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- [ ] **Crear API Key**
- [ ] **Copiar key** (empieza con `AIzaSy...`)
- [ ] **Guardar en lugar seguro**

### Perplexity AI ($20/mes)

- [ ] **Crear cuenta en:** [https://www.perplexity.ai/](https://www.perplexity.ai/)
- [ ] **Ir a:** [https://www.perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)
- [ ] **Generar API Key**
- [ ] **Copiar key** (empieza con `pplx-...`)
- [ ] **Activar plan de pago** (necesario para API)
- [ ] **Guardar en lugar seguro**

---

## ⚙️ Fase 3: Configuración del .env

### Opción A: Asistente Interactivo (Recomendado)

- [ ] **Ejecutar asistente:**
  ```bash
  python setup_env.py
  ```
- [ ] **Seguir las instrucciones** y completar los campos

### Opción B: Configuración Manual

- [ ] **Copiar template:**
  ```bash
  cp .env.template .env
  ```
- [ ] **Editar `.env` con tu editor favorito**
- [ ] **Completar campos obligatorios:**
  - [ ] `YOUR_NAME`
  - [ ] `YOUR_ROLE`
  - [ ] `GOOGLE_AI_STUDIO`
  - [ ] `PERPLEXITY_API_KEY`

---

## 🧪 Fase 4: Verificación

- [ ] **Verificar configuración:**
  ```bash
  python check_config.py
  ```
- [ ] **Confirmar que todos los obligatorios están ✓**
- [ ] **Leer las advertencias de opcionales (si las hay)**

---

## 🚀 Fase 5: Primera Ejecución

- [ ] **Iniciar servidor:**
  ```bash
  python main.py
  ```
- [ ] **Verificar que inicia sin errores**
- [ ] **Abrir en navegador:** [http://localhost:8000/docs](http://localhost:8000/docs)
- [ ] **Ver documentación interactiva de la API**

---

## 🧪 Fase 6: Test de Funcionalidad Core

- [ ] **Ejecutar tests básicos:**
  ```bash
  ./test_integrations.sh core
  ```
- [ ] **Verificar que funcionan:**
  - [ ] Health check
  - [ ] Person research
  - [ ] Outreach drafting
  - [ ] Full pipeline

### Test Manual Rápido

En el navegador ([http://localhost:8000/docs](http://localhost:8000/docs)):

- [ ] **Probar endpoint:** `POST /api/v1/integrations/pipeline/research-and-draft`
- [ ] **Usar estos datos de prueba:**
  ```json
  {
    "name": "Dr. Juan Pérez",
    "context": "Visto en Twitter hablando de IA en hospitales",
    "company": "Hospital San José",
    "tone": "professional",
    "language": "es",
    "goal": "Explorar colaboración en IA diagnóstica"
  }
  ```
- [ ] **Verificar respuesta con:**
  - [ ] Datos de investigación del contacto
  - [ ] Mensaje de outreach personalizado
  - [ ] Canales de contacto sugeridos

---

## 📊 Fase 7: Integraciones Opcionales (Recomendadas)

### HubSpot CRM (GRATIS)

- [ ] **Leer:** [GUIA_CONFIGURACION.md](GUIA_CONFIGURACION.md#3-hubspot-crm) sección 3
- [ ] **Ir a HubSpot Settings → Integrations → Private Apps**
- [ ] **Crear Private App** con nombre: `AiMedic Scraper`
- [ ] **Activar scopes:**
  - [ ] `crm.objects.companies.read`
  - [ ] `crm.objects.companies.write`
  - [ ] `crm.objects.contacts.read`
  - [ ] `crm.objects.contacts.write`
- [ ] **Copiar Access Token**
- [ ] **Agregar a `.env`:** `HUBSPOT_ACCESS_TOKEN=...`
- [ ] **Probar:**
  ```bash
  ./test_integrations.sh hubspot
  ```

### Linear (GRATIS)

- [ ] **Leer:** [GUIA_CONFIGURACION.md](GUIA_CONFIGURACION.md#4-linear-project-management) sección 4
- [ ] **Ir a Linear Settings → API → Personal API Keys**
- [ ] **Crear nueva API Key** con nombre: `AiMedic`
- [ ] **Copiar key**
- [ ] **Agregar a `.env`:** `LINEAR_API_KEY=...`
- [ ] **(Opcional) Copiar Team ID**
- [ ] **Probar:**
  ```bash
  ./test_integrations.sh linear
  ```

### Zoho Email ($1-5/mes)

- [ ] **Leer:** [GUIA_CONFIGURACION.md](GUIA_CONFIGURACION.md#5-zoho-email) sección 5
- [ ] **Ir a:** [https://api-console.zoho.com/](https://api-console.zoho.com/)
- [ ] **Crear Self Client** con nombre: `AiMedic Email`
- [ ] **Copiar Client ID y Client Secret**
- [ ] **Generar Refresh Token** (seguir pasos de la guía)
- [ ] **Agregar a `.env`:**
  - [ ] `ZOHO_CLIENT_ID`
  - [ ] `ZOHO_CLIENT_SECRET`
  - [ ] `ZOHO_REFRESH_TOKEN`
  - [ ] `ZOHO_ACCOUNT_ID`
  - [ ] `ZOHO_FROM_EMAIL`
- [ ] **Probar:**
  ```bash
  ./test_integrations.sh zoho
  ```
  (⚠️ Esto envía un email real, editar el script primero)

### Google Calendar (GRATIS)

- [ ] **Leer:** [GUIA_CONFIGURACION.md](GUIA_CONFIGURACION.md#6-google-calendar) sección 6
- [ ] **Ir a:** [https://console.cloud.google.com/](https://console.cloud.google.com/)
- [ ] **Crear proyecto:** `AiMedic Integration`
- [ ] **Habilitar Google Calendar API**
- [ ] **Crear Service Account**
- [ ] **Descargar JSON key**
- [ ] **Renombrar archivo a:** `google_service_account.json`
- [ ] **Guardar en carpeta raíz del proyecto**
- [ ] **Compartir calendario** con email de service account
- [ ] **Agregar a `.env`:** `GOOGLE_SERVICE_ACCOUNT_FILE=google_service_account.json`
- [ ] **Probar:**
  ```bash
  ./test_integrations.sh calendar
  ```
  (⚠️ Esto crea un evento real, editar el script primero)

---

## 🎯 Fase 8: Verificación Final

- [ ] **Ejecutar verificación completa:**
  ```bash
  python check_config.py
  ```
- [ ] **Verificar que todo muestra ✓**
- [ ] **Probar todas las integraciones:**
  ```bash
  ./test_integrations.sh all
  ```

---

## 📚 Fase 9: Conocer el Sistema

- [ ] **Leer:** [README.md](README.md) - Overview general
- [ ] **Leer:** [SETUP_RAPIDO.md](SETUP_RAPIDO.md) - Referencia rápida
- [ ] **Explorar:** [http://localhost:8000/docs](http://localhost:8000/docs) - API completa
- [ ] **Revisar logs:** `tail -f health_scraper.log`
- [ ] **Explorar base de datos:**
  ```bash
  sqlite3 health_institutions.db
  .tables
  .exit
  ```

---

## 🎓 Fase 10: Primer Uso Real

### Flujo Completo de Trabajo

1. **Descubres una persona potencial** (Twitter, LinkedIn, conferencia, etc.)

2. **Usas el endpoint principal:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/integrations/pipeline/research-and-draft" \
        -H "Content-Type: application/json" \
        -d '{
          "name": "Nombre Real",
          "context": "Dónde lo viste y por qué te interesa",
          "company": "Su empresa",
          "twitter_handle": "su_twitter",
          "tone": "professional",
          "language": "es",
          "goal": "Tu objetivo con este contacto"
        }'
   ```

3. **Recibes:**
   - ✅ Investigación completa del contacto
   - ✅ Mensaje personalizado listo para enviar
   - ✅ Canales de contacto sugeridos

4. **Copiar y enviar** el mensaje via LinkedIn, Email, Twitter, etc.

5. **(Opcional) Si tienes HubSpot:** El contacto se guarda automáticamente en tu CRM

6. **(Opcional) Si tienes Linear:** Se crea una tarea de seguimiento

---

## 💰 Resumen de Costos

| Componente | Costo | ¿Obligatorio? |
|------------|-------|---------------|
| Google Gemini | **GRATIS** | ✅ Sí |
| Perplexity AI | **$20/mes** | ✅ Sí |
| HubSpot CRM | **GRATIS** | ❌ No (recomendado) |
| Linear | **GRATIS** | ❌ No (recomendado) |
| Google Calendar | **GRATIS** | ❌ No |
| Zoho Email | **$1-5/mes** | ❌ No |
| **TOTAL MÍNIMO** | **$20/mes** | Core funcionando |
| **TOTAL RECOMENDADO** | **$20/mes** | Con CRM y PM |
| **TOTAL COMPLETO** | **$25/mes** | Con todo |

---

## 🆘 Si Algo Sale Mal

### El servidor no inicia

- [ ] Verificar que `.env` existe
- [ ] Ejecutar `python check_config.py`
- [ ] Ver logs: `health_scraper.log`
- [ ] Verificar que las dependencias están instaladas

### Las APIs no funcionan

- [ ] Verificar que las API keys son correctas
- [ ] Verificar que no tienen espacios ni comillas
- [ ] Reiniciar el servidor después de cambiar `.env`
- [ ] Ver logs de errores específicos

### HubSpot devuelve 403

- [ ] Verificar que todos los scopes están activados
- [ ] Regenerar el token si es necesario

### Linear no encuentra el team

- [ ] Dejar `LINEAR_DEFAULT_TEAM_ID` vacío (se auto-detecta)
- [ ] Verificar que la API key es correcta

---

## 🎉 ¡Todo Listo!

Una vez que hayas completado este checklist, tendrás:

✅ Un sistema completo de research y outreach  
✅ Integración con CRM (opcional)  
✅ Gestión automática de tareas (opcional)  
✅ Todo centralizado y automatizado  

**¿Próximos pasos?**

1. Empieza a usar el sistema con contactos reales
2. Refina tus mensajes según las respuestas
3. Ajusta los prompts si es necesario
4. Explora endpoints adicionales en `/docs`

---

## 📞 Recursos de Ayuda

- **Guía Completa:** [GUIA_CONFIGURACION.md](GUIA_CONFIGURACION.md)
- **Setup Rápido:** [SETUP_RAPIDO.md](SETUP_RAPIDO.md)
- **Referencia de Variables:** [ENV_REFERENCE.md](ENV_REFERENCE.md)
- **API Docs:** http://localhost:8000/docs
- **Logs:** `health_scraper.log`

---

**Última actualización:** 2026-03-08

¡Feliz networking automatizado! 🚀
