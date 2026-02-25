from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class PipelineStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"

class InsightSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    POSITIVE = "positive"

class EnvironmentStatus(str, Enum):
    IN_SYNC = "in_sync"
    DRIFTED = "drifted"
    UNKNOWN = "unknown"

class PipelineRunCreate(BaseModel):
    repo_full_name: str
    branch: str
    commit_sha: str
    commit_message: Optional[str] = None
    workflow_name: str
    status: PipelineStatus
    duration_seconds: int = Field(..., ge=0)
    started_at: datetime
    finished_at: Optional[datetime] = None
    triggered_by: Optional[str] = None
    runner_os: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    error_logs: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class EnvironmentSnapshot(BaseModel):
    environment_name: str
    project_name: str
    config_keys: List[str]
    config_hashes: Dict[str, str]
    service_versions: Optional[Dict[str, str]] = None
    captured_at: datetime = Field(default_factory=datetime.utcnow)

class InsightSeverityEnum(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    POSITIVE = "positive"

class APIResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
