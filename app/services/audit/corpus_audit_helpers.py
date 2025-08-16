"""Corpus audit service helper utilities for decomposed operations."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from app.schemas.registry import (
    CorpusAuditRecord, CorpusAuditAction, CorpusAuditStatus,
    CorpusAuditMetadata, CorpusAuditSearchFilter
)
from app.db.models_postgres import CorpusAuditLog


def prepare_audit_data_dict(action: CorpusAuditAction, resource_type: str, 
                           status: CorpusAuditStatus, user_id: Optional[str],
                           corpus_id: Optional[str], resource_id: Optional[str],
                           operation_duration_ms: Optional[float], result_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Prepare base audit data dictionary."""
    return {
        "action": action.value,
        "resource_type": resource_type,
        "status": status.value,
        "user_id": user_id,
        "corpus_id": corpus_id,
        "resource_id": resource_id,
        "operation_duration_ms": operation_duration_ms,
        "result_data": result_data or {}
    }


def extract_metadata_core_fields(metadata: Optional[CorpusAuditMetadata]) -> Dict[str, Any]:
    """Extract core metadata fields for database storage."""
    if not metadata:
        return {}
    
    return {
        "user_agent": metadata.user_agent,
        "ip_address": metadata.ip_address,
        "request_id": metadata.request_id,
        "session_id": metadata.session_id
    }


def extract_metadata_extended_fields(metadata: Optional[CorpusAuditMetadata]) -> Dict[str, Any]:
    """Extract extended metadata fields for database storage."""
    if not metadata:
        return {}
    
    return {
        "configuration": metadata.configuration,
        "performance_metrics": metadata.performance_metrics,
        "error_details": metadata.error_details,
        "compliance_flags": metadata.compliance_flags
    }


def create_audit_record_base(audit_log: CorpusAuditLog) -> Dict[str, Any]:
    """Create base fields for audit record."""
    return {
        "id": audit_log.id,
        "timestamp": audit_log.timestamp,
        "user_id": audit_log.user_id,
        "action": CorpusAuditAction(audit_log.action),
        "status": CorpusAuditStatus(audit_log.status)
    }


def create_audit_record_extended(audit_log: CorpusAuditLog, metadata: CorpusAuditMetadata) -> Dict[str, Any]:
    """Create extended fields for audit record."""
    return {
        "corpus_id": audit_log.corpus_id,
        "resource_type": audit_log.resource_type,
        "resource_id": audit_log.resource_id,
        "operation_duration_ms": audit_log.operation_duration_ms,
        "result_data": audit_log.result_data or {},
        "metadata": metadata
    }


def build_metadata_from_log(audit_log: CorpusAuditLog) -> CorpusAuditMetadata:
    """Build CorpusAuditMetadata from database log."""
    basic_fields = {
        "user_agent": audit_log.user_agent,
        "ip_address": audit_log.ip_address,
        "request_id": audit_log.request_id,
        "session_id": audit_log.session_id
    }
    
    extended_fields = {
        "configuration": audit_log.configuration or {},
        "performance_metrics": audit_log.performance_metrics or {},
        "error_details": audit_log.error_details,
        "compliance_flags": audit_log.compliance_flags or []
    }
    
    return CorpusAuditMetadata(**basic_fields, **extended_fields)


def create_time_range_from_filters(filters: CorpusAuditSearchFilter) -> Dict[str, Any]:
    """Create time range dictionary from search filters."""
    return {
        "start_date": filters.start_date,
        "end_date": filters.end_date
    }