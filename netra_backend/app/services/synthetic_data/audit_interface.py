"""
Audit Interface Module - Handles audit logging for synthetic data generation
"""

from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.services.synthetic_data.audit_logger import AuditLogger


class AuditInterface:
    """Interface for audit logging operations"""

    def __init__(self):
        self.audit_logger = AuditLogger()

    async def generate_with_audit(
        self, 
        service,
        config, 
        job_id: str, 
        user_id: str, 
        db: Optional[AsyncSession] = None
    ) -> Dict:
        """Generate synthetic data with comprehensive audit logging"""
        result = await service.generate_synthetic_data(config, db, user_id, None, job_id)
        await self.audit_logger.log_generation_with_audit(result, job_id, user_id, db)
        return result

    async def get_audit_logs(self, job_id: str, db: Optional[AsyncSession] = None) -> List[Dict]:
        """Retrieve audit logs for a specific job"""
        return await self.audit_logger.get_audit_logs_for_job(job_id, db)