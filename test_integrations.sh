#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# Script de Testing de Integraciones - Scrapper Salud AiMedic
# ═══════════════════════════════════════════════════════════════════════════
# 
# Prueba todas las integraciones configuradas
# 
# Uso:
#   ./test_integrations.sh
#
# O prueba integraciones específicas:
#   ./test_integrations.sh hubspot
#   ./test_integrations.sh linear
#   ./test_integrations.sh all
# ═══════════════════════════════════════════════════════════════════════════

BASE_URL="http://localhost:8000"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para printear headers
print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}\n"
}

# Función para verificar si el servidor está corriendo
check_server() {
    echo -e "${YELLOW}Verificando servidor...${NC}"
    if curl -s "${BASE_URL}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Servidor corriendo en ${BASE_URL}${NC}\n"
        return 0
    else
        echo -e "${RED}✗ El servidor no está corriendo en ${BASE_URL}${NC}"
        echo -e "${YELLOW}Inicia el servidor con: python main.py${NC}\n"
        return 1
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: Health Check
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
test_health() {
    print_header "🏥 Health Check"
    
    echo -e "${YELLOW}GET ${BASE_URL}/health${NC}"
    response=$(curl -s "${BASE_URL}/health")
    echo "$response" | jq . 2>/dev/null || echo "$response"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: Person Research (Perplexity)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
test_person_research() {
    print_header "🔍 Person Research (Perplexity AI)"
    
    echo -e "${YELLOW}POST ${BASE_URL}/api/v1/integrations/research/person${NC}\n"
    
    curl -X POST "${BASE_URL}/api/v1/integrations/research/person" \
         -H "Content-Type: application/json" \
         -d '{
           "name": "Dr. Luis García",
           "context": "Médico especialista en cardiología mencionado en conferencia",
           "company": "Hospital San José"
         }' | jq . 2>/dev/null || echo "Error al parsear respuesta"
    
    echo -e "\n"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: Outreach Drafting (Gemini)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
test_outreach_drafting() {
    print_header "✍️  Outreach Drafting (Google Gemini)"
    
    echo -e "${YELLOW}POST ${BASE_URL}/api/v1/integrations/outreach/draft${NC}\n"
    
    curl -X POST "${BASE_URL}/api/v1/integrations/outreach/draft" \
         -H "Content-Type: application/json" \
         -d '{
           "research_data": {
             "name": "Dr. Luis García",
             "title": "Director de Innovación",
             "company": "Hospital San José",
             "bio": "Especialista en implementación de tecnologías médicas",
             "interests": ["AI en salud", "telemedicina", "innovación hospitalaria"]
           },
           "tone": "professional",
           "language": "es",
           "goal": "Explorar colaboración en IA diagnóstica"
         }' | jq . 2>/dev/null || echo "Error al parsear respuesta"
    
    echo -e "\n"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: Full Pipeline (Research + Draft)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
test_full_pipeline() {
    print_header "🚀 Full Pipeline (Research + Draft)"
    
    echo -e "${YELLOW}POST ${BASE_URL}/api/v1/integrations/pipeline/research-and-draft${NC}\n"
    
    curl -X POST "${BASE_URL}/api/v1/integrations/pipeline/research-and-draft" \
         -H "Content-Type: application/json" \
         -d '{
           "name": "Dr. María Rodríguez",
           "context": "Vista en Twitter discutiendo IA en hospitales colombianos",
           "twitter_handle": "mariarodriguezmd",
           "company": "Hospital Universitario San Ignacio",
           "tone": "warm",
           "language": "es",
           "goal": "Explorar asociación para herramientas de IA diagnóstica"
         }' | jq . 2>/dev/null || echo "Error al parsear respuesta"
    
    echo -e "\n"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: HubSpot CRM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
test_hubspot() {
    print_header "📊 HubSpot CRM"
    
    echo -e "${YELLOW}POST ${BASE_URL}/api/v1/integrations/hubspot/companies${NC}\n"
    
    curl -X POST "${BASE_URL}/api/v1/integrations/hubspot/companies" \
         -H "Content-Type: application/json" \
         -d '{
           "name": "Hospital de Prueba SAS",
           "domain": "hospital-prueba.com.co",
           "industry": "HEALTH_CARE",
           "city": "Bogotá",
           "country": "Colombia",
           "phone": "+57 1 234 5678",
           "description": "Hospital de prueba para testing de integración"
         }' | jq . 2>/dev/null || echo "Error al parsear respuesta"
    
    echo -e "\n${YELLOW}GET ${BASE_URL}/api/v1/integrations/hubspot/companies?limit=5${NC}\n"
    
    curl -X GET "${BASE_URL}/api/v1/integrations/hubspot/companies?limit=5" \
         -H "Content-Type: application/json" | jq . 2>/dev/null || echo "Error al parsear respuesta"
    
    echo -e "\n"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: Linear
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
test_linear() {
    print_header "📋 Linear (Project Management)"
    
    echo -e "${YELLOW}POST ${BASE_URL}/api/v1/integrations/linear/issues${NC}\n"
    
    curl -X POST "${BASE_URL}/api/v1/integrations/linear/issues" \
         -H "Content-Type: application/json" \
         -d '{
           "title": "Seguimiento: Hospital de Prueba SAS",
           "description": "Nueva oportunidad de negocio detectada.\n\n**Contacto:** Dr. Luis García\n**Empresa:** Hospital de Prueba SAS\n**Estado:** Investigación inicial completada",
           "priority": 2,
           "labels": ["sales", "colombia"]
         }' | jq . 2>/dev/null || echo "Error al parsear respuesta"
    
    echo -e "\n${YELLOW}GET ${BASE_URL}/api/v1/integrations/linear/teams${NC}\n"
    
    curl -X GET "${BASE_URL}/api/v1/integrations/linear/teams" \
         -H "Content-Type: application/json" | jq . 2>/dev/null || echo "Error al parsear respuesta"
    
    echo -e "\n"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: Zoho Email
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
test_zoho_email() {
    print_header "📧 Zoho Email"
    
    echo -e "${YELLOW}POST ${BASE_URL}/api/v1/integrations/zoho/send${NC}\n"
    
    echo -e "${RED}⚠️  Este test enviará un email real. Descomenta cuando quieras probarlo.${NC}\n"
    
    # Descomenta las siguientes líneas para enviar un email de prueba
    # curl -X POST "${BASE_URL}/api/v1/integrations/zoho/send" \
    #      -H "Content-Type: application/json" \
    #      -d '{
    #        "to_email": "tu-email-prueba@example.com",
    #        "subject": "Test de integración Zoho",
    #        "body": "<p>Este es un email de prueba de la integración Zoho.</p>",
    #        "from_name": "AiMedic Team"
    #      }' | jq . 2>/dev/null || echo "Error al parsear respuesta"
    
    echo -e "\n"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: Google Calendar
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
test_google_calendar() {
    print_header "📅 Google Calendar"
    
    echo -e "${YELLOW}POST ${BASE_URL}/api/v1/integrations/calendar/events${NC}\n"
    
    # Fecha de mañana
    tomorrow=$(date -d "+1 day" +"%Y-%m-%d")
    
    echo -e "${RED}⚠️  Este test creará un evento real en tu calendario. Descomenta cuando quieras probarlo.${NC}\n"
    
    # Descomenta las siguientes líneas para crear un evento de prueba
    # curl -X POST "${BASE_URL}/api/v1/integrations/calendar/events" \
    #      -H "Content-Type: application/json" \
    #      -d "{
    #        \"summary\": \"Seguimiento: Hospital de Prueba\",
    #        \"description\": \"Follow-up con Dr. Luis García sobre implementación de IA\",
    #        \"start_time\": \"${tomorrow}T10:00:00\",
    #        \"end_time\": \"${tomorrow}T11:00:00\",
    #        \"attendees\": []
    #      }" | jq . 2>/dev/null || echo "Error al parsear respuesta"
    
    echo -e "\n"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main() {
    clear
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║          Test de Integraciones - Scrapper Salud AiMedic                  ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
    
    # Verificar servidor
    if ! check_server; then
        exit 1
    fi
    
    # Determinar qué tests ejecutar
    test_type=${1:-"all"}
    
    case "$test_type" in
        "health")
            test_health
            ;;
        "research")
            test_person_research
            ;;
        "outreach")
            test_outreach_drafting
            ;;
        "pipeline")
            test_full_pipeline
            ;;
        "hubspot")
            test_hubspot
            ;;
        "linear")
            test_linear
            ;;
        "zoho")
            test_zoho_email
            ;;
        "calendar")
            test_google_calendar
            ;;
        "core")
            test_health
            test_person_research
            test_outreach_drafting
            test_full_pipeline
            ;;
        "integrations")
            test_hubspot
            test_linear
            test_zoho_email
            test_google_calendar
            ;;
        "all")
            test_health
            test_person_research
            test_outreach_drafting
            test_full_pipeline
            test_hubspot
            test_linear
            test_zoho_email
            test_google_calendar
            ;;
        *)
            echo -e "${RED}Test desconocido: $test_type${NC}"
            echo -e "\n${YELLOW}Uso:${NC}"
            echo -e "  ./test_integrations.sh [test_name]"
            echo -e "\n${YELLOW}Tests disponibles:${NC}"
            echo -e "  all            - Ejecutar todos los tests (default)"
            echo -e "  core           - Tests core (health, research, outreach, pipeline)"
            echo -e "  integrations   - Tests de integraciones (hubspot, linear, zoho, calendar)"
            echo -e "  health         - Health check"
            echo -e "  research       - Person research (Perplexity)"
            echo -e "  outreach       - Outreach drafting (Gemini)"
            echo -e "  pipeline       - Full pipeline"
            echo -e "  hubspot        - HubSpot CRM"
            echo -e "  linear         - Linear"
            echo -e "  zoho           - Zoho Email"
            echo -e "  calendar       - Google Calendar"
            echo ""
            exit 1
            ;;
    esac
    
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                           Tests Completados                               ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════════════╝${NC}\n"
}

# Ejecutar
main "$@"
