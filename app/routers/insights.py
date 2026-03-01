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
@router.get("/dora", response_model=APIResponse)
async def get_dora_metrics(
    days: int = Query(default=30, le=90),
    auth: dict = Depends(verify_api_key),
    supabase: Client = Depends(get_supabase_admin),
):
    """Compute DORA metrics for the authenticated org."""
    from datetime import datetime, timedelta, timezone

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    result = supabase.table("pipeline_runs").select("*").eq(
        "org_id", auth["org_id"]
    ).gte("created_at", since).order("created_at", desc=False).execute()

    runs = result.data or []
    total = len(runs)

    if total == 0:
        return APIResponse(success=True, data={
            "deployment_frequency": {"value": 0, "unit": "per day", "rating": "low"},
            "change_failure_rate": {"value": 0, "unit": "%", "rating": "elite"},
            "mean_time_to_recovery": {"value": 0, "unit": "minutes", "rating": "elite"},
            "lead_time": {"value": 0, "unit": "minutes", "rating": "low"},
            "period_days": days,
            "total_runs": 0,
        })

    # 1. Deployment Frequency
    deployments = [r for r in runs if r["status"] in ["success", "failure"]]
    deploy_freq = round(len(deployments) / days, 2)

    if deploy_freq >= 1:
        freq_rating = "elite"
    elif deploy_freq >= 1/7:
        freq_rating = "high"
    elif deploy_freq >= 1/30:
        freq_rating = "medium"
    else:
        freq_rating = "low"

    # 2. Change Failure Rate
    failures = [r for r in runs if r["status"] == "failure"]
    cfr = round((len(failures) / total) * 100, 1) if total > 0 else 0

    if cfr <= 5:
        cfr_rating = "elite"
    elif cfr <= 10:
        cfr_rating = "high"
    elif cfr <= 15:
        cfr_rating = "medium"
    else:
        cfr_rating = "low"

    # 3. Mean Time to Recovery
    recovery_times = []
    i = 0
    def parse_dt(s):
        from dateutil import parser as dateparser
        return dateparser.parse(s)
    while i < len(runs):
        if runs[i]["status"] == "failure":
            fail_time = parse_dt(runs[i]["created_at"])
            for j in range(i + 1, len(runs)):
                if runs[j]["status"] == "success" and runs[j]["repo_full_name"] == runs[i]["repo_full_name"]:
                    recovery_time = parse_dt(runs[j]["created_at"])
                    recovery_times.append((recovery_time - fail_time).total_seconds() / 60)
                    break
        i += 1

    mttr = round(sum(recovery_times) / len(recovery_times), 1) if recovery_times else 0

    if mttr <= 60:
        mttr_rating = "elite"
    elif mttr <= 24 * 60:
        mttr_rating = "high"
    elif mttr <= 7 * 24 * 60:
        mttr_rating = "medium"
    else:
        mttr_rating = "low"

    # 4. Lead Time (avg duration as proxy)
    durations = [r["duration_seconds"] for r in runs if r["duration_seconds"]]
    avg_duration = round(sum(durations) / len(durations) / 60, 1) if durations else 0

    if avg_duration <= 60:
        lt_rating = "elite"
    elif avg_duration <= 7 * 24 * 60:
        lt_rating = "high"
    elif avg_duration <= 30 * 24 * 60:
        lt_rating = "medium"
    else:
        lt_rating = "low"

    return APIResponse(success=True, data={
        "deployment_frequency": {"value": deploy_freq, "unit": "per day", "rating": freq_rating},
        "change_failure_rate": {"value": cfr, "unit": "%", "rating": cfr_rating},
        "mean_time_to_recovery": {"value": mttr, "unit": "minutes", "rating": mttr_rating},
        "lead_time": {"value": avg_duration, "unit": "minutes", "rating": lt_rating},
        "period_days": days,
        "total_runs": total,
    })