import httpx
import uuid
import base64
from app.config import settings

class MTNMobileMoneyService:
    def __init__(self):
        self.base_url = "https://sandbox.momodeveloper.mtn.com" if settings.MOMO_TARGET_ENV == "sandbox" else "https://proxy.momoapi.mtn.co.ug"
        self.subscription_key = settings.MOMO_SUBSCRIPTION_KEY

    async def _get_access_token((self) -> str:
        """Generates OAuth2 Bearer Token using API User and API Key."""
        auth_string = f"{settings.MOMO_API_USER}:{settings.MOMO_API_KEY}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Ocp-Apim-Subscription-Key": self.subscription_key
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/collection/token/", headers=headers)
            response.raise_for_status()
            return response.json().get("access_token")

    async def request_to_pay(self, phone_number: str, amount_ugx: float, order_id: str) -> str:
        """Triggers USSD Prompt on customer's MTN Uganda phone for payment."""
        token = await self._get_access_token()
        reference_id = str(uuid.uuid4())
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": reference_id,
            "X-Target-Environment": settings.MOMO_TARGET_ENV,
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json"
        }
        
        # Format phone number for MTN API (must be 256XXXXXXXXX)
        formatted_phone = phone_number.replace("+", "")
        
        payload = {
            "amount": str(int(amount_ugx)),
            "currency": "UGX",
            "externalId": str(order_id),
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": formatted_phone
            },
            "payerMessage": f"MedSupply Order #{order_id}",
            "payeeNote": "Pharma Wholesale Payment"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/collection/v1_0/requesttopay", json=payload, headers=headers)
            if response.status_code == 202:
                return reference_id
            raise Exception(f"MoMo Request Failed: {response.text}")

momo_service = MTNMobileMoneyService()