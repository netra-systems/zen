"""
Corpus Audit Service

Comprehensive audit logging for all corpus operations with search, filtering,
and reporting capabilities. Follows 300-line limit and 8-line function rule.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from app.schemas.registry import (
    CorpusAuditRecord, CorpusAuditAction, CorpusAuditStatus,
    CorpusAuditMetadata, CorpusAuditSearchFilter, CorpusAuditReport
)
from app.db.models_postgres import CorpusAuditLog
from app.services.database.base_repository import BaseRepository
from app.logging_config import central_logger
from app.core.exceptions_database import DatabaseError
from app.core.exceptions_base import NetraException
import time
import uuid

logger = central_logger.get_logger(__name__)


class CorpusAuditRepository(BaseRepository[CorpusAuditLog]):
    """Repository for corpus audit operations with async patterns."""

    def __init__(self):
        super().__init__(CorpusAuditLog)

    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[CorpusAuditLog]:
        """Find audit records by user ID."""
        try:
            result = await db.execute(
                select(CorpusAuditLog).where(CorpusAuditLog.user_id == user_id)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error finding audit records by user {user_id}: {e}")
            raise DatabaseError(f"Failed to find audit records", context={"user_id": user_id})

    async def search_records(self, db: AsyncSession, filters: CorpusAuditSearchFilter) -> List[CorpusAuditLog]:
        """Search audit records with comprehensive filtering."""
        try:
            query = self._build_search_query(filters)
            result = await db.execute(query.limit(filters.limit).offset(filters.offset))
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error searching audit records: {e}")
            raise DatabaseError("Failed to search audit records", context={"filters": filters.model_dump()})

    def _build_search_query(self, filters: CorpusAuditSearchFilter):
        """Build search query with all filters applied."""
        query = select(CorpusAuditLog).order_by(desc(CorpusAuditLog.timestamp))
        
        if filters.user_id:
            query = query.where(CorpusAuditLog.user_id == filters.user_id)
        if filters.action:
            query = query.where(CorpusAuditLog.action == filters.action.value)
        if filters.status:
            query = query.where(CorpusAuditLog.status == filters.status.value)
        
        return self._apply_additional_filters(query, filters)

    def _apply_additional_filters(self, query, filters: CorpusAuditSearchFilter):
        """Apply additional search filters to query."""
        if filters.corpus_id:
            query = query.where(CorpusAuditLog.corpus_id == filters.corpus_id)
        if filters.resource_type:
            query = query.where(CorpusAuditLog.resource_type == filters.resource_type)
        if filters.start_date:
            query = query.where(CorpusAuditLog.timestamp >= filters.start_date)
        if filters.end_date:
            query = query.where(CorpusAuditLog.timestamp <= filters.end_date)
        
        return query

    async def count_records(self, db: AsyncSession, filters: CorpusAuditSearchFilter) -> int:
        """Count total records matching search filters."""
        try:
            query = self._build_count_query(filters)
            result = await db.execute(query)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting audit records: {e}")
            raise DatabaseError("Failed to count audit records", context={"filters": filters.model_dump()})

    def _build_count_query(self, filters: CorpusAuditSearchFilter):
        """Build count query with filters applied."""
        query = select(func.count()).select_from(CorpusAuditLog)
        
        conditions = []
        if filters.user_id:
            conditions.append(CorpusAuditLog.user_id == filters.user_id)
        if filters.action:
            conditions.append(CorpusAuditLog.action == filters.action.value)
        if filters.status:
            conditions.append(CorpusAuditLog.status == filters.status.value)
        
        return self._apply_count_conditions(query, conditions, filters)

    def _apply_count_conditions(self, query, conditions: List, filters: CorpusAuditSearchFilter):
        """Apply remaining conditions to count query."""
        if filters.corpus_id:
            conditions.append(CorpusAuditLog.corpus_id == filters.corpus_id)
        if filters.resource_type:
            conditions.append(CorpusAuditLog.resource_type == filters.resource_type)
        if filters.start_date:
            conditions.append(CorpusAuditLog.timestamp >= filters.start_date)
        if filters.end_date:
            conditions.append(CorpusAuditLog.timestamp <= filters.end_date)
        
        return query.where(and_(*conditions)) if conditions else query

    async def get_summary_stats(self, db: AsyncSession, filters: CorpusAuditSearchFilter) -> Dict[str, int]:
        """Get summary statistics for audit records."""
        try:
            query = select(
                CorpusAuditLog.action,
                CorpusAuditLog.status,
                func.count().label('count')
            ).group_by(CorpusAuditLog.action, CorpusAuditLog.status)
            
            result = await db.execute(query)
            return self._process_summary_results(result.fetchall())
        except Exception as e:
            logger.error(f"Error getting summary stats: {e}")
            raise DatabaseError("Failed to get summary statistics")

    def _process_summary_results(self, results: List) -> Dict[str, int]:
        """Process summary query results into organized stats."""
        stats = {}
        for action, status, count in results:
            key = f"{action}_{status}"
            stats[key] = count
        return stats


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
            audit_data = self._prepare_audit_data(
                action, resource_type, status, user_id, corpus_id,
                resource_id, operation_duration_ms, result_data, metadata
            )
            audit_log = await self.repository.create(db, **audit_data)
            return self._convert_to_record(audit_log)
        except Exception as e:
            logger.error(f"Failed to log audit operation: {e}")
            raise NetraException(f"Audit logging failed: {str(e)}")

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
        metadata = CorpusAuditMetadata(
            user_agent=audit_log.user_agent,
            ip_address=audit_log.ip_address,
            request_id=audit_log.request_id,
            session_id=audit_log.session_id,
            configuration=audit_log.configuration or {},
            performance_metrics=audit_log.performance_metrics or {},
            error_details=audit_log.error_details,
            compliance_flags=audit_log.compliance_flags or []
        )
        
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


# Context manager for operation timing
class AuditTimer:
    """Context manager for measuring operation duration."""

    def __init__(self):
        self.start_time = None
        self.duration_ms = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            end_time = time.perf_counter()
            self.duration_ms = (end_time - self.start_time) * 1000

    def get_duration(self) -> Optional[float]:
        """Get operation duration in milliseconds."""
        return self.duration_ms


async def create_audit_logger(db: AsyncSession) -> CorpusAuditLogger:
    """Factory function to create configured audit logger."""
    repository = CorpusAuditRepository()
    return CorpusAuditLogger(repository)