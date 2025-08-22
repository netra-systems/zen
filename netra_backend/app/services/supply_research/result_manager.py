"""
Research Result Management
Handles retrieval and management of research results
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.supply_research.scheduler_models import ResearchSchedule


class ResultManager:
    """Manages research results and cached data"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
    
    async def get_recent_results(
        self,
        schedules: List[ResearchSchedule],
        schedule_name: Optional[str] = None,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """Get recent research results from cache"""
        if not self.redis_manager:
            return []
        
        results = []
        cutoff_date = datetime.now(UTC) - timedelta(days=days_back)
        
        # Check last N days
        for i in range(days_back):
            date = (datetime.now(UTC) - timedelta(days=i)).date()
            
            if schedule_name:
                keys = [f"schedule_result:{schedule_name}:{date}"]
            else:
                keys = [f"schedule_result:{s.name}:{date}" for s in schedules]
            
            for key in keys:
                result = await self._get_cached_result(key)
                if result:
                    results.append(result)
        
        return results
    
    async def _get_cached_result(self, key: str) -> Optional[Dict[str, Any]]:
        """Get single cached result"""
        try:
            data = await self.redis_manager.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.debug(f"Failed to get cached result for {key}: {e}")
        return None