"""
Prospect Intelligence Service
================================
Usa Perplexity (sonar) para investigar una institución de salud y descubrir
contactos de decisión TI, con la estructura completa de la tabla de prospección:

  Canal | Contacto | Email | Teléfono | Rol TI | Next Action | Prioridad | Razón

Incluye "ventana de contexto" configurable: puedes pasarle tu propio contexto
de búsqueda de Perplexity para afinar la especificidad (qué buscar, qué evitar,
foco geográfico, foco de rol, etc.).

Flujo esperado:
  1. search_institution(name, context_window) → List[ProspectContact]
  2. Cada ProspectContact puede usarse para generar M1/M2/M3 en LinkedInOutreachService
  3. El resultado completo puede enviarse por Zoho, guardarse en HubSpot, etc.
"""

import logging
import json
import re
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

# ── Prioridad (como rating de 1-5 estrellas) ─────────────────────────────────

class Prioridad(str, Enum):
    CRITICA   = "⭐⭐⭐⭐⭐"
    ALTA      = "⭐⭐⭐⭐"
    MEDIA     = "⭐⭐⭐"
    BAJA      = "⭐⭐"
    MINIMA    = "⭐"


# ── Modelo de un contacto prospectado ────────────────────────────────────────

@dataclass
class ProspectContact:
    """Un contacto encontrado en la investigación Perplexity de una institución"""
    canal: str                              # Canal de contacto (PBX, Email directo, etc.)
    contacto: str                           # Nombre / cargo / departamento
    email: Optional[str] = None
    telefono: Optional[str] = None
    rol_ti: str = ""                        # Descripción de su rol en TI / decisión
    next_action: str = "Email + Llamada"   # Acción recomendada
    prioridad: str = "⭐⭐⭐"               # Rating como string de estrellas
    razon: str = ""                         # Por qué es relevante para Aimedic
    # Datos extra para generar los mensajes LinkedIn
    nombre: Optional[str] = None           # Nombre propio (si disponible)
    apellido: Optional[str] = None
    cargo: Optional[str] = None            # Título exacto del cargo
    linkedin_url: Optional[str] = None
    banner_linkedin: Optional[str] = None  # Frase del banner de LinkedIn
    notas: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProspectIntelResult:
    """Resultado completo de una búsqueda de prospección"""
    institution_name: str
    contacts: List[ProspectContact] = field(default_factory=list)
    summary: str = ""
    pain_points: List[str] = field(default_factory=list)
    context_used: str = ""
    source: str = "perplexity"
    success: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "institution_name": self.institution_name,
            "contacts": [c.to_dict() for c in self.contacts],
            "summary": self.summary,
            "pain_points": self.pain_points,
            "context_used": self.context_used,
            "source": self.source,
            "success": self.success,
            "error": self.error,
        }


# ── Servicio principal ────────────────────────────────────────────────────────

class ProspectIntelService:
    """
    Investiga una institución de salud usando Perplexity y devuelve
    una tabla estructurada de contactos de decisión.

    Args:
        perplexity_api_key: Clave de la API de Perplexity (sonar model)
        default_context_window: Texto fijo de contexto de búsqueda que se
            prepende a TODAS las búsquedas (tu "ventana de contexto" global).
            Ejemplo:
              "Busca SOLO contactos en instituciones de nivel complejidad 3 en
               Colombia. No incluir Bogotá. Foco en EPS o IPS con más de 200
               camas. Cargo que decide la compra de software: CIO, CTO, Gerente
               de Sistemas, Director TI o equivalente."
        extra_fields_prompt: Prompt extra para pedir campos adicionales.
    """

    # ── Prompt base del sistema ──────────────────────────────────────────────
    SYSTEM_PROMPT = """Eres un investigador experto en prospección B2B para el sector salud en Colombia.
Tu especialidad es encontrar los contactos correctos de tecnología/TI y decisión en instituciones de salud.
Siempre respondes con JSON válido, sin markdown, sin texto adicional.
Pones null cuando no encuentras un dato — NUNCA inventas datos."""

    # ── Prompt usuario plantilla ─────────────────────────────────────────────
    USER_PROMPT_TEMPLATE = """Investiga la institución de salud: "{institution_name}"

{context_block}

Necesito encontrar los mejores canales y contactos para prospectar a Aimedic, una startup colombiana de IA médica
(respaldada por Google for Startups y NVIDIA) que trabaja con Fundación Cardio Infantil y Fundación Neumológica.
Aimedic vende:
- Analítica avanzada de salud (riesgo, tiempos de espera, dashboards)
- Modelos IA corriendo on-premise (datos nunca salen de la infraestructura de la institución)

Devuelve ÚNICAMENTE este JSON:
{{
  "institution_name": "nombre oficial completo de la institución",
  "summary": "breve descripción de la institución (2-3 oraciones)",
  "pain_points": ["pain point TI 1", "pain point TI 2", "pain point TI 3"],
  "contacts": [
    {{
      "canal": "descripción del canal (ej: 'PBX principal', 'Email oficial TI', 'LinkedIn directo')",
      "contacto": "nombre de la persona O nombre del departamento/cargo si no hay persona",
      "email": "email si existe o null",
      "telefono": "teléfono con extensión si aplica o null",
      "rol_ti": "descripción breve de su poder de decisión en TI/tecnología",
      "next_action": "LLAMAR YA | Email | Llamada | Email + Llamada | LinkedIn | LinkedIn + Email",
      "prioridad": "⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐",
      "razon": "por qué este canal es relevante para llegar al decisor TI",
      "nombre": "nombre propio del contacto o null",
      "apellido": "apellido del contacto o null",
      "cargo": "título exacto del cargo o null",
      "linkedin_url": "URL de LinkedIn si encontraste o null",
      "banner_linkedin": "frase del banner de LinkedIn si encontraste o null",
      "notas": "cualquier nota adicional relevante o null"
    }}
  ]
}}

Ordena los contactos de mayor a menor prioridad (⭐⭐⭐⭐⭐ primero).
Incluye mínimo 3 y máximo 8 contactos/canales. 
Si hay un decisor directo de TI (CIO, CTO, Gerente Sistemas, Director TI), ponlo de primero.
Incluye también el PBX / número principal si lo encuentras.
NO mezcles especulación con datos reales — marca lo incierto en "notas"."""

    def __init__(
        self,
        perplexity_api_key: Optional[str] = None,
        default_context_window: str = "",
    ):
        self.perplexity_key = perplexity_api_key
        self.default_context_window = default_context_window.strip()

    @property
    def available(self) -> bool:
        return bool(self.perplexity_key)

    # ── Método principal ─────────────────────────────────────────────────────

    async def search_institution(
        self,
        institution_name: str,
        context_window: Optional[str] = None,
        model: str = "sonar",
    ) -> ProspectIntelResult:
        """
        Busca contactos de prospección para una institución de salud.

        Args:
            institution_name: Nombre de la institución (ej: "Clínica CES Medellín")
            context_window: Contexto adicional de búsqueda para ESTA búsqueda específica.
                Se combina con el default_context_window global.
                Aquí puedes poner hints específicos:
                  - "Enfocarse en clínica CES cardiology, no en la universidad"
                  - "El CTO se llama Hernán Díaz, verificar si sigue ahí"
                  - "Buscar en LinkedIn: 'sistemas CES Medellín'"
            model: Modelo de Perplexity a usar (sonar, sonar-pro, etc.)

        Returns:
            ProspectIntelResult con la tabla de contactos
        """
        if not self.perplexity_key:
            return ProspectIntelResult(
                institution_name=institution_name,
                success=False,
                error="PERPLEXITY_API_KEY no configurado",
            )

        # Construir bloque de contexto combinado
        context_parts = []
        if self.default_context_window:
            context_parts.append(f"CONTEXTO GLOBAL DE BÚSQUEDA:\n{self.default_context_window}")
        if context_window and context_window.strip():
            context_parts.append(f"CONTEXTO ESPECÍFICO PARA ESTA BÚSQUEDA:\n{context_window.strip()}")

        context_block = "\n\n".join(context_parts) if context_parts else ""
        context_full = f"\n{context_block}\n" if context_block else ""

        prompt = self.USER_PROMPT_TEMPLATE.format(
            institution_name=institution_name,
            context_block=context_full,
        )

        try:
            result = await self._call_perplexity(prompt, model=model)
            result.context_used = context_block
            return result
        except Exception as e:
            logger.error(f"ProspectIntelService error para '{institution_name}': {e}")
            return ProspectIntelResult(
                institution_name=institution_name,
                success=False,
                error=str(e),
                context_used=context_block,
            )

    async def search_batch(
        self,
        institution_names: List[str],
        context_window: Optional[str] = None,
    ) -> List[ProspectIntelResult]:
        """Busca múltiples instituciones en secuencia (respeta rate limits)"""
        import asyncio
        results = []
        for name in institution_names:
            result = await self.search_institution(name, context_window=context_window)
            results.append(result)
            await asyncio.sleep(1.5)  # rate limit amistoso con Perplexity
        return results

    # ── Llamada a la API ─────────────────────────────────────────────────────

    async def _call_perplexity(
        self,
        user_prompt: str,
        model: str = "sonar",
    ) -> ProspectIntelResult:
        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        }

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(PERPLEXITY_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        raw_content = data["choices"][0]["message"]["content"]
        return self._parse_response(raw_content)

    # ── Parseo del JSON ──────────────────────────────────────────────────────

    def _parse_response(self, content: str) -> ProspectIntelResult:
        """Parsea la respuesta de Perplexity a ProspectIntelResult"""
        # Eliminar bloques markdown si Perplexity los añade
        clean = re.sub(r"```(?:json)?", "", content).strip()
        clean = re.sub(r"```", "", clean).strip()

        json_match = re.search(r"\{[\s\S]*\}", clean)
        if not json_match:
            return ProspectIntelResult(
                institution_name="Desconocido",
                success=False,
                error=f"No se pudo parsear JSON de la respuesta: {content[:200]}",
            )

        try:
            parsed = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            return ProspectIntelResult(
                institution_name="Desconocido",
                success=False,
                error=f"JSON inválido: {e}. Fragmento: {content[:200]}",
            )

        # Construir contactos
        contacts: List[ProspectContact] = []
        for raw_c in parsed.get("contacts", []):
            contacts.append(ProspectContact(
                canal=raw_c.get("canal", ""),
                contacto=raw_c.get("contacto", ""),
                email=raw_c.get("email"),
                telefono=raw_c.get("telefono"),
                rol_ti=raw_c.get("rol_ti", ""),
                next_action=raw_c.get("next_action", "Email + Llamada"),
                prioridad=raw_c.get("prioridad", "⭐⭐⭐"),
                razon=raw_c.get("razon", ""),
                nombre=raw_c.get("nombre"),
                apellido=raw_c.get("apellido"),
                cargo=raw_c.get("cargo"),
                linkedin_url=raw_c.get("linkedin_url"),
                banner_linkedin=raw_c.get("banner_linkedin"),
                notas=raw_c.get("notas"),
            ))

        return ProspectIntelResult(
            institution_name=parsed.get("institution_name", "Desconocido"),
            contacts=contacts,
            summary=parsed.get("summary", ""),
            pain_points=parsed.get("pain_points", []),
            source="perplexity",
            success=True,
        )
