#!/usr/bin/env python3
"""
Script interactivo para generar tu archivo .env
===============================================
Te guía paso a paso para crear tu configuración personalizada.

Uso:
    python setup_env.py
"""

import os
import sys
from pathlib import Path


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Imprime un header bonito."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")


def get_input(prompt: str, default: str = "", required: bool = False) -> str:
    """Obtiene input del usuario con un default opcional."""
    default_text = f" [{default}]" if default else ""
    required_text = f" {Colors.RED}(OBLIGATORIO){Colors.END}" if required else f" {Colors.YELLOW}(opcional){Colors.END}"
    
    full_prompt = f"{Colors.CYAN}{prompt}{Colors.END}{default_text}{required_text}: "
    
    while True:
        value = input(full_prompt).strip()
        
        if not value and default:
            return default
        elif not value and required:
            print(f"{Colors.RED}Este campo es obligatorio. Por favor, ingresa un valor.{Colors.END}")
            continue
        elif not value:
            return ""
        else:
            return value


def main():
    print(f"\n{Colors.BOLD}{Colors.GREEN}🚀 Configurador de Scrapper Salud AiMedic{Colors.END}")
    print(f"{Colors.YELLOW}Este asistente te ayudará a crear tu archivo .env{Colors.END}\n")
    
    # Verificar si ya existe .env
    if Path(".env").exists():
        print(f"{Colors.YELLOW}⚠️  Ya existe un archivo .env{Colors.END}")
        overwrite = input("¿Deseas sobrescribirlo? (y/N): ").lower()
        if overwrite != 'y':
            print("Operación cancelada.")
            sys.exit(0)
        print()
    
    config = {}
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INFORMACIÓN PERSONAL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print_header("🏢 Tu Información Personal")
    print("Esta información se usará para personalizar mensajes de outreach.\n")
    
    config['BUSINESS_NAME'] = get_input("Nombre del negocio", "AiMedic", False)
    config['BUSINESS_DESCRIPTION'] = get_input(
        "Descripción del negocio",
        "Empresa de salud digital que provee soluciones de IA",
        False
    )
    config['YOUR_NAME'] = get_input("Tu nombre completo", "", True)
    config['YOUR_ROLE'] = get_input("Tu rol/cargo", "CEO", True)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # APIS CORE (OBLIGATORIAS)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print_header("🤖 APIs Core (Obligatorias)")
    print(f"{Colors.YELLOW}Estas APIs son necesarias para el funcionamiento básico.{Colors.END}\n")
    
    print(f"{Colors.CYAN}Google Gemini AI{Colors.END}")
    print(f"   Obtener en: {Colors.BLUE}https://aistudio.google.com/apikey{Colors.END}")
    print(f"   Costo: GRATIS\n")
    config['GOOGLE_AI_STUDIO'] = get_input("API Key de Google Gemini", "", True)
    
    print(f"\n{Colors.CYAN}Perplexity AI{Colors.END}")
    print(f"   Obtener en: {Colors.BLUE}https://www.perplexity.ai/settings/api{Colors.END}")
    print(f"   Costo: ~$20/mes\n")
    config['PERPLEXITY_API_KEY'] = get_input("API Key de Perplexity", "", True)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INTEGRACIONES OPCIONALES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print_header("📊 Integraciones Opcionales")
    print(f"{Colors.YELLOW}Puedes configurarlas ahora o dejarlas vacías y añadirlas después.{Colors.END}\n")
    
    configure_integrations = input(f"{Colors.CYAN}¿Deseas configurar las integraciones opcionales ahora?{Colors.END} (y/N): ").lower()
    
    if configure_integrations == 'y':
        # HubSpot
        print(f"\n{Colors.CYAN}HubSpot CRM{Colors.END}")
        print(f"   Guía: {Colors.BLUE}Ver GUIA_CONFIGURACION.md sección 3{Colors.END}")
        config['HUBSPOT_ACCESS_TOKEN'] = get_input("HubSpot Access Token", "", False)
        
        # Linear
        print(f"\n{Colors.CYAN}Linear (Project Management){Colors.END}")
        print(f"   Guía: {Colors.BLUE}Ver GUIA_CONFIGURACION.md sección 4{Colors.END}")
        config['LINEAR_API_KEY'] = get_input("Linear API Key", "", False)
        config['LINEAR_DEFAULT_TEAM_ID'] = get_input("Linear Team ID", "", False)
        
        # Zoho Email
        print(f"\n{Colors.CYAN}Zoho Email{Colors.END}")
        print(f"   Guía: {Colors.BLUE}Ver GUIA_CONFIGURACION.md sección 5{Colors.END}")
        config['ZOHO_CLIENT_ID'] = get_input("Zoho Client ID", "", False)
        config['ZOHO_CLIENT_SECRET'] = get_input("Zoho Client Secret", "", False)
        config['ZOHO_REFRESH_TOKEN'] = get_input("Zoho Refresh Token", "", False)
        config['ZOHO_ACCOUNT_ID'] = get_input("Zoho Account ID", "", False)
        config['ZOHO_FROM_EMAIL'] = get_input("Zoho From Email", "", False)
        
        # Google Calendar
        print(f"\n{Colors.CYAN}Google Calendar{Colors.END}")
        print(f"   Guía: {Colors.BLUE}Ver GUIA_CONFIGURACION.md sección 6{Colors.END}")
        config['GOOGLE_SERVICE_ACCOUNT_FILE'] = get_input(
            "Ruta al archivo JSON de service account",
            "google_service_account.json",
            False
        )
    else:
        print(f"\n{Colors.GREEN}✓{Colors.END} Puedes añadirlas después editando el archivo .env")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CONFIGURACIÓN GENERAL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    config['SCRAPER_MODE'] = 'development'
    config['LOG_LEVEL'] = 'INFO'
    config['API_HOST'] = '0.0.0.0'
    config['API_PORT'] = '8000'
    config['DATABASE_URL'] = 'sqlite:///health_institutions.db'
    config['HEADLESS_MODE'] = 'True'
    config['SELENIUM_TIMEOUT'] = '30'
    config['RATE_LIMIT_DELAY'] = '2'
    config['VISION_MODEL'] = 'gemini-1.5-flash'
    config['PIPELINE_AUTO_SNAPSHOT'] = 'True'
    config['CONNECT_API_ENABLED'] = 'True'
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # GENERAR ARCHIVO .env
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print_header("💾 Generando archivo .env")
    
    env_content = """# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                    SCRAPPER SALUD - CONFIGURACIÓN                         ║
# ║                        AiMedic Health Scraper                             ║
# ║                   Generado automáticamente por setup_env.py               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
#
# ⚠️  NUNCA compartas este archivo. Contiene tus API keys privadas.
# 📖 Guía completa: GUIA_CONFIGURACION.md

# ═══════════════════════════════════════════════════════════════════════════
# 🏢 TU INFORMACIÓN
# ═══════════════════════════════════════════════════════════════════════════
BUSINESS_NAME={BUSINESS_NAME}
BUSINESS_DESCRIPTION={BUSINESS_DESCRIPTION}
YOUR_NAME={YOUR_NAME}
YOUR_ROLE={YOUR_ROLE}

# ═══════════════════════════════════════════════════════════════════════════
# 🔧 CONFIGURACIÓN GENERAL
# ═══════════════════════════════════════════════════════════════════════════
SCRAPER_MODE={SCRAPER_MODE}
LOG_LEVEL={LOG_LEVEL}
API_HOST={API_HOST}
API_PORT={API_PORT}
DATABASE_URL={DATABASE_URL}
HEADLESS_MODE={HEADLESS_MODE}
SELENIUM_TIMEOUT={SELENIUM_TIMEOUT}
RATE_LIMIT_DELAY={RATE_LIMIT_DELAY}

# ═══════════════════════════════════════════════════════════════════════════
# 🤖 INTELIGENCIA ARTIFICIAL (CORE)
# ═══════════════════════════════════════════════════════════════════════════
GOOGLE_AI_STUDIO={GOOGLE_AI_STUDIO}
VISION_MODEL={VISION_MODEL}
PERPLEXITY_API_KEY={PERPLEXITY_API_KEY}

# ═══════════════════════════════════════════════════════════════════════════
# 📊 INTEGRACIONES OPCIONALES
# ═══════════════════════════════════════════════════════════════════════════

# HubSpot CRM
HUBSPOT_ACCESS_TOKEN={HUBSPOT_ACCESS_TOKEN}

# Linear
LINEAR_API_KEY={LINEAR_API_KEY}
LINEAR_DEFAULT_TEAM_ID={LINEAR_DEFAULT_TEAM_ID}

# Zoho Email
ZOHO_CLIENT_ID={ZOHO_CLIENT_ID}
ZOHO_CLIENT_SECRET={ZOHO_CLIENT_SECRET}
ZOHO_REFRESH_TOKEN={ZOHO_REFRESH_TOKEN}
ZOHO_ACCOUNT_ID={ZOHO_ACCOUNT_ID}
ZOHO_FROM_EMAIL={ZOHO_FROM_EMAIL}
ZOHO_DOMAIN=zoho.com

# Google Calendar
GOOGLE_SERVICE_ACCOUNT_FILE={GOOGLE_SERVICE_ACCOUNT_FILE}
GOOGLE_CREDENTIALS_FILE=

# ═══════════════════════════════════════════════════════════════════════════
# ⚙️ CONFIGURACIÓN AVANZADA
# ═══════════════════════════════════════════════════════════════════════════
PIPELINE_AUTO_SNAPSHOT={PIPELINE_AUTO_SNAPSHOT}
CONNECT_API_ENABLED={CONNECT_API_ENABLED}
""".format(**{k: v or '' for k, v in config.items()})
    
    # Escribir archivo
    with open(".env", "w") as f:
        f.write(env_content)
    
    print(f"{Colors.GREEN}✓ Archivo .env creado exitosamente{Colors.END}\n")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # VERIFICACIÓN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print_header("✅ Siguiente Paso")
    print(f"{Colors.CYAN}1. Verifica tu configuración:{Colors.END}")
    print(f"   python check_config.py\n")
    
    print(f"{Colors.CYAN}2. Inicia el servidor:{Colors.END}")
    print(f"   python main.py\n")
    
    print(f"{Colors.CYAN}3. Abre la documentación API:{Colors.END}")
    print(f"   {Colors.BLUE}http://localhost:8000/docs{Colors.END}\n")
    
    print(f"{Colors.GREEN}¡Listo para empezar! 🚀{Colors.END}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Operación cancelada por el usuario.{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}")
        sys.exit(1)
