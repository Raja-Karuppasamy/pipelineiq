from fastapi import Header, HTTPException, Depends
from supabase import create_client, Client
from app.core.config import settings
import hashlib

def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def get_supabase_admin() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

async def verify_api_key(
    x_pipelineiq_key: str = Header(...),
    supabase: Client = Depends(get_supabase_admin),
) -> dict:
    if not x_pipelineiq_key or len(x_pipelineiq_key) < 20:
        raise HTTPException(status_code=401, detail="Invalid API key format")
    key_hash = hashlib.sha256(x_pipelineiq_key.encode()).hexdigest()
    result = supabase.table("api_keys").select(
        "*, organizations(id, name, plan, is_active)"
    ).eq("key_hash", key_hash).eq("is_active", True).single().execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    org = result.data.get("organizations")
    if not org or not org.get("is_active"):
        raise HTTPException(status_code=403, detail="Organization account is inactive")
    return {"org_id": org["id"], "org_name": org["name"], "plan": org["plan"], "api_key_id": result.data["id"]}
