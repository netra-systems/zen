"""Analytics tracking for demo service."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Dict

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)

class AnalyticsTracker:
    """Tracks and analyzes demo interactions."""
    
    def __init__(self):
        self.redis_client = None
        
    async def _get_redis(self):
        """Get Redis client lazily."""
        if not self.redis_client:
            self.redis_client = await redis_manager.get_client()
        return self.redis_client
        
    async def track_interaction(self, session_id: str, interaction_type: str,
                               data: Dict[str, Any]) -> None:
        """Track demo interaction for analytics."""
        try:
            redis = await self._get_redis()
            analytics_key = f"demo:analytics:{datetime.now(UTC).strftime('%Y%m%d')}"
            interaction_data = {
                "session_id": session_id,
                "type": interaction_type,
                "data": data,
                "timestamp": datetime.now(UTC).isoformat()
            }
            await redis.lpush(analytics_key, json.dumps(interaction_data))
            await redis.expire(analytics_key, 3600 * 24 * 90)
        except Exception as e:
            logger.error(f"Analytics tracking error: {str(e)}")
            
    async def submit_feedback(self, session_id: str, 
                            feedback: Dict[str, Any]) -> None:
        """Submit feedback for a demo session."""
        try:
            redis = await self._get_redis()
            feedback_key = f"demo:feedback:{session_id}"
            feedback_data = {
                "session_id": session_id,
                "feedback": feedback,
                "submitted_at": datetime.now(UTC).isoformat()
            }
            await redis.setex(feedback_key, 3600 * 24 * 30, 
                            json.dumps(feedback_data))
        except Exception as e:
            logger.error(f"Feedback submission error: {str(e)}")
            raise
            
    async def process_analytics_data(self, data: list, 
                                    metrics: dict) -> tuple:
        """Process analytics data items."""
        for item in data:
            if item:
                interaction = json.loads(item)
                metrics["total_interactions"] += 1
                if interaction["type"] == "chat":
                    metrics["total_sessions"] += 1
                    industry = interaction["data"].get("industry", "unknown")
                    metrics["industries"][industry] = (
                        metrics["industries"].get(industry, 0) + 1)
                if interaction["type"] == "report_export":
                    metrics["conversion_events"] += 1
        return metrics
            
    async def get_analytics_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get analytics summary for demo usage."""
        try:
            redis = await self._get_redis()
            metrics = {
                "total_sessions": 0,
                "total_interactions": 0,
                "industries": {},
                "conversion_events": 0
            }
            end_date = datetime.now(UTC)
            for i in range(days):
                date = end_date - timedelta(days=i)
                key = f"demo:analytics:{date.strftime('%Y%m%d')}"
                data = await redis.lrange(key, 0, -1)
                metrics = await self.process_analytics_data(data, metrics)
            conversion_rate = ((metrics["conversion_events"] / 
                              metrics["total_sessions"] * 100) 
                             if metrics["total_sessions"] > 0 else 0)
            return {
                "period_days": days,
                "total_sessions": metrics["total_sessions"],
                "total_interactions": metrics["total_interactions"],
                "conversion_rate": conversion_rate,
                "industries": metrics["industries"],
                "avg_interactions_per_session": (metrics["total_interactions"] / 
                    metrics["total_sessions"] if metrics["total_sessions"] > 0 else 0),
                "report_exports": metrics["conversion_events"]
            }
        except Exception as e:
            logger.error(f"Analytics summary error: {str(e)}")
            raise