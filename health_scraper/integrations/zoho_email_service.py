"""
Zoho Email Integration Service
================================
Integrates with Zoho Mail API for sending emails as part of the sales pipeline.

Zoho Mail API docs: https://www.zoho.com/mail/help/api/

Setup:
1. Go to Zoho Developer Console: https://api-console.zoho.com/
2. Create a Self Client or Server-based Application
3. Generate OAuth tokens with scopes:
   - ZohoMail.messages.ALL
   - ZohoMail.accounts.READ
4. Set in .env:
   - ZOHO_CLIENT_ID
   - ZOHO_CLIENT_SECRET
   - ZOHO_REFRESH_TOKEN
   - ZOHO_ACCOUNT_ID (your Zoho Mail account ID)
   - ZOHO_FROM_EMAIL (your email address in Zoho)

Token refresh:
  The service auto-refreshes the access token using the refresh token.
"""

import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

ZOHO_AUTH_URL = "https://accounts.zoho.com/oauth/v2/token"
ZOHO_MAIL_API = "https://mail.zoho.com/api"


class ZohoEmailService:
    """
    Service for sending and tracking emails via Zoho Mail API.
    
    Supports:
    - Sending individual emails
    - Sending templated bulk emails
    - Tracking sent emails
    - Reading inbox/folders
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        account_id: str,
        from_email: str,
        zoho_domain: str = "zoho.com",  # zoho.com, zoho.eu, zoho.in, etc.
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.account_id = account_id
        self.from_email = from_email
        self.zoho_domain = zoho_domain
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        
        # Build URLs based on region
        if "eu" in zoho_domain:
            self.auth_url = "https://accounts.zoho.eu/oauth/v2/token"
            self.api_base = "https://mail.zoho.eu/api"
        elif "in" in zoho_domain:
            self.auth_url = "https://accounts.zoho.in/oauth/v2/token"
            self.api_base = "https://mail.zoho.in/api"
        else:
            self.auth_url = ZOHO_AUTH_URL
            self.api_base = ZOHO_MAIL_API

    @property
    def available(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token and self.account_id)

    async def _get_access_token(self) -> str:
        """Get or refresh the OAuth access token"""
        if self._access_token and self._token_expiry and datetime.utcnow() < self._token_expiry:
            return self._access_token

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.auth_url,
                data={
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                },
            )
            response.raise_for_status()
            data = response.json()

            if "access_token" not in data:
                raise Exception(f"Zoho auth failed: {data}")

            self._access_token = data["access_token"]
            # Token expires in ~1 hour, refresh 5 minutes early
            from datetime import timedelta
            self._token_expiry = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600) - 300)
            
            logger.info("Zoho access token refreshed")
            return self._access_token

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Execute an authenticated request to Zoho Mail API"""
        token = await self._get_access_token()
        url = f"{self.api_base}/accounts/{self.account_id}{endpoint}"
        
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method, url, json=json_data, params=params, headers=headers,
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    # ── Send Emails ───────────────────────────────────────────────────

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        is_html: bool = True,
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a single email via Zoho Mail.
        
        Returns:
            Dict with message ID and status.
        """
        payload: Dict[str, Any] = {
            "fromAddress": self.from_email,
            "toAddress": to_email,
            "subject": subject,
            "content": body,
            "mailFormat": "html" if is_html else "plaintext",
        }
        
        if cc:
            payload["ccAddress"] = ",".join(cc)
        if bcc:
            payload["bccAddress"] = ",".join(bcc)
        if reply_to:
            payload["replyTo"] = reply_to

        try:
            result = await self._request("POST", "/messages", json_data=payload)
            logger.info(f"Email sent to {to_email}: {subject}")
            return {
                "success": True,
                "message_id": result.get("data", {}).get("messageId"),
                "to": to_email,
                "subject": subject,
                "sent_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return {
                "success": False,
                "error": str(e),
                "to": to_email,
                "subject": subject,
            }

    async def send_templated_email(
        self,
        to_email: str,
        subject_template: str,
        body_template: str,
        variables: Dict[str, str],
        cc: Optional[List[str]] = None,
        is_html: bool = True,
    ) -> Dict[str, Any]:
        """
        Send an email with template variable substitution.
        
        Variables use {{variable}} syntax.
        Example: "Hola {{nombre}}, le escribo de {{empresa}}..."
        """
        subject = subject_template
        body = body_template
        
        for key, value in variables.items():
            subject = subject.replace(f"{{{{{key}}}}}", str(value))
            body = body.replace(f"{{{{{key}}}}}", str(value))
        
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            cc=cc,
            is_html=is_html,
        )

    async def send_bulk_emails(
        self,
        recipients: List[Dict[str, Any]],
        subject_template: str,
        body_template: str,
        delay_seconds: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Send templated emails to multiple recipients.
        
        Each recipient dict should have:
        - email: str (required)
        - variables: Dict[str, str] (template variables)
        
        Returns summary of sent/failed.
        """
        import asyncio
        
        sent = []
        failed = []
        
        for i, recipient in enumerate(recipients):
            email = recipient.get("email")
            if not email:
                failed.append({"index": i, "error": "No email address"})
                continue
            
            variables = recipient.get("variables", {})
            
            try:
                result = await self.send_templated_email(
                    to_email=email,
                    subject_template=subject_template,
                    body_template=body_template,
                    variables=variables,
                )
                
                if result.get("success"):
                    sent.append({
                        "email": email,
                        "message_id": result.get("message_id"),
                    })
                else:
                    failed.append({
                        "email": email,
                        "error": result.get("error"),
                    })
            except Exception as e:
                failed.append({"email": email, "error": str(e)})
            
            # Rate limiting
            if i < len(recipients) - 1:
                await asyncio.sleep(delay_seconds)
        
        return {
            "total": len(recipients),
            "sent": len(sent),
            "failed": len(failed),
            "sent_details": sent,
            "failed_details": failed,
        }

    # ── Read Emails ───────────────────────────────────────────────────

    async def get_folders(self) -> List[Dict[str, Any]]:
        """Get email folders list"""
        result = await self._request("GET", "/folders")
        return result.get("data", [])

    async def get_emails(
        self,
        folder_id: Optional[str] = None,
        limit: int = 20,
        start: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get emails from a folder (default: inbox)"""
        params: Dict[str, Any] = {
            "limit": limit,
            "start": start,
        }
        
        endpoint = f"/folders/{folder_id}/messages" if folder_id else "/messages/view"
        result = await self._request("GET", endpoint, params=params)
        return result.get("data", [])

    async def get_email_detail(self, message_id: str, folder_id: str = "inbox") -> Dict[str, Any]:
        """Get full email detail"""
        result = await self._request("GET", f"/folders/{folder_id}/messages/{message_id}/content")
        return result.get("data", {})

    # ── Account Info ──────────────────────────────────────────────────

    async def get_account_info(self) -> Dict[str, Any]:
        """Get Zoho account information"""
        try:
            token = await self._get_access_token()
            url = f"{self.api_base}/accounts/{self.account_id}"
            headers = {"Authorization": f"Zoho-oauthtoken {token}"}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json().get("data", {})
        except Exception as e:
            logger.error(f"Error getting Zoho account: {e}")
            return {"error": str(e)}

    # ── Outreach Templates ────────────────────────────────────────────

    @staticmethod
    def get_default_templates() -> List[Dict[str, Any]]:
        """Get default outreach email templates in Spanish"""
        return [
            {
                "id": "intro_cold",
                "name": "Introducción en Frío",
                "subject": "{{empresa_propia}} - Solución de salud digital para {{empresa_destino}}",
                "body": """
<div style="font-family: Arial, sans-serif; max-width: 600px;">
    <p>Estimado/a {{nombre_contacto}},</p>
    
    <p>Mi nombre es {{mi_nombre}} de <strong>{{empresa_propia}}</strong>. Nos especializamos en 
    soluciones de tecnología para instituciones de salud en Colombia.</p>
    
    <p>Noté que <strong>{{empresa_destino}}</strong> {{contexto_personalizado}} y creo que 
    nuestra plataforma podría ser de gran valor para ustedes.</p>
    
    <p>¿Le gustaría agendar una breve llamada de 15 minutos esta semana para explorar 
    cómo podemos ayudarles?</p>
    
    <p>Quedo atento a su respuesta.</p>
    
    <p>Cordialmente,<br>
    {{mi_nombre}}<br>
    {{mi_cargo}}<br>
    {{empresa_propia}}</p>
</div>""",
                "variables": ["nombre_contacto", "empresa_destino", "contexto_personalizado", "mi_nombre", "mi_cargo", "empresa_propia"],
            },
            {
                "id": "follow_up_1",
                "name": "Seguimiento #1",
                "subject": "Re: {{empresa_propia}} - Seguimiento",
                "body": """
<div style="font-family: Arial, sans-serif; max-width: 600px;">
    <p>Hola {{nombre_contacto}},</p>
    
    <p>Le escribo para dar seguimiento a mi correo anterior. Entiendo que su agenda 
    puede estar ocupada.</p>
    
    <p>En resumen, en <strong>{{empresa_propia}}</strong> ayudamos a instituciones de salud 
    como <strong>{{empresa_destino}}</strong> a {{propuesta_valor}}.</p>
    
    <p>¿Tiene 10 minutos disponibles esta semana?</p>
    
    <p>Saludos,<br>
    {{mi_nombre}}</p>
</div>""",
                "variables": ["nombre_contacto", "empresa_destino", "propuesta_valor", "mi_nombre", "empresa_propia"],
            },
            {
                "id": "meeting_request",
                "name": "Solicitud de Reunión",
                "subject": "Solicitud de reunión - {{empresa_propia}} x {{empresa_destino}}",
                "body": """
<div style="font-family: Arial, sans-serif; max-width: 600px;">
    <p>Estimado/a {{nombre_contacto}},</p>
    
    <p>Gracias por su interés en {{empresa_propia}}. Me gustaría agendar una reunión 
    para presentarle nuestra solución y cómo puede beneficiar a {{empresa_destino}}.</p>
    
    <p><strong>Propuesta de agenda:</strong></p>
    <ul>
        <li>Breve presentación de {{empresa_propia}} (5 min)</li>
        <li>Demo de la plataforma (15 min)</li>
        <li>Preguntas y próximos pasos (10 min)</li>
    </ul>
    
    <p>¿Cuál de estos horarios le funciona mejor?</p>
    <ul>
        <li>{{opcion_horario_1}}</li>
        <li>{{opcion_horario_2}}</li>
        <li>{{opcion_horario_3}}</li>
    </ul>
    
    <p>Cordialmente,<br>
    {{mi_nombre}}<br>
    {{mi_cargo}}</p>
</div>""",
                "variables": ["nombre_contacto", "empresa_destino", "mi_nombre", "mi_cargo", "empresa_propia", "opcion_horario_1", "opcion_horario_2", "opcion_horario_3"],
            },
            {
                "id": "proposal_send",
                "name": "Envío de Propuesta",
                "subject": "Propuesta comercial - {{empresa_propia}} para {{empresa_destino}}",
                "body": """
<div style="font-family: Arial, sans-serif; max-width: 600px;">
    <p>Estimado/a {{nombre_contacto}},</p>
    
    <p>Fue un gusto conversar con usted. Adjunto encontrará la propuesta comercial 
    que hemos preparado para <strong>{{empresa_destino}}</strong>.</p>
    
    <p><strong>Resumen de la propuesta:</strong></p>
    <ul>
        <li>{{punto_1}}</li>
        <li>{{punto_2}}</li>
        <li>{{punto_3}}</li>
    </ul>
    
    <p>Quedo disponible para resolver cualquier duda. ¿Podemos agendar una 
    llamada de seguimiento para la próxima semana?</p>
    
    <p>Cordialmente,<br>
    {{mi_nombre}}<br>
    {{mi_cargo}}<br>
    {{empresa_propia}}</p>
</div>""",
                "variables": ["nombre_contacto", "empresa_destino", "mi_nombre", "mi_cargo", "empresa_propia", "punto_1", "punto_2", "punto_3"],
            },
        ]
