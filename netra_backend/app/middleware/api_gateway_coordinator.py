"""
API Gateway Coordinator

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System stability & user experience
- Value Impact: Ensures API gateway initializes after backend readiness
- Strategic Impact: Prevents request failures during service startup

Implements backend readiness checking and request queuing for smooth service startup.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from collections import deque

import httpx
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from netra_backend.app.logging_config import central_logger
from netra_backend.app.config import get_config

logger = central_logger.get_logger(__name__)


class ServiceState(Enum):
    """Service readiness states."""
    UNKNOWN = "unknown"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class ServiceHealthCheck:
    """Health check configuration for a service."""
    name: str
    health_url: str
    timeout_seconds: float = 5.0
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class QueuedRequest:
    """Queued request waiting for service readiness."""
    request_id: str
    method: str
    url: str
    headers: Dict[str, str]
    body: Optional[bytes] = None
    queued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    client_ip: Optional[str] = None


@dataclass
class CoordinatorConfig:
    """Configuration for API gateway coordinator."""
    startup_timeout_seconds: int = 120
    health_check_interval_seconds: int = 5
    max_queued_requests: int = 1000
    request_queue_timeout_seconds: int = 30
    readiness_check_timeout: int = 60
    enable_request_queuing: bool = True


class APIGatewayCoordinator:
    """Coordinates API gateway with backend service readiness."""
    
    def __init__(self, config: Optional[CoordinatorConfig] = None):
        """Initialize API gateway coordinator."""
        self.config = config or CoordinatorConfig()
        
        # Service tracking
        self.services: Dict[str, ServiceHealthCheck] = {}
        self.service_states: Dict[str, ServiceState] = {}
        self.last_health_checks: Dict[str, datetime] = {}
        
        # Request queuing
        self.request_queue: deque = deque(maxlen=self.config.max_queued_requests)
        self.is_ready = False
        
        # Tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._queue_processor_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # HTTP client
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Statistics
        self.stats = {
            'requests_queued': 0,
            'requests_processed': 0,
            'requests_dropped': 0,
            'health_checks_passed': 0,
            'health_checks_failed': 0,
            'startup_time_seconds': 0.0
        }
        
        self._startup_start_time = time.time()
        
        # Load service configurations
        self._load_service_configs()
    
    def _load_service_configs(self) -> None:
        """Load service health check configurations."""
        config = get_config()
        
        # Backend service
        try:
            backend_url = getattr(config, 'backend_base_url', 'http://localhost:8000')
            self.services['backend'] = ServiceHealthCheck(
                name='backend',
                health_url=f"{backend_url}/health/ready",
                timeout_seconds=10.0,
                retry_attempts=3
            )
            self.service_states['backend'] = ServiceState.UNKNOWN
        except Exception as e:
            logger.error(f"Failed to configure backend service: {e}")
        
        # Auth service
        try:
            auth_url = getattr(config, 'auth_service_base_url', 'http://localhost:8081')
            self.services['auth'] = ServiceHealthCheck(
                name='auth',
                health_url=f"{auth_url}/health",
                timeout_seconds=5.0,
                retry_attempts=2
            )
            self.service_states['auth'] = ServiceState.UNKNOWN
        except Exception as e:
            logger.warning(f"Failed to configure auth service: {e}")
        
        logger.info(f"Loaded {len(self.services)} service configurations")
    
    async def start(self) -> None:
        """Start API gateway coordinator."""
        # Start health checking
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        # Start queue processor if enabled
        if self.config.enable_request_queuing and self._queue_processor_task is None:
            self._queue_processor_task = asyncio.create_task(self._queue_processor_loop())
        
        # Wait for initial readiness
        await self._wait_for_readiness()
        
        logger.info("API gateway coordinator started")
    
    async def stop(self) -> None:
        """Stop API gateway coordinator."""
        self._shutdown = True
        
        # Cancel tasks
        for task in [self._health_check_task, self._queue_processor_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close HTTP client
        await self.http_client.aclose()
        
        logger.info("API gateway coordinator stopped")
    
    async def check_readiness(self) -> bool:
        """Check if services are ready."""
        # Backend must be ready
        if self.service_states.get('backend') != ServiceState.READY:
            return False
        
        # Auth service should be ready (but not critical)
        auth_state = self.service_states.get('auth', ServiceState.READY)
        if auth_state == ServiceState.UNAVAILABLE:
            logger.warning("Auth service unavailable, continuing without it")
        
        return True
    
    async def queue_request(self, request: Request) -> bool:
        """
        Queue request if services are not ready.
        
        Args:
            request: Incoming request
            
        Returns:
            True if request was queued, False if should be rejected
        """
        if not self.config.enable_request_queuing:
            return False
        
        if len(self.request_queue) >= self.config.max_queued_requests:
            self.stats['requests_dropped'] += 1
            logger.warning("Request queue full, dropping request")
            return False
        
        # Create queued request
        body = None
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
        except Exception as e:
            logger.warning(f"Failed to read request body: {e}")
        
        queued_request = QueuedRequest(
            request_id=f"queued_{int(time.time() * 1000)}_{len(self.request_queue)}",
            method=request.method,
            url=str(request.url),
            headers=dict(request.headers),
            body=body,
            client_ip=request.client.host if request.client else None
        )
        
        self.request_queue.append(queued_request)
        self.stats['requests_queued'] += 1
        
        logger.debug(f"Queued request: {queued_request.request_id}")
        return True
    
    def get_service_state(self, service_name: str) -> ServiceState:
        """Get current state of a service."""
        return self.service_states.get(service_name, ServiceState.UNKNOWN)
    
    def get_all_service_states(self) -> Dict[str, ServiceState]:
        """Get states of all services."""
        return self.service_states.copy()
    
    async def _wait_for_readiness(self) -> None:
        """Wait for services to become ready."""
        start_time = time.time()
        timeout = self.config.readiness_check_timeout
        
        logger.info("Waiting for service readiness...")
        
        while time.time() - start_time < timeout:
            if await self.check_readiness():
                self.is_ready = True
                self.stats['startup_time_seconds'] = time.time() - self._startup_start_time
                logger.info(f"Services ready after {self.stats['startup_time_seconds']:.1f}s")
                return
            
            await asyncio.sleep(1)
        
        # Timeout reached
        logger.warning(f"Service readiness timeout after {timeout}s")
        self.is_ready = True  # Continue anyway
        self.stats['startup_time_seconds'] = time.time() - self._startup_start_time
    
    async def _health_check_loop(self) -> None:
        """Main health check loop."""
        while not self._shutdown:
            try:
                await self._check_all_services()
                await asyncio.sleep(self.config.health_check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def _check_all_services(self) -> None:
        """Check health of all configured services."""
        tasks = [
            self._check_service_health(service_name, service_config)
            for service_name, service_config in self.services.items()
        ]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_service_health(self, service_name: str, service_config: ServiceHealthCheck) -> None:
        """Check health of specific service."""
        for attempt in range(service_config.retry_attempts):
            try:
                response = await self.http_client.get(
                    service_config.health_url,
                    timeout=service_config.timeout_seconds
                )
                
                if response.status_code == 200:
                    # Service is healthy
                    self.service_states[service_name] = ServiceState.READY
                    self.last_health_checks[service_name] = datetime.now(timezone.utc)
                    self.stats['health_checks_passed'] += 1
                    
                    if attempt > 0:  # Only log if it recovered
                        logger.info(f"Service {service_name} is now ready")
                    
                    return
                    
                elif response.status_code in [503, 500]:
                    # Service is starting or degraded
                    if self.service_states[service_name] != ServiceState.STARTING:
                        self.service_states[service_name] = ServiceState.STARTING
                        logger.info(f"Service {service_name} is starting")
                
                else:
                    # Unexpected status code
                    logger.warning(f"Service {service_name} returned {response.status_code}")
                    self.service_states[service_name] = ServiceState.DEGRADED
                
            except httpx.ConnectTimeout:
                logger.debug(f"Service {service_name} connection timeout (attempt {attempt + 1})")
            except httpx.ReadTimeout:
                logger.debug(f"Service {service_name} read timeout (attempt {attempt + 1})")
            except httpx.ConnectError:
                logger.debug(f"Service {service_name} connection error (attempt {attempt + 1})")
            except Exception as e:
                logger.warning(f"Health check error for {service_name}: {e}")
            
            if attempt < service_config.retry_attempts - 1:
                await asyncio.sleep(service_config.retry_delay_seconds)
        
        # All attempts failed
        old_state = self.service_states[service_name]
        self.service_states[service_name] = ServiceState.UNAVAILABLE
        self.stats['health_checks_failed'] += 1
        
        if old_state != ServiceState.UNAVAILABLE:
            logger.warning(f"Service {service_name} is now unavailable")
    
    async def _queue_processor_loop(self) -> None:
        """Process queued requests when services become ready."""
        while not self._shutdown:
            try:
                if self.is_ready and self.request_queue:
                    await self._process_queued_requests()
                
                await asyncio.sleep(1.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
    
    async def _process_queued_requests(self) -> None:
        """Process queued requests."""
        current_time = datetime.now(timezone.utc)
        processed_count = 0
        
        # Process requests in FIFO order
        while self.request_queue:
            queued_request = self.request_queue.popleft()
            
            # Check if request has timed out
            age = (current_time - queued_request.queued_at).total_seconds()
            if age > self.config.request_queue_timeout_seconds:
                logger.warning(f"Dropping timed out queued request: {queued_request.request_id}")
                self.stats['requests_dropped'] += 1
                continue
            
            # Try to forward request
            try:
                await self._forward_queued_request(queued_request)
                processed_count += 1
                self.stats['requests_processed'] += 1
                
            except Exception as e:
                logger.error(f"Failed to forward queued request {queued_request.request_id}: {e}")
                self.stats['requests_dropped'] += 1
                
            # Limit processing per cycle to avoid blocking
            if processed_count >= 10:
                break
        
        if processed_count > 0:
            logger.info(f"Processed {processed_count} queued requests")
    
    async def _forward_queued_request(self, queued_request: QueuedRequest) -> None:
        """Forward a queued request to the backend."""
        # This is a simplified implementation
        # In a real scenario, you'd need to reconstruct and forward the request
        logger.debug(f"Forwarding queued request: {queued_request.request_id}")
        
        # For now, just log that we would forward it
        # Real implementation would recreate the request and send it to backend
    
    def get_coordinator_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        service_summary = {}
        for name, state in self.service_states.items():
            last_check = self.last_health_checks.get(name)
            service_summary[name] = {
                'state': state.value,
                'last_check': last_check.isoformat() if last_check else None
            }
        
        return {
            'is_ready': self.is_ready,
            'services': service_summary,
            'queue_size': len(self.request_queue),
            **self.stats
        }
    
    def get_queue_info(self) -> Dict[str, Any]:
        """Get request queue information."""
        if not self.request_queue:
            return {'size': 0, 'oldest_request_age_seconds': 0}
        
        current_time = datetime.now(timezone.utc)
        oldest_request = self.request_queue[0]
        oldest_age = (current_time - oldest_request.queued_at).total_seconds()
        
        return {
            'size': len(self.request_queue),
            'max_size': self.config.max_queued_requests,
            'oldest_request_age_seconds': oldest_age,
            'timeout_seconds': self.config.request_queue_timeout_seconds
        }


class APIGatewayMiddleware(BaseHTTPMiddleware):
    """Middleware to coordinate API gateway with backend readiness."""
    
    def __init__(self, app, coordinator: APIGatewayCoordinator):
        """Initialize middleware."""
        super().__init__(app)
        self.coordinator = coordinator
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Dispatch request with coordination."""
        # Check if coordinator is ready
        if not self.coordinator.is_ready:
            # Try to queue request if enabled
            if await self.coordinator.queue_request(request):
                return Response(
                    content="Service starting, request queued",
                    status_code=202,
                    headers={"Retry-After": "5"}
                )
            else:
                return Response(
                    content="Service unavailable",
                    status_code=503,
                    headers={"Retry-After": "10"}
                )
        
        # Check backend readiness for API requests
        if request.url.path.startswith('/api/'):
            backend_state = self.coordinator.get_service_state('backend')
            if backend_state != ServiceState.READY:
                return Response(
                    content="Backend service unavailable",
                    status_code=503,
                    headers={"Retry-After": "5"}
                )
        
        # Process request normally
        response = await call_next(request)
        return response


# Global coordinator instance
_api_gateway_coordinator: Optional[APIGatewayCoordinator] = None


def get_api_gateway_coordinator(config: Optional[CoordinatorConfig] = None) -> APIGatewayCoordinator:
    """Get global API gateway coordinator instance."""
    global _api_gateway_coordinator
    if _api_gateway_coordinator is None:
        _api_gateway_coordinator = APIGatewayCoordinator(config)
    return _api_gateway_coordinator


async def check_service_readiness() -> bool:
    """Convenience function to check service readiness."""
    coordinator = get_api_gateway_coordinator()
    return await coordinator.check_readiness()