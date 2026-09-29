from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MedSupply Uganda"

    # Supabase Credentials
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    DATABASE_URL: str

    # WhatsApp API
    WHATSAPP_TOKEN: str
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_VERIFY_TOKEN: str = "medsupply_secret_2026"

    # MTN MoMo API
    MOMO_SUBSCRIPTION_KEY: str
    MOMO_API_USER: str
    MOMO_API_KEY: str
    MOMO_TARGET_ENV: str = "sandbox"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
