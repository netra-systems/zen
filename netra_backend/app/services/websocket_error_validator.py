"""
WebSocket Error Validator - Comprehensive validation for WebSocket event emission.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Error Prevention & Chat Reliability
- Value Impact: Prevents silent failures, ensures reliable real-time communication
- Strategic Impact: Maintains business value through guaranteed event delivery

This validator implements loud error patterns with conditional logging to prevent
silent failures in WebSocket event emission, per CLAUDE.md requirements.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class EventCriticality(Enum):
    """Event criticality levels for business value assessment."""
    MISSION_CRITICAL = "mission_critical"  # agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
    BUSINESS_VALUE = "business_value"     # progress_update, custom events
    OPERATIONAL = "operational"           # connection events, cleanup events


@dataclass
class ValidationResult:
    """Result of event validation."""
    is_valid: bool
    error_message: Optional[str] = None
    warning_message: Optional[str] = None
    criticality: EventCriticality = EventCriticality.OPERATIONAL
    business_impact: Optional[str] = None


class WebSocketEventValidator:
    """Comprehensive validator for WebSocket events with loud error patterns."""
    
    # Mission critical events that must never fail silently
    MISSION_CRITICAL_EVENTS = {
        "agent_started", "agent_thinking", "tool_executing", 
        "tool_completed", "agent_completed"
    }
    
    # Required fields for each event type
    EVENT_SCHEMAS = {
        "agent_started": {"run_id", "agent_name", "timestamp", "payload"},
        "agent_thinking": {"run_id", "agent_name", "timestamp", "payload"},
        "tool_executing": {"run_id", "agent_name", "timestamp", "payload"},
        "tool_completed": {"run_id", "agent_name", "timestamp", "payload"},
        "agent_completed": {"run_id", "agent_name", "timestamp", "payload"},
        "progress_update": {"run_id", "timestamp", "payload"},
        "agent_error": {"run_id", "agent_name", "timestamp", "payload"},
    }
    
    def __init__(self):
        """Initialize the validator."""
        self.validation_stats = {
            "total_validations": 0,
            "failed_validations": 0,
            "mission_critical_failures": 0,
            "last_reset": datetime.now(timezone.utc)
        }
    
    def validate_event(self, event: Dict[str, Any], user_id: str, 
                      connection_id: Optional[str] = None) -> ValidationResult:
        """Validate a WebSocket event with comprehensive error checking.
        
        Args:
            event: Event data to validate
            user_id: Target user ID
            connection_id: Optional connection ID
            
        Returns:
            ValidationResult with validation outcome and error details
        """
        self.validation_stats["total_validations"] += 1
        
        try:
            # Basic event structure validation
            result = self._validate_basic_structure(event)
            if not result.is_valid:
                self._log_validation_failure(result, event, user_id, connection_id)
                self.validation_stats["failed_validations"] += 1
                return result
            
            # Event type specific validation
            event_type = event.get("type", "unknown")
            result = self._validate_event_type(event, event_type)
            if not result.is_valid:
                self._log_validation_failure(result, event, user_id, connection_id)
                self.validation_stats["failed_validations"] += 1
                return result
            
            # Mission critical event validation
            if event_type in self.MISSION_CRITICAL_EVENTS:
                result = self._validate_mission_critical_event(event, event_type)
                if not result.is_valid:
                    self.validation_stats["mission_critical_failures"] += 1
                    self.validation_stats["failed_validations"] += 1
                    self._log_mission_critical_failure(result, event, user_id, connection_id)
                    return result
            
            # User context validation
            result = self._validate_user_context(event, user_id)
            if not result.is_valid:
                self._log_validation_failure(result, event, user_id, connection_id)
                self.validation_stats["failed_validations"] += 1
                return result
            
            # Success case
            logger.debug(f"✅ Event validation passed: {event_type} for user {user_id[:8]}...")
            return ValidationResult(
                is_valid=True,
                criticality=self._get_event_criticality(event_type)
            )
            
        except Exception as e:
            self.validation_stats["failed_validations"] += 1
            logger.critical(f"🚨 CRITICAL: Event validation exception: {e}")
            logger.critical(f"🚨 BUSINESS VALUE FAILURE: Event validation system failure")
            logger.critical(f"🚨 Impact: Event may be malformed or cause downstream issues")
            # Log stack trace for debugging
            import traceback
            logger.critical(f"🚨 Stack trace: {traceback.format_exc()}")
            
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation system failure: {e}",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Event validation system failure - all events at risk"
            )
    
    def validate_connection_ready(self, user_id: str, connection_id: str, 
                                 websocket_manager: Optional[Any] = None) -> ValidationResult:
        """Validate that connection is ready for event emission.
        
        Args:
            user_id: User ID for the connection
            connection_id: Connection ID to validate
            websocket_manager: Optional WebSocket manager to check against
            
        Returns:
            ValidationResult with connection readiness status
        """
        try:
            # Basic parameter validation
            if not user_id or not user_id.strip():
                return ValidationResult(
                    is_valid=False,
                    error_message="Empty or invalid user_id",
                    criticality=EventCriticality.MISSION_CRITICAL,
                    business_impact="User cannot receive events - complete chat failure"
                )
            
            if not connection_id or not connection_id.strip():
                return ValidationResult(
                    is_valid=False,
                    error_message="Empty or invalid connection_id",
                    criticality=EventCriticality.MISSION_CRITICAL,
                    business_impact="Connection not identifiable - events will be lost"
                )
            
            # WebSocket manager validation
            if websocket_manager is None:
                return ValidationResult(
                    is_valid=False,
                    error_message="WebSocket manager not available",
                    criticality=EventCriticality.MISSION_CRITICAL,
                    business_impact="No WebSocket infrastructure - all events will fail"
                )
            
            # Connection state validation (if manager supports it)
            if hasattr(websocket_manager, 'is_connection_active'):
                try:
                    is_active = websocket_manager.is_connection_active(connection_id)
                    if not is_active:
                        return ValidationResult(
                            is_valid=False,
                            error_message=f"Connection {connection_id} is not active",
                            criticality=EventCriticality.BUSINESS_VALUE,
                            business_impact="User will not receive real-time updates"
                        )
                except Exception as check_error:
                    logger.warning(f"⚠️ Could not check connection status: {check_error}")
                    # Continue with validation - connection check failure is not fatal
            
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            logger.critical(f"🚨 CRITICAL: Connection validation exception: {e}")
            return ValidationResult(
                is_valid=False,
                error_message=f"Connection validation failure: {e}",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Connection validation system failure"
            )
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics for monitoring."""
        uptime = (datetime.now(timezone.utc) - self.validation_stats["last_reset"]).total_seconds()
        total = self.validation_stats["total_validations"]
        failed = self.validation_stats["failed_validations"]
        
        success_rate = ((total - failed) / total * 100) if total > 0 else 100
        
        return {
            "total_validations": total,
            "failed_validations": failed,
            "mission_critical_failures": self.validation_stats["mission_critical_failures"],
            "success_rate": success_rate,
            "uptime_seconds": uptime,
            "last_reset": self.validation_stats["last_reset"].isoformat()
        }
    
    def reset_stats(self):
        """Reset validation statistics."""
        self.validation_stats = {
            "total_validations": 0,
            "failed_validations": 0,
            "mission_critical_failures": 0,
            "last_reset": datetime.now(timezone.utc)
        }
        logger.info("WebSocket event validation statistics reset")
    
    # Private validation methods
    
    def _validate_basic_structure(self, event: Any) -> ValidationResult:
        """Validate basic event structure."""
        if not isinstance(event, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Event is not a dictionary",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Malformed event - cannot be processed"
            )
        
        if "type" not in event:
            return ValidationResult(
                is_valid=False,
                error_message="Event missing required 'type' field",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Event type unknown - cannot be routed"
            )
        
        if not event.get("type") or not isinstance(event["type"], str):
            return ValidationResult(
                is_valid=False,
                error_message="Event 'type' field is empty or not a string",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Invalid event type - cannot be processed"
            )
        
        return ValidationResult(is_valid=True)
    
    def _validate_event_type(self, event: Dict[str, Any], event_type: str) -> ValidationResult:
        """Validate event type specific requirements."""
        if event_type in self.EVENT_SCHEMAS:
            required_fields = self.EVENT_SCHEMAS[event_type]
            missing_fields = required_fields - event.keys()
            
            if missing_fields:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Event missing required fields: {missing_fields}",
                    criticality=self._get_event_criticality(event_type),
                    business_impact=f"Incomplete {event_type} event - user experience degraded"
                )
        
        return ValidationResult(is_valid=True)
    
    def _validate_mission_critical_event(self, event: Dict[str, Any], event_type: str) -> ValidationResult:
        """Validate mission critical events with strict requirements."""
        # Validate run_id is present and valid
        run_id = event.get("run_id")
        if not run_id or not isinstance(run_id, str) or not run_id.strip():
            return ValidationResult(
                is_valid=False,
                error_message=f"Mission critical event {event_type} missing valid run_id",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Event cannot be traced to user execution - chat value lost"
            )
        
        # Validate agent_name for agent events
        if event_type.startswith("agent_") or event_type.startswith("tool_"):
            agent_name = event.get("agent_name")
            if not agent_name or not isinstance(agent_name, str) or not agent_name.strip():
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Mission critical event {event_type} missing valid agent_name",
                    criticality=EventCriticality.MISSION_CRITICAL,
                    business_impact="User cannot identify which AI agent is working"
                )
        
        # Validate payload structure
        payload = event.get("payload")
        if payload is not None and not isinstance(payload, dict):
            return ValidationResult(
                is_valid=False,
                error_message=f"Mission critical event {event_type} has invalid payload structure",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Event payload malformed - user cannot receive complete information"
            )
        
        return ValidationResult(is_valid=True)
    
    def _validate_user_context(self, event: Dict[str, Any], user_id: str) -> ValidationResult:
        """Validate user context for security."""
        if not user_id or not isinstance(user_id, str) or not user_id.strip():
            return ValidationResult(
                is_valid=False,
                error_message="Invalid user_id for event routing",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Event cannot be routed to user - complete failure"
            )
        
        # Check for potential cross-user leakage in event data
        event_user_id = event.get("user_id")
        if event_user_id and event_user_id != user_id:
            return ValidationResult(
                is_valid=False,
                error_message=f"Event contains different user_id ({event_user_id}) than target ({user_id[:8]}...)",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="SECURITY BREACH: Cross-user event leakage detected"
            )
        
        return ValidationResult(is_valid=True)
    
    def _get_event_criticality(self, event_type: str) -> EventCriticality:
        """Determine event criticality level."""
        if event_type in self.MISSION_CRITICAL_EVENTS:
            return EventCriticality.MISSION_CRITICAL
        elif event_type in {"progress_update", "custom"}:
            return EventCriticality.BUSINESS_VALUE
        else:
            return EventCriticality.OPERATIONAL
    
    def _log_validation_failure(self, result: ValidationResult, event: Any, 
                               user_id: str, connection_id: Optional[str]):
        """Log validation failure with appropriate severity."""
        # Don't increment here - already incremented in calling method
        
        event_type = "unknown"
        if isinstance(event, dict):
            event_type = event.get("type", "unknown")
        elif event is not None:
            event_type = f"malformed({type(event).__name__})"
        
        log_level = logger.critical if result.criticality == EventCriticality.MISSION_CRITICAL else logger.error
        
        log_level(f"🚨 EVENT VALIDATION FAILURE: {result.error_message}")
        log_level(f"🚨 Event: {event_type}, User: {user_id[:8]}..., Connection: {connection_id}")
        log_level(f"🚨 Criticality: {result.criticality.value}")
        
        if result.business_impact:
            log_level(f"🚨 BUSINESS IMPACT: {result.business_impact}")
    
    def _log_mission_critical_failure(self, result: ValidationResult, event: Any, 
                                     user_id: str, connection_id: Optional[str]):
        """Log mission critical event failure with maximum visibility."""
        event_type = "unknown"
        if isinstance(event, dict):
            event_type = event.get("type", "unknown")
        elif event is not None:
            event_type = f"malformed({type(event).__name__})"
        
        logger.critical(f"🚨 MISSION CRITICAL EVENT VALIDATION FAILURE")
        logger.critical(f"🚨 Event Type: {event_type}")
        logger.critical(f"🚨 Error: {result.error_message}")
        logger.critical(f"🚨 User: {user_id[:8]}..., Connection: {connection_id}")
        logger.critical(f"🚨 BUSINESS VALUE AT RISK: {result.business_impact}")
        logger.critical(f"🚨 This is a CRITICAL FAILURE requiring immediate attention")
        logger.critical(f"🚨 Mission critical events MUST NOT fail - chat value depends on them")


# Global validator instance
_validator_instance: Optional[WebSocketEventValidator] = None


def get_websocket_validator() -> WebSocketEventValidator:
    """Get the global WebSocket event validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = WebSocketEventValidator()
    return _validator_instance


def reset_websocket_validator():
    """Reset the global validator instance (for testing)."""
    global _validator_instance
    _validator_instance = None