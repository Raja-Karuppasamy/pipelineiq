from fastapi import APIRouter, Depends
from supabase import Client
from app.core.auth import verify_api_key, get_supabase_admin
from app.models.schemas import EnvironmentSnapshot, APIResponse
from datetime import datetime

router = APIRouter()

@router.post("/snapshot", response_model=APIResponse)
async def submit_snapshot(
    snapshot: EnvironmentSnapshot,
    auth: dict = Depends(verify_api_key),
    supabase: Client = Depends(get_supabase_admin),
):
    record = {
        "org_id": auth["org_id"],
        "environment_name": snapshot.environment_name,
        "project_name": snapshot.project_name,
        "config_keys": snapshot.config_keys,
        "config_hashes": snapshot.config_hashes,
        "service_versions": snapshot.service_versions,
        "captured_at": snapshot.captured_at.isoformat(),
    }
    result = supabase.table("environment_snapshots").upsert(
        record, on_conflict="org_id,environment_name,project_name"
    ).execute()
    return APIResponse(success=True, data=result.data[0] if result.data else record)

@router.get("/drift/{project_name}", response_model=APIResponse)
async def check_drift(
    project_name: str,
    auth: dict = Depends(verify_api_key),
    supabase: Client = Depends(get_supabase_admin),
):
    result = supabase.table("environment_snapshots").select("*").eq(
        "org_id", auth["org_id"]
    ).eq("project_name", project_name).execute()
    snapshots = result.data or []
    if len(snapshots) < 2:
        return APIResponse(success=True, data=[], meta={"message": "Need at least 2 environments to compare."})
    reports = []
    for i in range(len(snapshots)):
        for j in range(i + 1, len(snapshots)):
            a, b = snapshots[i], snapshots[j]
            keys_a = set(a.get("config_keys", []))
            keys_b = set(b.get("config_keys", []))
            missing_in_b = list(keys_a - keys_b)
            missing_in_a = list(keys_b - keys_a)
            common = keys_a & keys_b
            mismatches = [k for k in common if a["config_hashes"].get(k) != b["config_hashes"].get(k)]
            total = len(keys_a | keys_b)
            drift_score = round((len(missing_in_b) + len(missing_in_a) + len(mismatches)) / total, 3) if total else 0
            reports.append({
                "env_a": a["environment_name"], "env_b": b["environment_name"],
                "status": "drifted" if drift_score > 0 else "in_sync",
                "missing_in_b": missing_in_b, "missing_in_a": missing_in_a,
                "value_mismatches": mismatches, "drift_score": drift_score,
                "compared_at": datetime.utcnow().isoformat(),
            })
    return APIResponse(success=True, data=reports)
