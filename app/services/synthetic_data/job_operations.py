"""Job Operations Module - Job management and status operations"""

from typing import Dict, Optional
from .core_service_base import CoreServiceBase


class JobOperations(CoreServiceBase):
    """Handles job management and status operations"""

    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status with admin-friendly format"""
        status = self.job_manager.get_job_status(job_id, self.active_jobs)
        if status:
            return self._transform_status_to_admin_format(status)
        return None

    async def cancel_job(self, job_id: str, reason: str = None) -> Dict:
        """Cancel generation job"""
        return await self.job_manager.cancel_job(job_id, self.active_jobs, reason)

    async def get_audit_logs(self, job_id: str, db = None) -> list:
        """Retrieve audit logs for a specific job"""
        return await self.audit_interface.get_audit_logs(job_id, db)

    async def generate_with_audit(
        self, config, job_id: str, user_id: str, db = None
    ) -> Dict:
        """Generate synthetic data with comprehensive audit logging"""
        return await self.audit_interface.generate_with_audit(self, config, job_id, user_id, db)