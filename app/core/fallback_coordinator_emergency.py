"""
Emergency fallback responses and cascade prevention.
"""

from typing import Dict, Any
from datetime import datetime

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class EmergencyFallbackManager:
    """Manages emergency fallback responses and cascade prevention"""
    
    def __init__(self):
        self._init_emergency_responses()
    
    def _init_emergency_responses(self) -> None:
        """Initialize emergency response templates"""
        self.emergency_responses = {
            "triage": {
                "category": "System Maintenance",
                "confidence_score": 0.1,
                "priority": "low",
                "message": "System is temporarily unavailable for maintenance",
                "fallback_type": "emergency"
            },
            "data_analysis": {
                "analysis_type": "emergency_fallback",
                "insights": ["System temporarily unavailable"],
                "recommendations": ["Please try again later"],
                "data": {"available": False},
                "fallback_type": "emergency"
            },
            "general": {
                "message": "System is temporarily experiencing issues. Please try again later.",
                "status": "emergency_fallback",
                "fallback_type": "emergency"
            }
        }
    
    async def execute_emergency_fallback(self, agent_name: str, operation_name: str, 
                                       fallback_type: str) -> Dict[str, Any]:
        """Execute emergency fallback when system is critical"""
        logger.warning(f"Executing emergency fallback for {agent_name}.{operation_name}")
        
        response = self.emergency_responses.get(fallback_type, self.emergency_responses["general"]).copy()
        response.update({
            "agent": agent_name,
            "operation": operation_name,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "emergency_fallback"
        })
        
        return response
    
    async def execute_limited_fallback(self, agent_name: str, operation_name: str) -> Dict[str, Any]:
        """Execute limited fallback to prevent cascade"""
        logger.warning(f"Executing cascade prevention fallback for {agent_name}.{operation_name}")
        
        return {
            "status": "cascade_prevention",
            "message": f"Limited fallback for {agent_name} to prevent system cascade failure",
            "agent": agent_name,
            "operation": operation_name,
            "timestamp": datetime.utcnow().isoformat(),
            "fallback_type": "cascade_prevention",
            "recommendations": [
                "System is under high load",
                "Try again in a few minutes",
                "Consider simplifying your request"
            ]
        }
    
    def get_emergency_response_template(self, fallback_type: str) -> Dict[str, Any]:
        """Get emergency response template for fallback type"""
        return self.emergency_responses.get(fallback_type, self.emergency_responses["general"]).copy()
    
    def update_emergency_response(self, fallback_type: str, response_template: Dict[str, Any]) -> None:
        """Update emergency response template"""
        self.emergency_responses[fallback_type] = response_template
        logger.info(f"Updated emergency response template for {fallback_type}")
    
    def get_all_emergency_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get all emergency response templates"""
        return self.emergency_responses.copy()