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
            return await self._execute_audit_logging(
                db, action, resource_type, status, user_id, corpus_id,
                resource_id, operation_duration_ms, result_data, metadata
            )
        except Exception as e:
            return self._handle_audit_logging_error(e)
    
    async def _execute_audit_logging(
        self, db: AsyncSession, action: CorpusAuditAction, resource_type: str,
        status: CorpusAuditStatus, user_id: Optional[str], corpus_id: Optional[str],
        resource_id: Optional[str], operation_duration_ms: Optional[float],
        result_data: Optional[Dict[str, Any]], metadata: Optional[CorpusAuditMetadata]
    ) -> CorpusAuditRecord:
        """Execute the audit logging operation."""
        audit_data = self._prepare_audit_data(
            action, resource_type, status, user_id, corpus_id,
            resource_id, operation_duration_ms, result_data, metadata
        )
        audit_log = await self.repository.create(db, **audit_data)
        return self._convert_to_record(audit_log)
    
    def _handle_audit_logging_error(self, error: Exception) -> None:
        """Handle audit logging errors with proper exception propagation."""
        logger.error(f"Failed to log audit operation: {error}")
        raise NetraException(f"Audit logging failed: {str(error)}")

    def _prepare_audit_data(
        self, action: CorpusAuditAction, resource_type: str, status: CorpusAuditStatus,
        user_id: Optional[str], corpus_id: Optional[str], resource_id: Optional[str],
        operation_duration_ms: Optional[float], result_data: Optional[Dict[str, Any]],
        metadata: Optional[CorpusAuditMetadata]
    ) -> Dict[str, Any]:
        """Prepare audit data for database insertion."""
        return {
            "action": action.value,
            "resource_type": resource_type,
            "status": status.value,
            "user_id": user_id,
            "corpus_id": corpus_id,
            "resource_id": resource_id,
            "operation_duration_ms": operation_duration_ms,
            "result_data": result_data or {},
            **self._extract_metadata_fields(metadata)
        }

    def _extract_metadata_fields(self, metadata: Optional[CorpusAuditMetadata]) -> Dict[str, Any]:
        """Extract metadata fields for database storage."""
        if not metadata:
            return {}
        
        return {
            "user_agent": metadata.user_agent,
            "ip_address": metadata.ip_address,
            "request_id": metadata.request_id,
            "session_id": metadata.session_id,
            "configuration": metadata.configuration,
            "performance_metrics": metadata.performance_metrics,
            "error_details": metadata.error_details,
            "compliance_flags": metadata.compliance_flags
        }

    def _convert_to_record(self, audit_log: CorpusAuditLog) -> CorpusAuditRecord:
        """Convert database model to audit record."""
        metadata = self._create_audit_metadata_from_log(audit_log)
        return self._create_audit_record_from_log(audit_log, metadata)
    
    def _create_audit_metadata_from_log(self, audit_log: CorpusAuditLog) -> CorpusAuditMetadata:
        """Create audit metadata object from database log."""
        return CorpusAuditMetadata(
            user_agent=audit_log.user_agent,
            ip_address=audit_log.ip_address,
            request_id=audit_log.request_id,
            session_id=audit_log.session_id,
            configuration=audit_log.configuration or {},
            performance_metrics=audit_log.performance_metrics or {},
            error_details=audit_log.error_details,
            compliance_flags=audit_log.compliance_flags or []
        )
    
    def _create_audit_record_from_log(self, audit_log: CorpusAuditLog, metadata: CorpusAuditMetadata) -> CorpusAuditRecord:
        """Create audit record object from database log and metadata."""
        return CorpusAuditRecord(
            id=audit_log.id,
            timestamp=audit_log.timestamp,
            user_id=audit_log.user_id,
            action=CorpusAuditAction(audit_log.action),
            status=CorpusAuditStatus(audit_log.status),
            corpus_id=audit_log.corpus_id,
            resource_type=audit_log.resource_type,
            resource_id=audit_log.resource_id,
            operation_duration_ms=audit_log.operation_duration_ms,
            result_data=audit_log.result_data or {},
            metadata=metadata
        )

    async def track_user_action(
        self, db: AsyncSession, user_id: str, action: CorpusAuditAction,
        resource_type: str, resource_id: Optional[str] = None,
        metadata: Optional[CorpusAuditMetadata] = None
    ) -> CorpusAuditRecord:
        """Track user-specific actions with enhanced metadata."""
        try:
            return await self.log_operation(
                db, action, resource_type, CorpusAuditStatus.SUCCESS,
                user_id, None, resource_id, None, None, metadata
            )
        except Exception as e:
            logger.error(f"Failed to track user action: {e}")
            raise NetraException(f"User action tracking failed: {str(e)}")

    async def record_configuration(
        self, db: AsyncSession, config_data: Dict[str, Any],
        user_id: Optional[str] = None, operation_name: str = "config_change"
    ) -> CorpusAuditRecord:
        """Record configuration changes with full audit trail."""
        try:
            metadata = CorpusAuditMetadata(configuration=config_data)
            return await self.log_operation(
                db, CorpusAuditAction.UPDATE, "configuration",
                CorpusAuditStatus.SUCCESS, user_id, None, operation_name, None, config_data, metadata
            )
        except Exception as e:
            logger.error(f"Failed to record configuration: {e}")
            raise NetraException(f"Configuration recording failed: {str(e)}")

    async def search_audit_logs(
        self,
        db: AsyncSession,
        filters: CorpusAuditSearchFilter
    ) -> CorpusAuditReport:
        """Search audit logs and generate comprehensive report."""
        try:
            records = await self.repository.search_records(db, filters)
            total_count = await self.repository.count_records(db, filters)
            summary_stats = await self.repository.get_summary_stats(db, filters)
            
            return self._build_audit_report(records, total_count, summary_stats, filters)
        except Exception as e:
            logger.error(f"Failed to search audit logs: {e}")
            raise NetraException(f"Audit search failed: {str(e)}")

    def _build_audit_report(
        self, records: List[CorpusAuditLog], total_count: int,
        summary_stats: Dict[str, int], filters: CorpusAuditSearchFilter
    ) -> CorpusAuditReport:
        """Build comprehensive audit report."""
        audit_records = [self._convert_to_record(record) for record in records]
        
        time_range = {
            "start_date": filters.start_date,
            "end_date": filters.end_date
        }
        
        return CorpusAuditReport(
            total_records=total_count,
            records=audit_records,
            summary=summary_stats,
            time_range=time_range
        )

    async def generate_audit_report(
        self, db: AsyncSession, filters: CorpusAuditSearchFilter
    ) -> CorpusAuditReport:
        """Generate comprehensive audit report with analytics."""
        try:
            return await self.search_audit_logs(db, filters)
        except Exception as e:
            logger.error(f"Failed to generate audit report: {e}")
            raise NetraException(f"Audit report generation failed: {str(e)}")


async def create_audit_logger(db: AsyncSession) -> CorpusAuditLogger:
    """Factory function to create configured audit logger."""
    repository = CorpusAuditRepository()
    return CorpusAuditLogger(repository)