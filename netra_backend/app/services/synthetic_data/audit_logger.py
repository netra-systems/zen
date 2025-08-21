"""
Synthetic Data Audit Logger - Modular audit logging for generation operations
Follows 450-line limit and 25-line function rule
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.schemas.registry import (
    CorpusAuditAction, CorpusAuditStatus, CorpusAuditSearchFilter,
    CorpusAuditMetadata
)
from netra_backend.app.services.audit import create_audit_logger


class SyntheticDataAuditLogger:
    """Handles audit logging for synthetic data operations"""
    
    def __init__(self):
        self._memory_audit_logs: List[Dict] = []
    
    async def log_generation_with_audit(
        self, result: Dict, job_id: str, user_id: str, db: Optional[AsyncSession]
    ) -> None:
        """Log generation operation with comprehensive audit trail"""
        audit_entry = {
            "timestamp": datetime.now(UTC), "action": "generate", "user_id": user_id,
            "job_id": job_id, "result": result
        }
        if db:
            await self._log_to_database(db, result, job_id, user_id)
        else:
            self._memory_audit_logs.append(audit_entry)
    
    async def _log_to_database(
        self, db: AsyncSession, result: Dict, job_id: str, user_id: str
    ) -> None:
        """Log to database using audit infrastructure"""
        audit_logger = await create_audit_logger(db)
        metadata = CorpusAuditMetadata(configuration={"job_id": job_id})
        await audit_logger.log_operation(
            db, CorpusAuditAction.GENERATE, "synthetic_data",
            CorpusAuditStatus.SUCCESS, user_id, None, job_id, None, result, metadata
        )
    
    async def get_audit_logs_for_job(
        self, job_id: str, db: Optional[AsyncSession]
    ) -> List[Dict]:
        """Retrieve audit logs for specific job"""
        if not db:
            return [log for log in self._memory_audit_logs if log.get("job_id") == job_id]
        return await self._get_database_audit_logs(db, job_id)
    
    async def _get_database_audit_logs(self, db: AsyncSession, job_id: str) -> List[Dict]:
        """Get audit logs from database"""
        audit_logger = await create_audit_logger(db)
        filters = CorpusAuditSearchFilter(resource_id=job_id, limit=100)
        report = await audit_logger.search_audit_logs(db, filters)
        return [{"timestamp": r.timestamp, "action": r.action.value, "user_id": r.user_id} 
                for r in report.records]


# Alias for backward compatibility
AuditLogger = SyntheticDataAuditLogger