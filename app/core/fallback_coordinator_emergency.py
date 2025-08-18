"""
Emergency fallback responses and cascade prevention.
"""

from typing import Dict, Any
from datetime import datetime, UTC

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class EmergencyFallbackManager:
    """Manages emergency fallback responses and cascade prevention"""
    
    def __init__(self):
        self._init_emergency_responses()
    
    def _init_emergency_responses(self) -> None:
        """Initialize emergency response templates"""
        triage_response = self._create_triage_response()
        data_analysis_response = self._create_data_analysis_response()
        general_response = self._create_general_response()
        self.emergency_responses = {
            "triage": triage_response,
            "data_analysis": data_analysis_response,
            "general": general_response
        }
    
    async def execute_emergency_fallback(self, agent_name: str, operation_name: str, 
                                       fallback_type: str) -> Dict[str, Any]:
        """Execute emergency fallback when system is critical"""
        logger.warning(f"Executing emergency fallback for {agent_name}.{operation_name}")
        response = self._get_emergency_response_template(fallback_type)
        return self._add_emergency_metadata(response, agent_name, operation_name)
    
    def _get_emergency_response_template(self, fallback_type: str) -> Dict[str, Any]:
        """Get emergency response template for fallback type."""
        return self.emergency_responses.get(fallback_type, self.emergency_responses["general"]).copy()
    
    def _create_triage_response(self) -> Dict[str, Any]:
        """Create triage emergency response template."""
        return {
            "category": "System Maintenance",
            "confidence_score": 0.1,
            "priority": "low",
            "message": "System is temporarily unavailable for maintenance",
            "fallback_type": "emergency"
        }
    
    def _create_data_analysis_response(self) -> Dict[str, Any]:
        """Create data analysis emergency response template."""
        return {
            "analysis_type": "emergency_fallback",
            "insights": ["System temporarily unavailable"],
            "recommendations": ["Please try again later"],
            "data": {"available": False},
            "fallback_type": "emergency"
        }
    
    def _create_general_response(self) -> Dict[str, Any]:
        """Create general emergency response template."""
        return {
            "message": "System is temporarily experiencing issues. Please try again later.",
            "status": "emergency_fallback",
            "fallback_type": "emergency"
        }
    
    def _add_emergency_metadata(self, response: Dict[str, Any], agent_name: str, operation_name: str) -> Dict[str, Any]:
        """Add metadata to emergency response."""
        metadata = self._create_emergency_metadata(agent_name, operation_name)
        response.update(metadata)
        return response
    
    def _create_emergency_metadata(self, agent_name: str, operation_name: str) -> Dict[str, Any]:
        """Create emergency metadata dictionary."""
        return {
            "agent": agent_name,
            "operation": operation_name,
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "emergency_fallback"
        }
    
    async def execute_limited_fallback(self, agent_name: str, operation_name: str) -> Dict[str, Any]:
        """Execute limited fallback to prevent cascade"""
        logger.warning(f"Executing cascade prevention fallback for {agent_name}.{operation_name}")
        basic_response = self._build_basic_cascade_response(agent_name, operation_name)
        return self._add_cascade_recommendations(basic_response)
    
    def _build_basic_cascade_response(self, agent_name: str, operation_name: str) -> Dict[str, Any]:
        """Build basic cascade prevention response."""
        basic_data = self._create_cascade_basic_data(agent_name, operation_name)
        timestamp_data = self._create_cascade_timestamp_data()
        return {**basic_data, **timestamp_data}
    
    def _create_cascade_basic_data(self, agent_name: str, operation_name: str) -> Dict[str, Any]:
        """Create basic cascade prevention data."""
        return {
            "status": "cascade_prevention",
            "message": f"Limited fallback for {agent_name} to prevent system cascade failure",
            "agent": agent_name,
            "operation": operation_name
        }
    
    def _create_cascade_timestamp_data(self) -> Dict[str, Any]:
        """Create cascade prevention timestamp data."""
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "fallback_type": "cascade_prevention"
        }
    
    def _add_cascade_recommendations(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Add recommendations to cascade prevention response."""
        response["recommendations"] = [
            "System is under high load",
            "Try again in a few minutes",
            "Consider simplifying your request"
        ]
        return response
    
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