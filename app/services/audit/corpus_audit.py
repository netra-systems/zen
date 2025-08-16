"""
Corpus Audit Service

Main audit logger for corpus operations with comprehensive tracking.
Follows 300-line limit and 8-line function rule.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.registry import (
    CorpusAuditRecord, CorpusAuditAction, CorpusAuditStatus,
    CorpusAuditMetadata, CorpusAuditSearchFilter, CorpusAuditReport
)
from app.db.models_postgres import CorpusAuditLog
from app.services.audit.repository import CorpusAuditRepository
from app.logging_config import central_logger
from app.core.exceptions_base import NetraException

logger = central_logger.get_logger(__name__)


class CorpusAuditLogger:
    """Main audit logger service for corpus operations."""

    def __init__(self, repository: CorpusAuditRepository):
        self.repository = repository

    async def log_operation(
        self,
        db: AsyncSession,
        action: CorpusAuditAction,
        resource_type: str,
        status: CorpusAuditStatus = CorpusAuditStatus.SUCCESS,
        user_id: Optional[str] = None,
        corpus_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        operation_duration_ms: Optional[float] = None,
        result_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[CorpusAuditMetadata] = None
    ) -> CorpusAuditRecord:
        """Log a corpus operation with comprehensive audit trail."""
        try:
            params = self._build_log_params(action, resource_type, status, user_id, corpus_id, resource_id, operation_duration_ms, result_data, metadata)
            return await self._execute_audit_logging(db, params)
        except Exception as e:
            return self._handle_audit_logging_error(e)
    
    def _build_log_params(self, action: CorpusAuditAction, resource_type: str, status: CorpusAuditStatus, user_id: Optional[str], corpus_id: Optional[str], resource_id: Optional[str], operation_duration_ms: Optional[float], result_data: Optional[Dict[str, Any]], metadata: Optional[CorpusAuditMetadata]) -> Dict[str, Any]:
        """Build parameters dictionary for audit logging."""
        return {
            "action": action, "resource_type": resource_type, "status": status,
            "user_id": user_id, "corpus_id": corpus_id, "resource_id": resource_id,
            "operation_duration_ms": operation_duration_ms, "result_data": result_data, "metadata": metadata
        }

    async def _execute_audit_logging(self, db: AsyncSession, params: Dict[str, Any]) -> CorpusAuditRecord:
        """Execute the audit logging operation."""
        audit_data = self._prepare_audit_data_from_params(params)
        audit_log = await self.repository.create(db, **audit_data)
        return self._convert_to_record(audit_log)
    
    def _handle_audit_logging_error(self, error: Exception) -> None:
        """Handle audit logging errors with proper exception propagation."""
        logger.error(f"Failed to log audit operation: {error}")
        raise NetraException(f"Audit logging failed: {str(error)}")

    def _prepare_audit_data_from_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare audit data from parameters dictionary."""
        from .corpus_audit_helpers import prepare_audit_data_dict, extract_metadata_core_fields, extract_metadata_extended_fields
        base_data = prepare_audit_data_dict(**{k: v for k, v in params.items() if k != 'metadata'})
        core_metadata = extract_metadata_core_fields(params['metadata'])
        extended_metadata = extract_metadata_extended_fields(params['metadata'])
        return {**base_data, **core_metadata, **extended_metadata}

    def _extract_metadata_fields(self, metadata: Optional[CorpusAuditMetadata]) -> Dict[str, Any]:
        """Extract metadata fields for database storage."""
        from .corpus_audit_helpers import extract_metadata_core_fields, extract_metadata_extended_fields
        if not metadata:
            return {}
        core_fields = extract_metadata_core_fields(metadata)
        extended_fields = extract_metadata_extended_fields(metadata)
        return {**core_fields, **extended_fields}

    def _convert_to_record(self, audit_log: CorpusAuditLog) -> CorpusAuditRecord:
        """Convert database model to audit record."""
        metadata = self._create_audit_metadata_from_log(audit_log)
        return self._create_audit_record_from_log(audit_log, metadata)
    
    def _create_audit_metadata_from_log(self, audit_log: CorpusAuditLog) -> CorpusAuditMetadata:
        """Create audit metadata object from database log."""
        from .corpus_audit_helpers import build_metadata_from_log
        return build_metadata_from_log(audit_log)
    
    def _create_audit_record_from_log(self, audit_log: CorpusAuditLog, metadata: CorpusAuditMetadata) -> CorpusAuditRecord:
        """Create audit record object from database log and metadata."""
        from .corpus_audit_helpers import create_audit_record_base, create_audit_record_extended
        core_fields = create_audit_record_base(audit_log)
        operational_fields = create_audit_record_extended(audit_log, metadata)
        return CorpusAuditRecord(**core_fields, **operational_fields)

    async def track_user_action(
        self, db: AsyncSession, user_id: str, action: CorpusAuditAction,
        resource_type: str, resource_id: Optional[str] = None,
        metadata: Optional[CorpusAuditMetadata] = None
    ) -> CorpusAuditRecord:
        """Track user-specific actions with enhanced metadata."""
        try:
            return await self._execute_user_action_logging(db, user_id, action, resource_type, resource_id, metadata)
        except Exception as e:
            self._handle_user_action_error(e)

    async def _execute_user_action_logging(self, db: AsyncSession, user_id: str, action: CorpusAuditAction, resource_type: str, resource_id: Optional[str], metadata: Optional[CorpusAuditMetadata]) -> CorpusAuditRecord:
        """Execute user action logging operation."""
        return await self.log_operation(
            db, action, resource_type, CorpusAuditStatus.SUCCESS,
            user_id, None, resource_id, None, None, metadata
        )

    async def record_configuration(
        self, db: AsyncSession, config_data: Dict[str, Any],
        user_id: Optional[str] = None, operation_name: str = "config_change"
    ) -> CorpusAuditRecord:
        """Record configuration changes with full audit trail."""
        try:
            return await self._execute_configuration_logging(db, config_data, user_id, operation_name)
        except Exception as e:
            self._handle_configuration_error(e)

    async def _execute_configuration_logging(self, db: AsyncSession, config_data: Dict[str, Any], user_id: Optional[str], operation_name: str) -> CorpusAuditRecord:
        """Execute configuration change logging."""
        metadata = CorpusAuditMetadata(configuration=config_data)
        return await self.log_operation(
            db, CorpusAuditAction.UPDATE, "configuration",
            CorpusAuditStatus.SUCCESS, user_id, None, operation_name, None, config_data, metadata
        )

    async def search_audit_logs(
        self,
        db: AsyncSession,
        filters: CorpusAuditSearchFilter
    ) -> CorpusAuditReport:
        """Search audit logs and generate comprehensive report."""
        try:
            return await self._execute_audit_search(db, filters)
        except Exception as e:
            return self._handle_search_error(e)
    
    async def _execute_audit_search(self, db: AsyncSession, filters: CorpusAuditSearchFilter) -> CorpusAuditReport:
        """Execute the audit search operation."""
        records = await self.repository.search_records(db, filters)
        total_count = await self.repository.count_records(db, filters)
        summary_stats = await self.repository.get_summary_stats(db, filters)
        return self._build_audit_report(records, total_count, summary_stats, filters)
    
    def _handle_search_error(self, error: Exception) -> None:
        """Handle audit search errors."""
        logger.error(f"Failed to search audit logs: {error}")
        raise NetraException(f"Audit search failed: {str(error)}")

    def _build_audit_report(
        self, records: List[CorpusAuditLog], total_count: int,
        summary_stats: Dict[str, int], filters: CorpusAuditSearchFilter
    ) -> CorpusAuditReport:
        """Build comprehensive audit report."""
        audit_records = [self._convert_to_record(record) for record in records]
        time_range = self._create_time_range_dict(filters)
        return self._create_audit_report_object(total_count, audit_records, summary_stats, time_range)
    
    def _create_time_range_dict(self, filters: CorpusAuditSearchFilter) -> Dict[str, Any]:
        """Create time range dictionary from filters."""
        from .corpus_audit_helpers import create_time_range_from_filters
        return create_time_range_from_filters(filters)
    
    def _create_audit_report_object(
        self, total_count: int, audit_records: List[CorpusAuditRecord],
        summary_stats: Dict[str, int], time_range: Dict[str, Any]
    ) -> CorpusAuditReport:
        """Create CorpusAuditReport object."""
        report_data = self._build_report_data(total_count, audit_records, summary_stats, time_range)
        return CorpusAuditReport(**report_data)

    def _build_report_data(self, total_count: int, audit_records: List[CorpusAuditRecord], summary_stats: Dict[str, int], time_range: Dict[str, Any]) -> Dict[str, Any]:
        """Build report data dictionary."""
        return {
            "total_records": total_count, "records": audit_records,
            "summary": summary_stats, "time_range": time_range
        }

    async def generate_audit_report(
        self, db: AsyncSession, filters: CorpusAuditSearchFilter
    ) -> CorpusAuditReport:
        """Generate comprehensive audit report with analytics."""
        try:
            return await self.search_audit_logs(db, filters)
        except Exception as e:
            return self._handle_report_generation_error(e)

    def _handle_report_generation_error(self, error: Exception) -> None:
        """Handle audit report generation errors."""
        logger.error(f"Failed to generate audit report: {error}")
        raise NetraException(f"Audit report generation failed: {str(error)}")
    
    def _handle_user_action_error(self, error: Exception) -> None:
        """Handle user action tracking errors."""
        logger.error(f"Failed to track user action: {error}")
        raise NetraException(f"User action tracking failed: {str(error)}")
    
    def _handle_configuration_error(self, error: Exception) -> None:
        """Handle configuration recording errors."""
        logger.error(f"Failed to record configuration: {error}")
        raise NetraException(f"Configuration recording failed: {str(error)}")


async def create_audit_logger(db: AsyncSession) -> CorpusAuditLogger:
    """Factory function to create configured audit logger."""
    repository = CorpusAuditRepository()
    return CorpusAuditLogger(repository)