#!/usr/bin/env python3
"""
Script de Verificación de Configuración
========================================
Verifica que todas las APIs y servicios estén correctamente configurados.

Uso:
    python check_config.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def check_env_var(var_name: str, required: bool = False) -> tuple[bool, str]:
    """Verifica si una variable de entorno está configurada."""
    value = os.getenv(var_name)
    
    if not value or value == "" or value.startswith("your-") or value == "tu-":
        if required:
            return False, f"{Colors.RED}✗{Colors.END} {var_name:<35} NO CONFIGURADA (OBLIGATORIA)"
        else:
            return False, f"{Colors.YELLOW}○{Colors.END} {var_name:<35} No configurada (opcional)"
    
    # Ocultar la key excepto los primeros caracteres
    if len(value) > 10:
        masked = value[:8] + "..." + value[-4:]
    else:
        masked = value[:3] + "***"
    
    return True, f"{Colors.GREEN}✓{Colors.END} {var_name:<35} {masked}"


def check_file_exists(file_path: str, var_name: str) -> tuple[bool, str]:
    """Verifica si un archivo existe."""
    env_value = os.getenv(var_name)
    
    if not env_value or env_value == "":
        return False, f"{Colors.YELLOW}○{Colors.END} {var_name:<35} No especificado"
    
    path = Path(env_value)
    
    if path.exists():
        return True, f"{Colors.GREEN}✓{Colors.END} {var_name:<35} {env_value} (existe)"
    else:
        return False, f"{Colors.RED}✗{Colors.END} {var_name:<35} {env_value} (NO ENCONTRADO)"


def print_section(title: str):
    """Imprime un título de sección."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")


def main():
    print(f"\n{Colors.BOLD}🔍 Verificación de Configuración - Scrapper Salud AiMedic{Colors.END}\n")
    
    all_ok = True
    required_ok = True
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. INFORMACIÓN PERSONAL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print_section("🏢 INFORMACIÓN PERSONAL")
    
    configs = [
        ("BUSINESS_NAME", False),
        ("BUSINESS_DESCRIPTION", False),
        ("YOUR_NAME", True),
        ("YOUR_ROLE", True),
    ]
    
    for var, required in configs:
        ok, msg = check_env_var(var, required)
        print(msg)
        if required and not ok:
            required_ok = False
        all_ok = all_ok and ok
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. INTELIGENCIA ARTIFICIAL (OBLIGATORIAS)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print_section("🤖 INTELIGENCIA ARTIFICIAL (CORE)")
    
    ai_configs = [
        ("GOOGLE_AI_STUDIO", True),
        ("PERPLEXITY_API_KEY", True),
    ]
    
    for var, required in ai_configs:
        ok, msg = check_env_var(var, required)
        print(msg)
        if required and not ok:
            required_ok = False
        all_ok = all_ok and ok
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. CRM & VENTAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print_section("📊 CRM & VENTAS")
    
    ok, msg = check_env_var("HUBSPOT_ACCESS_TOKEN", False)
    print(msg)
    all_ok = all_ok and ok
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. GESTIÓN DE PROYECTOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print_section("📋 GESTIÓN DE PROYECTOS")
    
    linear_configs = [
        ("LINEAR_API_KEY", False),
        ("LINEAR_DEFAULT_TEAM_ID", False),
    ]
    
    for var, required in linear_configs:
        ok, msg = check_env_var(var, required)
        print(msg)
        all_ok = all_ok and ok
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5. EMAIL AUTOMATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print_section("📧 EMAIL AUTOMATION")
    
    zoho_configs = [
        ("ZOHO_CLIENT_ID", False),
        ("ZOHO_CLIENT_SECRET", False),
        ("ZOHO_REFRESH_TOKEN", False),
        ("ZOHO_ACCOUNT_ID", False),
        ("ZOHO_FROM_EMAIL", False),
    ]
    
    for var, required in zoho_configs:
        ok, msg = check_env_var(var, required)
        print(msg)
        all_ok = all_ok and ok
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 6. CALENDARIO
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print_section("📅 CALENDARIO")
    
    ok, msg = check_file_exists("google_service_account.json", "GOOGLE_SERVICE_ACCOUNT_FILE")
    print(msg)
    
    ok2, msg2 = check_file_exists("credentials.json", "GOOGLE_CREDENTIALS_FILE")
    print(msg2)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 7. BASE DE DATOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print_section("💾 BASE DE DATOS")
    
    ok, msg = check_env_var("DATABASE_URL", False)
    print(msg)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # RESUMEN FINAL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    if required_ok:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ Todas las configuraciones OBLIGATORIAS están OK{Colors.END}")
        print(f"\n{Colors.BLUE}💡 Puedes iniciar el servidor con:{Colors.END}")
        print(f"   python main.py\n")
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ Faltan configuraciones OBLIGATORIAS{Colors.END}")
        print(f"\n{Colors.YELLOW}📖 Lee la guía completa en:{Colors.END}")
        print(f"   {Colors.BLUE}GUIA_CONFIGURACION.md{Colors.END}\n")
        sys.exit(1)
    
    if not all_ok:
        print(f"{Colors.YELLOW}⚠️  Algunas integraciones opcionales no están configuradas{Colors.END}")
        print(f"{Colors.YELLOW}   El sistema funcionará pero con funcionalidad limitada{Colors.END}\n")
    else:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ¡TODO CONFIGURADO PERFECTAMENTE!{Colors.END}\n")


if __name__ == "__main__":
    # Verificar si existe el archivo .env
    if not Path(".env").exists():
        print(f"{Colors.RED}✗ No se encontró el archivo .env{Colors.END}")
        print(f"\n{Colors.YELLOW}Crea uno con:{Colors.END}")
        print(f"   cp .env.example .env")
        print(f"   # O")
        print(f"   cp .env.template .env\n")
        sys.exit(1)
    
    main()
