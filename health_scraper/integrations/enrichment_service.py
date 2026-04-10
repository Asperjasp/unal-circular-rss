"""
AI Enrichment Service
=====================
Uses Perplexity API (or fallback to Google Gemini) to enrich company data
from minimal input (e.g., just a name) by researching online.

Perplexity API docs: https://docs.perplexity.ai/

Usage:
- Given a company name + domain, returns enriched fields like:
  industry, description, employee count, LinkedIn, etc.
- Especially useful when importing from Excel with incomplete data.
"""

import logging
import json
import re
import httpx
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


class AIEnrichmentService:
    """
    Service to enrich company data using AI (Perplexity or Gemini).
    
    Priority: Perplexity → Gemini → None
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

    async def enrich_company(
        self,
        company_name: str,
        domain: Optional[str] = None,
        city: Optional[str] = None,
        country: str = "Colombia",
    ) -> Dict[str, Any]:
        """
        Enrich company data by researching online via AI.

        Returns a dict with enriched fields matching HubSpot company properties.
        """
        if self.perplexity_key:
            return await self._enrich_with_perplexity(company_name, domain, city, country)
        elif self.gemini_key:
            return await self._enrich_with_gemini(company_name, domain, city, country)
        else:
            logger.warning("No AI enrichment service configured")
            return {"enriched": False, "reason": "No AI API key configured"}

    async def _enrich_with_perplexity(
        self, name: str, domain: Optional[str], city: Optional[str], country: str
    ) -> Dict[str, Any]:
        """Use Perplexity sonar model to research company info"""
        context = f"empresa '{name}'"
        if domain:
            context += f" con sitio web {domain}"
        if city:
            context += f" ubicada en {city}, {country}"

        prompt = f"""Investiga la siguiente {context}.

Devuelve ÚNICAMENTE un JSON válido con la siguiente estructura (sin texto adicional):
{{
    "name": "Nombre oficial completo",
    "domain": "dominio web principal",
    "industry": "sector/industria",
    "description": "descripción breve de la empresa (2-3 oraciones)",
    "city": "ciudad",
    "state": "departamento o región",
    "country": "{country}",
    "numberofemployees": número estimado o null,
    "phone": "teléfono principal o null",
    "website": "sitio web completo con https",
    "linkedin_company_page": "URL de LinkedIn corporativo o null",
    "services": ["lista", "de", "servicios", "principales"],
    "nit": "NIT si es empresa colombiana o null",
    "type_classification": "hospital|clinica|eps|ips|laboratorio|farmacia|aseguradora|gobierno|otro"
}}

Si no encuentras algún dato, pon null. No inventes datos."""

        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un investigador de empresas. Siempre respondes con JSON válido sin markdown ni texto adicional.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    PERPLEXITY_API_URL, json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()

            content = data["choices"][0]["message"]["content"]
            # Parse JSON from the response (handle markdown code blocks)
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                enriched = json.loads(json_match.group())
                enriched["enriched"] = True
                enriched["source"] = "perplexity"
                logger.info(f"Enriched company data for: {name}")
                return enriched
            else:
                logger.warning(f"Could not parse JSON from Perplexity response for: {name}")
                return {"enriched": False, "reason": "Could not parse AI response", "raw": content}

        except Exception as e:
            logger.error(f"Perplexity enrichment failed for {name}: {e}")
            # Fallback to Gemini if available
            if self.gemini_key:
                return await self._enrich_with_gemini(name, domain, city, country)
            return {"enriched": False, "reason": str(e)}

    async def _enrich_with_gemini(
        self, name: str, domain: Optional[str], city: Optional[str], country: str
    ) -> Dict[str, Any]:
        """Fallback: use Google Gemini to enrich (less real-time data)"""
        try:
            from google import genai

            client = genai.Client(api_key=self.gemini_key)

            context = f"empresa '{name}'"
            if domain:
                context += f" con sitio web {domain}"
            if city:
                context += f" ubicada en {city}, {country}"

            prompt = f"""Genera un JSON con información sobre la {context}.
Estructura:
{{
    "name": "Nombre oficial",
    "industry": "sector",
    "description": "descripción breve",
    "city": "ciudad",
    "state": "departamento",
    "services": ["servicios"],
    "type_classification": "tipo"
}}
Responde SOLO con JSON válido sin bloques de código."""

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
                return enriched

        except Exception as e:
            logger.error(f"Gemini enrichment failed for {name}: {e}")

        return {"enriched": False, "reason": "All AI enrichment methods failed"}

    async def enrich_batch(
        self,
        companies: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """
        Enrich a batch of companies.
        Each item should have at least 'name' key.
        """
        results = []
        for company in companies:
            enriched = await self.enrich_company(
                company_name=company.get("name", ""),
                domain=company.get("domain"),
                city=company.get("city"),
            )
            # Merge original data with enriched
            merged = {**company, **{k: v for k, v in enriched.items() if v is not None}}
            results.append(merged)
        return results
