"""
Research Execution and Notifications
Handles execution of scheduled research tasks and change notifications
"""

import json
from datetime import UTC, datetime
from typing import Any, Dict, List

from netra_backend.app.agents.supply_researcher_sub_agent import SupplyResearcherAgent
from netra_backend.app.config import get_config
settings = get_config()
from netra_backend.app.db.postgres import Database
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.supply_research.scheduler_models import ResearchSchedule
from netra_backend.app.services.supply_research_service import SupplyResearchService


class ResearchExecutor:
    """Handles execution of research tasks and change notifications"""
    
    def __init__(self, llm_manager: LLMManager, redis_manager: RedisManager, websocket_bridge=None):
        self.llm_manager = llm_manager
        self.redis_manager = redis_manager
        self.websocket_bridge = websocket_bridge
    
    async def execute_scheduled_research(
        self,
        schedule: ResearchSchedule
    ) -> Dict[str, Any]:
        """Execute a scheduled research task"""
        logger.info(f"Executing scheduled research: {schedule.name}")
        result = self._initialize_research_result(schedule)
        
        try:
            await self._execute_research_workflow(schedule, result)
        except Exception as e:
            self._handle_research_error(e, schedule, result)
        
        return result
    
    def _initialize_research_result(self, schedule: ResearchSchedule) -> Dict[str, Any]:
        """Initialize research result structure"""
        return {
            "schedule_name": schedule.name,
            "started_at": datetime.now(UTC).isoformat(),
            "research_type": schedule.research_type.value,
            "providers": schedule.providers,
            "results": []
        }
    
    async def _execute_research_workflow(self, schedule: ResearchSchedule, result: Dict[str, Any]):
        """Execute the main research workflow"""
        db_manager = Database(settings.database_url)
        with db_manager.get_db() as db:
            research_result = await self._run_research_agents(schedule, db)
            await self._process_research_completion(schedule, result, research_result, db)
    
    async def _run_research_agents(self, schedule: ResearchSchedule, db) -> Dict[str, Any]:
        """Run research agents for the schedule"""
        supply_service = SupplyResearchService(db)
        agent = SupplyResearcherAgent(self.llm_manager, db, supply_service)
        
        # Set WebSocket bridge if available for real-time research progress updates
        if self.websocket_bridge:
            run_id = f"research_{schedule.research_type}_{schedule.name}"
            agent.set_websocket_bridge(self.websocket_bridge, run_id)
            logger.debug(f"Set WebSocket bridge on SupplyResearcherAgent for run_id: {run_id}")
        
        return await agent.process_scheduled_research(
            schedule.research_type,
            schedule.providers
        )
    
    async def _process_research_completion(
        self, schedule: ResearchSchedule, result: Dict[str, Any], 
        research_result: Dict[str, Any], db
    ):
        """Process research completion tasks"""
        result["results"] = research_result.get("results", [])
        result["status"] = "completed"
        result["completed_at"] = datetime.now(UTC).isoformat()
        
        await self._finalize_research_tasks(schedule, result, db)
    
    async def _finalize_research_tasks(self, schedule: ResearchSchedule, result: Dict[str, Any], db):
        """Finalize research tasks and notifications"""
        if self.redis_manager:
            await self._cache_result(schedule, result)
        
        supply_service = SupplyResearchService(db)
        await self._check_and_notify_changes(result, supply_service)
        schedule.update_after_run()
        logger.info(f"Completed scheduled research: {schedule.name}")
    
    def _handle_research_error(self, error: Exception, schedule: ResearchSchedule, result: Dict[str, Any]):
        """Handle research execution error"""
        logger.error(f"Failed to execute scheduled research {schedule.name}: {error}")
        result["status"] = "failed"
        result["error"] = str(error)
    
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