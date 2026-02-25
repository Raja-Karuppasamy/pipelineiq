from fastapi import APIRouter, Depends, Query
from typing import Optional
from supabase import Client
from app.core.auth import verify_api_key, get_supabase_admin
from app.models.schemas import APIResponse

router = APIRouter()

@router.get("/", response_model=APIResponse)
async def get_insights(
    severity: Optional[str] = Query(default=None),
    limit: int = Query(default=20, le=100),
    auth: dict = Depends(verify_api_key),
    supabase: Client = Depends(get_supabase_admin),
):
    query = supabase.table("insights").select("*").eq("org_id", auth["org_id"])
    if severity:
        query = query.eq("severity", severity)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return APIResponse(success=True, data=result.data or [])

@router.patch("/{insight_id}/resolve", response_model=APIResponse)
async def resolve_insight(
    insight_id: str,
    auth: dict = Depends(verify_api_key),
    supabase: Client = Depends(get_supabase_admin),
):
    result = supabase.table("insights").update(
        {"resolved_at": "now()"}
    ).eq("id", insight_id).eq("org_id", auth["org_id"]).execute()
    return APIResponse(success=True, data=result.data[0] if result.data else {})
