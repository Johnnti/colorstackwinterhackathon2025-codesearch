from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from enum import Enum
from datetime import datetime


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Request schemas
class AnalyzeOptions(BaseModel):
    """Options for the analysis."""
    use_repo_rules: bool = False
    rules_yaml: Optional[str] = None  # Custom rules YAML
    language_hint: Optional[str] = None  # e.g., "python", "javascript"


class AnalyzeRequest(BaseModel):
    """Request body for /api/analyze endpoint."""
    pr_url: Optional[str] = None
    diff_text: Optional[str] = None
    options: AnalyzeOptions = Field(default_factory=AnalyzeOptions)
    
    class Config:
        json_schema_extra = {
            "example": {
                "pr_url": "https://github.com/owner/repo/pull/123",
                "options": {
                    "use_repo_rules": False,
                    "language_hint": "python"
                }
            }
        }


# Response schemas - Structured Review Output
class PRSummary(BaseModel):
    """Summary of the PR changes."""
    what_changed: str
    why_it_changed: str
    key_files: list[str]


class Finding(BaseModel):
    """Individual finding from the code review."""
    title: str
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    file: str
    line_number: Optional[int] = None
    evidence: str
    recommendation: str


class RiskMatrix(BaseModel):
    """Risk assessment across different dimensions."""
    security: RiskLevel
    performance: RiskLevel
    breaking_change: RiskLevel
    maintainability: RiskLevel


class TestPlan(BaseModel):
    """Suggested tests for the PR."""
    unit_tests: list[str]
    integration_tests: list[str]
    edge_cases: list[str]


class MergeReadiness(BaseModel):
    """Overall merge readiness assessment."""
    score: int = Field(ge=0, le=100)
    blockers: list[str]
    notes: str


class StructuredReview(BaseModel):
    """The complete structured review output."""
    pr_summary: PRSummary
    findings: list[Finding]
    risk_matrix: RiskMatrix
    test_plan: TestPlan
    merge_readiness: MergeReadiness


# API Response schemas
class AnalyzeResponse(BaseModel):
    """Response from /api/analyze endpoint."""
    run_id: int
    status: str
    message: str = "Analysis started"
    result: Optional[StructuredReview] = None  # Included if sync mode


class RunStatusResponse(BaseModel):
    """Response from /api/runs/{run_id} endpoint."""
    run_id: int
    status: str
    repo: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class AnalysisResultResponse(BaseModel):
    """Response from /api/runs/{run_id}/result endpoint."""
    run_id: int
    status: str
    result: Optional[StructuredReview] = None
    model_version: Optional[str] = None
    markdown_comment: Optional[str] = None  # Pre-formatted for GitHub comment
