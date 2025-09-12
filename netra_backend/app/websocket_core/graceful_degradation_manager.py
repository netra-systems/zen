"""
Graceful Degradation Manager - SSOT for Service Unavailability Handling

Business Value Justification:
- Segment: Platform/All Segments 
- Business Goal: Revenue Protection & User Experience
- Value Impact: Ensures users always receive some level of functionality during service outages
- Strategic Impact: Protects $500K+ ARR chat functionality from complete failure

This module provides comprehensive graceful degradation when critical services
(agent supervisor, thread service) are unavailable during WebSocket connection.

CRITICAL BUSINESS REQUIREMENT:
Users must ALWAYS get some level of chat functionality, even if limited,
to maintain business continuity and prevent complete service failures.

Key Features:
- Service availability monitoring with timeout handling
- Fallback handler creation for basic chat responses
- Service recovery detection and transition to full mode
- User messaging about service status and capabilities
- Progressive enhancement when services become available
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.utils import safe_websocket_send, create_server_message, create_error_message, MessageType


logger = central_logger.get_logger(__name__)


class ServiceStatus(Enum):
    """Service availability status."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable" 
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    UNKNOWN = "unknown"


class DegradationLevel(Enum):
    """Levels of service degradation."""
    NONE = "none"                    # Full functionality
    MINIMAL = "minimal"              # Basic responses only
    MODERATE = "moderate"            # Some advanced features disabled
    SEVERE = "severe"               # Very limited functionality
    EMERGENCY = "emergency"         # Absolute minimum to prevent crashes


@dataclass
class ServiceHealth:
    """Health status of a service."""
    service_name: str
    status: ServiceStatus
    last_check: datetime
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self.status in [ServiceStatus.AVAILABLE, ServiceStatus.RECOVERING]
    
    @property
    def can_retry(self) -> bool:
        """Check if service can be retried."""
        return self.retry_count < self.max_retries


@dataclass
class DegradationContext:
    """Context for current degradation state."""
    level: DegradationLevel
    degraded_services: List[str]
    available_services: List[str]
    user_message: str
    capabilities: Dict[str, bool]
    estimated_recovery_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "level": self.level.value,
            "degraded_services": self.degraded_services,
            "available_services": self.available_services,
            "user_message": self.user_message,
            "capabilities": self.capabilities,
            "estimated_recovery_time": self.estimated_recovery_time
        }


class FallbackChatHandler:
    """
    Fallback chat handler that provides basic responses when full services unavailable.
    
    This handler ensures users always get SOME response, maintaining business continuity.
    Compatible with MessageRouter interface expectations.
    """
    
    def __init__(self, degradation_level: DegradationLevel, websocket):
        self.degradation_level = degradation_level
        self.websocket = websocket
        self.logger = central_logger.get_logger(f"{__name__}.FallbackHandler")
        self.response_templates = self._initialize_response_templates()
        
        # MessageRouter interface compatibility
        self.handler_id = f"fallback_handler_{int(time.time())}"
        self.handler_type = "fallback_chat"
    
    def _initialize_response_templates(self) -> Dict[str, str]:
        """Initialize response templates based on degradation level."""
        if self.degradation_level == DegradationLevel.MINIMAL:
            return {
                "greeting": "Hello! I'm currently running with limited capabilities due to service maintenance. I can provide basic responses but advanced AI features may be unavailable.",
                "agent_unavailable": "I apologize, but our advanced AI agents are temporarily unavailable due to system maintenance. I can help with basic information or you can try again shortly.",
                "service_status": "Some services are currently unavailable. We're working to restore full functionality. Please try again in a few minutes.",
                "fallback_response": "I'm operating with limited functionality right now. For the best experience, please try your request again in a few minutes when all services are restored."
            }
        elif self.degradation_level == DegradationLevel.MODERATE:
            return {
                "greeting": "Hello! Some advanced features are currently unavailable, but I can still help with basic requests.",
                "agent_unavailable": "Advanced AI analysis is temporarily limited. I can provide basic responses or queue your request for when services are restored.",
                "service_status": "We're operating with reduced functionality while services are being restored.",
                "fallback_response": "I can provide basic assistance, though some advanced features are temporarily unavailable."
            }
        else:  # SEVERE or EMERGENCY
            return {
                "greeting": "Hello! System is in maintenance mode. Basic connectivity available.",
                "agent_unavailable": "AI services are currently under maintenance. Please try again shortly.",
                "service_status": "System maintenance in progress. Limited functionality available.",
                "fallback_response": "System is in maintenance mode. Please try again in a few minutes."
            }
    
    async def handle_message(self, message: Dict[str, Any]) -> bool:
        """
        MessageRouter interface method - handle incoming message.
        
        Args:
            message: Incoming WebSocket message
            
        Returns:
            bool: True if message was handled, False otherwise
        """
        return await self.handle_user_message(message)
    
    async def handle_user_message(self, message: Dict[str, Any]) -> bool:
        """
        Handle user message with fallback responses.
        
        Returns:
            bool: True if message was handled, False otherwise
        """
        try:
            message_content = message.get("content", "").lower().strip()
            
            # Handle common user queries with fallback responses
            if any(greeting in message_content for greeting in ["hello", "hi", "hey", "start"]):
                await self._send_fallback_response("greeting")
                return True
            
            elif any(status in message_content for status in ["status", "available", "working"]):
                await self._send_service_status_response()
                return True
            
            elif "agent" in message_content or "ai" in message_content:
                await self._send_fallback_response("agent_unavailable")
                return True
            
            else:
                # Generic fallback for any other message
                await self._send_fallback_response("fallback_response")
                return True
                
        except Exception as e:
            self.logger.error(f"Fallback handler error: {e}")
            await self._send_emergency_response()
            return True  # Always claim to handle to prevent crashes
    
    async def _send_fallback_response(self, template_key: str):
        """Send a fallback response using templates."""
        response_text = self.response_templates.get(template_key, self.response_templates["fallback_response"])
        
        response_msg = create_server_message(
            MessageType.AGENT_RESPONSE,
            {
                "content": response_text,
                "type": "fallback_response",
                "degradation_level": self.degradation_level.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "fallback_handler"
            }
        )
        
        await safe_websocket_send(self.websocket, response_msg.model_dump())
        self.logger.info(f"Sent fallback response ({template_key}) with degradation level {self.degradation_level.value}")
    
    async def _send_service_status_response(self):
        """Send current service status to user."""
        status_msg = create_server_message(
            MessageType.SYSTEM_MESSAGE,
            {
                "event": "service_status_update",
                "degradation_level": self.degradation_level.value,
                "message": self.response_templates["service_status"],
                "capabilities": self._get_current_capabilities(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        await safe_websocket_send(self.websocket, status_msg.model_dump())
        self.logger.info("Sent service status update to user")
    
    async def _send_emergency_response(self):
        """Send emergency response when fallback handler fails."""
        emergency_msg = create_server_message(
            MessageType.SYSTEM_MESSAGE,
            {
                "content": "System experiencing technical difficulties. Please try again in a few minutes.",
                "type": "emergency_response",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        try:
            await safe_websocket_send(self.websocket, emergency_msg.model_dump())
        except Exception:
            pass  # Best effort - don't crash on emergency response failure
    
    def _get_current_capabilities(self) -> Dict[str, bool]:
        """Get current system capabilities based on degradation level."""
        if self.degradation_level == DegradationLevel.MINIMAL:
            return {
                "basic_chat": True,
                "agent_execution": False,
                "advanced_analysis": False,
                "tool_execution": False,
                "data_processing": False
            }
        elif self.degradation_level == DegradationLevel.MODERATE:
            return {
                "basic_chat": True,
                "agent_execution": False,
                "advanced_analysis": False,
                "tool_execution": False,
                "data_processing": False
            }
        else:  # SEVERE or EMERGENCY
            return {
                "basic_chat": True,
                "agent_execution": False,
                "advanced_analysis": False,
                "tool_execution": False,
                "data_processing": False
            }


class GracefulDegradationManager:
    """
    SSOT Manager for handling service unavailability with graceful degradation.
    
    Ensures users always receive some level of functionality even when critical
    services like agent supervisor or thread service are unavailable.
    """
    
    def __init__(self, websocket, app_state):
        self.websocket = websocket
        self.app_state = app_state
        self.logger = central_logger.get_logger(__name__)
        
        # Service monitoring
        self.service_health: Dict[str, ServiceHealth] = {}
        self.monitoring_task: Optional[asyncio.Task] = None
        self.recovery_callbacks: List[Callable] = []
        
        # Degradation state
        self.current_degradation: Optional[DegradationContext] = None
        self.fallback_handler: Optional[FallbackChatHandler] = None
        
        # Recovery settings
        self.service_check_interval = 30.0  # Check every 30 seconds
        self.service_timeout = 5.0  # 5 second timeout for service checks
        self.recovery_stabilization_time = 10.0  # Wait 10s before declaring recovery
        
    async def assess_service_availability(self) -> DegradationContext:
        """
        Assess current service availability and determine degradation level.
        
        Returns:
            DegradationContext: Current system degradation state
        """
        self.logger.info(" SEARCH:  Assessing service availability for graceful degradation...")
        
        # Check critical services
        critical_services = {
            "agent_supervisor": getattr(self.app_state, 'agent_supervisor', None),
            "thread_service": getattr(self.app_state, 'thread_service', None),
            "agent_websocket_bridge": getattr(self.app_state, 'agent_websocket_bridge', None),
        }
        
        # Update service health status
        available_services = []
        degraded_services = []
        
        for service_name, service_obj in critical_services.items():
            health = await self._check_service_health(service_name, service_obj)
            self.service_health[service_name] = health
            
            if health.is_healthy:
                available_services.append(service_name)
            else:
                degraded_services.append(service_name)
        
        # Determine degradation level
        degradation_level = self._calculate_degradation_level(available_services, degraded_services)
        
        # Create user message
        user_message = self._generate_user_message(degradation_level, degraded_services)
        
        # Estimate recovery time
        estimated_recovery = self._estimate_recovery_time(degraded_services)
        
        degradation_context = DegradationContext(
            level=degradation_level,
            degraded_services=degraded_services,
            available_services=available_services,
            user_message=user_message,
            capabilities=self._get_capabilities_for_level(degradation_level),
            estimated_recovery_time=estimated_recovery
        )
        
        self.current_degradation = degradation_context
        self.logger.info(f" PASS:  Service assessment complete: {degradation_level.value} degradation, {len(available_services)}/{len(critical_services)} services available")
        
        return degradation_context
    
    async def _check_service_health(self, service_name: str, service_obj: Any) -> ServiceHealth:
        """Check health of a specific service."""
        check_start = time.time()
        
        try:
            if service_obj is None:
                return ServiceHealth(
                    service_name=service_name,
                    status=ServiceStatus.UNAVAILABLE,
                    last_check=datetime.now(timezone.utc),
                    error_message="Service object is None"
                )
            
            # Basic service health check - verify it's not crashed
            if hasattr(service_obj, 'health_check'):
                # Use service's own health check if available
                health_result = await asyncio.wait_for(
                    service_obj.health_check(), 
                    timeout=self.service_timeout
                )
                status = ServiceStatus.AVAILABLE if health_result else ServiceStatus.DEGRADED
            else:
                # Basic existence check - service object exists and appears functional
                status = ServiceStatus.AVAILABLE
            
            response_time = time.time() - check_start
            
            return ServiceHealth(
                service_name=service_name,
                status=status,
                last_check=datetime.now(timezone.utc),
                response_time=response_time
            )
            
        except asyncio.TimeoutError:
            return ServiceHealth(
                service_name=service_name,
                status=ServiceStatus.UNAVAILABLE,
                last_check=datetime.now(timezone.utc),
                error_message="Health check timeout",
                response_time=self.service_timeout
            )
        except Exception as e:
            return ServiceHealth(
                service_name=service_name,
                status=ServiceStatus.UNAVAILABLE,
                last_check=datetime.now(timezone.utc),
                error_message=str(e),
                response_time=time.time() - check_start
            )
    
    def _calculate_degradation_level(self, available: List[str], degraded: List[str]) -> DegradationLevel:
        """Calculate appropriate degradation level based on service availability."""
        total_services = len(available) + len(degraded)
        available_count = len(available)
        
        if available_count == total_services:
            return DegradationLevel.NONE
        elif available_count >= total_services * 0.75:  # 75% available
            return DegradationLevel.MINIMAL
        elif available_count >= total_services * 0.5:   # 50% available
            return DegradationLevel.MODERATE
        elif available_count > 0:                       # Some services available
            return DegradationLevel.SEVERE
        else:                                           # No services available
            return DegradationLevel.EMERGENCY
    
    def _generate_user_message(self, level: DegradationLevel, degraded: List[str]) -> str:
        """Generate user-friendly message about current system status."""
        if level == DegradationLevel.NONE:
            return "All systems operational. Full functionality available."
        elif level == DegradationLevel.MINIMAL:
            return f"Some services ({', '.join(degraded)}) are temporarily unavailable. Basic functionality is available."
        elif level == DegradationLevel.MODERATE:
            return f"Multiple services are currently unavailable. Limited functionality is available while we restore services."
        elif level == DegradationLevel.SEVERE:
            return "Most services are currently unavailable due to maintenance. Very limited functionality is available."
        else:  # EMERGENCY
            return "System is in emergency mode. Please try again in a few minutes."
    
    def _get_capabilities_for_level(self, level: DegradationLevel) -> Dict[str, bool]:
        """Get system capabilities for a given degradation level."""
        capabilities = {
            "websocket_connection": True,  # Always available if we got this far
            "basic_messaging": True,       # Always provide basic messaging
            "agent_execution": False,
            "advanced_analysis": False, 
            "tool_execution": False,
            "data_processing": False,
            "real_time_updates": False
        }
        
        if level in [DegradationLevel.NONE, DegradationLevel.MINIMAL]:
            # Some advanced features may be available
            capabilities.update({
                "real_time_updates": True
            })
        
        return capabilities
    
    def _estimate_recovery_time(self, degraded_services: List[str]) -> Optional[float]:
        """Estimate recovery time based on degraded services."""
        if not degraded_services:
            return None
        
        # Base recovery time per service
        base_time_per_service = 30.0  # 30 seconds
        return len(degraded_services) * base_time_per_service
    
    async def create_fallback_handler(self) -> FallbackChatHandler:
        """Create appropriate fallback handler for current degradation level."""
        if self.current_degradation is None:
            await self.assess_service_availability()
        
        self.fallback_handler = FallbackChatHandler(
            self.current_degradation.level,
            self.websocket
        )
        
        self.logger.info(f" PASS:  Created fallback handler for {self.current_degradation.level.value} degradation")
        return self.fallback_handler
    
    async def notify_user_of_degradation(self):
        """Send degradation status notification to user."""
        if self.current_degradation is None:
            return
        
        notification = create_server_message(
            MessageType.SYSTEM_MESSAGE,
            {
                "event": "service_degradation",
                "degradation_context": self.current_degradation.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "graceful_degradation_manager"
            }
        )
        
        await safe_websocket_send(self.websocket, notification.model_dump())
        self.logger.info(f"[U+1F4E2] Notified user of {self.current_degradation.level.value} service degradation")
    
    async def start_recovery_monitoring(self):
        """Start background task to monitor for service recovery."""
        if self.monitoring_task is not None:
            return  # Already monitoring
        
        self.logger.info(" CYCLE:  Starting service recovery monitoring...")
        self.monitoring_task = asyncio.create_task(self._recovery_monitoring_loop())
    
    async def _recovery_monitoring_loop(self):
        """Background loop to monitor service recovery."""
        try:
            while True:
                await asyncio.sleep(self.service_check_interval)
                
                # Reassess service availability
                previous_degradation = self.current_degradation
                new_degradation = await self.assess_service_availability()
                
                # Check if degradation level improved
                if (previous_degradation and 
                    new_degradation.level != previous_degradation.level and
                    self._is_degradation_improved(previous_degradation.level, new_degradation.level)):
                    
                    self.logger.info(f" CELEBRATION:  Service recovery detected: {previous_degradation.level.value} -> {new_degradation.level.value}")
                    
                    # Wait for stabilization
                    await asyncio.sleep(self.recovery_stabilization_time)
                    
                    # Re-check to ensure recovery is stable
                    stable_degradation = await self.assess_service_availability()
                    if stable_degradation.level == new_degradation.level:
                        await self._handle_service_recovery(previous_degradation, stable_degradation)
                    else:
                        self.logger.warning("Service recovery unstable, continuing monitoring")
                
        except asyncio.CancelledError:
            self.logger.info("Recovery monitoring stopped")
        except Exception as e:
            self.logger.error(f"Recovery monitoring error: {e}")
    
    def _is_degradation_improved(self, old_level: DegradationLevel, new_level: DegradationLevel) -> bool:
        """Check if degradation level has improved."""
        level_order = [
            DegradationLevel.EMERGENCY,
            DegradationLevel.SEVERE,
            DegradationLevel.MODERATE,
            DegradationLevel.MINIMAL,
            DegradationLevel.NONE
        ]
        
        old_index = level_order.index(old_level)
        new_index = level_order.index(new_level)
        return new_index > old_index
    
    async def _handle_service_recovery(self, old_degradation: DegradationContext, new_degradation: DegradationContext):
        """Handle transition from degraded to recovered state."""
        self.logger.info(f" PASS:  Service recovery confirmed: {old_degradation.level.value} -> {new_degradation.level.value}")
        
        # Notify user of recovery
        recovery_notification = create_server_message(
            MessageType.SYSTEM_MESSAGE,
            {
                "event": "service_recovery",
                "old_degradation": old_degradation.to_dict(),
                "new_degradation": new_degradation.to_dict(),
                "recovered_services": [s for s in old_degradation.degraded_services if s in new_degradation.available_services],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        await safe_websocket_send(self.websocket, recovery_notification.model_dump())
        
        # Execute recovery callbacks
        for callback in self.recovery_callbacks:
            try:
                await callback(old_degradation, new_degradation)
            except Exception as e:
                self.logger.error(f"Recovery callback error: {e}")
        
        # If fully recovered, update fallback handler
        if new_degradation.level == DegradationLevel.NONE:
            self.logger.info(" CELEBRATION:  Full service recovery - stopping degradation monitoring")
            self.fallback_handler = None
            if self.monitoring_task:
                self.monitoring_task.cancel()
                self.monitoring_task = None
    
    def register_recovery_callback(self, callback: Callable):
        """Register callback to be called when services recover."""
        self.recovery_callbacks.append(callback)
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            self.monitoring_task = None
        
        self.recovery_callbacks.clear()
        self.service_health.clear()
        self.logger.info("Graceful degradation manager cleaned up")


async def create_graceful_degradation_manager(websocket, app_state) -> GracefulDegradationManager:
    """
    Create and initialize graceful degradation manager.
    
    Args:
        websocket: WebSocket connection
        app_state: Application state containing services
        
    Returns:
        GracefulDegradationManager: Initialized degradation manager
    """
    manager = GracefulDegradationManager(websocket, app_state)
    await manager.assess_service_availability()
    return manager