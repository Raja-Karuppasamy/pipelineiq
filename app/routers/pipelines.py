from fastapi import APIRouter, Depends, Query, BackgroundTasks
from typing import Optional
from supabase import Client
from app.core.auth import verify_api_key, get_supabase_admin
from app.models.schemas import PipelineRunCreate, APIResponse
from datetime import datetime, timedelta
import statistics

router = APIRouter()


async def run_ai_diagnosis(run: dict, org_id: str, supabase: Client):
    try:
        from app.services.ai_diagnosis import diagnose_from_run
        from app.services.slack_service import send_pipeline_alert

        insight = await diagnose_from_run(run)
        if not insight:
            return

        supabase.table("insights").insert({
            "org_id": org_id,
            "pipeline_run_id": run.get("id"),
            "repo_full_name": run.get("repo_full_name"),
            "source": "ai_diagnosis",
            "severity": insight.get("severity", "info"),
            "title": insight.get("title", "Pipeline failure detected"),
            "diagnosis": insight.get("diagnosis", ""),
            "recommendation": insight.get("recommendation", ""),
            "estimated_time_save_minutes": insight.get("estimated_time_save_minutes"),
            "confidence": insight.get("confidence"),
        }).execute()

        print(f"✅ AI insight generated: {insight.get('title')}")

       # Send Slack alert
        await send_pipeline_alert(insight, run)

        # Send email alert
        from app.services.email import send_failure_email
        org = supabase.table("organizations").select("billing_email").eq("id", org_id).single().execute()
        alert_email = org.data.get("billing_email") if org.data else None
        if alert_email:
            await send_failure_email(insight, run, alert_email)


    except Exception as e:
        print(f"❌ AI diagnosis failed: {e}")


@router.post("/runs", response_model=APIResponse)
async def submit_pipeline_run(
    run: PipelineRunCreate,
    background_tasks: BackgroundTasks,
    auth: dict = Depends(verify_api_key),
    supabase: Client = Depends(get_supabase_admin),
):
    record = run.model_dump()
    record["org_id"] = auth["org_id"]
    record["started_at"] = run.started_at.isoformat()
    record["finished_at"] = run.finished_at.isoformat() if run.finished_at else None

    result = supabase.table("pipeline_runs").insert(record).execute()
    stored = result.data[0] if result.data else {}

    if run.status.value == "failure":
        background_tasks.add_task(run_ai_diagnosis, stored, auth["org_id"], supabase)

    return APIResponse(success=True, data=stored)

@router.get("/runs", response_model=APIResponse)
async def get_pipeline_runs(
    limit: int = 50,
    auth: dict = Depends(verify_api_key),
    supabase: Client = Depends(get_supabase_admin),
):
    """Get pipeline runs for the authenticated org."""
    result = supabase.table("pipeline_runs").select("*").eq(
        "org_id", auth["org_id"]
    ).order("created_at", desc=True).limit(limit).execute()

    return APIResponse(success=True, data={"runs": result.data or []})

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
    failures = len([r for r in runs if r["status"] == "failure"])
    durations = [r["duration_seconds"] for r in runs if r.get("duration_seconds", 0) > 0]
    return APIResponse(success=True, data={
        "repo_full_name": repo_full_name,
        "period_days": period_days,
        "total_runs": total,
        "success_rate": round(successes / total, 3),
        "avg_duration_seconds": round(statistics.mean(durations), 1) if durations else 0,
        "failure_rate": round(failures / total, 3),
        "total_failures": failures,
        "total_successes": successes,
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
