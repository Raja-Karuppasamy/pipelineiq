from fastapi import APIRouter, Request, Header, Depends, BackgroundTasks
from typing import Optional
from supabase import Client
from app.core.auth import get_supabase_admin
import hmac, hashlib
from app.core.config import settings

router = APIRouter()

def verify_signature(body: bytes, sig: str) -> bool:
    if not sig or not sig.startswith("sha256="):
        return False
    mac = hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode(), msg=body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), sig[7:])

@router.post("/github")
async def receive_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
):
    body = await request.body()
    # Skip verification if no secret configured (dev mode)
    if settings.GITHUB_WEBHOOK_SECRET and not verify_signature(body, x_hub_signature_256 or ""):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    payload = await request.json()
    if x_github_event == "ping":
        return {"message": "pong"}
    print(f"Webhook received: {x_github_event} | delivery: {x_github_delivery}")
    return {"status": "accepted", "event": x_github_event}
