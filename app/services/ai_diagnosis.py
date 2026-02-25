import anthropic
import json
from typing import Optional, Dict, Any
from app.core.config import settings

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

DIAGNOSIS_PROMPT = """You are PipelineIQ's DevOps AI. Analyze this CI/CD pipeline failure and return a specific, actionable diagnosis.

Rules:
1. Be SPECIFIC — reference actual error text, not generic advice
2. Give exact fix steps a developer can action immediately
3. Estimate minutes saved if fixed
4. Output ONLY valid JSON, no markdown, no preamble

Output format:
{
  "severity": "critical|warning|info",
  "title": "Short title under 60 chars",
  "diagnosis": "What failed and exactly why (2-3 sentences)",
  "recommendation": "Step by step fix — be specific",
  "estimated_time_save_minutes": 30,
  "confidence": 0.95
}"""


async def diagnose_failure(
    error_logs: str,
    workflow_name: str,
    repo: str,
    branch: str,
    commit_message: Optional[str] = None,
) -> Dict[str, Any]:
    """Send failure data to Claude and get a structured diagnosis back."""

    # Truncate logs to last 3000 chars — most relevant part
    logs = error_logs[-3000:] if len(error_logs) > 3000 else error_logs

    user_message = f"""
Repository: {repo}
Branch: {branch}
Workflow: {workflow_name}
Commit: {commit_message or 'N/A'}

Error logs:
```
{logs}
```

Diagnose this failure and provide a specific fix.
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=DIAGNOSIS_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = message.content[0].text

    # Strip any accidental markdown fences
    clean = response_text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


async def diagnose_from_run(run: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Called automatically when a failed pipeline run is stored.
    Returns None if no error logs available.
    """
    if run.get("status") != "failure":
        return None

    error_logs = run.get("error_logs", "")
    if not error_logs:
        # No logs — still generate a basic diagnosis from context
        error_logs = f"Pipeline '{run.get('workflow_name')}' failed with no captured logs."

    return await diagnose_failure(
        error_logs=error_logs,
        workflow_name=run.get("workflow_name", "Unknown"),
        repo=run.get("repo_full_name", "Unknown"),
        branch=run.get("branch", "Unknown"),
        commit_message=run.get("commit_message"),
    )
