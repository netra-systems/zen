"""
Schedule Manager for Supply Research
Manages research schedules and timing
"""

import json
from datetime import datetime, UTC, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.supply_research.scheduler_models import ResearchSchedule, ScheduleFrequency

logger = central_logger.get_logger(__name__)

class ScheduleManager:
    """Manages research schedules"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        
    async def create_schedule(self, schedule: ResearchSchedule) -> bool:
        """Create a new research schedule"""
        try:
            key = f"schedule:{schedule.id}"
            value = json.dumps({
                "id": schedule.id,
                "frequency": schedule.frequency.value,
                "next_run": schedule.next_run.isoformat(),
                "active": schedule.active
            })
            await self.redis_manager.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Error creating schedule {schedule.id}: {e}")
            return False
            
    async def get_schedule(self, schedule_id: str) -> Optional[ResearchSchedule]:
        """Get a research schedule"""
        try:
            key = f"schedule:{schedule_id}"
            value = await self.redis_manager.get(key)
            if not value:
                return None
                
            data = json.loads(value)
            return ResearchSchedule(
                id=data["id"],
                frequency=ScheduleFrequency(data["frequency"]),
                next_run=datetime.fromisoformat(data["next_run"]),
                active=data["active"]
            )
        except Exception as e:
            logger.error(f"Error getting schedule {schedule_id}: {e}")
            return None
            
    async def get_due_schedules(self) -> List[ResearchSchedule]:
        """Get schedules that are due for execution"""
        try:
            # This is a simplified implementation
            # In production, this would scan Redis for due schedules
            return []
        except Exception as e:
            logger.error(f"Error getting due schedules: {e}")
            return []
