"""Monitoring interfaces - compliance with 25-line function limit."""

from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime


class ComplianceMetrics(BaseModel):
    """Metrics for spec compliance monitoring."""
    score: float = 0.0
    violations: int = 0
    critical_issues: int = 0
    compliance_level: str = "unknown"
    timestamp: datetime = datetime.now()
    details: Optional[Dict[str, Any]] = None