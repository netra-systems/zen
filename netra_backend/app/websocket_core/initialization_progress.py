"""
WebSocket Initialization Progress Communications

This module provides transparent user experience during service initialization
by sending real-time progress updates via WebSocket connections.

CRITICAL: This ensures users understand what's happening when services are
being initialized instead of receiving fallback handlers or timeouts.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
from fastapi import WebSocket

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.utils import safe_websocket_send


class InitializationProgressEvent(Enum):
    """WebSocket events for initialization progress."""
    INITIALIZATION_STARTED = "initialization_started"
    SERVICE_INITIALIZING = "service_initializing"
    SERVICE_COMPLETED = "service_completed"
    SERVICE_FAILED = "service_failed"
    INITIALIZATION_COMPLETED = "initialization_completed"
    INITIALIZATION_FAILED = "initialization_failed"
    INITIALIZATION_TIMEOUT = "initialization_timeout"


@dataclass
class ProgressMessage:
    """Progress message structure for WebSocket communication."""
    event: str
    message: str
    service_name: Optional[str] = None
    progress_percentage: Optional[int] = None
    elapsed_time: Optional[float] = None
    error_message: Optional[str] = None
    services_completed: Optional[List[str]] = None
    services_remaining: Optional[List[str]] = None
    total_services: Optional[int] = None
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class InitializationProgressCommunicator:
    """
    Handles WebSocket communication during service initialization.
    
    Provides transparent user experience by sending real-time progress updates
    while services are being initialized using SSOT patterns.
    """
    
    def __init__(self, websocket: Optional[WebSocket] = None):
        """
        Initialize progress communicator.
        
        Args:
            websocket: WebSocket connection for progress updates
        """
        self.websocket = websocket
        self.logger = central_logger.get_logger(__name__)
        
        # Progress tracking
        self.initialization_start_time: Optional[float] = None
        self.services_to_initialize: List[str] = []
        self.services_completed: List[str] = []
        self.services_failed: List[str] = []
        
        # Communication state
        self.communication_enabled = websocket is not None
        self.last_message_time: Optional[float] = None
        self.message_count = 0
    
    def set_websocket(self, websocket: WebSocket) -> None:
        """Set or update the WebSocket connection."""
        self.websocket = websocket
        self.communication_enabled = True
        self.logger.info("[U+2713] WebSocket connection set for progress communication")
    
    async def send_initialization_started(
        self, 
        services_to_initialize: List[str],
        estimated_time: Optional[float] = None
    ) -> None:
        """
        Send initialization started event.
        
        Args:
            services_to_initialize: List of services that will be initialized
            estimated_time: Estimated time for completion (optional)
        """
        self.initialization_start_time = time.time()
        self.services_to_initialize = services_to_initialize.copy()
        self.services_completed.clear()
        self.services_failed.clear()
        
        message = ProgressMessage(
            event=InitializationProgressEvent.INITIALIZATION_STARTED.value,
            message=f"Starting service initialization for WebSocket functionality...",
            total_services=len(services_to_initialize),
            services_remaining=services_to_initialize.copy(),
            progress_percentage=0
        )
        
        await self._send_progress_message(message)
        
        # Send detailed message about what's happening
        detail_message = ProgressMessage(
            event="system_message",
            message=(
                f" CYCLE:  Initializing {len(services_to_initialize)} critical services for AI functionality. "
                f"This ensures you receive authentic AI responses, not mock data. "
                f"Expected time: {estimated_time or 10}s"
            ),
            total_services=len(services_to_initialize)
        )
        await self._send_progress_message(detail_message)
        
        self.logger.info(f"[U+1F4E4] Sent initialization started event for {len(services_to_initialize)} services")
    
    async def send_service_initializing(self, service_name: str, step_number: Optional[int] = None) -> None:
        """
        Send service initialization in progress event.
        
        Args:
            service_name: Name of the service being initialized
            step_number: Optional step number for progress tracking
        """
        elapsed_time = self._get_elapsed_time()
        current_step = len(self.services_completed) + 1
        total_services = len(self.services_to_initialize)
        progress_percentage = int((current_step - 1) / total_services * 100) if total_services > 0 else 0
        
        # Create user-friendly service names
        friendly_names = {
            'agent_supervisor': 'AI Agent Supervisor',
            'thread_service': 'Conversation Thread Manager', 
            'agent_websocket_bridge': 'Real-time Communication Bridge',
            'tool_classes': 'AI Tool Configuration'
        }
        
        friendly_name = friendly_names.get(service_name, service_name.replace('_', ' ').title())
        
        message = ProgressMessage(
            event=InitializationProgressEvent.SERVICE_INITIALIZING.value,
            message=f" CYCLE:  Initializing {friendly_name}...",
            service_name=service_name,
            progress_percentage=progress_percentage,
            elapsed_time=elapsed_time,
            services_completed=self.services_completed.copy(),
            services_remaining=[s for s in self.services_to_initialize if s not in self.services_completed and s not in self.services_failed],
            total_services=total_services
        )
        
        await self._send_progress_message(message)
        self.logger.info(f"[U+1F4E4] Sent service initializing event: {service_name} ({progress_percentage}%)")
    
    async def send_service_completed(self, service_name: str, initialization_time: Optional[float] = None) -> None:
        """
        Send service initialization completed event.
        
        Args:
            service_name: Name of the service that completed
            initialization_time: Time taken for this service initialization
        """
        if service_name not in self.services_completed:
            self.services_completed.append(service_name)
        
        elapsed_time = self._get_elapsed_time()
        progress_percentage = int(len(self.services_completed) / len(self.services_to_initialize) * 100) if self.services_to_initialize else 100
        
        # Create user-friendly service names
        friendly_names = {
            'agent_supervisor': 'AI Agent Supervisor',
            'thread_service': 'Conversation Thread Manager',
            'agent_websocket_bridge': 'Real-time Communication Bridge',
            'tool_classes': 'AI Tool Configuration'
        }
        
        friendly_name = friendly_names.get(service_name, service_name.replace('_', ' ').title())
        
        message = ProgressMessage(
            event=InitializationProgressEvent.SERVICE_COMPLETED.value,
            message=f" PASS:  {friendly_name} initialized successfully" + (f" ({initialization_time:.1f}s)" if initialization_time else ""),
            service_name=service_name,
            progress_percentage=progress_percentage,
            elapsed_time=elapsed_time,
            services_completed=self.services_completed.copy(),
            services_remaining=[s for s in self.services_to_initialize if s not in self.services_completed and s not in self.services_failed],
            total_services=len(self.services_to_initialize)
        )
        
        await self._send_progress_message(message)
        self.logger.info(f"[U+1F4E4] Sent service completed event: {service_name} ({progress_percentage}%)")
    
    async def send_service_failed(
        self, 
        service_name: str, 
        error_message: str,
        can_retry: bool = False
    ) -> None:
        """
        Send service initialization failed event.
        
        Args:
            service_name: Name of the service that failed
            error_message: Error message describing the failure
            can_retry: Whether the service can be retried
        """
        if service_name not in self.services_failed:
            self.services_failed.append(service_name)
        
        elapsed_time = self._get_elapsed_time()
        
        # Create user-friendly service names
        friendly_names = {
            'agent_supervisor': 'AI Agent Supervisor',
            'thread_service': 'Conversation Thread Manager',
            'agent_websocket_bridge': 'Real-time Communication Bridge', 
            'tool_classes': 'AI Tool Configuration'
        }
        
        friendly_name = friendly_names.get(service_name, service_name.replace('_', ' ').title())
        
        retry_text = " (will retry)" if can_retry else ""
        
        message = ProgressMessage(
            event=InitializationProgressEvent.SERVICE_FAILED.value,
            message=f" FAIL:  {friendly_name} initialization failed{retry_text}",
            service_name=service_name,
            error_message=error_message,
            elapsed_time=elapsed_time,
            services_completed=self.services_completed.copy(),
            services_remaining=[s for s in self.services_to_initialize if s not in self.services_completed and s not in self.services_failed],
            total_services=len(self.services_to_initialize)
        )
        
        await self._send_progress_message(message)
        self.logger.error(f"[U+1F4E4] Sent service failed event: {service_name} - {error_message}")
    
    async def send_initialization_completed(
        self, 
        successful_services: List[str],
        failed_services: List[str],
        total_time: float
    ) -> None:
        """
        Send initialization completed event.
        
        Args:
            successful_services: List of services that initialized successfully
            failed_services: List of services that failed to initialize
            total_time: Total time taken for initialization
        """
        success_count = len(successful_services)
        total_count = len(self.services_to_initialize)
        
        if not failed_services:
            # Complete success
            message = ProgressMessage(
                event=InitializationProgressEvent.INITIALIZATION_COMPLETED.value,
                message=f" CELEBRATION:  All services initialized successfully! AI functionality is now fully available.",
                progress_percentage=100,
                elapsed_time=total_time,
                services_completed=successful_services.copy(),
                total_services=total_count
            )
        else:
            # Partial success
            message = ProgressMessage(
                event=InitializationProgressEvent.INITIALIZATION_COMPLETED.value,
                message=f" WARNING: [U+FE0F] Initialization completed with {success_count}/{total_count} services successful. Some functionality may be limited.",
                progress_percentage=int(success_count / total_count * 100) if total_count > 0 else 0,
                elapsed_time=total_time,
                services_completed=successful_services.copy(),
                total_services=total_count
            )
        
        await self._send_progress_message(message)
        
        # Send detailed status message
        if not failed_services:
            status_message = ProgressMessage(
                event="system_message",
                message=(
                    f" PASS:  Service initialization complete in {total_time:.1f}s. "
                    f"You can now send messages and receive authentic AI responses."
                )
            )
        else:
            status_message = ProgressMessage(
                event="system_message",
                message=(
                    f" WARNING: [U+FE0F] Partial initialization complete in {total_time:.1f}s. "
                    f"Successfully initialized: {', '.join(successful_services)}. "
                    f"Failed services: {', '.join(failed_services)}."
                )
            )
        
        await self._send_progress_message(status_message)
        
        self.logger.info(f"[U+1F4E4] Sent initialization completed event: {success_count}/{total_count} successful")
    
    async def send_initialization_failed(
        self, 
        error_message: str,
        failed_services: List[str],
        total_time: float
    ) -> None:
        """
        Send initialization completely failed event.
        
        Args:
            error_message: Overall error message
            failed_services: List of services that failed
            total_time: Total time spent attempting initialization
        """
        message = ProgressMessage(
            event=InitializationProgressEvent.INITIALIZATION_FAILED.value,
            message=" FAIL:  Service initialization failed - AI functionality unavailable",
            error_message=error_message,
            elapsed_time=total_time,
            services_completed=self.services_completed.copy(),
            total_services=len(self.services_to_initialize)
        )
        
        await self._send_progress_message(message)
        
        # Send detailed error message
        detail_message = ProgressMessage(
            event="system_message",
            message=(
                f" ALERT:  Critical service initialization failure after {total_time:.1f}s. "
                f"Failed services: {', '.join(failed_services)}. "
                f"Please try reconnecting or contact support if the issue persists. "
                f"Error: {error_message}"
            )
        )
        await self._send_progress_message(detail_message)
        
        self.logger.error(f"[U+1F4E4] Sent initialization failed event: {error_message}")
    
    async def send_timeout_warning(self, elapsed_time: float, max_time: float) -> None:
        """
        Send timeout warning event.
        
        Args:
            elapsed_time: Time already elapsed
            max_time: Maximum allowed time
        """
        remaining_time = max_time - elapsed_time
        
        message = ProgressMessage(
            event=InitializationProgressEvent.INITIALIZATION_TIMEOUT.value,
            message=f"[U+23F1][U+FE0F] Service initialization is taking longer than expected ({elapsed_time:.1f}s/{max_time:.1f}s)",
            elapsed_time=elapsed_time,
            services_completed=self.services_completed.copy(),
            services_remaining=[s for s in self.services_to_initialize if s not in self.services_completed and s not in self.services_failed],
            total_services=len(self.services_to_initialize)
        )
        
        await self._send_progress_message(message)
        
        # Send explanatory message
        detail_message = ProgressMessage(
            event="system_message",
            message=(
                f" CYCLE:  Initialization is taking longer than usual. "
                f"This may happen during high system load or when starting services for the first time. "
                f"We'll continue trying for {remaining_time:.0f} more seconds..."
            )
        )
        await self._send_progress_message(detail_message)
        
        self.logger.warning(f"[U+1F4E4] Sent timeout warning: {elapsed_time:.1f}s elapsed")
    
    async def _send_progress_message(self, message: ProgressMessage) -> None:
        """
        Send progress message via WebSocket.
        
        Args:
            message: Progress message to send
        """
        if not self.communication_enabled or not self.websocket:
            self.logger.debug(f"WebSocket communication disabled - skipping message: {message.event}")
            return
        
        try:
            # Convert dataclass to dict and clean up None values
            message_dict = {k: v for k, v in asdict(message).items() if v is not None}
            
            # Add metadata
            message_dict['message_type'] = 'initialization_progress'
            message_dict['message_id'] = f"init_progress_{self.message_count}"
            self.message_count += 1
            
            # Send via WebSocket
            await safe_websocket_send(self.websocket, message_dict)
            self.last_message_time = time.time()
            
            self.logger.debug(f"[U+1F4E4] Sent progress message: {message.event}")
            
        except Exception as e:
            self.logger.error(f" FAIL:  Failed to send progress message: {e}")
            # Don't fail the entire initialization due to communication issues
            self.communication_enabled = False
    
    def _get_elapsed_time(self) -> Optional[float]:
        """Get elapsed time since initialization started."""
        if self.initialization_start_time is None:
            return None
        return time.time() - self.initialization_start_time
    
    def get_progress_status(self) -> Dict[str, Any]:
        """
        Get current progress status.
        
        Returns:
            Dictionary with current progress information
        """
        elapsed_time = self._get_elapsed_time()
        total_services = len(self.services_to_initialize)
        completed_count = len(self.services_completed)
        failed_count = len(self.services_failed)
        
        return {
            'elapsed_time': elapsed_time,
            'progress_percentage': int(completed_count / total_services * 100) if total_services > 0 else 0,
            'services_total': total_services,
            'services_completed': completed_count,
            'services_failed': failed_count,
            'services_remaining': total_services - completed_count - failed_count,
            'services_completed_list': self.services_completed.copy(),
            'services_failed_list': self.services_failed.copy(),
            'communication_enabled': self.communication_enabled,
            'messages_sent': self.message_count
        }


# Utility functions for easy integration

async def create_progress_communicator(websocket: Optional[WebSocket] = None) -> InitializationProgressCommunicator:
    """
    Create a progress communicator for service initialization.
    
    Args:
        websocket: Optional WebSocket connection
        
    Returns:
        InitializationProgressCommunicator instance
    """
    return InitializationProgressCommunicator(websocket)


async def send_simple_progress_message(
    websocket: Optional[WebSocket],
    event: str,
    message: str,
    **kwargs
) -> None:
    """
    Send a simple progress message without creating a full communicator.
    
    Args:
        websocket: WebSocket connection
        event: Event type
        message: Message text
        **kwargs: Additional message parameters
    """
    if not websocket:
        return
    
    try:
        message_data = {
            'event': event,
            'message': message,
            'message_type': 'initialization_progress',
            'timestamp': time.time(),
            **kwargs
        }
        
        await safe_websocket_send(websocket, message_data)
        
    except Exception as e:
        logger = central_logger.get_logger(__name__)
        logger.error(f" FAIL:  Failed to send simple progress message: {e}")