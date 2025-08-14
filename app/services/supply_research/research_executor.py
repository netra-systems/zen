"""
Research Execution and Notifications
Handles execution of scheduled research tasks and change notifications
"""

import json
from typing import Dict, Any, List
from datetime import datetime, UTC
from app.agents.supply_researcher_sub_agent import SupplyResearcherAgent
from app.services.supply_research_service import SupplyResearchService
from app.llm.llm_manager import LLMManager
from app.redis_manager import RedisManager
from app.db.postgres import Database
from app.logging_config import central_logger as logger
from .scheduler_models import ResearchSchedule


class ResearchExecutor:
    """Handles execution of research tasks and change notifications"""
    
    def __init__(self, llm_manager: LLMManager, redis_manager: RedisManager):
        self.llm_manager = llm_manager
        self.redis_manager = redis_manager
    
    async def execute_scheduled_research(
        self,
        schedule: ResearchSchedule
    ) -> Dict[str, Any]:
        """Execute a scheduled research task"""
        logger.info(f"Executing scheduled research: {schedule.name}")
        
        result = {
            "schedule_name": schedule.name,
            "started_at": datetime.now(UTC).isoformat(),
            "research_type": schedule.research_type.value,
            "providers": schedule.providers,
            "results": []
        }
        
        try:
            # Get database session
            db_manager = Database()
            with db_manager.get_db() as db:
                # Create agent and service
                supply_service = SupplyResearchService(db)
                agent = SupplyResearcherAgent(self.llm_manager, db, supply_service)
                
                # Process research for each provider
                research_result = await agent.process_scheduled_research(
                    schedule.research_type,
                    schedule.providers
                )
                
                result["results"] = research_result.get("results", [])
                result["status"] = "completed"
                result["completed_at"] = datetime.now(UTC).isoformat()
                
                # Cache result if Redis available
                if self.redis_manager:
                    await self._cache_result(schedule, result)
                
                # Check for significant changes and send notifications
                await self._check_and_notify_changes(result, supply_service)
                
                # Update schedule
                schedule.update_after_run()
                
                logger.info(f"Completed scheduled research: {schedule.name}")
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled research {schedule.name}: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
        
        return result
    
    async def _cache_result(self, schedule: ResearchSchedule, result: Dict[str, Any]):
        """Cache research result"""
        cache_key = f"schedule_result:{schedule.name}:{datetime.now(UTC).date()}"
        await self.redis_manager.set(
            cache_key,
            json.dumps(result, default=str),
            ex=86400  # Cache for 24 hours
        )
    
    async def _check_and_notify_changes(
        self,
        result: Dict[str, Any],
        supply_service: SupplyResearchService
    ):
        """Check for significant changes and send notifications"""
        try:
            # Check for price changes above threshold
            price_changes = supply_service.calculate_price_changes(days_back=1)
            
            significant_changes = []
            for change in price_changes.get("all_changes", []):
                if abs(change["percent_change"]) > 10:  # 10% threshold
                    significant_changes.append({
                        "type": "price_change",
                        "provider": change["provider"],
                        "model": change["model"],
                        "field": change["field"],
                        "percent_change": change["percent_change"]
                    })
            
            # Check for new models
            new_models = self._extract_new_models(result)
            significant_changes.extend(new_models)
            
            if significant_changes:
                await self._send_notifications(significant_changes)
        
        except Exception as e:
            logger.error(f"Failed to check and notify changes: {e}")
    
    def _extract_new_models(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract new models from research result"""
        new_models = []
        for provider_result in result.get("results", []):
            if provider_result.get("result", {}).get("updates_made", {}).get("updates_count", 0) > 0:
                for update in provider_result["result"]["updates_made"]["updates"]:
                    if update.get("action") == "created":
                        new_models.append({
                            "type": "new_model",
                            "model": update["model"]
                        })
        return new_models
    
    async def _send_notifications(self, significant_changes: List[Dict[str, Any]]):
        """Send notifications for significant changes"""
        # In production, send notifications via email/webhook/etc.
        logger.warning(f"Significant changes detected: {json.dumps(significant_changes, indent=2)}")
        
        # Cache notifications
        if self.redis_manager:
            await self.redis_manager.lpush(
                "supply_notifications",
                json.dumps({
                    "timestamp": datetime.now(UTC).isoformat(),
                    "changes": significant_changes
                }, default=str)
            )