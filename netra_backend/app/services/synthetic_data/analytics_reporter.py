"""Analytics Reporter Module - Analytics and reporting functionality"""

from typing import Dict, Any
from netra_backend.app.core_service_base import CoreServiceBase
from netra_backend.app.resource_tracker import ResourceTracker
from netra_backend.app.metrics import profile_generation, get_generation_metrics


class AnalyticsReporter(CoreServiceBase):
    """Handles analytics and reporting functionality"""

    async def get_corpus_analytics(self) -> Dict:
        """Get corpus usage analytics for admin visibility"""
        return await self.utilities.get_corpus_analytics()

    async def profile_generation(self, config) -> Dict[str, Any]:
        """Profile generation performance for admin optimization"""
        return await profile_generation(config)

    async def generate_monitored(self, config, job_id: str) -> Dict:
        """Generate synthetic data with monitoring"""
        from .synthetic_data_service_main import SyntheticDataService
        service = SyntheticDataService()
        return await service.generate_synthetic_data(config, job_id=job_id)

    async def get_generation_metrics(self, time_range_hours: int = 24) -> Dict:
        """Get generation metrics for admin dashboard"""
        return await get_generation_metrics(time_range_hours)

    async def start_resource_tracking(self) -> ResourceTracker:
        """Start resource usage tracking"""
        return ResourceTracker()