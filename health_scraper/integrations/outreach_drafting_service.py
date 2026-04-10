"""
Outreach Drafting Service
==========================
Uses Google Gemini to draft personalized outreach messages based on
researched person data and YOUR business context.

Workflow Step 2:  Perplexity researched the person → Gemini drafts a
                  personalized email/LinkedIn/Twitter message using its
                  deeper understanding of your business.

Why Gemini for drafting (not Perplexity):
- Gemini knows more about your business context via system prompts
- Better at creative, persuasive writing
- Can maintain your brand voice across messages
- Supports multiple outreach channels in one call
"""

import logging
import json
import re
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class OutreachChannel(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    WHATSAPP = "whatsapp"


class OutreachTone(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    WARM = "warm"
    DIRECT = "direct"


class OutreachDraft:
    """A single outreach message draft"""

    def __init__(self, channel: str, subject: str, body: str, notes: str = ""):
        self.channel = channel
        self.subject = subject
        self.body = body
        self.notes = notes  # internal notes for the sender

    def to_dict(self) -> Dict[str, str]:
        return {
            "channel": self.channel,
            "subject": self.subject,
            "body": self.body,
            "notes": self.notes,
        }


class OutreachDraftResult:
    """Complete set of outreach drafts for one person"""

    def __init__(self):
        self.person_name: str = ""
        self.drafts: List[OutreachDraft] = []
        self.strategy_notes: str = ""
        self.recommended_sequence: List[str] = []
        self.success: bool = False
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "person_name": self.person_name,
            "drafts": [d.to_dict() for d in self.drafts],
            "strategy_notes": self.strategy_notes,
            "recommended_sequence": self.recommended_sequence,
            "success": self.success,
            "error": self.error,
        }


class OutreachDraftingService:
    """
    Drafts personalized outreach messages using Gemini.
    
    Requires: GOOGLE_AI_STUDIO API key (Gemini).
    
    This service takes the output of PersonResearchService (enriched person data)
    and generates channel-specific outreach messages.
    """

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        business_name: str = "",
        business_description: str = "",
        your_name: str = "",
        your_role: str = "",
    ):
        self.gemini_key = gemini_api_key
        self.business_name = business_name
        self.business_description = business_description
        self.your_name = your_name
        self.your_role = your_role

    @property
    def available(self) -> bool:
        return bool(self.gemini_key)

    async def draft_outreach(
        self,
        person_data: Dict[str, Any],
        channels: List[OutreachChannel] = None,
        tone: OutreachTone = OutreachTone.PROFESSIONAL,
        language: str = "es",
        custom_context: Optional[str] = None,
        goal: str = "Schedule an introductory meeting",
    ) -> OutreachDraftResult:
        """
        Draft personalized outreach messages for a researched person.

        Args:
            person_data: Output from PersonResearchService.to_dict()
            channels: Which channels to draft for (default: all available for this person)
            tone: Tone of the message
            language: 'es' for Spanish, 'en' for English
            custom_context: Any extra context for the drafting
            goal: What you want to achieve with the outreach

        Returns:
            OutreachDraftResult with drafts for each channel
        """
        if channels is None:
            # Auto-detect from person's contact channels
            channels = self._detect_channels(person_data)

        if not channels:
            channels = [OutreachChannel.EMAIL, OutreachChannel.LINKEDIN]

        if not self.gemini_key:
            result = OutreachDraftResult()
            result.person_name = person_data.get("name", "Unknown")
            result.error = "Gemini API key not configured (GOOGLE_AI_STUDIO)"
            return result

        return await self._draft_with_gemini(
            person_data, channels, tone, language, custom_context, goal
        )

    def _detect_channels(self, person_data: Dict[str, Any]) -> List[OutreachChannel]:
        """Auto-detect available outreach channels from person data"""
        channels = []
        contact_channels = person_data.get("contact_channels", [])

        if person_data.get("email") or "Email" in contact_channels:
            channels.append(OutreachChannel.EMAIL)
        if person_data.get("linkedin_url") or "LinkedIn" in contact_channels:
            channels.append(OutreachChannel.LINKEDIN)
        if person_data.get("twitter_handle") or "Twitter" in contact_channels:
            channels.append(OutreachChannel.TWITTER)

        return channels if channels else [OutreachChannel.EMAIL, OutreachChannel.LINKEDIN]

    async def _draft_with_gemini(
        self,
        person_data: Dict[str, Any],
        channels: List[OutreachChannel],
        tone: OutreachTone,
        language: str,
        custom_context: Optional[str],
        goal: str,
    ) -> OutreachDraftResult:
        """Use Gemini to draft personalized outreach messages"""
        result = OutreachDraftResult()
        result.person_name = person_data.get("name", "Unknown")

        try:
            from google import genai

            client = genai.Client(api_key=self.gemini_key)

            # Build the person summary
            person_summary = self._build_person_summary(person_data)
            channels_str = ", ".join([c.value for c in channels])
            lang_instruction = "en español" if language == "es" else "in English"

            system_prompt = f"""Eres un experto en outreach y networking profesional.
Trabajas para {self.business_name or 'una empresa de health-tech'}.
{f'Descripción del negocio: {self.business_description}' if self.business_description else ''}
{f'Nombre del remitente: {self.your_name}' if self.your_name else ''}
{f'Cargo del remitente: {self.your_role}' if self.your_role else ''}

Tu tarea es escribir mensajes de outreach personalizados, auténticos y efectivos.
NO uses lenguaje genérico. Cada mensaje debe mostrar que INVESTIGASTE a la persona.
Referencia detalles específicos de su perfil, intereses o actividad reciente."""

            prompt = f"""Redacta mensajes de outreach {lang_instruction} para contactar a esta persona:

--- PERSONA INVESTIGADA ---
{person_summary}
--- FIN PERSONA ---

Canales solicitados: {channels_str}
Tono: {tone.value}
Objetivo: {goal}
{f'Contexto adicional: {custom_context}' if custom_context else ''}

Devuelve ÚNICAMENTE un JSON válido con esta estructura (sin markdown, sin bloques de código):
{{
    "drafts": [
        {{
            "channel": "email|linkedin|twitter|whatsapp",
            "subject": "Asunto del mensaje (solo para email)",
            "body": "Cuerpo del mensaje completo",
            "notes": "Notas internas para el remitente (tips de timing, contexto)"
        }}
    ],
    "strategy_notes": "Estrategia general de acercamiento y por qué estos mensajes funcionarían",
    "recommended_sequence": ["canal1", "canal2", "canal3"]
}}

REGLAS:
- LinkedIn: máximo 300 caracteres para connection request, o mensaje InMail más largo
- Twitter: máximo 280 caracteres para DM inicial
- Email: profesional pero personal, máximo 150 palabras
- WhatsApp: breve y directo, máximo 100 palabras
- Siempre referencia algo ESPECÍFICO de la persona (no genérico)
- NO uses "Espero que este mensaje te encuentre bien" ni frases cliché"""

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    {"role": "user", "parts": [{"text": system_prompt + "\n\n" + prompt}]}
                ],
            )

            content = response.text
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                parsed = json.loads(json_match.group())

                for draft_data in parsed.get("drafts", []):
                    result.drafts.append(OutreachDraft(
                        channel=draft_data.get("channel", "email"),
                        subject=draft_data.get("subject", ""),
                        body=draft_data.get("body", ""),
                        notes=draft_data.get("notes", ""),
                    ))

                result.strategy_notes = parsed.get("strategy_notes", "")
                result.recommended_sequence = parsed.get("recommended_sequence", [])
                result.success = True
                logger.info(f"Drafted {len(result.drafts)} outreach messages for: {result.person_name}")
            else:
                result.error = "Could not parse Gemini response"
                logger.warning(f"Could not parse outreach drafts for: {result.person_name}")

        except Exception as e:
            result.error = str(e)
            logger.error(f"Outreach drafting failed for {result.person_name}: {e}")

        return result

    def _build_person_summary(self, data: Dict[str, Any]) -> str:
        """Format person data into a readable summary for the prompt"""
        lines = []
        field_labels = {
            "name": "Nombre",
            "title": "Cargo",
            "company": "Empresa",
            "company_role": "Rol",
            "industry": "Industria",
            "location": "Ubicación",
            "bio": "Bio",
            "background": "Trayectoria",
            "recent_activity": "Actividad reciente",
            "mutual_relevance": "Relevancia mutua",
            "linkedin_url": "LinkedIn",
            "twitter_handle": "Twitter",
            "email": "Email",
        }

        for key, label in field_labels.items():
            value = data.get(key)
            if value:
                lines.append(f"- {label}: {value}")

        interests = data.get("interests", [])
        if interests:
            lines.append(f"- Intereses: {', '.join(interests)}")

        channels = data.get("contact_channels", [])
        if channels:
            lines.append(f"- Canales de contacto: {', '.join(channels)}")

        return "\n".join(lines) if lines else f"- Nombre: {data.get('name', 'Desconocido')}"

    async def draft_batch(
        self,
        people_data: List[Dict[str, Any]],
        channels: List[OutreachChannel] = None,
        tone: OutreachTone = OutreachTone.PROFESSIONAL,
        language: str = "es",
        goal: str = "Schedule an introductory meeting",
    ) -> List[Dict[str, Any]]:
        """Draft outreach for multiple people"""
        results = []
        for person in people_data:
            draft_result = await self.draft_outreach(
                person_data=person,
                channels=channels,
                tone=tone,
                language=language,
                goal=goal,
            )
            results.append(draft_result.to_dict())
        return results
