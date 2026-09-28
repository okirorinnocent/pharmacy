from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "MedSupply Uganda (Supabase Powered)"

    # Supabase Credentials (Found in Supabase Dashboard > Project Settings > API)
    SUPABASE_URL: str = "https://your-project-id.supabase.co"
    # Service role key bypasses RLS for server-side FastAPI writes
    SUPABASE_SERVICE_ROLE_KEY: str = "eyJhbG..."

    # WhatsApp & MoMo Secrets
    WHATSAPP_TOKEN: str = "your_whatsapp_token"
    WHATSAPP_PHONE_NUMBER_ID: str = "your_phone_id"
    WHATSAPP_VERIFY_TOKEN: str = "medsupply_secret_2026"


settings = Settings()
