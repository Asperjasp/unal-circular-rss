"""
Person Research Service
========================
Uses Perplexity API to deeply research a person from minimal input
(e.g., name spotted on Twitter, a PDF, a conference, etc.).

Workflow Step 1:  You find someone interesting → feed their name/context here
                  → Perplexity researches everything about them online.

Perplexity API docs: https://docs.perplexity.ai/
"""

import logging
import json
import re
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


class PersonResearchResult:
    """Structured result of person research"""

    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.name: str = raw.get("name", "")
        self.title: Optional[str] = raw.get("title")
        self.company: Optional[str] = raw.get("company")
        self.company_role: Optional[str] = raw.get("company_role")
        self.industry: Optional[str] = raw.get("industry")
        self.linkedin_url: Optional[str] = raw.get("linkedin_url")
        self.twitter_handle: Optional[str] = raw.get("twitter_handle")
        self.email: Optional[str] = raw.get("email")
        self.location: Optional[str] = raw.get("location")
        self.bio: Optional[str] = raw.get("bio")
        self.background: Optional[str] = raw.get("background")
        self.interests: List[str] = raw.get("interests", [])
        self.recent_activity: Optional[str] = raw.get("recent_activity")
        self.mutual_relevance: Optional[str] = raw.get("mutual_relevance")
        self.contact_channels: List[str] = raw.get("contact_channels", [])
        self.enriched: bool = raw.get("enriched", False)
        self.source: str = raw.get("source", "unknown")
        self.researched_at: str = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "company": self.company,
            "company_role": self.company_role,
            "industry": self.industry,
            "linkedin_url": self.linkedin_url,
            "twitter_handle": self.twitter_handle,
            "email": self.email,
            "location": self.location,
            "bio": self.bio,
            "background": self.background,
            "interests": self.interests,
            "recent_activity": self.recent_activity,
            "mutual_relevance": self.mutual_relevance,
            "contact_channels": self.contact_channels,
            "enriched": self.enriched,
            "source": self.source,
            "researched_at": self.researched_at,
        }


class PersonResearchService:
    """
    Research people using Perplexity API from minimal context.
    
    Typical inputs:
    - A name from a tweet
    - A name + company from a PDF
    - A LinkedIn URL
    - A Twitter handle
    """

    def __init__(
        self,
        perplexity_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
    ):
        self.perplexity_key = perplexity_api_key
        self.gemini_key = gemini_api_key

    @property
    def available(self) -> bool:
        return bool(self.perplexity_key or self.gemini_key)

    async def research_person(
        self,
        name: str,
        context: Optional[str] = None,
        twitter_handle: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        company: Optional[str] = None,
        your_business_context: str = "health-tech company selling to hospitals and clinics in Colombia",
    ) -> PersonResearchResult:
        """
        Research a person from minimal input.

        Args:
            name: Person's name (required)
            context: Any extra context (e.g., "saw on Twitter discussing AI in healthcare")
            twitter_handle: Their Twitter/X handle if known
            linkedin_url: Their LinkedIn profile URL if known
            company: Their company if known
            your_business_context: Description of YOUR business for relevance scoring

        Returns:
            PersonResearchResult with all discovered information
        """
        if self.perplexity_key:
            return await self._research_with_perplexity(
                name, context, twitter_handle, linkedin_url, company, your_business_context
            )
        elif self.gemini_key:
            return await self._research_with_gemini(
                name, context, twitter_handle, linkedin_url, company, your_business_context
            )
        else:
            return PersonResearchResult({
                "enriched": False, "name": name, "source": "none",
                "reason": "No API key configured (need PERPLEXITY_API_KEY or GOOGLE_AI_STUDIO)"
            })

    async def _research_with_perplexity(
        self,
        name: str,
        context: Optional[str],
        twitter_handle: Optional[str],
        linkedin_url: Optional[str],
        company: Optional[str],
        business_context: str,
    ) -> PersonResearchResult:
        """Use Perplexity sonar model to deeply research a person"""

        # Build context clues
        clues = [f"Persona: '{name}'"]
        if company:
            clues.append(f"Empresa: {company}")
        if twitter_handle:
            clues.append(f"Twitter/X: @{twitter_handle.lstrip('@')}")
        if linkedin_url:
            clues.append(f"LinkedIn: {linkedin_url}")
        if context:
            clues.append(f"Contexto adicional: {context}")

        clues_text = "\n".join(clues)

        prompt = f"""Investiga a fondo a la siguiente persona:

{clues_text}

Necesito esta información para evaluar si es un contacto relevante para mi negocio ({business_context}).

Devuelve ÚNICAMENTE un JSON válido con esta estructura (sin texto adicional):
{{
    "name": "Nombre completo",
    "title": "Cargo o título profesional actual",
    "company": "Empresa actual",
    "company_role": "Descripción breve de su rol",
    "industry": "Sector/industria en la que trabaja",
    "linkedin_url": "URL de LinkedIn o null",
    "twitter_handle": "Handle de Twitter/X sin @ o null",
    "email": "Email profesional si es público, o null",
    "location": "Ciudad, País",
    "bio": "Biografía profesional breve (2-3 oraciones)",
    "background": "Trayectoria profesional resumida (empresas anteriores, logros clave)",
    "interests": ["interés1", "interés2", "interés3"],
    "recent_activity": "Actividad reciente relevante (publicaciones, conferencias, proyectos)",
    "mutual_relevance": "Por qué esta persona podría ser relevante para {business_context}",
    "contact_channels": ["LinkedIn", "Twitter", "Email"]
}}

Si no encuentras algún dato, pon null. NO inventes datos. Si no estás seguro, indica 'no confirmado'."""

        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Eres un investigador profesional de networking. "
                        "Investigas personas a fondo usando fuentes públicas. "
                        "Siempre respondes con JSON válido sin markdown ni texto adicional."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 1500,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    PERPLEXITY_API_URL, json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()

            content = data["choices"][0]["message"]["content"]
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                enriched = json.loads(json_match.group())
                enriched["enriched"] = True
                enriched["source"] = "perplexity"
                logger.info(f"Researched person: {name}")
                return PersonResearchResult(enriched)
            else:
                logger.warning(f"Could not parse JSON from Perplexity response for: {name}")
                return PersonResearchResult({
                    "enriched": False, "name": name, "source": "perplexity",
                    "reason": "Could not parse AI response",
                })

        except Exception as e:
            logger.error(f"Perplexity research failed for {name}: {e}")
            if self.gemini_key:
                return await self._research_with_gemini(
                    name, context, twitter_handle, linkedin_url, company, business_context
                )
            return PersonResearchResult({
                "enriched": False, "name": name, "source": "perplexity",
                "reason": str(e),
            })

    async def _research_with_gemini(
        self,
        name: str,
        context: Optional[str],
        twitter_handle: Optional[str],
        linkedin_url: Optional[str],
        company: Optional[str],
        business_context: str,
    ) -> PersonResearchResult:
        """Fallback: use Gemini to research (less real-time but still useful)"""
        try:
            from google import genai

            client = genai.Client(api_key=self.gemini_key)

            clues = [f"Persona: '{name}'"]
            if company:
                clues.append(f"Empresa: {company}")
            if twitter_handle:
                clues.append(f"Twitter: @{twitter_handle.lstrip('@')}")
            if context:
                clues.append(f"Contexto: {context}")

            prompt = f"""Investiga a: {chr(10).join(clues)}

Mi negocio: {business_context}

Devuelve JSON con: name, title, company, industry, bio, background, interests (lista),
mutual_relevance. Responde SOLO con JSON válido sin bloques de código."""

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )

            content = response.text
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                enriched = json.loads(json_match.group())
                enriched["enriched"] = True
                enriched["source"] = "gemini"
                enriched["name"] = enriched.get("name", name)
                return PersonResearchResult(enriched)

        except Exception as e:
            logger.error(f"Gemini person research failed for {name}: {e}")

        return PersonResearchResult({
            "enriched": False, "name": name, "source": "none",
            "reason": "All research methods failed",
        })

    async def research_batch(
        self,
        people: List[Dict[str, str]],
        your_business_context: str = "health-tech company selling to hospitals and clinics in Colombia",
    ) -> List[Dict[str, Any]]:
        """
        Research a batch of people.

        Each item should have at least 'name', and optionally
        'context', 'twitter_handle', 'linkedin_url', 'company'.
        """
        results = []
        for person in people:
            result = await self.research_person(
                name=person.get("name", ""),
                context=person.get("context"),
                twitter_handle=person.get("twitter_handle"),
                linkedin_url=person.get("linkedin_url"),
                company=person.get("company"),
                your_business_context=your_business_context,
            )
            results.append(result.to_dict())
        return results
