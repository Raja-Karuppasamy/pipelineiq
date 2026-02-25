import httpx
from app.core.config import settings

SEVERITY_EMOJI = {
    "critical": "🔴",
    "warning": "🟡", 
    "info": "🔵",
    "positive": "🟢",
}

async def send_pipeline_alert(insight: dict, run: dict):
    """Send AI diagnosis to Slack when a pipeline fails."""
    if not settings.SLACK_BOT_TOKEN:
        return

    emoji = SEVERITY_EMOJI.get(insight.get("severity", "info"), "🔵")
    repo = run.get("repo_full_name", "unknown")
    branch = run.get("branch", "unknown")
    commit = run.get("commit_message", "")[:60]
    workflow = run.get("workflow_name", "unknown")

    message = {
        "channel": settings.SLACK_CHANNEL,
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Pipeline Failure: {insight.get('title', 'Unknown')}",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Repo:*\n`{repo}`"},
                    {"type": "mrkdwn", "text": f"*Branch:*\n`{branch}`"},
                    {"type": "mrkdwn", "text": f"*Workflow:*\n`{workflow}`"},
                    {"type": "mrkdwn", "text": f"*Commit:*\n{commit}"},
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🧠 AI Diagnosis:*\n{insight.get('diagnosis', '')}",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*✅ Recommended Fix:*\n{insight.get('recommendation', '')}",
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"⏱ Estimated fix time: {insight.get('estimated_time_save_minutes', '?')} min saved | Confidence: {int((insight.get('confidence', 0)) * 100)}% | Powered by PipelineIQ"
                    }
                ]
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            json=message,
            timeout=10.0,
        )
        result = response.json()
        if not result.get("ok"):
            print(f"❌ Slack error: {result.get('error')}")
        else:
            print(f"✅ Slack alert sent to #{settings.SLACK_CHANNEL}")
