"""
outreach_templates.py — AiMedic M1/M2/M3 cold email templates (Spanish)
=========================================================================

Templates are designed for cold outreach to Colombian health institutions
(IPS, EPS, clinics). They follow anti-spam best practices:
- Plain conversational tone, no marketing language
- Short (under 150 words for M1)
- One clear CTA per email
- Personalization via {{variables}}

Sequence cadence:
- M1: Day 0 (cold intro)
- M2: Day 4 (follow-up, adds value)
- M3: Day 9 (breakup, removes friction)
- If reply at any point: move to human-led conversation

Variables required per template are listed in REQUIRED_VARS.
"""

from typing import Dict, List

# ── Template Definitions ────────────────────────────────────────────────

TEMPLATES: Dict[str, Dict] = {

    # ── M1: Cold intro — P2 AiMedic Connect (analytics) ─────────────────
    "M1_CONNECT": {
        "name": "M1 — Intro fría (P2 Connect)",
        "subject": "{{empresa}} — centralizar datos operacionales",
        "body": """\
<div style="font-family: Georgia, serif; font-size: 15px; line-height: 1.6; max-width: 580px; color: #1a1a1a;">

<p>Hola {{nombre}},</p>

<p>Le escribo brevemente. Soy Alejandro de <strong>AiMedic</strong>, startup de salud digital en Bogotá.</p>

<p>Trabajamos con clínicas e IPS en Colombia para centralizar datos de {{tipo_entidad}} en un solo panel: RIPS, historias clínicas, indicadores operacionales — sin exportar manualmente a Excel.</p>

<p>Notamos que {{empresa}} {{contexto_personalizado}}. Pensamos que hay oportunidad de ahorrar fácilmente 8-10 horas de trabajo administrativo a la semana.</p>

<p>¿Tiene 15 minutos esta semana para explorar si tiene sentido para {{empresa}}?</p>

<p>Quedo atento,<br>
<strong>Alejandro Sánchez</strong><br>
Founding Engineer — AiMedic<br>
<a href="https://aimedic.com.co">aimedic.com.co</a></p>

</div>""",
        "required_vars": ["nombre", "empresa", "tipo_entidad", "contexto_personalizado"],
        "product": "P2_CONNECT",
        "stage_after": "Contactado",
    },

    # ── M1: Cold intro — P1 AiMedic Operator (desktop AI assistant) ──────
    "M1_OPERATOR": {
        "name": "M1 — Intro fría (P1 Operator)",
        "subject": "{{empresa}} — asistente IA para {{especialidad}}",
        "body": """\
<div style="font-family: Georgia, serif; font-size: 15px; line-height: 1.6; max-width: 580px; color: #1a1a1a;">

<p>Hola {{nombre}},</p>

<p>Soy Alejandro de <strong>AiMedic</strong>. Le escribo porque vimos que {{empresa}} atiende pacientes de {{especialidad}} y queremos compartirles algo que puede ayudar al equipo médico.</p>

<p>Desarrollamos <strong>AiMedic Operator</strong>, un asistente de IA para profesionales de salud que ayuda con documentación clínica, búsqueda de protocolos y análisis de datos de pacientes — directamente en el computador del médico, sin depender de internet.</p>

<p>El problema que más resuelve: {{dolor}}.</p>

<p>¿Le parece si le mostramos una demo de 20 minutos? No tiene costo y puede ser virtual.</p>

<p>Saludos,<br>
<strong>Alejandro Sánchez</strong><br>
Founding Engineer — AiMedic<br>
<a href="https://aimedic.com.co">aimedic.com.co</a></p>

</div>""",
        "required_vars": ["nombre", "empresa", "especialidad", "dolor"],
        "product": "P1_OPERATOR",
        "stage_after": "Contactado",
    },

    # ── M2: Follow-up — adds a case study / concrete value ───────────────
    "M2_EMAIL": {
        "name": "M2 — Seguimiento (caso similar)",
        "subject": "Re: {{empresa}} — {{caso_similar}}",
        "body": """\
<div style="font-family: Georgia, serif; font-size: 15px; line-height: 1.6; max-width: 580px; color: #1a1a1a;">

<p>Hola {{nombre}},</p>

<p>Le hago un seguimiento breve a mi correo de hace unos días.</p>

<p>Quería compartirle que recientemente trabajamos con <strong>{{caso_similar}}</strong>, una institución con un perfil similar al de {{empresa}}. Logramos {{resultado_caso}} en los primeros 60 días.</p>

<p>Sé que el tiempo es escaso. Por eso propongo algo concreto: una llamada de 10 minutos donde le muestro exactamente qué haría diferente en {{empresa}}. Sin presentación larga, directo al punto.</p>

<p>¿Le funciona el {{fecha_propuesta}}?</p>

<p>Saludos,<br>
<strong>Alejandro Sánchez</strong><br>
AiMedic — <a href="https://aimedic.com.co">aimedic.com.co</a></p>

</div>""",
        "required_vars": ["nombre", "empresa", "caso_similar", "resultado_caso", "fecha_propuesta"],
        "product": None,  # applies to both P1 and P2
        "stage_after": "Contactado",
    },

    # ── CAMILO_V1: Camilo CEO template — IT Directors / Systems teams ────
    "CAMILO_V1": {
        "name": "Camilo V1 — Propuesta Cooperación (Director TI / Sistemas)",
        "subject": "Propuesta de Cooperación: {{empresa}} X Aimedic | Analítica Local e IA",
        "body": """\
<div style="font-family: Georgia, serif; font-size: 15px; line-height: 1.7; max-width: 600px; color: #1a1a1a;">

<p>Hola {{nombre}} y equipo de sistemas y dirección de {{empresa}},</p>

<p>Somos <strong>Aimedic</strong>, una plataforma de inteligencia artificial construida específicamente para instituciones de salud en Colombia. Les escribimos porque creemos que lo que estamos haciendo se alinea directamente con los desafíos que ustedes enfrentan hoy.</p>

<p>Estos son los tres frentes donde impactamos:</p>

<ul>
  <li><strong>Analítica Avanzada:</strong> Procesamos datos clínicos para anticipar riesgos y optimizar tiempos de espera, dando al médico herramientas que potencian su criterio — sin reemplazarlo.</li>
  <li><strong>Seguridad Local (On-Premise):</strong> Nuestra IA corre directamente en sus servidores. Los modelos más potentes del mercado, sin que un solo dato salga de su infraestructura.</li>
  <li><strong>Respaldo Clínico Validado:</strong> Trabajamos con la Fundación Cardio Infantil, la Fundación Neumológica y contamos con el respaldo de Google for Startups y NVIDIA — instituciones que avalan nuestra precisión y nuestro cuidado con los datos.</li>
</ul>

<p>Antes de contarles más, nos gustaría escucharlos.</p>

<p>Entender cómo están operando hoy y ver si tiene sentido trabajar juntos.</p>

<p>Nuestro CEO, <strong>Camilo Daza</strong>, tiene espacio esta semana.</p>

<p>Si les parece, aquí pueden agendar directamente:<br>
📅 <a href="https://calendar.app.google/iwNTpueCort26EuNA">https://calendar.app.google/iwNTpueCort26EuNA</a></p>

<p>¡Que tengan una gran semana!</p>

</div>""",
        "required_vars": ["nombre", "empresa"],
        "product": None,
        "stage_after": "Contactado",
    },

    # ── M3: Breakup — removes friction, leaves door open ─────────────────
    "M3_EMAIL": {
        "name": "M3 — Cierre (breakup)",
        "subject": "Última consulta — AiMedic x {{empresa}}",
        "body": """\
<div style="font-family: Georgia, serif; font-size: 15px; line-height: 1.6; max-width: 580px; color: #1a1a1a;">

<p>Hola {{nombre}},</p>

<p>Le escribo por última vez para no seguir interrumpiendo su agenda.</p>

<p>Si {{empresa}} no está evaluando soluciones de este tipo en este momento, lo entiendo completamente. A veces el momento simplemente no es el adecuado.</p>

<p>Solo le pido un favor de 10 segundos: ¿podría responderme con un número?</p>

<ul>
  <li><strong>1</strong> — No es el momento, pero contácteme en 3-6 meses</li>
  <li><strong>2</strong> — No me interesa por ahora</li>
  <li><strong>3</strong> — Me interesa, ¿podemos hablar esta semana?</li>
</ul>

<p>Sea cual sea la respuesta, la respeto y le agradezco el tiempo.</p>

<p>Saludos,<br>
<strong>Alejandro Sánchez</strong><br>
AiMedic — <a href="https://aimedic.com.co">aimedic.com.co</a></p>

</div>""",
        "required_vars": ["nombre", "empresa"],
        "product": None,
        "stage_after": "Contactado",
    },
}


# ── Template helpers ─────────────────────────────────────────────────────

def get_template(template_name: str) -> Dict:
    """Get a template by name. Raises KeyError if not found."""
    if template_name not in TEMPLATES:
        available = list(TEMPLATES.keys())
        raise KeyError(f"Template '{template_name}' not found. Available: {available}")
    return TEMPLATES[template_name]


def render_template(template_name: str, variables: Dict[str, str]) -> Dict[str, str]:
    """
    Render a template with variables.

    Returns dict with 'subject' and 'body' ready to send.
    Raises ValueError if required variables are missing.
    """
    tmpl = get_template(template_name)
    required = tmpl.get("required_vars", [])
    missing = [v for v in required if v not in variables or not variables[v]]

    if missing:
        raise ValueError(
            f"Template '{template_name}' missing required variables: {missing}"
        )

    subject = tmpl["subject"]
    body = tmpl["body"]

    for key, value in variables.items():
        subject = subject.replace(f"{{{{{key}}}}}", str(value))
        body = body.replace(f"{{{{{key}}}}}", str(value))

    return {"subject": subject, "body": body}


def list_templates() -> List[Dict]:
    """List all available templates with their metadata."""
    return [
        {
            "id": k,
            "name": v["name"],
            "product": v.get("product"),
            "required_vars": v.get("required_vars", []),
        }
        for k, v in TEMPLATES.items()
    ]


# ── Context examples for each template (for AI variable generation) ──────

CONTEXT_EXAMPLES = {
    "M1_CONNECT": {
        "tipo_entidad": "IPS",
        "contexto_personalizado": "opera 3 sedes en Bogotá y actualmente genera reportes RIPS de forma manual",
    },
    "M1_OPERATOR": {
        "especialidad": "cardiología",
        "dolor": "tiempo excesivo en documentación post-consulta (45+ min por paciente)",
    },
    "M2_EMAIL": {
        "caso_similar": "Clínica del Country",
        "resultado_caso": "reducir 40% el tiempo en generación de informes operacionales",
        "fecha_propuesta": "jueves 9 de abril a las 10am",
    },
    "M3_EMAIL": {},
}
