"""
Audit Models: Single Source of Truth for Corpus Audit Operations

This module contains all audit-related models used for corpus operations across 
the Netra platform, ensuring consistency and preventing duplication.

CRITICAL ARCHITECTURAL COMPLIANCE:
- All audit model definitions MUST be imported from this module
- NO duplicate audit model definitions allowed anywhere else in codebase
- This file maintains strong typing and single sources of truth
- Maximum file size: 300 lines (currently under limit)

Usage:
    from netra_backend.app.schemas.audit_models import CorpusAuditRecord, CorpusAuditMetadata
"""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

# ISSUE #841 SSOT FIX: Import UnifiedIdGenerator for audit record ID generation
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Import enums from the dedicated module
from netra_backend.app.schemas.core_enums import CorpusAuditAction, CorpusAuditStatus


class CorpusAuditMetadata(BaseModel):
    """Unified corpus audit metadata."""
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None
    compliance_flags: List[str] = Field(default_factory=list)


class CorpusAuditRecord(BaseModel):
    """Unified corpus audit record - single source of truth."""
    # ISSUE #841 SSOT FIX: Use UnifiedIdGenerator for audit record ID generation
    id: str = Field(default_factory=lambda: UnifiedIdGenerator.generate_base_id("audit", True, 8))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    user_id: Optional[str] = None
    action: CorpusAuditAction
    status: CorpusAuditStatus
    corpus_id: Optional[str] = None
    resource_type: str
    resource_id: Optional[str] = None
    operation_duration_ms: Optional[float] = None
    result_data: Optional[Dict[str, Any]] = None
    metadata: CorpusAuditMetadata = Field(default_factory=CorpusAuditMetadata)
    
    model_config = ConfigDict(from_attributes=True)


class CorpusAuditSearchFilter(BaseModel):
    """Unified corpus audit search filter."""
    user_id: Optional[str] = None
    action: Optional[CorpusAuditAction] = None
    status: Optional[CorpusAuditStatus] = None
    corpus_id: Optional[str] = None
    resource_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class CorpusAuditReport(BaseModel):
    """Unified corpus audit report."""
    total_records: int
    records: List[CorpusAuditRecord]
    summary: Dict[str, int] = Field(default_factory=dict)
    time_range: Dict[str, Optional[datetime]] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# Export all audit models
__all__ = [
    "CorpusAuditMetadata",
    "CorpusAuditRecord",
    "CorpusAuditSearchFilter",
    "CorpusAuditReport"
]