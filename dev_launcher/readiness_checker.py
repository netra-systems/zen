"""
Service Readiness Checking System.

This module provides readiness checks separate from health checks as required
by the service coordination tests. Readiness checks determine if a service
is fully initialized and ready to serve traffic, while health checks monitor
ongoing operational status.

Business Value: Platform/Internal - Stability - Prevents false positive health
reports during service initialization by distinguishing readiness from liveness.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


class ReadinessState(Enum):
    """States of service readiness."""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing" 
    STARTING = "starting"
    READY = "ready"
    NOT_READY = "not_ready"
    FAILED = "failed"


@dataclass
class ReadinessCheck:
    """Definition of a readiness check."""
    name: str
    check_function: Callable[[], Union[bool, Dict[str, Any]]]
    timeout: float = 5.0
    retry_count: int = 3
    retry_delay: float = 1.0
    required: bool = True  # If False, failure won't mark service as not ready
    description: Optional[str] = None


@dataclass
class ReadinessResult:
    """Result of a readiness check."""
    check_name: str
    success: bool
    duration: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class ServiceReadinessStatus:
    """Overall readiness status of a service."""
    service_name: str
    state: ReadinessState
    overall_ready: bool
    check_results: List[ReadinessResult]
    last_check_time: float
    initialization_time: Optional[float] = None
    ready_time: Optional[float] = None
    failure_reason: Optional[str] = None
    
    @property
    def startup_duration(self) -> Optional[float]:
        """Get startup duration if ready."""
        if self.initialization_time and self.ready_time:
            return self.ready_time - self.initialization_time
        return None


class BaseReadinessChecker(ABC):
    """Base class for service readiness checkers."""
    
    @abstractmethod
    async def check_ready(self) -> bool:
        """Check if the service is ready."""
        pass
    
    @abstractmethod
    def get_service_name(self) -> str:
        """Get the service name."""
        pass


class ReadinessManager:
    """
    Manages readiness checks for multiple services.
    
    Provides centralized readiness checking with proper state management
    and distinction from health monitoring.
    """
    
    def __init__(self):
        """Initialize readiness manager."""
        self.services: Dict[str, Dict[str, ReadinessCheck]] = {}
        self.service_status: Dict[str, ServiceReadinessStatus] = {}
        self.checkers: Dict[str, BaseReadinessChecker] = {}
        self._lock = asyncio.Lock()
        
        logger.info("ReadinessManager initialized")
    
    def register_service(self, service_name: str, checks: List[ReadinessCheck] = None) -> None:
        """
        Register a service for readiness monitoring.
        
        Args:
            service_name: Name of the service
            checks: List of readiness checks for this service
        """
        if checks is None:
            checks = []
        
        self.services[service_name] = {check.name: check for check in checks}
        self.service_status[service_name] = ServiceReadinessStatus(
            service_name=service_name,
            state=ReadinessState.UNKNOWN,
            overall_ready=False,
            check_results=[],
            last_check_time=0
        )
        
        logger.info(f"Registered service {service_name} with {len(checks)} readiness checks")
        for check in checks:
            logger.debug(f"  → {check.name}: required={check.required}, timeout={check.timeout}s")
    
    def register_checker(self, service_name: str, checker: BaseReadinessChecker) -> None:
        """
        Register a custom readiness checker for a service.
        
        Args:
            service_name: Name of the service
            checker: Custom readiness checker implementation
        """
        self.checkers[service_name] = checker
        
        # Also register the service if not already registered
        if service_name not in self.services:
            self.register_service(service_name)
        
        logger.info(f"Registered custom readiness checker for {service_name}")
    
    async def mark_service_initializing(self, service_name: str) -> None:
        """Mark a service as starting initialization."""
        async with self._lock:
            if service_name in self.service_status:
                status = self.service_status[service_name]
                status.state = ReadinessState.INITIALIZING
                status.initialization_time = time.time()
                logger.info(f"Service {service_name} marked as initializing")
    
    async def mark_service_starting(self, service_name: str) -> None:
        """Mark a service as starting (post-initialization)."""
        async with self._lock:
            if service_name in self.service_status:
                status = self.service_status[service_name]
                status.state = ReadinessState.STARTING
                logger.info(f"Service {service_name} marked as starting")
    
    async def check_service_ready(self, service_name: str) -> bool:
        """
        Check if a specific service is ready.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            True if service is ready, False otherwise
        """
        if service_name not in self.services:
            logger.warning(f"Service {service_name} not registered for readiness checking")
            return False
        
        start_time = time.time()
        
        # Run all readiness checks for the service
        check_results = []
        
        # Use custom checker if available
        if service_name in self.checkers:
            try:
                checker = self.checkers[service_name]
                ready = await checker.check_ready()
                
                result = ReadinessResult(
                    check_name="custom_checker",
                    success=ready,
                    duration=time.time() - start_time
                )
                check_results.append(result)
                
            except Exception as e:
                logger.error(f"Custom readiness checker failed for {service_name}: {e}")
                result = ReadinessResult(
                    check_name="custom_checker",
                    success=False,
                    duration=time.time() - start_time,
                    error_message=str(e)
                )
                check_results.append(result)
        
        # Run individual readiness checks
        service_checks = self.services[service_name]
        for check_name, check in service_checks.items():
            result = await self._run_single_check(check)
            check_results.append(result)
        
        # Determine overall readiness
        overall_ready = await self._evaluate_readiness(service_name, check_results)
        
        # Update service status
        async with self._lock:
            status = self.service_status[service_name]
            status.check_results = check_results
            status.last_check_time = time.time()
            status.overall_ready = overall_ready
            
            if overall_ready and status.state != ReadinessState.READY:
                status.state = ReadinessState.READY
                status.ready_time = time.time()
                
                if status.startup_duration:
                    logger.info(f"Service {service_name} ready after {status.startup_duration:.2f}s")
                else:
                    logger.info(f"Service {service_name} ready")
                    
            elif not overall_ready and status.state != ReadinessState.NOT_READY:
                status.state = ReadinessState.NOT_READY
                
                # Find failure reasons
                failed_checks = [r for r in check_results if not r.success]
                if failed_checks:
                    failure_reasons = [f"{r.check_name}: {r.error_message or 'failed'}" 
                                     for r in failed_checks]
                    status.failure_reason = "; ".join(failure_reasons)
                    logger.warning(f"Service {service_name} not ready: {status.failure_reason}")
        
        return overall_ready
    
    async def _run_single_check(self, check: ReadinessCheck) -> ReadinessResult:
        """
        Run a single readiness check with retry logic.
        
        Args:
            check: The readiness check to run
            
        Returns:
            Result of the readiness check
        """
        start_time = time.time()
        last_error = None
        
        for attempt in range(check.retry_count + 1):
            try:
                # Call the check function
                if asyncio.iscoroutinefunction(check.check_function):
                    result = await asyncio.wait_for(check.check_function(), timeout=check.timeout)
                else:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(check.check_function), 
                        timeout=check.timeout
                    )
                
                # Handle different return types
                if isinstance(result, bool):
                    success = result
                    details = None
                elif isinstance(result, dict):
                    success = result.get('success', result.get('ready', False))
                    details = result
                else:
                    success = bool(result)
                    details = {"raw_result": result}
                
                if success:
                    return ReadinessResult(
                        check_name=check.name,
                        success=True,
                        duration=time.time() - start_time,
                        details=details
                    )
                
                # If not successful and this is not the last attempt, wait before retry
                if attempt < check.retry_count:
                    await asyncio.sleep(check.retry_delay * (attempt + 1))  # Exponential backoff
                
                last_error = "Check returned false/failed result"
                
            except asyncio.TimeoutError:
                last_error = f"Check timed out after {check.timeout}s"
                if attempt < check.retry_count:
                    await asyncio.sleep(check.retry_delay * (attempt + 1))
            except Exception as e:
                last_error = str(e)
                if attempt < check.retry_count:
                    await asyncio.sleep(check.retry_delay * (attempt + 1))
        
        # All attempts failed
        return ReadinessResult(
            check_name=check.name,
            success=False,
            duration=time.time() - start_time,
            error_message=last_error
        )
    
    async def _evaluate_readiness(self, service_name: str, check_results: List[ReadinessResult]) -> bool:
        """
        Evaluate overall readiness based on check results.
        
        Args:
            service_name: Name of the service
            check_results: Results of all readiness checks
            
        Returns:
            True if service is considered ready
        """
        if not check_results:
            # No checks means ready (for services with custom checkers only)
            return True
        
        service_checks = self.services[service_name]
        
        # Check required checks
        for result in check_results:
            if result.check_name in service_checks:
                check = service_checks[result.check_name]
                if check.required and not result.success:
                    logger.debug(f"Required check {result.check_name} failed for {service_name}")
                    return False
            elif result.check_name == "custom_checker":
                # Custom checker failure means not ready
                if not result.success:
                    logger.debug(f"Custom checker failed for {service_name}")
                    return False
        
        # All required checks passed
        return True
    
    async def wait_for_service_ready(self, service_name: str, timeout: float = 60.0, 
                                   check_interval: float = 1.0) -> bool:
        """
        Wait for a service to become ready.
        
        Args:
            service_name: Name of the service to wait for
            timeout: Maximum time to wait in seconds
            check_interval: Time between checks in seconds
            
        Returns:
            True if service became ready within timeout
        """
        start_time = time.time()
        
        logger.info(f"Waiting for service {service_name} to be ready (timeout: {timeout}s)")
        
        while (time.time() - start_time) < timeout:
            ready = await self.check_service_ready(service_name)
            if ready:
                elapsed = time.time() - start_time
                logger.info(f"Service {service_name} ready after {elapsed:.2f}s")
                return True
            
            await asyncio.sleep(check_interval)
        
        elapsed = time.time() - start_time
        logger.error(f"Service {service_name} not ready after {elapsed:.2f}s timeout")
        return False
    
    async def check_all_services_ready(self, services: List[str] = None) -> Dict[str, bool]:
        """
        Check readiness of multiple services.
        
        Args:
            services: List of service names to check (None for all)
            
        Returns:
            Dictionary mapping service names to readiness status
        """
        if services is None:
            services = list(self.services.keys())
        
        results = {}
        
        # Create tasks for concurrent checking
        tasks = []
        for service_name in services:
            task = asyncio.create_task(self.check_service_ready(service_name))
            tasks.append((service_name, task))
        
        # Wait for all tasks
        for service_name, task in tasks:
            try:
                ready = await task
                results[service_name] = ready
            except Exception as e:
                logger.error(f"Error checking readiness of {service_name}: {e}")
                results[service_name] = False
        
        return results
    
    def get_service_status(self, service_name: str) -> Optional[ServiceReadinessStatus]:
        """Get readiness status for a specific service."""
        return self.service_status.get(service_name)
    
    def get_all_service_status(self) -> Dict[str, ServiceReadinessStatus]:
        """Get readiness status for all services."""
        return self.service_status.copy()
    
    def is_service_ready(self, service_name: str) -> bool:
        """Check if a service is currently marked as ready (cached result)."""
        status = self.service_status.get(service_name)
        if not status:
            return False
        
        return status.overall_ready and status.state == ReadinessState.READY
    
    def get_ready_services(self) -> List[str]:
        """Get list of services that are currently ready."""
        ready_services = []
        for service_name, status in self.service_status.items():
            if status.overall_ready and status.state == ReadinessState.READY:
                ready_services.append(service_name)
        return ready_services
    
    def get_not_ready_services(self) -> List[str]:
        """Get list of services that are not ready."""
        not_ready_services = []
        for service_name, status in self.service_status.items():
            if not status.overall_ready or status.state != ReadinessState.READY:
                not_ready_services.append(service_name)
        return not_ready_services
    
    def clear_service_status(self, service_name: str) -> None:
        """Clear status for a service (reset to unknown)."""
        if service_name in self.service_status:
            status = self.service_status[service_name]
            status.state = ReadinessState.UNKNOWN
            status.overall_ready = False
            status.check_results = []
            status.last_check_time = 0
            status.ready_time = None
            status.failure_reason = None
            
            logger.info(f"Cleared readiness status for {service_name}")


# Predefined readiness check functions
async def http_endpoint_ready(url: str, expected_status: int = 200, timeout: float = 5.0) -> bool:
    """Check if an HTTP endpoint is ready."""
    try:
        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as response:
                return response.status == expected_status
    except Exception:
        return False


def port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is available (opposite of port_bound)."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            sock.bind((host, port))
            return True
    except OSError:
        return False


def port_bound(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is bound (service is listening)."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0  # 0 means connection successful
    except OSError:
        return False


def process_running(process) -> bool:
    """Check if a process is still running."""
    if hasattr(process, 'poll'):
        return process.poll() is None
    return False


# Predefined service-specific readiness checkers
class BackendReadinessChecker(BaseReadinessChecker):
    """Readiness checker for backend service."""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.health_url = f"http://localhost:{port}/health/ready"
    
    async def check_ready(self) -> bool:
        """Check if backend is ready using the /health/ready endpoint."""
        return await http_endpoint_ready(self.health_url)
    
    def get_service_name(self) -> str:
        return "backend"


class FrontendReadinessChecker(BaseReadinessChecker):
    """Readiness checker for frontend service."""
    
    def __init__(self, port: int = 3000):
        self.port = port
        self.url = f"http://localhost:{port}"
    
    async def check_ready(self) -> bool:
        """Check if frontend is ready."""
        # Frontend is ready if it responds to requests (200 or 404 acceptable)
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(self.url) as response:
                    return response.status in [200, 404]
        except Exception:
            return False
    
    def get_service_name(self) -> str:
        return "frontend"


class AuthServiceReadinessChecker(BaseReadinessChecker):
    """Readiness checker for auth service."""
    
    def __init__(self, port: int = 8081):
        self.port = port
        self.config_url = f"http://localhost:{port}/auth/config"
    
    async def check_ready(self) -> bool:
        """Check if auth service is ready using the /auth/config endpoint."""
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(self.config_url) as response:
                    return response.status in [200, 404]  # 404 is acceptable
        except Exception:
            return False
    
    def get_service_name(self) -> str:
        return "auth"


def create_standard_readiness_checks(service_name: str, port: int = None) -> List[ReadinessCheck]:
    """
    Create standard readiness checks for common services.
    
    Args:
        service_name: Name of the service
        port: Port the service runs on
        
    Returns:
        List of appropriate readiness checks
    """
    checks = []
    
    if service_name.lower() == "backend":
        port = port or 8000
        checks.append(ReadinessCheck(
            name="http_health",
            check_function=lambda: http_endpoint_ready(f"http://localhost:{port}/health/ready"),
            timeout=10.0,
            retry_count=3,
            description="Check backend health endpoint"
        ))
        
    elif service_name.lower() == "frontend":
        port = port or 3000
        checks.append(ReadinessCheck(
            name="http_response",
            check_function=lambda: http_endpoint_ready(f"http://localhost:{port}", expected_status=200),
            timeout=10.0,
            retry_count=2,
            description="Check frontend responds to requests"
        ))
        
    elif service_name.lower() == "auth":
        port = port or 8081
        checks.append(ReadinessCheck(
            name="auth_config",
            check_function=lambda: http_endpoint_ready(f"http://localhost:{port}/auth/config"),
            timeout=5.0,
            retry_count=2,
            description="Check auth service config endpoint"
        ))
    
    if port and checks:
        # Add port binding check for all services
        checks.append(ReadinessCheck(
            name="port_bound",
            check_function=lambda: port_bound(port),
            timeout=2.0,
            retry_count=1,
            required=True,
            description=f"Check service is listening on port {port}"
        ))
    
    return checks