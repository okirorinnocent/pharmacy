import httpx
from app.config import settings


class WhatsAppService:
    def __init__(self):
        self.url = f"https://graph.facebook.com/v21.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        self.headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }

    async def send_text_message(self, recipient_phone: str, message: str):
        """Sends a plain text message to a drug shop owner's WhatsApp number."""
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "text",
            "text": {"body": message}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, json=payload, headers=self.headers)
            return response.json()

    async def send_order_confirmation_interactive(self, recipient_phone: str, text_body: str, order_id: int):
        """Sends an interactive WhatsApp button for quick Mobile Money payment approval."""
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text_body},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": f"pay_momo_{order_id}", "title": "Pay via MoMo"}
                        },
                        {
                            "type": "reply",
                            "reply": {"id": f"pay_credit_{order_id}", "title": "Use 7-Day Credit"}
                        }
                    ]
                }
            }
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, json=payload, headers=self.headers)
            return response.json()


whatsapp_service = WhatsAppService()
