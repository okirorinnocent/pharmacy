from fastapi import FastAPI
from app.routers import webhook
from app.supabase_client import init_supabase

app = FastAPI(title="MedSupply Uganda (Supabase Backend)")


@app.on_event("startup")
async def startup_event():
    # Initialize Supabase async client on app launch
    await init_supabase()

app.include_router(webhook.router)
