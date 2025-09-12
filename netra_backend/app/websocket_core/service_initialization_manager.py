"""
ServiceInitializationManager - SSOT singleton for WebSocket service initialization.

This module eliminates the fallback handler anti-pattern by providing proper
SSOT service initialization that follows existing startup patterns from smd.py.

CRITICAL: This replaces the dumb fallback handler creation with authentic 
service initialization that ensures users NEVER receive mock responses.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass
from threading import Lock

from fastapi import FastAPI

from netra_backend.app.logging_config import central_logger


class InitializationState(Enum):
    """Service initialization states."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ServiceInitializationStatus:
    """Status information for a service initialization."""
    service_name: str
    state: InitializationState
    start_time: Optional[float] = None
    completion_time: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    @property
    def elapsed_time(self) -> Optional[float]:
        """Get elapsed time for the initialization."""
        if self.start_time is None:
            return None
        end_time = self.completion_time or time.time()
        return end_time - self.start_time
    
    @property
    def is_complete(self) -> bool:
        """Check if initialization is complete (success or failure)."""
        return self.state in [InitializationState.COMPLETED, InitializationState.FAILED]
    
    @property
    def can_retry(self) -> bool:
        """Check if service can be retried."""
        return self.state == InitializationState.FAILED and self.retry_count < self.max_retries


class ServiceInitializationManager:
    """
    SSOT singleton manager for WebSocket service initialization.
    
    This manager eliminates fallback handler creation by providing proper
    service initialization following Phase 5 patterns from smd.py.
    
    Key Features:
    - Singleton pattern with thread safety
    - Initialization locks to prevent duplicate work
    - Progress tracking for transparent user experience
    - Concurrent safety for multiple WebSocket connections
    - SSOT compliance with existing startup patterns
    """
    
    _instance: Optional['ServiceInitializationManager'] = None
    _instance_lock = Lock()
    
    def __new__(cls, app: Optional[FastAPI] = None) -> 'ServiceInitializationManager':
        """Ensure singleton with thread safety."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super(ServiceInitializationManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, app: Optional[FastAPI] = None):
        """Initialize the service initialization manager."""
        if self._initialized:
            return
            
        self.app = app
        self.logger = central_logger.get_logger(__name__)
        
        # Initialization state tracking
        self.services_status: Dict[str, ServiceInitializationStatus] = {}
        self.initialization_locks: Dict[str, asyncio.Lock] = {}
        self.global_initialization_lock = asyncio.Lock()
        
        # Progress tracking
        self.initialization_start_time: Optional[float] = None
        self.initialization_complete: bool = False
        self.initialization_failed: bool = False
        self.initialization_error: Optional[str] = None
        
        # Critical services that must be initialized for WebSocket functionality
        self.critical_services = {
            'agent_supervisor',
            'thread_service', 
            'agent_websocket_bridge',
            'tool_classes'
        }
        
        self._initialized = True
        self.logger.info("[U+2713] ServiceInitializationManager singleton created")
    
    def get_app(self) -> Optional[FastAPI]:
        """Get the FastAPI app instance."""
        return self.app
    
    def set_app(self, app: FastAPI) -> None:
        """Set the FastAPI app instance."""
        self.app = app
        self.logger.info("[U+2713] ServiceInitializationManager app instance set")
    
    async def initialize_missing_services(
        self, 
        missing_services: Set[str],
        max_initialization_time: float = 30.0
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Initialize missing services using SSOT patterns.
        
        Args:
            missing_services: Set of service names that need initialization
            max_initialization_time: Maximum time to wait for initialization
            
        Returns:
            Tuple of (success, status_report)
        """
        if not self.app:
            error_msg = "FastAPI app not set - cannot initialize services"
            self.logger.error(f" ALERT:  {error_msg}")
            return False, {'error': error_msg}
        
        self.logger.info(f" CYCLE:  Starting SSOT service initialization for: {missing_services}")
        
        async with self.global_initialization_lock:
            # Check if already initialized
            if self.initialization_complete:
                self.logger.info("[U+2713] Services already initialized - skipping")
                return True, {'status': 'already_complete', 'services': list(missing_services)}
            
            # Start initialization
            self.initialization_start_time = time.time()
            self.initialization_failed = False
            self.initialization_error = None
            
            try:
                # Initialize each missing service
                success_count = 0
                failed_services = []
                
                for service_name in missing_services:
                    if service_name not in self.critical_services:
                        self.logger.warning(f" WARNING: [U+FE0F] Service '{service_name}' not in critical services list")
                    
                    success = await self._initialize_single_service(service_name)
                    if success:
                        success_count += 1
                        self.logger.info(f"[U+2713] Service '{service_name}' initialized successfully")
                    else:
                        failed_services.append(service_name)
                        self.logger.error(f" FAIL:  Service '{service_name}' initialization failed")
                
                # Check overall success
                total_time = time.time() - self.initialization_start_time
                if failed_services:
                    self.initialization_failed = True
                    self.initialization_error = f"Failed to initialize: {failed_services}"
                    
                    # Check if any critical services failed
                    critical_failures = [s for s in failed_services if s in self.critical_services]
                    if critical_failures:
                        error_msg = f"CRITICAL service initialization failed: {critical_failures}"
                        self.logger.error(f" ALERT:  {error_msg}")
                        return False, {
                            'error': error_msg,
                            'failed_services': failed_services,
                            'successful_services': success_count,
                            'total_time': total_time
                        }
                
                # Success
                self.initialization_complete = True
                self.logger.info(f" PASS:  Service initialization complete: {success_count}/{len(missing_services)} in {total_time:.2f}s")
                
                return True, {
                    'status': 'success',
                    'successful_services': success_count,
                    'failed_services': failed_services,
                    'total_time': total_time,
                    'services_initialized': list(missing_services - set(failed_services))
                }
                
            except Exception as e:
                total_time = time.time() - (self.initialization_start_time or time.time())
                self.initialization_failed = True
                self.initialization_error = str(e)
                
                error_msg = f"Service initialization exception: {e}"
                self.logger.error(f" ALERT:  {error_msg}", exc_info=True)
                
                return False, {
                    'error': error_msg,
                    'exception': str(e),
                    'total_time': total_time
                }
    
    async def _initialize_single_service(self, service_name: str) -> bool:
        """
        Initialize a single service with proper locking and error handling.
        
        Args:
            service_name: Name of the service to initialize
            
        Returns:
            True if successful, False otherwise
        """
        # Get or create lock for this service
        if service_name not in self.initialization_locks:
            self.initialization_locks[service_name] = asyncio.Lock()
        
        async with self.initialization_locks[service_name]:
            # Check if already initialized
            if hasattr(self.app.state, service_name) and getattr(self.app.state, service_name) is not None:
                self.logger.info(f"[U+2713] Service '{service_name}' already initialized")
                return True
            
            # Update status
            status = ServiceInitializationStatus(
                service_name=service_name,
                state=InitializationState.IN_PROGRESS,
                start_time=time.time()
            )
            self.services_status[service_name] = status
            
            try:
                # Import SSOT service initializer
                from netra_backend.app.websocket_core.ssot_service_initializer import initialize_service_ssot
                
                # Initialize service using SSOT patterns
                success = await initialize_service_ssot(self.app, service_name)
                
                if success:
                    status.state = InitializationState.COMPLETED
                    status.completion_time = time.time()
                    self.logger.info(f" PASS:  Service '{service_name}' initialized in {status.elapsed_time:.2f}s")
                    return True
                else:
                    status.state = InitializationState.FAILED
                    status.completion_time = time.time()
                    status.error_message = f"SSOT initialization returned False"
                    self.logger.error(f" FAIL:  Service '{service_name}' SSOT initialization failed")
                    return False
                    
            except Exception as e:
                status.state = InitializationState.FAILED
                status.completion_time = time.time()
                status.error_message = str(e)
                
                self.logger.error(f" FAIL:  Service '{service_name}' initialization exception: {e}", exc_info=True)
                return False
    
    def get_initialization_status(self) -> Dict[str, Any]:
        """
        Get current initialization status for progress reporting.
        
        Returns:
            Dictionary with initialization status information
        """
        total_elapsed = None
        if self.initialization_start_time:
            total_elapsed = time.time() - self.initialization_start_time
        
        return {
            'initialization_complete': self.initialization_complete,
            'initialization_failed': self.initialization_failed,
            'initialization_error': self.initialization_error,
            'total_elapsed_time': total_elapsed,
            'services_status': {
                name: {
                    'state': status.state.value,
                    'elapsed_time': status.elapsed_time,
                    'error_message': status.error_message,
                    'retry_count': status.retry_count
                }
                for name, status in self.services_status.items()
            }
        }
    
    def reset_initialization_state(self) -> None:
        """Reset initialization state for fresh start."""
        self.logger.info(" CYCLE:  Resetting service initialization state")
        
        self.services_status.clear()
        self.initialization_locks.clear()
        self.initialization_start_time = None
        self.initialization_complete = False
        self.initialization_failed = False
        self.initialization_error = None
        
        self.logger.info("[U+2713] Service initialization state reset complete")


# Global singleton access function
def get_service_initialization_manager(app: Optional[FastAPI] = None) -> ServiceInitializationManager:
    """
    Get the global ServiceInitializationManager singleton.
    
    Args:
        app: Optional FastAPI app instance
        
    Returns:
        ServiceInitializationManager singleton instance
    """
    manager = ServiceInitializationManager(app)
    if app and not manager.get_app():
        manager.set_app(app)
    return manager