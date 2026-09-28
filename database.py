import asyncio
from supabase import acreate_client, AsyncClient
from app.config import settings

# Global async client instance
supabase_client: AsyncClient = None


async def init_supabase():
    global supabase_client
    supabase_client = await acreate_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY
    )


def get_supabase() -> AsyncClient:
    return supabase_client
