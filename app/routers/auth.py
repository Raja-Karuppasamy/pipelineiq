from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from app.core.auth import get_supabase_admin
from app.models.schemas import APIResponse
import secrets
import string
import resend
from app.core.config import settings

router = APIRouter()

def generate_api_key() -> str:
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(32))
    return f"piq_live_{random_part}"

async def send_welcome_email(email: str, name: str, api_key: str):
    resend.api_key = settings.RESEND_API_KEY
    html = f"""
    <div style="font-family: monospace; max-width: 600px; margin: 0 auto; background: #020812; color: #fff; padding: 32px; border-radius: 12px;">
      <div style="margin-bottom: 24px;">
        <span style="font-size: 20px; font-weight: 900;">PipelineIQ</span>
        <span style="color: #475569; margin-left: 12px; font-size: 13px;">AI-powered DevOps Intelligence</span>
      </div>

      <h2 style="color: #64d8a3; margin-bottom: 8px;">Welcome, {name}! 🚀</h2>
      <p style="color: #94a3b8; margin-bottom: 24px;">Your API key is ready. Add PipelineIQ to any GitHub Actions workflow in 30 seconds.</p>

      <div style="background: #0f172a; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
        <div style="font-size: 11px; color: #475569; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px;">Your API Key</div>
        <div style="font-size: 16px; color: #64d8a3; font-weight: 700; letter-spacing: 0.05em;">{api_key}</div>
      </div>

      <div style="background: #0f172a; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
        <div style="font-size: 11px; color: #475569; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px;">Quick Start — Add to your workflow</div>
        <pre style="color: #94a3b8; font-size: 13px; line-height: 1.8; margin: 0;">- name: PipelineIQ
  if: always()
  uses: Raja-Karuppasamy/pipelineiq-action@v1
  with:
    api-key: ${{{{ secrets.PIPELINEIQ_API_KEY }}}}
    job-status: ${{{{ job.status }}}}</pre>
      </div>

      <div style="background: #0f172a; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
        <div style="font-size: 13px; color: #94a3b8; margin-bottom: 8px;">1. Add <strong style="color:#64d8a3;">PIPELINEIQ_API_KEY</strong> to your GitHub repo secrets</div>
        <div style="font-size: 13px; color: #94a3b8; margin-bottom: 8px;">2. Add the step above to your workflow</div>
        <div style="font-size: 13px; color: #94a3b8;">3. Push a commit — AI diagnosis appears in Slack on failures</div>
      </div>

      <div style="margin-bottom: 24px; padding: 16px; background: #0f172a; border-radius: 8px; border-left: 3px solid #64d8a3;">
        <div style="font-size: 12px; color: #475569; margin-bottom: 4px;">Free tier includes</div>
        <div style="font-size: 14px; color: #fff;">100 pipeline runs/month · AI diagnosis · Slack alerts · DORA metrics</div>
      </div>

      <a href="https://pipelineiq.dev/dashboard" style="display: inline-block; padding: 12px 24px; background: #64d8a3; color: #020812; border-radius: 8px; font-weight: 700; text-decoration: none; font-size: 14px;">
        View Dashboard →
      </a>

      <div style="margin-top: 32px; padding-top: 20px; border-top: 1px solid #0f172a; font-size: 11px; color: #334155;">
        PipelineIQ · <a href="https://pipelineiq.dev" style="color: #475569;">pipelineiq.dev</a>
        · Free tier: 100 runs/month
      </div>
    </div>
    """
    try:
        resend.Emails.send({
            "from": "PipelineIQ <onboarding@resend.dev>",
            "to": email,
            "subject": "Your PipelineIQ API key is ready 🚀",
            "html": html,
        })
    except Exception as e:
        print(f"⚠️ Welcome email failed: {e}")

@router.post("/signup", response_model=APIResponse)
async def signup(
    request_data: dict,
    supabase: Client = Depends(get_supabase_admin),
):
    name = request_data.get("name", "").strip()
    email = request_data.get("email", "").strip().lower()
    company = request_data.get("company", "").strip()

    if not name or not email:
        raise HTTPException(status_code=400, detail="Name and email required")

    # Check if email already exists
    existing = supabase.table("organizations").select("id").eq("billing_email", email).execute()
    if existing.data:
        org_id = existing.data[0]["id"]
        existing_key = supabase.table("api_keys").select("key_hash").eq("org_id", org_id).execute()
        api_key = "your existing key — check your original welcome email"
        await send_welcome_email(email, name, api_key)
        return APIResponse(success=True, data={
            "message": "Account already exists. Check your email for your API key.",
            "already_exists": True,
        })

    # Create org
    org_name = company or f"{name}'s Workspace"
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', org_name.lower()).strip('-')
    slug = f"{slug}-{secrets.token_hex(4)}"

    result = supabase.table("organizations").insert({
        "name": org_name,
        "slug": slug,
        "plan": "free",
        "billing_email": email,
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create account")

    org_id = result.data[0]["id"]

    # Create API key
    # Create API key
    api_key = generate_api_key()
    import hashlib
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    supabase.table("api_keys").insert({
        "org_id": org_id,
        "key_hash": key_hash,
        "key_prefix": api_key[:12],
        "name": "Default",
        "is_active": True,
    }).execute()

    # Send welcome email with API key
    await send_welcome_email(email, name, api_key)

    return APIResponse(success=True, data={
        "message": "Account created! Check your email for your API key.",
        "api_key": api_key,
    })