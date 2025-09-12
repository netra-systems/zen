"""
Service Coordination System.

This module provides centralized coordination for service startup, dependency management,
and state tracking. Addresses issues identified in test_critical_cold_start_initialization.py
tests 6-10.

Business Value: Platform/Internal - Stability - Prevents service coordination failures
that cause production outages during system initialization.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from dev_launcher.dependency_manager import DependencyManager, ServiceDependency, DependencyType, setup_default_dependency_manager

logger = logging.getLogger(__name__)


class CoordinationState(Enum):
    """States of the service coordination process."""
    INITIALIZING = "initializing"
    DEPENDENCY_RESOLUTION = "dependency_resolution"
    SEQUENTIAL_STARTUP = "sequential_startup"
    PARALLEL_STARTUP = "parallel_startup"
    READINESS_VERIFICATION = "readiness_verification"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ServiceStartupResult:
    """Result of a service startup attempt."""
    service_name: str
    success: bool
    start_time: float
    end_time: float
    error_message: Optional[str] = None
    port: Optional[int] = None
    process_id: Optional[int] = None
    
    @property
    def duration(self) -> float:
        """Get startup duration in seconds."""
        return self.end_time - self.start_time


@dataclass
class CoordinationConfig:
    """Configuration for service coordination."""
    max_parallel_starts: int = 3
    dependency_timeout: int = 60
    readiness_timeout: int = 90
    startup_retry_count: int = 2
    enable_graceful_degradation: bool = True
    required_services: Set[str] = None
    optional_services: Set[str] = None
    
    def __post_init__(self):
        if self.required_services is None:
            self.required_services = {"database", "backend"}
        if self.optional_services is None:
            self.optional_services = {"redis", "auth", "frontend"}


class ServiceCoordinator:
    """
    Centralized service coordination system.
    
    Manages service startup order, dependency resolution, and state tracking
    to prevent the issues identified in cold start tests.
    """
    
    def __init__(self, config: CoordinationConfig = None):
        """Initialize service coordinator."""
        self.config = config or CoordinationConfig()
        self.dependency_manager = setup_default_dependency_manager()
        self.state = CoordinationState.INITIALIZING
        self.startup_results: Dict[str, ServiceStartupResult] = {}
        self.service_callbacks: Dict[str, Callable] = {}
        self.readiness_checkers: Dict[str, Callable] = {}
        self.port_reservations: Dict[str, int] = {}
        self.coordination_lock = asyncio.Lock()
        self.startup_futures: Dict[str, asyncio.Task] = {}
        
        logger.info(f"ServiceCoordinator initialized with config: "
                   f"required={self.config.required_services}, "
                   f"optional={self.config.optional_services}")
    
    def register_service(self, service_name: str, 
                        startup_callback: Callable,
                        readiness_checker: Callable,
                        dependencies: List[ServiceDependency] = None) -> None:
        """
        Register a service for coordination.
        
        Args:
            service_name: Name of the service
            startup_callback: Function to call to start the service
            readiness_checker: Function to check if service is ready
            dependencies: List of service dependencies
        """
        self.service_callbacks[service_name] = startup_callback
        self.readiness_checkers[service_name] = readiness_checker
        
        if dependencies:
            self.dependency_manager.add_service(service_name, dependencies)
        
        logger.info(f"Registered service {service_name} for coordination")
    
    def reserve_port(self, service_name: str, port: int) -> bool:
        """
        Reserve a port for a service to prevent conflicts.
        
        Args:
            service_name: Name of the service
            port: Port to reserve
            
        Returns:
            True if port was reserved successfully
        """
        if port in self.port_reservations.values():
            existing_service = next(s for s, p in self.port_reservations.items() if p == port)
            logger.warning(f"Port {port} already reserved by {existing_service}")
            return False
        
        self.port_reservations[service_name] = port
        logger.info(f"Reserved port {port} for service {service_name}")
        return True
    
    async def coordinate_startup(self, services: List[str] = None) -> bool:
        """
        Coordinate startup of all or specified services.
        
        Args:
            services: List of service names to start (None for all registered)
            
        Returns:
            True if all required services started successfully
        """
        async with self.coordination_lock:
            return await self._coordinate_startup_impl(services)
    
    async def _coordinate_startup_impl(self, services: List[str] = None) -> bool:
        """Internal implementation of startup coordination."""
        start_time = time.time()
        self.state = CoordinationState.DEPENDENCY_RESOLUTION
        
        try:
            # Determine which services to start
            if services is None:
                services = list(self.service_callbacks.keys())
            
            logger.info(f"Starting coordination for services: {services}")
            
            # Get startup order based on dependencies
            self.state = CoordinationState.DEPENDENCY_RESOLUTION
            startup_order = await self._resolve_startup_order(services)
            
            # Start services in dependency order
            self.state = CoordinationState.SEQUENTIAL_STARTUP
            success = await self._start_services_sequentially(startup_order)
            
            if success:
                # Verify all services are ready
                self.state = CoordinationState.READINESS_VERIFICATION
                success = await self._verify_all_ready(services)
            
            # Final state
            self.state = CoordinationState.COMPLETED if success else CoordinationState.FAILED
            
            elapsed = time.time() - start_time
            if success:
                logger.info(f"Service coordination completed successfully in {elapsed:.2f}s")
            else:
                logger.error(f"Service coordination failed after {elapsed:.2f}s")
            
            return success
            
        except Exception as e:
            self.state = CoordinationState.FAILED
            logger.error(f"Service coordination failed with exception: {e}")
            return False
    
    async def _resolve_startup_order(self, services: List[str]) -> List[str]:
        """
        Resolve the order in which services should be started.
        
        Args:
            services: List of services to order
            
        Returns:
            Ordered list of services based on dependencies
        """
        try:
            # Get full topological order
            full_order = self.dependency_manager.get_startup_order()
            
            # Filter to only requested services while preserving order
            ordered_services = [s for s in full_order if s in services]
            
            # Add any services not in dependency manager to the end
            remaining_services = set(services) - set(ordered_services)
            ordered_services.extend(sorted(remaining_services))
            
            logger.info(f"Resolved startup order: {'  ->  '.join(ordered_services)}")
            return ordered_services
            
        except ValueError as e:
            # Circular dependency detected
            logger.error(f"Cannot resolve startup order: {e}")
            # Fallback to simple order
            return sorted(services)
    
    async def _start_services_sequentially(self, services: List[str]) -> bool:
        """
        Start services sequentially, waiting for dependencies.
        
        Args:
            services: List of services in startup order
            
        Returns:
            True if all required services started successfully
        """
        required_failures = []
        optional_failures = []
        
        for service_name in services:
            success = await self._start_single_service(service_name)
            
            if not success:
                if service_name in self.config.required_services:
                    required_failures.append(service_name)
                    logger.error(f"Required service {service_name} failed to start")
                else:
                    optional_failures.append(service_name)
                    logger.warning(f"Optional service {service_name} failed to start")
        
        # Log results
        if optional_failures and self.config.enable_graceful_degradation:
            logger.warning(f"System running in degraded mode. Failed optional services: {optional_failures}")
        
        # Success if no required services failed
        success = len(required_failures) == 0
        
        if success:
            started_services = [s for s in services if s not in required_failures + optional_failures]
            logger.info(f"Successfully started services: {started_services}")
        
        return success
    
    async def _start_single_service(self, service_name: str) -> bool:
        """
        Start a single service with dependency checking.
        
        Args:
            service_name: Name of the service to start
            
        Returns:
            True if service started successfully
        """
        logger.info(f"Starting service: {service_name}")
        start_time = time.time()
        
        try:
            # Mark service as starting
            await self.dependency_manager.mark_service_starting(service_name)
            
            # Wait for dependencies
            logger.debug(f"Waiting for dependencies of {service_name}")
            dependencies_ready = await self.dependency_manager.wait_for_dependencies(service_name)
            
            if not dependencies_ready:
                logger.error(f"Dependencies not ready for {service_name}")
                await self.dependency_manager.mark_service_failed(service_name, "Dependencies not ready")
                return self._record_startup_failure(service_name, start_time, "Dependencies not ready")
            
            # Check port availability if reserved
            if service_name in self.port_reservations:
                port = self.port_reservations[service_name]
                if not await self._check_port_available(port):
                    logger.error(f"Reserved port {port} not available for {service_name}")
                    return self._record_startup_failure(service_name, start_time, f"Port {port} not available")
            
            # Call service startup callback
            if service_name not in self.service_callbacks:
                logger.error(f"No startup callback registered for {service_name}")
                return self._record_startup_failure(service_name, start_time, "No startup callback")
            
            callback = self.service_callbacks[service_name]
            startup_result = await self._call_startup_callback(callback, service_name)
            
            if not startup_result:
                logger.error(f"Startup callback failed for {service_name}")
                await self.dependency_manager.mark_service_failed(service_name, "Startup callback failed")
                return self._record_startup_failure(service_name, start_time, "Startup callback failed")
            
            # Wait for service to be ready
            ready = await self._wait_for_service_ready(service_name)
            
            if ready:
                await self.dependency_manager.mark_service_ready(service_name)
                self._record_startup_success(service_name, start_time, startup_result)
                return True
            else:
                await self.dependency_manager.mark_service_failed(service_name, "Readiness check failed")
                return self._record_startup_failure(service_name, start_time, "Readiness check failed")
                
        except Exception as e:
            logger.error(f"Exception starting service {service_name}: {e}")
            await self.dependency_manager.mark_service_failed(service_name, str(e))
            return self._record_startup_failure(service_name, start_time, str(e))
    
    async def _call_startup_callback(self, callback: Callable, service_name: str) -> Any:
        """Call service startup callback safely."""
        try:
            # Handle both sync and async callbacks
            if asyncio.iscoroutinefunction(callback):
                return await callback()
            else:
                return callback()
        except Exception as e:
            logger.error(f"Startup callback exception for {service_name}: {e}")
            return None
    
    async def _wait_for_service_ready(self, service_name: str) -> bool:
        """
        Wait for a service to be ready using its readiness checker.
        
        Args:
            service_name: Name of the service to wait for
            
        Returns:
            True if service became ready within timeout
        """
        if service_name not in self.readiness_checkers:
            logger.warning(f"No readiness checker for {service_name}, assuming ready")
            return True
        
        checker = self.readiness_checkers[service_name]
        timeout = self.config.readiness_timeout
        start_time = time.time()
        check_interval = 1.0
        
        logger.debug(f"Waiting for {service_name} to be ready (timeout: {timeout}s)")
        
        while (time.time() - start_time) < timeout:
            try:
                # Call readiness checker
                if asyncio.iscoroutinefunction(checker):
                    ready = await checker()
                else:
                    ready = checker()
                
                if ready:
                    elapsed = time.time() - start_time
                    logger.info(f"Service {service_name} ready after {elapsed:.2f}s")
                    return True
                
                await asyncio.sleep(check_interval)
                # Increase interval progressively
                check_interval = min(check_interval * 1.1, 3.0)
                
            except Exception as e:
                logger.warning(f"Readiness check error for {service_name}: {e}")
                await asyncio.sleep(check_interval)
        
        elapsed = time.time() - start_time
        logger.error(f"Service {service_name} not ready after {elapsed:.2f}s timeout")
        return False
    
    async def _check_port_available(self, port: int) -> bool:
        """Check if a port is available for binding."""
        import socket
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('127.0.0.1', port))
                return True
        except OSError:
            return False
    
    def _record_startup_success(self, service_name: str, start_time: float, result: Any) -> None:
        """Record successful service startup."""
        end_time = time.time()
        
        # Extract port and process info if available
        port = None
        process_id = None
        
        if isinstance(result, dict):
            port = result.get('port')
            process_id = result.get('process_id')
        elif hasattr(result, '__iter__') and len(result) >= 2:
            # Assume (process, streamer) tuple format
            process, _ = result[:2]
            if hasattr(process, 'pid'):
                process_id = process.pid
        
        self.startup_results[service_name] = ServiceStartupResult(
            service_name=service_name,
            success=True,
            start_time=start_time,
            end_time=end_time,
            port=port,
            process_id=process_id
        )
    
    def _record_startup_failure(self, service_name: str, start_time: float, error_message: str) -> bool:
        """Record failed service startup and return False."""
        end_time = time.time()
        
        self.startup_results[service_name] = ServiceStartupResult(
            service_name=service_name,
            success=False,
            start_time=start_time,
            end_time=end_time,
            error_message=error_message
        )
        return False
    
    async def _verify_all_ready(self, services: List[str]) -> bool:
        """
        Verify that all required services are ready.
        
        Args:
            services: List of services to verify
            
        Returns:
            True if all required services are ready
        """
        logger.info("Performing final readiness verification")
        
        verification_tasks = []
        for service_name in services:
            if service_name in self.config.required_services:
                task = self._verify_service_ready(service_name)
                verification_tasks.append((service_name, task))
        
        # Wait for all verifications
        results = []
        for service_name, task in verification_tasks:
            try:
                ready = await task
                results.append((service_name, ready))
            except Exception as e:
                logger.error(f"Readiness verification failed for {service_name}: {e}")
                results.append((service_name, False))
        
        # Check results
        failed_services = [name for name, ready in results if not ready]
        
        if failed_services:
            logger.error(f"Required services not ready: {failed_services}")
            return False
        
        ready_services = [name for name, ready in results if ready]
        logger.info(f"All required services ready: {ready_services}")
        return True
    
    async def _verify_service_ready(self, service_name: str) -> bool:
        """Verify a single service is ready."""
        if service_name not in self.readiness_checkers:
            return True  # Assume ready if no checker
        
        try:
            checker = self.readiness_checkers[service_name]
            if asyncio.iscoroutinefunction(checker):
                return await checker()
            else:
                return checker()
        except Exception as e:
            logger.error(f"Readiness verification error for {service_name}: {e}")
            return False
    
    def get_startup_status(self) -> Dict[str, Any]:
        """Get comprehensive startup status."""
        status = {
            "coordination_state": self.state.value,
            "services": {},
            "summary": {
                "total_services": len(self.service_callbacks),
                "started_services": len([r for r in self.startup_results.values() if r.success]),
                "failed_services": len([r for r in self.startup_results.values() if not r.success]),
                "required_services_ready": 0,
                "optional_services_ready": 0
            }
        }
        
        # Service details
        for service_name, result in self.startup_results.items():
            dep_state = self.dependency_manager.get_service_state(service_name)
            
            service_status = {
                "startup_success": result.success,
                "dependency_state": dep_state,
                "startup_time": result.duration,
                "error_message": result.error_message,
                "port": result.port,
                "process_id": result.process_id,
                "is_required": service_name in self.config.required_services
            }
            
            status["services"][service_name] = service_status
            
            # Update summary
            if result.success and dep_state == "ready":
                if service_name in self.config.required_services:
                    status["summary"]["required_services_ready"] += 1
                else:
                    status["summary"]["optional_services_ready"] += 1
        
        # Add dependency status
        status["dependencies"] = self.dependency_manager.get_dependency_status()
        
        return status
    
    def is_healthy(self) -> bool:
        """
        Check if the coordinated system is healthy.
        
        Returns:
            True if all required services are running and ready
        """
        if self.state != CoordinationState.COMPLETED:
            return False
        
        # Check that all required services are ready
        for service_name in self.config.required_services:
            if service_name not in self.startup_results:
                return False
            
            result = self.startup_results[service_name]
            if not result.success:
                return False
            
            dep_state = self.dependency_manager.get_service_state(service_name)
            if dep_state != "ready":
                return False
        
        return True
    
    def get_degraded_services(self) -> List[str]:
        """Get list of optional services that failed to start."""
        degraded = []
        
        for service_name in self.config.optional_services:
            if service_name in self.startup_results:
                result = self.startup_results[service_name]
                if not result.success:
                    degraded.append(service_name)
            else:
                # Service not started
                degraded.append(service_name)
        
        return degraded
    
    def reset(self) -> None:
        """Reset coordinator state for fresh startup."""
        self.state = CoordinationState.INITIALIZING
        self.startup_results.clear()
        self.dependency_manager.reset_all_states()
        
        # Cancel any running startup tasks
        for task in self.startup_futures.values():
            if not task.done():
                task.cancel()
        self.startup_futures.clear()
        
        logger.info("Service coordinator reset")