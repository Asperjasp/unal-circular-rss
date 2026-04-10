"""
Prospect Intelligence Endpoints
=================================
Endpoints para el flujo completo de prospección inteligente:

  1. POST /api/v1/prospect-intel/search
     → Perplexity investiga una institución y devuelve tabla de contactos

  2. POST /api/v1/prospect-intel/generate-linkedin
     → Claude genera M1/M2/M3 para un contacto específico

  3. POST /api/v1/prospect-intel/send-email
     → Zoho envía email de outreach + registra en HubSpot + tarea en Linear

  4. POST /api/v1/prospect-intel/full-workflow
     → Todo en uno: buscar → generar mensajes → crear en HubSpot → enviar email → Linear

  5. GET/POST /api/v1/prospect-intel/context-window
     → Lee / actualiza la ventana de contexto global de Perplexity

  6. POST /api/v1/prospect-intel/generate-email-body
     → Claude genera un email de outreach basado en los datos del prospecto
       (para enviarlo con Zoho)
"""

import logging
import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .prospect_intel_service import ProspectIntelService, ProspectContact
from .linkedin_outreach_service import (
    LinkedInOutreachService, PERSONAS, INSTITUCIONES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/prospect-intel", tags=["Prospect Intelligence"])

# ── Estado en memoria de la ventana de contexto global ──────────────────────
# Se puede persistir en .env o en DB; aquí lo mantenemos en memoria por sesión.
_global_context_window: str = os.getenv(
    "PERPLEXITY_CONTEXT_WINDOW",
    (
        "Foco exclusivo en instituciones de salud colombianas. "
        "Busca SOLO contactos que tengan poder de decisión sobre compra de software/tecnología: "
        "CIO, CTO, Gerente de Sistemas, Director TI, Gerente de Tecnología, o equivalente. "
        "Incluir también el número de PBX / centralita si lo encuentras. "
        "No incluir médicos generales ni personal administrativo sin poder TI."
    ),
)


def get_prospect_intel_svc() -> ProspectIntelService:
    """Crea instancia de ProspectIntelService con el contexto global actual"""
    return ProspectIntelService(
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"),
        default_context_window=_global_context_window,
    )


def get_linkedin_svc() -> LinkedInOutreachService:
    return LinkedInOutreachService(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


# ── Schemas Pydantic ─────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    institution_name: str = Field(..., description="Nombre de la institución a investigar")
    context_window: Optional[str] = Field(
        None,
        description=(
            "Contexto adicional específico para ESTA búsqueda. "
            "Ej: 'El CTO se llama Hernán Díaz, verificar si sigue ahí. "
            "Foco en la sede de Medellín, no en Bogotá.'"
        ),
    )
    model: str = Field("sonar", description="Modelo Perplexity: sonar, sonar-pro")


class GenerateLinkedInRequest(BaseModel):
    name: str
    last_name: str = ""
    persona: str = Field("cio_cto", description="Clave de PERSONAS")
    institution: str = ""
    institution_type: str = Field("eps", description="Clave de INSTITUCIONES")
    banner_quote: str = ""
    notes: str = ""


class SendEmailRequest(BaseModel):
    to_email: str
    to_name: str
    subject: str
    body: str
    # Metadatos para HubSpot
    institution: Optional[str] = None
    cargo: Optional[str] = None
    hubspot_lifecycle: Optional[str] = Field(
        "ATTEMPTED_TO_CONTACT",
        description="Etapa HubSpot: ATTEMPTED_TO_CONTACT | CONNECTED | OPEN_DEAL",
    )
    # Metadatos para Linear
    create_linear_task: bool = False
    linear_task_title: Optional[str] = None


class GenerateEmailBodyRequest(BaseModel):
    """Para generar el cuerpo de un email de outreach con Claude"""
    name: str
    last_name: str = ""
    cargo: str = ""
    institution: str = ""
    institution_type: str = "eps"
    pain_points: List[str] = Field(default_factory=list)
    notes: str = ""
    email_goal: str = "solicitar una llamada de 20 minutos"


class FullWorkflowRequest(BaseModel):
    # Institución
    institution_name: str
    context_window: Optional[str] = None
    # Para el contacto principal (si ya lo tienes seleccionado)
    selected_contact_index: int = Field(
        0, description="Índice del contacto principal en la lista devuelta por Perplexity"
    )
    # LinkedIn
    persona: str = "cio_cto"
    institution_type: str = "eps"
    # Email
    send_email: bool = False
    email_subject: Optional[str] = None
    # Integraciones
    create_hubspot_contact: bool = True
    create_linear_task: bool = True


class ContextWindowRequest(BaseModel):
    context_window: str = Field(
        ...,
        description=(
            "Texto de contexto que se incluirá en TODAS las búsquedas de Perplexity. "
            "Define aquí qué tipos de institución, qué cargos, qué geografía, etc."
        ),
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/personas")
async def list_personas():
    """Lista los tipos de persona disponibles para generar mensajes LinkedIn"""
    return {k: {"label": v["label"], "m2_angle": v["m2_angle"]} for k, v in PERSONAS.items()}


@router.get("/institution-types")
async def list_institution_types():
    """Lista los tipos de institución disponibles"""
    return INSTITUCIONES


@router.get("/context-window")
async def get_context_window():
    """Lee la ventana de contexto global de Perplexity"""
    return {"context_window": _global_context_window}


@router.post("/context-window")
async def set_context_window(req: ContextWindowRequest):
    """
    Actualiza la ventana de contexto global que se enviará a Perplexity
    en todas las búsquedas.

    Aquí puedes escribir instrucciones como:
    - "Solo instituciones en Medellín con más de 200 camas"
    - "Foco en EPS, ignorar IPS pequeñas"
    - "Buscar solo directores de TI o cargos equivalentes"
    """
    global _global_context_window
    _global_context_window = req.context_window.strip()
    logger.info(f"Ventana de contexto Perplexity actualizada ({len(_global_context_window)} chars)")
    return {"ok": True, "context_window": _global_context_window}


@router.post("/search")
async def search_institution(req: SearchRequest):
    """
    🔍 Investiga una institución de salud y devuelve la tabla de contactos.

    Usa Perplexity sonar para encontrar:
    - Contactos de TI / decisión
    - Emails y teléfonos
    - Canal de contacto recomendado
    - Prioridad (⭐⭐⭐⭐⭐ a ⭐)
    - Next action sugerida

    La ventana de contexto global + la específica de esta búsqueda se combinan
    para dar especificidad a la búsqueda.
    """
    svc = get_prospect_intel_svc()
    if not svc.available:
        raise HTTPException(
            status_code=503,
            detail="Perplexity no configurado. Agrega PERPLEXITY_API_KEY al .env",
        )

    result = await svc.search_institution(
        institution_name=req.institution_name,
        context_window=req.context_window,
        model=req.model,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return result.to_dict()


@router.post("/generate-linkedin")
async def generate_linkedin_messages(req: GenerateLinkedInRequest):
    """
    ✉️ Genera los mensajes M1 / M2 / M3 de LinkedIn para un prospecto.

    - M1: Nota de conexión (≤300 chars, zero venta)
    - M2: Pregunta de descubrimiento (se envía tras aceptar)
    - M3: Propuesta + calendario (solo si respondió M2)
    """
    svc = get_linkedin_svc()
    if not svc.available:
        raise HTTPException(
            status_code=503,
            detail="Anthropic no configurado. Agrega ANTHROPIC_API_KEY al .env",
        )

    messages = await svc.generate_messages(
        name=req.name,
        last_name=req.last_name,
        persona=req.persona,
        institution=req.institution,
        institution_type=req.institution_type,
        banner_quote=req.banner_quote,
        notes=req.notes,
    )

    if not messages.success:
        raise HTTPException(status_code=500, detail=messages.error)

    return messages.to_dict()


@router.post("/generate-email-body")
async def generate_email_body(req: GenerateEmailBodyRequest):
    """
    📧 Genera el cuerpo de un email de outreach usando Claude.

    El email sigue el tono Aimedic:
    - Sin lambonería
    - Referencia el pain point específico de la institución
    - CTA claro: llamada de 20 minutos
    - Incluye enlace al calendario
    """
    import os
    import httpx
    import re

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY no configurado",
        )

    inst_data = INSTITUCIONES.get(req.institution_type, INSTITUCIONES["eps"])
    pain_str  = "\n- ".join(req.pain_points) if req.pain_points else inst_data["pain"]
    calendar  = "https://calendar.app.google/iwNTpueCort26EuNA"

    prompt = f"""Eres el equipo de ventas de Aimedic, startup colombiana de IA médica respaldada por Google for Startups y NVIDIA. 
Clientes: Fundación Cardio Infantil, Fundación Neumológica.
Vendes: analítica avanzada de salud y modelos IA on-premise para hospitales y EPS.

Escribe un email de prospección en español (Colombia) para:
- Nombre: {req.name} {req.last_name}
- Cargo: {req.cargo or inst_data['label']}
- Institución: {req.institution or '[Institución]'} ({inst_data['label']})
- Pain points detectados:
  - {pain_str}
- Notas: {req.notes or 'Ninguna'}
- Objetivo del email: {req.email_goal}

REGLAS:
- Asunto corto y sin clickbait (incluirlo al inicio en la forma "Asunto: ...")
- Cuerpo: máx 150 palabras
- Tono: directo, profesional, sin lambonería
- Menciona UN caso de éxito real (Cardio Infantil o Neumológica)
- CTA: agendar llamada de 20 min en {calendar}
- NUNCA uses "don/doña" — usa solo el nombre propio
- Firma: equipo Aimedic

Devuelve JSON:
{{
  "subject": "asunto del email",
  "body": "cuerpo del email en texto plano con saltos de línea"
}}
Solo el JSON, sin markdown."""

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 600,
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    raw = data["content"][0]["text"].strip()
    clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```")
    parsed = __import__("json").loads(clean)

    return {
        "subject": parsed.get("subject", ""),
        "body": parsed.get("body", ""),
    }


@router.post("/send-email")
async def send_email_outreach(req: SendEmailRequest):
    """
    📤 Envía un email de outreach por Zoho y opcionalmente:
    - Crea/actualiza el contacto en HubSpot
    - Crea tarea en Linear
    - Registra el intento en el pipeline de HubSpot
    """
    results: Dict[str, Any] = {}

    # ── 1. Enviar por Zoho ───────────────────────────────────────────────────
    zoho_enabled = all([
        os.getenv("ZOHO_CLIENT_ID"),
        os.getenv("ZOHO_CLIENT_SECRET"),
        os.getenv("ZOHO_REFRESH_TOKEN"),
        os.getenv("ZOHO_ACCOUNT_ID"),
        os.getenv("ZOHO_FROM_EMAIL"),
    ])

    if not zoho_enabled:
        results["email"] = {"ok": False, "reason": "Zoho no configurado en .env"}
    else:
        try:
            from .zoho_email_service import ZohoEmailService
            zoho = ZohoEmailService(
                client_id=os.getenv("ZOHO_CLIENT_ID"),
                client_secret=os.getenv("ZOHO_CLIENT_SECRET"),
                refresh_token=os.getenv("ZOHO_REFRESH_TOKEN"),
                account_id=os.getenv("ZOHO_ACCOUNT_ID"),
                from_email=os.getenv("ZOHO_FROM_EMAIL"),
                zoho_domain=os.getenv("ZOHO_DOMAIN", "zoho.com"),
            )
            email_result = await zoho.send_email(
                to_address=req.to_email,
                subject=req.subject,
                body=req.body,
                to_name=req.to_name,
            )
            results["email"] = {"ok": True, "detail": email_result}
        except Exception as e:
            logger.error(f"Zoho email error: {e}")
            results["email"] = {"ok": False, "reason": str(e)}

    # ── 2. HubSpot contact + lifecycle stage ─────────────────────────────────
    hs_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
    if hs_token:
        try:
            from .hubspot_service import HubSpotService
            hs = HubSpotService(access_token=hs_token)
            name_parts = req.to_name.split() if req.to_name else [""]
            contact = await hs.create_contact(
                email=req.to_email,
                firstname=name_parts[0],
                lastname=" ".join(name_parts[1:]) if len(name_parts) > 1 else "",
                jobtitle=req.cargo or "",
            )
            results["hubspot"] = {"ok": True, "contact_id": contact.get("id")}
        except Exception as e:
            logger.warning(f"HubSpot contact creation failed: {e}")
            results["hubspot"] = {"ok": False, "reason": str(e)}
    else:
        results["hubspot"] = {"ok": False, "reason": "HUBSPOT_ACCESS_TOKEN no configurado"}

    # ── 3. Linear task ───────────────────────────────────────────────────────
    linear_key = os.getenv("LINEAR_API_KEY")
    if req.create_linear_task and linear_key:
        try:
            from .linear_service import LinearService, LinearPriority
            linear = LinearService(api_key=linear_key)
            team_id = os.getenv("LINEAR_DEFAULT_TEAM_ID", "")
            if not team_id:
                results["linear"] = {"ok": False, "reason": "LINEAR_DEFAULT_TEAM_ID no configurado"}
            else:
              task_title = req.linear_task_title or f"Email enviado → {req.to_name} ({req.institution or req.to_email})"
              task = await linear.create_issue(
                team_id=team_id,
                title=task_title,
                description=(
                    f"Email de outreach enviado a {req.to_name} <{req.to_email}>\n"
                    f"Institución: {req.institution or 'N/A'}\n"
                    f"Cargo: {req.cargo or 'N/A'}\n"
                    f"Asunto: {req.subject}\n\n"
                    f"---\n{req.body}"
                ),
                priority=LinearPriority.MEDIUM,
              )
              results["linear"] = {"ok": True, "issue_id": task.get("id"), "url": task.get("url")}
        except Exception as e:
            logger.warning(f"Linear task creation failed: {e}")
            results["linear"] = {"ok": False, "reason": str(e)}
    else:
        results["linear"] = {"ok": False, "reason": "LINEAR_API_KEY no configurado o create_linear_task=false"}

    return {"ok": True, "results": results}


@router.post("/full-workflow")
async def full_workflow(req: FullWorkflowRequest):
    """
    🚀 Flujo completo de prospección en un solo endpoint:

    1. Perplexity investiga la institución → tabla de contactos
    2. Claude genera M1/M2/M3 para el contacto principal
    3. Crea contacto en HubSpot (opcional)
    4. Crea tarea en Linear (opcional)
    5. (Opcional) Genera y envía email por Zoho

    Devuelve todo en un solo objeto para mostrar en el panel.
    """
    result: Dict[str, Any] = {}

    # ── 1. Búsqueda con Perplexity ───────────────────────────────────────────
    intel_svc = get_prospect_intel_svc()
    if not intel_svc.available:
        raise HTTPException(
            status_code=503,
            detail="PERPLEXITY_API_KEY no configurado",
        )

    intel = await intel_svc.search_institution(
        institution_name=req.institution_name,
        context_window=req.context_window,
    )

    if not intel.success:
        raise HTTPException(status_code=500, detail=intel.error)

    result["intel"] = intel.to_dict()

    # ── 2. Generar M1/M2/M3 para el contacto seleccionado ───────────────────
    contacts = intel.contacts
    if not contacts:
        result["linkedin"] = {"ok": False, "reason": "No se encontraron contactos"}
        return result

    idx = min(req.selected_contact_index, len(contacts) - 1)
    contact = contacts[idx]

    linkedin_svc = get_linkedin_svc()
    if linkedin_svc.available:
        msgs = await linkedin_svc.generate_messages(
            name=contact.nombre or contact.contacto.split()[0],
            last_name=contact.apellido or "",
            persona=req.persona,
            institution=req.institution_name,
            institution_type=req.institution_type,
            banner_quote=contact.banner_linkedin or "",
            notes=contact.notas or contact.rol_ti,
        )
        result["linkedin"] = msgs.to_dict()
    else:
        result["linkedin"] = {"ok": False, "reason": "ANTHROPIC_API_KEY no configurado"}

    # ── 3. HubSpot (si hay email y está habilitado) ──────────────────────────
    if req.create_hubspot_contact and contact.email:
        hs_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
        if hs_token:
            try:
                from .hubspot_service import HubSpotService
                hs = HubSpotService(access_token=hs_token)
                hs_contact = await hs.create_contact(
                    email=contact.email,
                    firstname=contact.nombre or "",
                    lastname=contact.apellido or "",
                    jobtitle=contact.cargo or "",
                    phone=contact.telefono,
                )
                result["hubspot"] = {"ok": True, "contact_id": hs_contact.get("id")}
            except Exception as e:
                result["hubspot"] = {"ok": False, "reason": str(e)}
        else:
            result["hubspot"] = {"ok": False, "reason": "HUBSPOT_ACCESS_TOKEN no configurado"}

    # ── 4. Linear task ───────────────────────────────────────────────────────
    if req.create_linear_task:
        linear_key = os.getenv("LINEAR_API_KEY")
        team_id_fw = os.getenv("LINEAR_DEFAULT_TEAM_ID", "")
        if linear_key and team_id_fw:
            try:
                from .linear_service import LinearService, LinearPriority
                linear = LinearService(api_key=linear_key)
                task_fw = await linear.create_issue(
                    team_id=team_id_fw,
                    title=f"Prospecto: {contact.contacto} — {req.institution_name}",
                    description=(
                        f"**Institución:** {intel.institution_name}\n"
                        f"**Pain points:** {', '.join(intel.pain_points)}\n\n"
                        f"**Contacto seleccionado:**\n"
                        f"- Canal: {contact.canal}\n"
                        f"- Nombre: {contact.contacto}\n"
                        f"- Email: {contact.email or 'N/A'}\n"
                        f"- Teléfono: {contact.telefono or 'N/A'}\n"
                        f"- Rol TI: {contact.rol_ti}\n"
                        f"- Next action: {contact.next_action}\n"
                        f"- Prioridad: {contact.prioridad}\n"
                        f"- Razón: {contact.razon}\n\n"
                        f"**LinkedIn M1:**\n{result.get('linkedin', {}).get('m1', 'N/A')}"
                    ),
                    priority=LinearPriority.HIGH,
                )
                result["linear"] = {"ok": True, "issue_id": task_fw.get("id"), "url": task_fw.get("url")}
            except Exception as e:
                result["linear"] = {"ok": False, "reason": str(e)}
        else:
            result["linear"] = {"ok": False, "reason": "LINEAR_API_KEY o LINEAR_DEFAULT_TEAM_ID no configurado"}

    return result


@router.get("/health")
async def health():
    """Estado de las integraciones necesarias para Prospect Intel"""
    return {
        "perplexity": bool(os.getenv("PERPLEXITY_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "hubspot": bool(os.getenv("HUBSPOT_ACCESS_TOKEN")),
        "linear": bool(os.getenv("LINEAR_API_KEY")),
        "zoho_email": all([
            os.getenv("ZOHO_CLIENT_ID"),
            os.getenv("ZOHO_REFRESH_TOKEN"),
            os.getenv("ZOHO_ACCOUNT_ID"),
        ]),
        "context_window_set": bool(_global_context_window),
        "context_window_preview": _global_context_window[:120] + "..." if len(_global_context_window) > 120 else _global_context_window,
    }
