import resend
from app.core.config import settings

resend.api_key = settings.RESEND_API_KEY

async def send_failure_email(insight: dict, run: dict, to_email: str):
    """Send AI diagnosis email when a pipeline fails."""
    if not settings.RESEND_API_KEY or not to_email:
        return

    severity_emoji = {
        "critical": "🔴",
        "high": "🟠", 
        "medium": "🟡",
        "low": "🟢",
    }.get(insight.get("severity", "medium"), "🔴")

    html = f"""
    <div style="font-family: monospace; max-width: 600px; margin: 0 auto; background: #020812; color: #fff; padding: 32px; border-radius: 12px;">
      <div style="margin-bottom: 24px;">
        <span style="font-size: 20px; font-weight: 900;">PipelineIQ</span>
        <span style="color: #475569; margin-left: 12px; font-size: 13px;">AI-powered DevOps Intelligence</span>
      </div>
      
      <div style="background: #0f172a; border-radius: 8px; padding: 20px; margin-bottom: 20px; border-left: 4px solid #ff6b6b;">
        <div style="font-size: 16px; font-weight: 700; margin-bottom: 12px;">
          {severity_emoji} Pipeline Failure: {insight.get('title', 'Unknown Error')}
        </div>
        <table style="width: 100%; font-size: 13px; color: #64748b;">
          <tr><td>Repo:</td><td style="color: #fff;">{run.get('repo_full_name', '')}</td></tr>
          <tr><td>Branch:</td><td style="color: #fff;">{run.get('branch', '')}</td></tr>
          <tr><td>Workflow:</td><td style="color: #fff;">{run.get('workflow_name', '')}</td></tr>
          <tr><td>Commit:</td><td style="color: #fff;">{run.get('commit_message', '')}</td></tr>
        </table>
      </div>

      <div style="background: #0f172a; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <div style="font-size: 12px; color: #475569; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px;">🧠 AI Diagnosis</div>
        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0;">{insight.get('diagnosis', '')}</p>
      </div>

      <div style="background: #0f172a; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <div style="font-size: 12px; color: #475569; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px;">✅ Recommended Fix</div>
        <p style="color: #64d8a3; font-size: 14px; line-height: 1.6; margin: 0;">{insight.get('recommendation', '')}</p>
      </div>

      <div style="display: flex; gap: 16px; font-size: 12px; color: #334155; margin-bottom: 24px;">
        <span>Confidence: <span style="color: #a78bfa;">{insight.get('confidence', 0)}%</span></span>
        <span style="margin-left: 16px;">Est. time saved: <span style="color: #64d8a3;">{insight.get('estimated_time_save_minutes', 0)} min</span></span>
      </div>

      <a href="https://pipelineiq.dev/dashboard" style="display: inline-block; padding: 12px 24px; background: #64d8a3; color: #020812; border-radius: 8px; font-weight: 700; text-decoration: none; font-size: 14px;">
        View Dashboard →
      </a>

      <div style="margin-top: 32px; padding-top: 20px; border-top: 1px solid #0f172a; font-size: 11px; color: #334155;">
        PipelineIQ · <a href="https://pipelineiq.dev" style="color: #475569;">pipelineiq.dev</a>
      </div>
    </div>
    """

    try:
        resend.Emails.send({
            "from": "PipelineIQ <alerts@pipelineiq.dev>",
            "to": to_email,
            "subject": f"{severity_emoji} Pipeline Failure: {insight.get('title', 'Unknown Error')} — {run.get('repo_full_name', '')}",
            "html": html,
        })
        print(f"✅ Email alert sent to {to_email}")
    except Exception as e:
        print(f"⚠️ Email alert failed: {e}")
