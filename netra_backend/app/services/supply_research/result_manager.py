"""
Research Result Management
Handles retrieval and management of research results
"""

import json
from datetime import datetime, UTC, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.supply_research.scheduler_models import ResearchSchedule

logger = central_logger.get_logger(__name__)

class ResultManager:
    """Manages research results"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        
    async def get_results(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get research results for a schedule"""
        try:
            result = await self.redis_manager.get(f"research_result:{schedule_id}")
            return json.loads(result) if result else None
        except Exception as e:
            logger.error(f"Error getting results for {schedule_id}: {e}")
            return None
            
    async def store_results(self, schedule_id: str, results: Dict[str, Any]) -> bool:
        """Store research results"""
        try:
            await self.redis_manager.set(
                f"research_result:{schedule_id}",
                json.dumps(results),
                ex=timedelta(days=7).total_seconds()
            )
            return True
        except Exception as e:
            logger.error(f"Error storing results for {schedule_id}: {e}")
            return False
