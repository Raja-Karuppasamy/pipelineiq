from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from app.routers import pipelines, insights, environments, webhooks, health
from app.core.config import settings

app = FastAPI(
    title="PipelineIQ API",
    description="AI-powered DevOps intelligence. Diagnose failures, predict bottlenecks, fix faster.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{round((time.time()-start)*1000, 2)}ms"
    return response

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(pipelines.router, prefix="/api/v1/pipelines", tags=["Pipelines"])
app.include_router(insights.router, prefix="/api/v1/insights", tags=["AI Insights"])
app.include_router(environments.router, prefix="/api/v1/environments", tags=["Environments"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])

from app.routers import billing, auth
app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
@app.get("/")
async def root():
    return {"product": "PipelineIQ", "version": "0.1.0", "docs": "/docs", "status": "operational"}