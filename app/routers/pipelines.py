from fastapi import APIRouter, Depends, Query
from typing import Optional
from supabase import Client
from app.core.auth import verify_api_key, get_supabase_admin
from app.models.schemas import PipelineRunCreate, APIResponse
from datetime import datetime, timedelta
import statistics

router = APIRouter()

@router.post("/runs", response_model=APIResponse)
async def submit_pipeline_run(
    run: PipelineRunCreate,
    auth: dict = Depends(verify_api_key),
    supabase: Client = Depends(get_supabase_admin),
):
    record = run.model_dump()
    record["org_id"] = auth["org_id"]
    record["started_at"] = run.started_at.isoformat()
    record["finished_at"] = run.finished_at.isoformat() if run.finished_at else None
    result = supabase.table("pipeline_runs").insert(record).execute()
    return APIResponse(success=True, data=result.data[0] if result.data else {})

@router.get("/stats/{repo_owner}/{repo_name}", response_model=APIResponse)
async def get_pipeline_stats(
    repo_owner: str,
    repo_name: str,
    period_days: int = Query(default=30, ge=1, le=365),
    auth: dict = Depends(verify_api_key),
    supabase: Client = Depends(get_supabase_admin),
):
    repo_full_name = f"{repo_owner}/{repo_name}"
    since = (datetime.utcnow() - timedelta(days=period_days)).isoformat()
    result = supabase.table("pipeline_runs").select("*").eq(
        "org_id", auth["org_id"]
    ).eq("repo_full_name", repo_full_name).gte("started_at", since).execute()
    runs = result.data or []
    if not runs:
        return APIResponse(success=True, data={"total_runs": 0, "repo": repo_full_name})
    total = len(runs)
    successes = len([r for r in runs if r["status"] == "success"])
    durations = [r["duration_seconds"] for r in runs if r.get("duration_seconds", 0) > 0]
    return APIResponse(success=True, data={
        "repo_full_name": repo_full_name,
        "period_days": period_days,
        "total_runs": total,
        "success_rate": round(successes / total, 3),
        "avg_duration_seconds": round(statistics.mean(durations), 1) if durations else 0,
        "failure_rate": round((total - successes) / total, 3),
    })

@router.get("/runs/{repo_owner}/{repo_name}", response_model=APIResponse)
async def get_pipeline_runs(
    repo_owner: str,
    repo_name: str,
    limit: int = Query(default=50, ge=1, le=500),
    auth: dict = Depends(verify_api_key),
    supabase: Client = Depends(get_supabase_admin),
):
    repo_full_name = f"{repo_owner}/{repo_name}"
    result = supabase.table("pipeline_runs").select("*").eq(
        "org_id", auth["org_id"]
    ).eq("repo_full_name", repo_full_name).order("started_at", desc=True).limit(limit).execute()
    return APIResponse(success=True, data=result.data or [])
