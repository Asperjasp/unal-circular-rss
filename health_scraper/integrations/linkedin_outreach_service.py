"""
LinkedIn Outreach Service — Sistema M1 / M2 / M3
==================================================
Genera los tres mensajes de LinkedIn para prospectar ejecutivos de salud en Colombia.

Replica la lógica del sistema de outreach Aimedic (LINKEDIN.md):
  M1 — Nota de conexión (0 venta, 0 tecnología, solo conexión humana, ≤300 chars)
  M2 — Descubrimiento (solo preguntas, sin mencionar productos)
  M3 — Propuesta (después de que responda M2, incluye calendario)

Usa Claude claude-sonnet-4-20250514 (Anthropic) para generar los mensajes — el mismo
modelo que se usa en la app React del LINKEDIN.md.

Variables de entorno requeridas:
  ANTHROPIC_API_KEY  — API key de Anthropic
"""

import logging
import json
import re
import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-20250514"


# ── Enums de Persona e Institución (espeja LINKEDIN.md) ─────────────────────

class PersonaTipo(str, Enum):
    CIO_CTO          = "cio_cto"
    GERENTE_TECH     = "gerente_tech"
    DIRECTOR_OPS     = "director_ops"
    MEDICO_CLINICO   = "medico_clinico"
    DIRECTOR_COMERCIAL = "director_comercial"


class InstitucionTipo(str, Enum):
    EPS         = "eps"
    CLINICA     = "clinica"
    LABORATORIO = "laboratorio"
    IPS         = "ips"


# ── Configuraciones (espeja el JS de LINKEDIN.md) ───────────────────────────

PERSONAS: Dict[str, Dict[str, str]] = {
    "cio_cto": {
        "label": "CIO / CTO",
        "m1_hook": "transformación digital centrada en las personas",
        "m2_question": "¿cómo ha sido llevar analítica real a la operación clínica? ¿Dónde encuentra más fricción cuando intenta mover algo nuevo?",
        "m2_angle": "Sabe dónde está el dato, pero también dónde se pierde antes de volverse inteligencia útil.",
        "greeting": "Silverio",  # placeholder, se reemplaza con el nombre real
    },
    "gerente_tech": {
        "label": "Gerente Tecnología",
        "m1_hook": "combina la visión estratégica con la base técnica en el sector salud",
        "m2_question": "¿cómo ha sido ese proceso de innovación tecnológica? ¿Dónde encuentra más fricción cuando intenta mover algo nuevo institucionalmente?",
        "m2_angle": "Tiene que hacer que los sistemas funcionen, que los equipos clínicos los adopten, y que todo tenga sentido estratégico.",
        "greeting": "",
    },
    "director_ops": {
        "label": "Director Operaciones / Salud",
        "m1_hook": "misión de mejorar la atención en salud desde la operación",
        "m2_question": "¿cómo ha sido convertir datos clínicos en decisiones útiles a tiempo? ¿Qué sistemas les han dado más fricción?",
        "m2_angle": "Toma decisiones con información que siempre llega tarde, incompleta o dispersa en múltiples sistemas.",
        "greeting": "",
    },
    "medico_clinico": {
        "label": "Médico / Clínico Senior",
        "m1_hook": "dedicación a la práctica clínica y la investigación",
        "m2_question": "¿cómo ha vivido la evolución de la tecnología en su práctica? ¿Qué cree que la tecnología aún no ha sabido darle bien al médico?",
        "m2_angle": "Tiene décadas viendo cómo llega y fracasa la tecnología en el mundo clínico.",
        "greeting": "Doctor",
    },
    "director_comercial": {
        "label": "Director Comercial",
        "m1_hook": "visión de negocio en el sector salud",
        "m2_question": "¿cómo han abordado la relación entre tecnología y crecimiento comercial? ¿Qué barreras han encontrado?",
        "m2_angle": "Ve la brecha entre lo que el paciente necesita y lo que los sistemas permiten ofrecer.",
        "greeting": "",
    },
}

INSTITUCIONES: Dict[str, Dict] = {
    "eps": {
        "label": "EPS",
        "pain": "tiempos de espera y Resolución 2117/2025",
        "urgency": True,
    },
    "clinica": {
        "label": "Clínica / Hospital",
        "pain": "fragmentación de datos clínicos y adopción tecnológica",
        "urgency": False,
    },
    "laboratorio": {
        "label": "Laboratorio",
        "pain": "volumen de datos y velocidad de procesamiento",
        "urgency": False,
    },
    "ips": {
        "label": "IPS",
        "pain": "autorización y coordinación con aseguradoras",
        "urgency": False,
    },
}


# ── Modelos de resultado ─────────────────────────────────────────────────────

@dataclass
class LinkedInMessages:
    m1: str
    m2: str
    m3: str
    # Metadatos
    prospect_name: str = ""
    institution: str = ""
    persona_label: str = ""
    institution_label: str = ""
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Servicio ─────────────────────────────────────────────────────────────────

class LinkedInOutreachService:
    """
    Genera mensajes M1/M2/M3 de LinkedIn usando Claude claude-sonnet-4-20250514.

    Implementa textualmente las reglas de LINKEDIN.md:
    - M1: 0 venta, 0 tecnología. Solo conexión humana. MAX 300 caracteres.
    - M2: Solo descubrimiento. Sin mencionar productos. Termina con pregunta abierta.
    - M3: Solo después de que responda M2. Conecta con lo que resuelve Aimedic.
          Incluye calendario: https://calendar.app.google/iwNTpueCort26EuNA
    """

    CALENDAR_URL = "https://calendar.app.google/iwNTpueCort26EuNA"

    def __init__(self, anthropic_api_key: Optional[str] = None):
        self.api_key = anthropic_api_key

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def generate_messages(
        self,
        name: str,
        last_name: str = "",
        persona: str = "cio_cto",
        institution: str = "",
        institution_type: str = "eps",
        banner_quote: str = "",
        notes: str = "",
    ) -> LinkedInMessages:
        """
        Genera los tres mensajes LinkedIn para un prospecto.

        Args:
            name: Nombre del prospecto
            last_name: Apellido del prospecto
            persona: Clave de PERSONAS (cio_cto, gerente_tech, director_ops, ...)
            institution: Nombre de la institución
            institution_type: Clave de INSTITUCIONES (eps, clinica, laboratorio, ips)
            banner_quote: Frase del banner de LinkedIn del prospecto (si disponible)
            notes: Notas adicionales sobre el prospecto

        Returns:
            LinkedInMessages con m1, m2, m3
        """
        if not self.api_key:
            return LinkedInMessages(
                m1="", m2="", m3="",
                prospect_name=f"{name} {last_name}".strip(),
                institution=institution,
                success=False,
                error="ANTHROPIC_API_KEY no configurado",
            )

        persona_data = PERSONAS.get(persona, PERSONAS["cio_cto"])
        inst_data    = INSTITUCIONES.get(institution_type, INSTITUCIONES["eps"])

        prompt = self._build_prompt(
            name=name,
            last_name=last_name,
            persona_data=persona_data,
            institution=institution,
            inst_data=inst_data,
            banner_quote=banner_quote,
            notes=notes,
        )

        try:
            messages = await self._call_claude(prompt)
            messages.prospect_name   = f"{name} {last_name}".strip()
            messages.institution     = institution
            messages.persona_label   = persona_data["label"]
            messages.institution_label = inst_data["label"]
            return messages
        except Exception as e:
            logger.error(f"LinkedInOutreachService error para {name}: {e}")
            return LinkedInMessages(
                m1="", m2="", m3="",
                prospect_name=f"{name} {last_name}".strip(),
                institution=institution,
                success=False,
                error=str(e),
            )

    # ── Construcción del prompt (espeja exactamente LINKEDIN.md) ────────────

    def _build_prompt(
        self,
        name: str,
        last_name: str,
        persona_data: Dict,
        institution: str,
        inst_data: Dict,
        banner_quote: str,
        notes: str,
    ) -> str:
        full_name = f"{name} {last_name}".strip()
        urgency_line = (
            "URGENCIA: Resolución 2117/2025 sobre tiempos de espera está activa."
            if inst_data.get("urgency") else ""
        )

        return f"""Eres el asistente de outreach de Aimedic, una startup colombiana de IA médica respaldada por Google for Startups y NVIDIA, que trabaja con Fundación Cardio Infantil y Fundación Neumológica.

CONTEXTO DEL PROSPECTO:
- Nombre: {full_name}
- Cargo: {persona_data['label']}
- Institución: {institution or '[Institución]'} ({inst_data['label']})
- Pain point principal: {inst_data['pain']}
- {urgency_line}
- Frase del banner LinkedIn: "{banner_quote or 'No disponible'}"
- Notas adicionales: {notes or 'Ninguna'}

REGLAS DE TONO (CRÍTICAS):
- M1: 0 venta, 0 tecnología. Solo conexión humana y misión compartida. MAX 300 caracteres.
- M2: Solo descubrimiento. Preguntar sobre su experiencia/desafíos. Sin mencionar productos. Terminar con pregunta abierta que no pueda rechazar.
- M3: Solo después de que responda M2. Conectar lo que dijo con lo que resuelve Aimedic. Incluir calendario: {self.CALENDAR_URL}
- NUNCA usar "don/doña" para perfiles ejecutivos de tech. Para médicos senior usar "doctor/a".
- Nunca frases genéricas como "me pareció interesante tu perfil" o "admiro tu trayectoria".
- Tono: directo, sin lambonería, con curiosidad genuina. Despedida humana.

PRODUCTOS AIMEDIC (solo M3):
- Analítica Avanzada: modelos de anticipación de riesgos, optimización tiempos de espera, dashboards ejecutivos
- On-Premise: IA corre en sus servidores, cero datos salen de su infraestructura  
- Validado clínicamente: Cardio Infantil + Neumológica + Google for Startups + NVIDIA

Genera exactamente 3 mensajes de LinkedIn en JSON con este formato:
{{
  "m1": "texto del mensaje M1",
  "m2": "texto del mensaje M2", 
  "m3": "texto del mensaje M3"
}}

Solo el JSON, sin explicaciones ni markdown."""

    # ── Llamada a Claude ─────────────────────────────────────────────────────

    async def _call_claude(self, prompt: str) -> LinkedInMessages:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        raw_text = data["content"][0]["text"].strip()
        # Limpiar posibles bloques markdown
        clean = re.sub(r"```(?:json)?", "", raw_text).strip()
        clean = re.sub(r"```", "", clean).strip()

        parsed = json.loads(clean)
        return LinkedInMessages(
            m1=parsed.get("m1", ""),
            m2=parsed.get("m2", ""),
            m3=parsed.get("m3", ""),
            success=True,
        )
