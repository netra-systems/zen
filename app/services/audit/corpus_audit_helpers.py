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
    base_fields = _build_base_audit_fields(action, resource_type, status)
    identity_fields = _build_identity_fields(user_id, corpus_id, resource_id)
    operational_fields = _build_operational_fields(operation_duration_ms, result_data)
    return {**base_fields, **identity_fields, **operational_fields}


def _build_base_audit_fields(action: CorpusAuditAction, resource_type: str, status: CorpusAuditStatus) -> Dict[str, Any]:
    """Build base audit fields for action, resource type, and status."""
    return {
        "action": action.value,
        "resource_type": resource_type,
        "status": status.value
    }


def _build_identity_fields(user_id: Optional[str], corpus_id: Optional[str], resource_id: Optional[str]) -> Dict[str, Any]:
    """Build identity fields for user, corpus, and resource."""
    return {
        "user_id": user_id,
        "corpus_id": corpus_id,
        "resource_id": resource_id
    }


def _build_operational_fields(operation_duration_ms: Optional[float], result_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build operational fields for duration and result data."""
    return {
        "operation_duration_ms": operation_duration_ms,
        "result_data": result_data or {}
    }


def extract_metadata_core_fields(metadata: Optional[CorpusAuditMetadata]) -> Dict[str, Any]:
    """Extract core metadata fields for database storage."""
    if not metadata:
        return {}
    return _build_core_metadata_dict(metadata)


def _build_core_metadata_dict(metadata: CorpusAuditMetadata) -> Dict[str, Any]:
    """Build core metadata dictionary from metadata object."""
    return {
        "user_agent": metadata.user_agent, "ip_address": metadata.ip_address,
        "request_id": metadata.request_id, "session_id": metadata.session_id
    }


def extract_metadata_extended_fields(metadata: Optional[CorpusAuditMetadata]) -> Dict[str, Any]:
    """Extract extended metadata fields for database storage."""
    if not metadata:
        return {}
    return _build_extended_metadata_dict(metadata)


def _build_extended_metadata_dict(metadata: CorpusAuditMetadata) -> Dict[str, Any]:
    """Build extended metadata dictionary from metadata object."""
    return {
        "configuration": metadata.configuration, "performance_metrics": metadata.performance_metrics,
        "error_details": metadata.error_details, "compliance_flags": metadata.compliance_flags
    }


def create_audit_record_base(audit_log: CorpusAuditLog) -> Dict[str, Any]:
    """Create base fields for audit record."""
    basic_fields = _extract_audit_record_basic_fields(audit_log)
    enum_fields = _extract_audit_record_enum_fields(audit_log)
    return {**basic_fields, **enum_fields}


def _extract_audit_record_basic_fields(audit_log: CorpusAuditLog) -> Dict[str, Any]:
    """Extract basic audit record fields."""
    return {
        "id": audit_log.id, "timestamp": audit_log.timestamp, "user_id": audit_log.user_id
    }


def _extract_audit_record_enum_fields(audit_log: CorpusAuditLog) -> Dict[str, Any]:
    """Extract enum fields from audit log."""
    return {
        "action": CorpusAuditAction(audit_log.action), "status": CorpusAuditStatus(audit_log.status)
    }


def create_audit_record_extended(audit_log: CorpusAuditLog, metadata: CorpusAuditMetadata) -> Dict[str, Any]:
    """Create extended fields for audit record."""
    resource_fields = _extract_audit_record_resource_fields(audit_log)
    operational_fields = _extract_audit_record_operational_fields(audit_log, metadata)
    return {**resource_fields, **operational_fields}


def _extract_audit_record_resource_fields(audit_log: CorpusAuditLog) -> Dict[str, Any]:
    """Extract resource-related audit record fields."""
    return {
        "corpus_id": audit_log.corpus_id, "resource_type": audit_log.resource_type, "resource_id": audit_log.resource_id
    }


def _extract_audit_record_operational_fields(audit_log: CorpusAuditLog, metadata: CorpusAuditMetadata) -> Dict[str, Any]:
    """Extract operational audit record fields."""
    return {
        "operation_duration_ms": audit_log.operation_duration_ms, "result_data": audit_log.result_data or {}, "metadata": metadata
    }


def build_metadata_from_log(audit_log: CorpusAuditLog) -> CorpusAuditMetadata:
    """Build CorpusAuditMetadata from database log."""
    basic_fields = _extract_basic_metadata_fields(audit_log)
    extended_fields = _extract_extended_metadata_fields(audit_log)
    return CorpusAuditMetadata(**basic_fields, **extended_fields)


def _extract_basic_metadata_fields(audit_log: CorpusAuditLog) -> Dict[str, Any]:
    """Extract basic metadata fields from audit log."""
    return {
        "user_agent": audit_log.user_agent,
        "ip_address": audit_log.ip_address,
        "request_id": audit_log.request_id,
        "session_id": audit_log.session_id
    }


def _extract_extended_metadata_fields(audit_log: CorpusAuditLog) -> Dict[str, Any]:
    """Extract extended metadata fields from audit log."""
    return {
        "configuration": audit_log.configuration or {},
        "performance_metrics": audit_log.performance_metrics or {},
        "error_details": audit_log.error_details,
        "compliance_flags": audit_log.compliance_flags or []
    }


def create_time_range_from_filters(filters: CorpusAuditSearchFilter) -> Dict[str, Any]:
    """Create time range dictionary from search filters."""
    return {
        "start_date": filters.start_date,
        "end_date": filters.end_date
    }