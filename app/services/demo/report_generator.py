"""Report generation for demo service."""

import json
import uuid
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional

from app.logging_config import central_logger
from app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)

class ReportGenerator:
    """Handles report generation and management."""
    
    def __init__(self):
        self.redis_client = None
        
    async def _get_redis(self):
        """Get Redis client lazily."""
        if not self.redis_client:
            self.redis_client = await redis_manager.get_client()
        return self.redis_client
        
    async def generate_report(self, session_id: str, format: str = "pdf",
                            include_sections: List[str] = None,
                            user_id: Optional[int] = None) -> str:
        """Generate a demo report for export."""
        try:
            redis = await self._get_redis()
            session_key = f"demo:session:{session_id}"
            session_data = await redis.get(session_key)
            if not session_data:
                raise ValueError(f"Session not found: {session_id}")
            session_data = json.loads(session_data)
            report_id = str(uuid.uuid4())
            report_url = f"/api/demo/reports/{report_id}.{format}"
            report_key = f"demo:report:{report_id}"
            report_data = {
                "session_id": session_id,
                "format": format,
                "sections": include_sections or ["summary", "metrics", "recommendations"],
                "generated_at": datetime.now(UTC).isoformat(),
                "user_id": user_id,
                "url": report_url
            }
            await redis.setex(report_key, 3600 * 24, json.dumps(report_data))
            return report_url
        except Exception as e:
            logger.error(f"Report generation error: {str(e)}")
            raise
            
    async def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get report metadata."""
        redis = await self._get_redis()
        report_key = f"demo:report:{report_id}"
        report_data = await redis.get(report_key)
        return json.loads(report_data) if report_data else None