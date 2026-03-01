from fastapi import APIRouter, Depends, Request, HTTPException
from supabase import Client
from app.core.auth import verify_api_key, get_supabase_admin
from app.core.config import settings
from app.models.schemas import APIResponse
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter()


@router.post("/checkout", response_model=APIResponse)
async def create_checkout_session(
    auth: dict = Depends(verify_api_key),
    supabase: Client = Depends(get_supabase_admin),
):
    """Create a Stripe checkout session for the Starter plan."""
    try:
        # Get org details
        org = supabase.table("organizations").select("*").eq(
            "id", auth["org_id"]
        ).single().execute()

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": settings.STRIPE_PRICE_ID,
                "quantity": 1,
            }],
            mode="subscription",
            success_url="https://pipelineiq.dev?upgraded=true",
            cancel_url="https://pipelineiq.dev?cancelled=true",
            metadata={
                "org_id": auth["org_id"],
            },
            customer_email=org.data.get("billing_email") if org.data else None,
        )

        return APIResponse(success=True, data={"checkout_url": session.url})

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request, supabase: Client = Depends(get_supabase_admin)):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        if settings.STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        else:
            import json
            event = json.loads(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        org_id = session.get("metadata", {}).get("org_id")

        if org_id:
            supabase.table("organizations").update({
                "plan": "starter",
                "stripe_customer_id": session.get("customer"),
                "stripe_subscription_id": session.get("subscription"),
            }).eq("id", org_id).execute()

            print(f"✅ Org {org_id} upgraded to Starter plan")

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")

        supabase.table("organizations").update({
            "plan": "free",
            "stripe_subscription_id": None,
        }).eq("stripe_customer_id", customer_id).execute()

        print(f"⚠️ Subscription cancelled for customer {customer_id}")

    return {"received": True}


@router.get("/status", response_model=APIResponse)
async def get_billing_status(
    auth: dict = Depends(verify_api_key),
    supabase: Client = Depends(get_supabase_admin),
):
    """Get current plan and usage for the org."""
    org = supabase.table("organizations").select("*").eq(
        "id", auth["org_id"]
    ).single().execute()

    runs_this_month = supabase.table("pipeline_runs").select(
        "id", count="exact"
    ).eq("org_id", auth["org_id"]).gte(
        "created_at", "2026-02-01"
    ).execute()

    return APIResponse(success=True, data={
        "plan": org.data.get("plan", "free"),
        "runs_this_month": runs_this_month.count or 0,
        "limit": 50 if org.data.get("plan") == "free" else -1,
    })
@router.post("/email", response_model=APIResponse)
async def set_alert_email(
    request: Request,
    auth: dict = Depends(verify_api_key),
    supabase: Client = Depends(get_supabase_admin),
):
    """Set the email address for pipeline failure alerts."""
    body = await request.json()
    email = body.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    supabase.table("organizations").update({
        "billing_email": email
    }).eq("id", auth["org_id"]).execute()

    return APIResponse(success=True, data={"message": f"Alert email set to {email}"})